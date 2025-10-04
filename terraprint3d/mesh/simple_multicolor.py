import numpy as np
import trimesh
from typing import Dict, List, Tuple
from terraprint3d.config.parser import Config
from terraprint3d.mesh.generator import MeshGenerator


class SimpleMultiColorMeshGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.base_generator = MeshGenerator(config)
    
    def generate_multi_color_meshes(self, lat_grid: np.ndarray, lon_grid: np.ndarray, elevation_grid: np.ndarray) -> Dict[str, trimesh.Trimesh]:
        """Generate multi-color terrain meshes using simple grid approach."""
        
        # Create the base coordinate grid
        x_grid, y_grid = self.base_generator._latlon_to_meters(lat_grid, lon_grid)
        z_grid = elevation_grid * self.config.terrain.vertical_exaggeration
        x_grid_norm, y_grid_norm, z_grid_norm = self.base_generator._normalize_to_printer_bed(x_grid, y_grid, z_grid)
        
        # Add layer thickness to ALL heights so base has proper thickness
        layer_thickness = self.config.terrain.colors.layer_thickness_mm
        z_grid_norm += layer_thickness
        
        # Calculate color zones
        zones = self._calculate_color_zones(z_grid_norm)
        
        meshes = {}
        
        # Generate base layer (covers everything)
        base_mesh = self._create_base_layer(x_grid_norm, y_grid_norm, z_grid_norm)
        meshes["layer00"] = base_mesh
        
        # Generate color layers (one for each zone)
        for i, (zone_min, zone_max) in enumerate(zones[1:], 1):  # Skip base zone
            layer_mesh = self._create_color_layer(x_grid_norm, y_grid_norm, z_grid_norm, zones, i)
            if layer_mesh is not None:
                meshes[f"layer{i:02d}"] = layer_mesh
        
        return meshes
    
    def _calculate_color_zones(self, z_grid: np.ndarray) -> List[Tuple[float, float]]:
        """Calculate elevation zones for colors."""
        min_z = np.nanmin(z_grid)
        max_z = np.nanmax(z_grid)
        
        num_colors = self.config.terrain.colors.num_colors
        zone_height = (max_z - min_z) / num_colors
        
        zones = []
        # Base zone (everything)
        zones.append((min_z, max_z))
        
        # Color zones
        for i in range(num_colors):
            zone_min = min_z + i * zone_height
            zone_max = min_z + (i + 1) * zone_height
            zones.append((zone_min, zone_max))
        
        return zones
    
    def _assign_elevation_to_zone(self, elevation: float, zones: List[Tuple[float, float]]) -> int:
        """Assign elevation to a zone index."""
        # Skip base zone (index 0), only assign to color zones (1+)
        color_zones = zones[1:]
        
        for idx, (zone_min, zone_max) in enumerate(color_zones):
            if zone_min <= elevation <= zone_max:
                return idx + 1
        
        # Fallback to nearest zone
        distances = []
        for idx, (zone_min, zone_max) in enumerate(color_zones):
            zone_center = (zone_min + zone_max) / 2
            distances.append(abs(elevation - zone_center))
        
        return distances.index(min(distances)) + 1
    
    def _is_boundary_point(self, i: int, j: int, x_grid: np.ndarray, y_grid: np.ndarray, 
                          z_grid: np.ndarray, zones: List[Tuple[float, float]], target_zone: int) -> bool:
        """Check if a point is adjacent to any point in the target zone."""
        rows, cols = x_grid.shape
        
        # Check all 8 neighbors (including diagonals)
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                if di == 0 and dj == 0:
                    continue
                    
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols and not np.isnan(z_grid[ni, nj]):
                    neighbor_height = z_grid[ni, nj]
                    neighbor_zone = self._assign_elevation_to_zone(neighbor_height, zones)
                    
                    if neighbor_zone == target_zone:
                        return True
        
        return False
    
    def _create_height_map_grid(self, x_grid: np.ndarray, y_grid: np.ndarray, z_grid: np.ndarray) -> Dict:
        """Generate height map grid (X, Y, Z)."""
        rows, cols = x_grid.shape
        
        height_map = {
            'x_grid': x_grid,
            'y_grid': y_grid, 
            'z_grid': z_grid,
            'rows': rows,
            'cols': cols
        }
        
        return height_map
    
    def _create_columns_from_grid(self, height_map: Dict, zones: List[Tuple[float, float]], layer_thickness: float) -> Dict:
        """Create columns from grid data like a fucking table."""
        x_grid = height_map['x_grid']
        y_grid = height_map['y_grid']
        z_grid = height_map['z_grid']
        rows = height_map['rows']
        cols = height_map['cols']
        
        all_vertices = []
        all_faces = []
        layer_info = {}  # Track which vertices belong to which zones
        
        # Loop through grid like columns on a table
        for i in range(rows):
            for j in range(cols):
                if not np.isnan(z_grid[i, j]):
                    x, y = x_grid[i, j], y_grid[i, j]
                    terrain_height = z_grid[i, j]
                    point_zone = self._assign_elevation_to_zone(terrain_height, zones)
                    
                    # Create column from base (0) to terrain height + layer thickness
                    column_vertices, column_faces, column_layer_info = self._create_single_column(
                        x, y, terrain_height, layer_thickness, point_zone, len(all_vertices)
                    )
                    
                    all_vertices.extend(column_vertices)
                    all_faces.extend(column_faces)
                    
                    # Store layer info for this column
                    layer_info[(i, j)] = column_layer_info
        
        return {
            'vertices': all_vertices,
            'faces': all_faces,
            'layer_info': layer_info,
            'zones': zones
        }
    
    def _create_single_column(self, x: float, y: float, terrain_height: float, layer_thickness: float, 
                             point_zone: int, vertex_offset: int) -> Tuple[List, List, Dict]:
        """Create a single column with all its layers."""
        vertices = []
        faces = []
        layer_info = {}
        
        # Create vertices for each layer this column belongs to
        for layer_idx in range(1, point_zone + 1):  # From layer 1 to point's zone
            # Bottom of layer
            bottom_z = (layer_idx - 1) * layer_thickness
            vertices.append([x, y, bottom_z])
            bottom_vertex_idx = vertex_offset + len(vertices) - 1
            
            # Top of layer
            top_z = layer_idx * layer_thickness
            vertices.append([x, y, top_z])
            top_vertex_idx = vertex_offset + len(vertices) - 1
            
            # Store layer info
            if layer_idx not in layer_info:
                layer_info[layer_idx] = []
            layer_info[layer_idx].extend([bottom_vertex_idx, top_vertex_idx])
        
        # Add terrain top vertex
        vertices.append([x, y, terrain_height + layer_thickness])
        terrain_top_idx = vertex_offset + len(vertices) - 1
        
        # Create faces for the column (connecting layers)
        for i in range(0, len(vertices) - 2, 2):
            bottom_idx = vertex_offset + i
            top_idx = vertex_offset + i + 1
            next_bottom_idx = vertex_offset + i + 2
            next_top_idx = vertex_offset + i + 3
            
            # Create quad faces between layers
            faces.extend([
                [bottom_idx, top_idx, next_bottom_idx],
                [top_idx, next_top_idx, next_bottom_idx]
            ])
        
        return vertices, faces, layer_info
    
    def _separate_layer_from_columns(self, column_mesh: Dict, zones: List[Tuple[float, float]], layer_idx: int) -> trimesh.Trimesh:
        """Separate a specific layer from the column mesh."""
        all_vertices = column_mesh['vertices']
        layer_info = column_mesh['layer_info']
        
        # Collect vertices and faces for this layer
        layer_vertices = []
        layer_faces = []
        vertex_map = {}  # old_idx -> new_idx
        
        # Go through each column and extract vertices for this layer
        for (i, j), column_layer_info in layer_info.items():
            if layer_idx in column_layer_info:
                vertex_indices = column_layer_info[layer_idx]
                
                for old_idx in vertex_indices:
                    if old_idx not in vertex_map:
                        vertex_map[old_idx] = len(layer_vertices)
                        layer_vertices.append(all_vertices[old_idx])
        
        if len(layer_vertices) == 0:
            return None
        
        # Create surface faces for this layer (connect adjacent columns)
        # This is where we create the actual layer surface
        layer_faces = self._create_layer_surface_faces(layer_vertices, vertex_map, layer_idx)
        
        if len(layer_faces) == 0:
            return None
        
        # Create mesh
        mesh = trimesh.Trimesh(vertices=layer_vertices, faces=layer_faces)
        mesh = self.base_generator._validate_and_fix_mesh(mesh)
        
        return mesh
    
    def _create_layer_surface_faces(self, layer_vertices: List, vertex_map: Dict, layer_idx: int) -> List:
        """Create surface faces for a layer by connecting adjacent columns."""
        faces = []
        
        # For now, create simple faces - this needs to connect adjacent grid points
        # This is a simplified version - you'd need to track grid topology
        
        # Create basic triangulation of the layer surface
        if len(layer_vertices) >= 3:
            # Simple fan triangulation from first vertex
            for i in range(1, len(layer_vertices) - 1):
                faces.append([0, i, i + 1])
        
        return faces
    
    def _create_point_grid(self, x_grid: np.ndarray, y_grid: np.ndarray, z_grid: np.ndarray, 
                          zones: List[Tuple[float, float]], layer_thickness: float) -> Dict:
        """Create a shared vertex map for all layers."""
        rows, cols = x_grid.shape
        
        # Shared vertex map: all vertices for all layers
        shared_vertices = []
        vertex_map = {}  # (i, j) -> vertex_index
        layer_assignment = np.full((rows, cols), -1, dtype=int)
        
        # Create shared vertices for all valid coordinates
        for i in range(rows):
            for j in range(cols):
                if not np.isnan(z_grid[i, j]):
                    terrain_height = z_grid[i, j]
                    point_zone = self._assign_elevation_to_zone(terrain_height, zones)
                    layer_assignment[i, j] = point_zone
                    
                    x, y = x_grid[i, j], y_grid[i, j]
                    
                    # Create shared vertex (top and bottom)
                    vertex_map[(i, j)] = len(shared_vertices)
                    shared_vertices.append([x, y, terrain_height + layer_thickness])  # Top
                    shared_vertices.append([x, y, terrain_height])  # Bottom
        
        return {
            'shared_vertices': shared_vertices,
            'vertex_map': vertex_map,
            'layer_assignment': layer_assignment,
            'layer_thickness': layer_thickness,
            'shape': (rows, cols)
        }
    
    def _create_base_layer(self, x_grid: np.ndarray, y_grid: np.ndarray, z_grid: np.ndarray) -> trimesh.Trimesh:
        """Create base layer that covers the entire terrain."""
        # Base layer: terrain surface down to z=0
        # The z_grid already has layer thickness added, so this creates proper base thickness
        vertices, faces = self.base_generator._create_surface_mesh(x_grid, y_grid, z_grid)
        
        # Store grid dimensions for base generation
        self.base_generator._grid_rows, self.base_generator._grid_cols = x_grid.shape
        
        # Add base (from terrain surface down to z=0)
        vertices, faces = self.base_generator._add_base(vertices, faces)
        
        # Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        mesh = self.base_generator._validate_and_fix_mesh(mesh)
        
        return mesh
    
    def _create_layer_from_point_grid(self, point_grid_data: Dict, grid_shape: Tuple[int, int], layer_idx: int) -> trimesh.Trimesh:
        """Create a layer using shared vertices."""
        shared_vertices = point_grid_data['shared_vertices']
        vertex_map = point_grid_data['vertex_map']
        layer_assignment = point_grid_data['layer_assignment']
        rows, cols = grid_shape
        
        # Use shared vertices and only create faces for this layer's coordinates
        vertex_indices = np.full((rows, cols), -1, dtype=int)
        
        for i in range(rows):
            for j in range(cols):
                if layer_assignment[i, j] >= layer_idx:  # Include if this layer is <= point's zone
                    # Use shared vertex index
                    vertex_indices[i, j] = vertex_map[(i, j)]
        
        # Check if this layer has any vertices
        if not np.any(vertex_indices >= 0):
            return None
        
        # Create faces using shared vertices
        faces = self._create_shared_faces(vertex_indices, rows, cols)
        
        if len(faces) == 0:
            return None
        
        # Create mesh with shared vertices
        mesh = trimesh.Trimesh(vertices=shared_vertices, faces=faces)
        mesh = self.base_generator._validate_and_fix_mesh(mesh)
        
        return mesh
    
    def _create_shared_faces(self, vertex_indices: np.ndarray, rows: int, cols: int) -> List:
        """Create faces using shared vertex indices."""
        faces = []
        
        # Create top surface faces
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Check if all 4 corners have vertices
                if (vertex_indices[i, j] >= 0 and vertex_indices[i, j+1] >= 0 and
                    vertex_indices[i+1, j] >= 0 and vertex_indices[i+1, j+1] >= 0):
                    
                    # Top face vertices (every vertex stored as pairs: top, bottom)
                    v00_top = vertex_indices[i, j]
                    v01_top = vertex_indices[i, j+1]
                    v10_top = vertex_indices[i+1, j]
                    v11_top = vertex_indices[i+1, j+1]
                    
                    # Create top surface triangles
                    faces.extend([
                        [v00_top, v01_top, v10_top],
                        [v01_top, v11_top, v10_top]
                    ])
                    
                    # Bottom face vertices
                    v00_bottom = v00_top + 1
                    v01_bottom = v01_top + 1
                    v10_bottom = v10_top + 1
                    v11_bottom = v11_top + 1
                    
                    # Create bottom surface triangles (reverse winding)
                    faces.extend([
                        [v00_bottom, v10_bottom, v01_bottom],
                        [v01_bottom, v10_bottom, v11_bottom]
                    ])
        
        # Create side walls between adjacent cells
        for i in range(rows):
            for j in range(cols):
                if vertex_indices[i, j] >= 0:
                    curr_top = vertex_indices[i, j]
                    curr_bottom = curr_top + 1
                    
                    # Check right neighbor
                    if j + 1 < cols and vertex_indices[i, j + 1] >= 0:
                        next_top = vertex_indices[i, j + 1]
                        next_bottom = next_top + 1
                        
                        # Create wall between current and right neighbor
                        faces.extend([
                            [curr_bottom, curr_top, next_bottom],
                            [curr_top, next_top, next_bottom]
                        ])
                    
                    # Check bottom neighbor
                    if i + 1 < rows and vertex_indices[i + 1, j] >= 0:
                        next_top = vertex_indices[i + 1, j]
                        next_bottom = next_top + 1
                        
                        # Create wall between current and bottom neighbor
                        faces.extend([
                            [curr_bottom, next_top, curr_top],
                            [curr_bottom, next_bottom, next_top]
                        ])
        
        return faces
    
    def _create_layer_faces_from_grid(self, layer_vertices: List, vertex_indices: np.ndarray, 
                                     vertex_map: Dict, layer_grid: Dict, rows: int, cols: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create faces for a layer from the point grid."""
        faces = []
        
        # Create top surface faces
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Check if all 4 corners have vertices in this layer
                if (vertex_indices[i, j] >= 0 and vertex_indices[i, j+1] >= 0 and
                    vertex_indices[i+1, j] >= 0 and vertex_indices[i+1, j+1] >= 0):
                    
                    # Top face vertices
                    v00_top = vertex_indices[i, j]
                    v01_top = vertex_indices[i, j+1]
                    v10_top = vertex_indices[i+1, j]
                    v11_top = vertex_indices[i+1, j+1]
                    
                    # Create top surface triangles
                    faces.extend([
                        [v00_top, v01_top, v10_top],
                        [v01_top, v11_top, v10_top]
                    ])
                    
                    # Get bottom vertices (every vertex stored as pairs: top, bottom)
                    # Find bottom vertex indices in the layer_vertices
                    v00_bottom = v00_top + 1 if v00_top + 1 < len(layer_vertices) else -1
                    v01_bottom = v01_top + 1 if v01_top + 1 < len(layer_vertices) else -1
                    v10_bottom = v10_top + 1 if v10_top + 1 < len(layer_vertices) else -1
                    v11_bottom = v11_top + 1 if v11_top + 1 < len(layer_vertices) else -1
                    
                    # Only create bottom faces if all bottom vertices exist
                    if all(v >= 0 for v in [v00_bottom, v01_bottom, v10_bottom, v11_bottom]):
                        faces.extend([
                            [v00_bottom, v10_bottom, v01_bottom],
                            [v01_bottom, v10_bottom, v11_bottom]
                        ])
        
        # Create side walls between adjacent cells
        for i in layer_grid:
            for j in layer_grid[i]:
                if vertex_indices[i, j] >= 0:
                    curr_top = vertex_indices[i, j]
                    curr_bottom = curr_top + 1 if curr_top + 1 < len(layer_vertices) else -1
                    
                    if curr_bottom >= 0:
                        # Check right neighbor
                        if j + 1 < cols and vertex_indices[i, j + 1] >= 0:
                            next_top = vertex_indices[i, j + 1]
                            next_bottom = next_top + 1 if next_top + 1 < len(layer_vertices) else -1
                            
                            if next_bottom >= 0:
                                faces.extend([
                                    [curr_bottom, curr_top, next_bottom],
                                    [curr_top, next_top, next_bottom]
                                ])
                        
                        # Check bottom neighbor
                        if i + 1 < rows and vertex_indices[i + 1, j] >= 0:
                            next_top = vertex_indices[i + 1, j]
                            next_bottom = next_top + 1 if next_top + 1 < len(layer_vertices) else -1
                            
                            if next_bottom >= 0:
                                faces.extend([
                                    [curr_bottom, next_top, curr_top],
                                    [curr_bottom, next_bottom, next_top]
                                ])
        
        return np.array(layer_vertices), np.array(faces)
    
    def _create_color_layer(self, x_grid: np.ndarray, y_grid: np.ndarray, z_grid: np.ndarray, 
                           zones: List[Tuple[float, float]], zone_idx: int) -> trimesh.Trimesh:
        """Create a color layer for the specified zone."""
        
        rows, cols = x_grid.shape
        vertices = []
        faces = []
        vertex_indices = np.full((rows, cols), -1, dtype=int)
        
        layer_thickness = self.config.terrain.colors.layer_thickness_mm
        
        # Loop through the grid and create vertices for this layer
        for i in range(rows):
            for j in range(cols):
                if not np.isnan(z_grid[i, j]):
                    terrain_height = z_grid[i, j]  # This already includes base layer thickness
                    point_zone = self._assign_elevation_to_zone(terrain_height, zones)
                    
                    # Include points that belong to this zone OR boundary points from higher zones
                    should_include = False
                    
                    if point_zone == zone_idx:
                        should_include = True
                    elif point_zone > zone_idx:
                        # Check if this higher-zone point is adjacent to a point in our zone
                        should_include = self._is_boundary_point(i, j, x_grid, y_grid, z_grid, zones, zone_idx)
                    
                    if should_include:
                        x, y = x_grid[i, j], y_grid[i, j]
                        
                        # Color layers sit ON TOP of the terrain
                        # Top vertex (terrain surface + additional layer thickness)
                        vertex_indices[i, j] = len(vertices)
                        vertices.append([x, y, terrain_height + layer_thickness])
                        
                        # Bottom vertex (terrain surface)
                        vertices.append([x, y, terrain_height])
        
        if len(vertices) == 0:
            return None
        
        # Create faces for the surface and walls
        vertices, faces = self._create_layer_faces(vertices, vertex_indices, rows, cols)
        
        # Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        mesh = self.base_generator._validate_and_fix_mesh(mesh)
        
        return mesh
    
    def _create_layer_faces(self, vertices: List, vertex_indices: np.ndarray, rows: int, cols: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create faces for a layer mesh - only connect adjacent cells, no walls between disconnected pieces."""
        faces = []
        
        # Create top surface faces
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Check if all 4 corners have vertices
                if (vertex_indices[i, j] >= 0 and vertex_indices[i, j+1] >= 0 and
                    vertex_indices[i+1, j] >= 0 and vertex_indices[i+1, j+1] >= 0):
                    
                    # Top face vertices (every vertex is stored as pairs: top, bottom)
                    v00_top = vertex_indices[i, j]
                    v01_top = vertex_indices[i, j+1]
                    v10_top = vertex_indices[i+1, j]
                    v11_top = vertex_indices[i+1, j+1]
                    
                    # Create top surface triangles
                    faces.extend([
                        [v00_top, v01_top, v10_top],
                        [v01_top, v11_top, v10_top]
                    ])
                    
                    # Bottom face vertices
                    v00_bottom = vertex_indices[i, j] + 1
                    v01_bottom = vertex_indices[i, j+1] + 1
                    v10_bottom = vertex_indices[i+1, j] + 1
                    v11_bottom = vertex_indices[i+1, j+1] + 1
                    
                    # Create bottom surface triangles (reverse winding)
                    faces.extend([
                        [v00_bottom, v10_bottom, v01_bottom],
                        [v01_bottom, v10_bottom, v11_bottom]
                    ])
        
        # Create side walls ONLY between adjacent cells - no boundary connection
        for i in range(rows):
            for j in range(cols):
                if vertex_indices[i, j] >= 0:
                    curr_top = vertex_indices[i, j]
                    curr_bottom = vertex_indices[i, j] + 1
                    
                    # Check right neighbor
                    if j + 1 < cols and vertex_indices[i, j + 1] >= 0:
                        next_top = vertex_indices[i, j + 1]
                        next_bottom = vertex_indices[i, j + 1] + 1
                        
                        # Create wall between current and right neighbor
                        faces.extend([
                            [curr_bottom, curr_top, next_bottom],
                            [curr_top, next_top, next_bottom]
                        ])
                    
                    # Check bottom neighbor
                    if i + 1 < rows and vertex_indices[i + 1, j] >= 0:
                        next_top = vertex_indices[i + 1, j]
                        next_bottom = vertex_indices[i + 1, j] + 1
                        
                        # Create wall between current and bottom neighbor
                        faces.extend([
                            [curr_bottom, next_top, curr_top],
                            [curr_bottom, next_bottom, next_top]
                        ])
        
        return np.array(vertices), np.array(faces)
    
    def _get_boundary_indices(self, vertex_indices: np.ndarray, rows: int, cols: int) -> List[int]:
        """Get boundary vertex indices for wall construction."""
        boundary = []
        
        # Top edge
        for j in range(cols):
            if vertex_indices[0, j] >= 0:
                boundary.append(vertex_indices[0, j])
        
        # Right edge
        for i in range(1, rows):
            if vertex_indices[i, cols-1] >= 0:
                boundary.append(vertex_indices[i, cols-1])
        
        # Bottom edge (reverse)
        for j in range(cols-2, -1, -1):
            if vertex_indices[rows-1, j] >= 0:
                boundary.append(vertex_indices[rows-1, j])
        
        # Left edge (reverse)
        for i in range(rows-2, 0, -1):
            if vertex_indices[i, 0] >= 0:
                boundary.append(vertex_indices[i, 0])
        
        return boundary
    
    def save_multi_color_stls(self, meshes: Dict[str, trimesh.Trimesh], base_filename: str) -> List[str]:
        """Save multi-color meshes as separate STL files."""
        import os
        
        # Create output directory
        output_dir = base_filename.replace('.stl', '_output')
        os.makedirs(output_dir, exist_ok=True)
        
        filenames = []
        for layer_name, mesh in meshes.items():
            filename = os.path.join(output_dir, f"{base_filename.replace('.stl', '')}_{layer_name}.stl")
            mesh.export(filename)
            filenames.append(filename)
        
        return filenames