import numpy as np
import trimesh
from terraprint3d.config.parser import Config


class MeshGenerator:
    def __init__(self, config: Config):
        self.config = config
    
    def generate_mesh(self, lat_grid: np.ndarray, lon_grid: np.ndarray, elevation_grid: np.ndarray) -> trimesh.Trimesh:
        """Generate 3D mesh from elevation data."""
        # Convert lat/lon to local coordinates (meters)
        x_grid, y_grid = self._latlon_to_meters(lat_grid, lon_grid)
        
        # Apply vertical exaggeration and convert to millimeters
        z_grid = elevation_grid * self.config.terrain.vertical_exaggeration
        
        # Normalize to fit printer bed
        x_grid_norm, y_grid_norm, z_grid_norm = self._normalize_to_printer_bed(x_grid, y_grid, z_grid)
        
        # Add base thickness
        z_grid_norm += self.config.terrain.base_thickness_mm
        
        # Generate vertices and faces
        vertices, faces = self._create_surface_mesh(x_grid_norm, y_grid_norm, z_grid_norm)
        
        # Store grid dimensions for base generation
        self._grid_rows, self._grid_cols = x_grid_norm.shape
        
        # Add base vertices and faces for 3D printing
        vertices, faces = self._add_base(vertices, faces)
        
        # Create trimesh object
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # Validate and fix mesh for 3D printing
        mesh = self._validate_and_fix_mesh(mesh)
        
        return mesh
    
    def _validate_and_fix_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Validate and fix mesh issues for 3D printing."""
        print(f"Initial mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        
        # Remove duplicate vertices and faces
        mesh.merge_vertices()
        mesh.remove_duplicate_faces()
        mesh.remove_degenerate_faces()
        
        print(f"After cleanup: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        
        # Check if mesh is watertight
        if not mesh.is_watertight:
            print("Warning: Mesh is not watertight, attempting to fix...")
            mesh.fill_holes()
            
            # If still not watertight, try convex hull as last resort
            if not mesh.is_watertight:
                print("Warning: Could not make mesh watertight with hole filling")
                # Could add convex hull here if needed: mesh = mesh.convex_hull
        else:
            print("✓ Mesh is watertight")
        
        # Check mesh orientation
        if not mesh.is_winding_consistent:
            print("Fixing face winding consistency...")
            mesh.fix_normals()
        
        return mesh
    
    def _latlon_to_meters(self, lat_grid: np.ndarray, lon_grid: np.ndarray) -> tuple:
        """Convert lat/lon to local meter coordinates."""
        # Use center as origin
        center_lat = np.mean(lat_grid)
        center_lon = np.mean(lon_grid)
        
        # Convert to meters using approximate conversion
        lat_to_meters = 111320.0  # meters per degree latitude
        lon_to_meters = 111320.0 * np.cos(np.radians(center_lat))  # meters per degree longitude
        
        x_grid = (lon_grid - center_lon) * lon_to_meters
        y_grid = (lat_grid - center_lat) * lat_to_meters
        
        return x_grid, y_grid
    
    def _normalize_to_printer_bed(self, x_grid: np.ndarray, y_grid: np.ndarray, z_grid: np.ndarray) -> tuple:
        """Scale coordinates to fit printer bed."""
        # Get dimensions
        x_range = np.max(x_grid) - np.min(x_grid)
        y_range = np.max(y_grid) - np.min(y_grid)
        z_range = np.max(z_grid) - np.min(z_grid)
        
        # Calculate scale factor to fit within printer bed (leaving 10mm margin)
        bed_size = self.config.output.printer_bed_mm - 20  # 10mm margin on each side
        scale_factor = min(bed_size / x_range, bed_size / y_range)
        
        # Scale coordinates to millimeters
        x_grid_norm = (x_grid - np.min(x_grid)) * scale_factor
        y_grid_norm = (y_grid - np.min(y_grid)) * scale_factor
        z_grid_norm = (z_grid - np.min(z_grid)) * scale_factor
        
        # Center on build plate
        x_offset = (self.config.output.printer_bed_mm - np.max(x_grid_norm)) / 2
        y_offset = (self.config.output.printer_bed_mm - np.max(y_grid_norm)) / 2
        
        x_grid_norm += x_offset
        y_grid_norm += y_offset
        
        return x_grid_norm, y_grid_norm, z_grid_norm
    
    def _create_surface_mesh(self, x_grid: np.ndarray, y_grid: np.ndarray, z_grid: np.ndarray) -> tuple:
        """Create surface mesh from grid data."""
        rows, cols = x_grid.shape
        vertices = []
        faces = []
        
        # Create vertices
        for i in range(rows):
            for j in range(cols):
                vertices.append([x_grid[i, j], y_grid[i, j], z_grid[i, j]])
        
        vertices = np.array(vertices)
        
        # Create faces (triangulate grid)
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Get vertex indices for current quad
                v1 = i * cols + j
                v2 = i * cols + (j + 1)
                v3 = (i + 1) * cols + j
                v4 = (i + 1) * cols + (j + 1)
                
                # Create two triangles for each quad
                faces.append([v1, v2, v3])
                faces.append([v2, v4, v3])
        
        return vertices, np.array(faces)
    
    def _add_base(self, vertices: np.ndarray, faces: np.ndarray) -> tuple:
        """Add base for 3D printing with proper wall topology."""
        surface_vertices = vertices.copy()
        
        # Create base vertices (set z to 0)
        base_vertices = surface_vertices.copy()
        base_vertices[:, 2] = 0
        
        # Combine vertices
        all_vertices = np.vstack([surface_vertices, base_vertices])
        
        # Use stored grid dimensions from surface mesh generation
        rows, cols = self._grid_rows, self._grid_cols
        
        # Get ordered boundary vertices (perimeter of the grid)
        boundary_indices = self._get_ordered_boundary_indices(rows, cols)
        
        # Create side wall faces
        side_faces = []
        for i in range(len(boundary_indices)):
            next_i = (i + 1) % len(boundary_indices)
            
            # Surface vertices
            v1 = boundary_indices[i]
            v2 = boundary_indices[next_i]
            
            # Corresponding base vertices
            v3 = v1 + len(surface_vertices)
            v4 = v2 + len(surface_vertices)
            
            # Create two triangles for the wall (proper winding order)
            side_faces.append([v1, v2, v3])  # First triangle
            side_faces.append([v2, v4, v3])  # Second triangle
        
        # Create base faces (reverse winding for bottom face)
        base_faces = faces.copy() + len(surface_vertices)
        base_faces = base_faces[:, [0, 2, 1]]  # Reverse winding for bottom
        
        # Combine all faces
        all_faces = np.vstack([faces, side_faces, base_faces])
        
        return all_vertices, all_faces
    
    def _get_grid_dimensions(self, num_vertices: int, faces: np.ndarray) -> tuple:
        """Determine grid dimensions from vertex count and face structure."""
        # For a rectangular grid with rows x cols vertices,
        # we need to find the factors that make sense
        possible_rows = []
        for r in range(2, int(np.sqrt(num_vertices)) + 10):
            if num_vertices % r == 0:
                c = num_vertices // r
                possible_rows.append((r, c))
        
        # If we can't determine from factors, estimate from face structure
        if not possible_rows:
            # Fallback: assume roughly square
            rows = int(np.sqrt(num_vertices))
            cols = num_vertices // rows
            return rows, cols
        
        # Choose the dimensions that are closest to square
        best_ratio = float('inf')
        best_dims = possible_rows[0]
        
        for r, c in possible_rows:
            ratio = max(r, c) / min(r, c)
            if ratio < best_ratio:
                best_ratio = ratio
                best_dims = (r, c)
        
        return best_dims
    
    def _get_ordered_boundary_indices(self, rows: int, cols: int) -> list:
        """Get boundary vertex indices in proper order for wall construction."""
        boundary = []
        
        # Top edge (left to right)
        for j in range(cols):
            boundary.append(j)
        
        # Right edge (top to bottom, excluding corners)
        for i in range(1, rows - 1):
            boundary.append(i * cols + (cols - 1))
        
        # Bottom edge (right to left, excluding right corner)
        if rows > 1:
            for j in range(cols - 1, -1, -1):
                boundary.append((rows - 1) * cols + j)
        
        # Left edge (bottom to top, excluding corners)
        for i in range(rows - 2, 0, -1):
            boundary.append(i * cols)
        
        return boundary
    
    def save_stl(self, mesh: trimesh.Trimesh, filename: str) -> None:
        """Save mesh as STL file."""
        mesh.export(filename)