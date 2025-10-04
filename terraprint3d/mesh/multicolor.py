import numpy as np
import trimesh
from typing import List, Tuple, Dict
from terraprint3d.config.parser import Config
from terraprint3d.mesh.generator import MeshGenerator


class MultiColorMeshGenerator(MeshGenerator):
    def __init__(self, config: Config):
        super().__init__(config)
        self.color_zones = []
    
    def generate_multi_color_meshes(self, lat_grid: np.ndarray, lon_grid: np.ndarray, 
                                   elevation_grid: np.ndarray) -> Dict[str, trimesh.Trimesh]:
        """Generate separate meshes for each color zone."""
        
        if not self.config.terrain.colors.enabled:
            # Single color - return original mesh
            mesh = self.generate_mesh(lat_grid, lon_grid, elevation_grid)
            return {"terrain": mesh}
        
        # Apply height stepping if enabled
        if self.config.terrain.height_stepping.enabled:
            elevation_grid = self._apply_height_stepping(elevation_grid)
        
        # Convert to mesh coordinates first
        x_grid, y_grid = self._latlon_to_meters(lat_grid, lon_grid)
        x_grid_norm, y_grid_norm, z_grid_norm = self._normalize_to_printer_bed(x_grid, y_grid, elevation_grid)
        z_grid_norm *= self.config.terrain.vertical_exaggeration
        z_grid_norm += self.config.terrain.base_thickness_mm
        
        # Calculate color zones based on the normalized elevation
        color_zones = self._calculate_color_zones(z_grid_norm)
        
        # Store grid dimensions
        self._grid_rows, self._grid_cols = x_grid_norm.shape
        
        # Generate meshes for each color zone
        meshes = {}
        color_names = self._get_color_names()
        
        for i, (zone_min, zone_max) in enumerate(color_zones):
            color_name = color_names[i] if i < len(color_names) else f"color_{i+1}"
            
            # Create mask for this elevation zone (using normalized heights)
            zone_mask = (z_grid_norm >= zone_min) & (z_grid_norm <= zone_max)
            
            if not np.any(zone_mask):
                continue  # Skip empty zones
            
            # Generate mesh for this zone
            zone_mesh = self._generate_zone_mesh(x_grid_norm, y_grid_norm, z_grid_norm, zone_mask, zone_min)
            
            if zone_mesh is not None:
                meshes[color_name] = zone_mesh
        
        # Validate for intersections
        # Validation disabled while fixing boundary approach
        # self.validate_layer_intersections(meshes)
        
        return meshes
    
    def _apply_height_stepping(self, elevation_grid: np.ndarray) -> np.ndarray:
        """Apply height stepping to elevation data."""
        step_height = self.config.terrain.height_stepping.step_height_mm / self.config.terrain.vertical_exaggeration
        
        # Calculate steps
        min_elev = np.min(elevation_grid)
        max_elev = np.max(elevation_grid)
        
        # Create stepped elevation
        stepped_grid = elevation_grid.copy()
        
        if self.config.terrain.height_stepping.smooth_transitions:
            # Smooth stepping - gradual transitions
            num_steps = int((max_elev - min_elev) / step_height) + 1
            step_levels = np.linspace(min_elev, max_elev, num_steps)
            
            for i in range(len(step_levels) - 1):
                mask = (elevation_grid >= step_levels[i]) & (elevation_grid < step_levels[i + 1])
                stepped_grid[mask] = step_levels[i] + (step_levels[i + 1] - step_levels[i]) * 0.5
        else:
            # Sharp stepping - discrete levels
            stepped_grid = np.round((elevation_grid - min_elev) / step_height) * step_height + min_elev
        
        return stepped_grid
    
    def _calculate_color_zones(self, elevation_grid: np.ndarray) -> List[Tuple[float, float]]:
        """Calculate elevation zones for color separation with no gaps."""
        min_elev = np.min(elevation_grid)
        max_elev = np.max(elevation_grid)
        num_colors = self.config.terrain.colors.num_colors
        
        if self.config.terrain.colors.color_mode == "elevation":
            zones = []
            
            # First zone: base layer (covers everything - special marker zone)
            zones.append((min_elev - 1.0, max_elev + 1.0))  # Base zone covers all elevations
            
            # Color zones: divide terrain elevation range into color layers
            zone_height = (max_elev - min_elev) / num_colors
            
            for i in range(num_colors):
                zone_min = min_elev + i * zone_height
                zone_max = min_elev + (i + 1) * zone_height
                
                # Add small overlap to eliminate gaps
                if i > 0:
                    zone_min -= 0.001  # Slight overlap with previous zone
                
                if i == num_colors - 1:  # Last zone extends beyond maximum
                    zone_max = max_elev + 1.0  # Large buffer to catch everything
                else:
                    zone_max += 0.001  # Slight overlap with next zone
                    
                zones.append((zone_min, zone_max))
            
            return zones
        
        elif self.config.terrain.colors.color_mode == "slope":
            # TODO: Implement slope-based coloring
            # For now, fall back to elevation
            return self._calculate_color_zones_elevation_fallback(elevation_grid)
    
    def _calculate_color_zones_elevation_fallback(self, elevation_grid: np.ndarray) -> List[Tuple[float, float]]:
        """Fallback elevation-based zones."""
        min_elev = np.min(elevation_grid)
        max_elev = np.max(elevation_grid)
        num_colors = self.config.terrain.colors.num_colors
        
        zone_height = (max_elev - min_elev) / num_colors
        zones = []
        
        for i in range(num_colors):
            zone_min = min_elev + i * zone_height
            zone_max = min_elev + (i + 1) * zone_height
            if i == num_colors - 1:
                zone_max = max_elev + 0.1
            zones.append((zone_min, zone_max))
        
        return zones
    
    def _get_color_names(self) -> List[str]:
        """Get color names for file output - base + color layer numbers."""
        num_colors = self.config.terrain.colors.num_colors
        total_layers = num_colors + 1  # base + color layers
        
        # Base is layer00, color layers are layer01, layer02, etc.
        names = []
        for i in range(total_layers):
            names.append(f"layer{i:02d}")  # Zero-padded starting from 00
        
        return names
    
    def _generate_zone_mesh(self, x_grid: np.ndarray, y_grid: np.ndarray, z_grid: np.ndarray, 
                           zone_mask: np.ndarray, zone_base_height: float) -> trimesh.Trimesh:
        """Generate mesh - base is full terrain, color layers are thin tops."""
        
        # Color layer thickness (configurable)
        color_layer_thickness = self.config.terrain.colors.layer_thickness_mm
        
        # Check if this is the base mesh (first/lowest zone)
        all_zones = self._calculate_color_zones(z_grid)
        if len(all_zones) == 0:
            return None
            
        min_zone_base = all_zones[0][0]
        is_base_mesh = abs(zone_base_height - min_zone_base) < 0.001
        
        if is_base_mesh:
            # BASE LAYER: Goes from floor (0) up to original terrain height
            
            # Base fills from floor up to original terrain height
            base_height_grid = z_grid.copy()
            
            # Ensure minimum height is base thickness
            base_height_grid = np.maximum(base_height_grid, self.config.terrain.base_thickness_mm)
            
            # Generate base mesh (covers ENTIRE terrain area up to original terrain height)
            vertices, faces = self._create_surface_mesh(x_grid, y_grid, base_height_grid)
            vertices, faces = self._add_base(vertices, faces)
        else:
            # COLOR LAYERS: Raised terrain at original_height + layer_thickness
            # Each color layer covers specific elevation zones across ENTIRE XY grid
            
            # Determine which areas of the XY grid belong to this color zone
            color_areas_mask = self._get_all_areas_for_color(z_grid, all_zones, zone_base_height)
            
            if not np.any(color_areas_mask):
                return None
            
            # Color layers are thin layers that stack on top of base layer
            # Each color layer only covers its assigned elevation zone
            # Calculate which elevation zones this layer should occupy
            
            # Find which zone index we're working on
            target_zone_idx = None
            for idx, (zone_min, zone_max) in enumerate(all_zones):
                if abs(zone_min - zone_base_height) < 0.001:
                    target_zone_idx = idx
                    break
            
            if target_zone_idx is None or target_zone_idx == 0:
                return None  # Skip base zone or invalid zone
                
            # Color layers stack on top of base layer (which ends at z_grid height)
            # Each color layer is a thin layer_thickness above the base
            # Layer 1: from base_top to base_top + layer_thickness
            # Layer 2: from base_top + layer_thickness to base_top + 2*layer_thickness, etc.
            
            # Color layers sit directly on top of base at terrain height
            # They are thin layers above the terrain surface
            
            layer_bottom = z_grid.copy()  # Start at terrain surface (where base ends)
            layer_top = z_grid + color_layer_thickness  # Add thickness above terrain
            
            zone_z_bottom = layer_bottom.copy()
            zone_z_top = layer_top.copy()
            
            # Only include areas assigned to this color zone
            zone_z_top[~color_areas_mask] = np.nan
            zone_z_bottom[~color_areas_mask] = np.nan
            
            # Generate raised color layer mesh
            vertices, faces = self._create_color_layer_mesh(x_grid, y_grid, zone_z_top, zone_z_bottom, color_areas_mask, zone_base_height, z_grid)
        
        if len(vertices) == 0:
            return None
        
        # Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        mesh = self._validate_and_fix_mesh(mesh)
        
        return mesh
    
    def _scan_visible_areas_for_color(self, z_grid: np.ndarray, all_zones: List[Tuple[float, float]], 
                                    target_zone_base: float) -> np.ndarray:
        """Scan grid top-down to find areas where this color would be visible from above."""
        
        visible_mask = np.zeros_like(z_grid, dtype=bool)
        
        # Find which zone index we're looking for
        target_zone_idx = None
        for idx, (zone_min, zone_max) in enumerate(all_zones):
            if abs(zone_min - target_zone_base) < 0.001:
                target_zone_idx = idx
                break
        
        if target_zone_idx is None:
            return visible_mask
        
        # For each X,Y point, determine which color zone is at the top surface
        for i in range(z_grid.shape[0]):
            for j in range(z_grid.shape[1]):
                elevation = z_grid[i, j]
                
                # Find which zone this elevation belongs to - MUST assign to a zone
                point_zone_idx = self._assign_elevation_to_zone(elevation, all_zones)
                
                # This color is visible if it's the assigned zone at this point
                if point_zone_idx == target_zone_idx:
                    visible_mask[i, j] = True
        
        return visible_mask
    
    def _get_all_areas_for_color(self, z_grid: np.ndarray, all_zones: List[Tuple[float, float]], 
                                target_zone_base: float) -> np.ndarray:
        """Get areas for this color including shared boundary points with adjacent layers."""
        
        color_mask = np.zeros_like(z_grid, dtype=bool)
        
        # Find which zone index we're looking for
        target_zone_idx = None
        for idx, (zone_min, zone_max) in enumerate(all_zones):
            if abs(zone_min - target_zone_base) < 0.001:
                target_zone_idx = idx
                break
        
        if target_zone_idx is None:
            return color_mask
        
        if target_zone_idx == 0:
            # Base zone covers everything 
            color_mask[:, :] = True
        else:
            # For color zones, only include points that belong to this zone
            for i in range(z_grid.shape[0]):
                for j in range(z_grid.shape[1]):
                    elevation = z_grid[i, j]
                    if not np.isnan(elevation):
                        point_zone = self._assign_elevation_to_zone(elevation, all_zones)
                        if point_zone == target_zone_idx:
                            color_mask[i, j] = True
        
        return color_mask
    
    def _is_boundary_point(self, i: int, j: int, z_grid: np.ndarray, 
                          all_zones: List[Tuple[float, float]], target_zone_idx: int) -> bool:
        """Disable boundary point logic - just use simple zone assignment."""
        return False
    
    def _get_zone_index_for_base(self, target_zone_base: float, elevation_grid: np.ndarray) -> int:
        """Get the zone index for the given zone base height."""
        all_zones = self._calculate_color_zones(elevation_grid)
        for idx, (zone_min, zone_max) in enumerate(all_zones):
            if abs(zone_min - target_zone_base) < 0.001:
                return idx
        return 0
    
    def _assign_elevation_to_zone(self, elevation: float, all_zones: List[Tuple[float, float]]) -> int:
        """Assign elevation to a zone, ensuring NO data is left out."""
        
        # Zone 0 is base (covers everything), zones 1+ are color layers by elevation
        # For color assignment, we only care about zones 1+ (the actual color zones)
        
        color_zones = all_zones[1:]  # Skip base zone (index 0)
        
        # Find which color zone this elevation belongs to
        for idx, (zone_min, zone_max) in enumerate(color_zones):
            if zone_min <= elevation <= zone_max:
                return idx + 1  # Return actual zone index (1+ for color layers)
        
        # Fallback: assign to nearest color zone
        min_distance = float('inf')
        best_zone = 1  # Start with first color zone
        
        for idx, (zone_min, zone_max) in enumerate(color_zones):
            # Calculate distance to zone center
            zone_center = (zone_min + zone_max) / 2
            distance = abs(elevation - zone_center)
            
            if distance < min_distance:
                min_distance = distance
                best_zone = idx + 1  # Return actual zone index
        
        return best_zone
    
    def _create_layer_mesh(self, x_grid: np.ndarray, y_grid: np.ndarray, z_grid: np.ndarray, 
                          zone_bottom: float, zone_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create a printable layer mesh that sits on the previous layer."""
        
        # Create surface mesh for the entire area, but with zone areas elevated
        vertices, faces = self._create_surface_mesh(x_grid, y_grid, z_grid)
        
        # Convert to lists for easier manipulation
        vertices = vertices.tolist() if isinstance(vertices, np.ndarray) else vertices
        faces = faces.tolist() if isinstance(faces, np.ndarray) else faces
        
        # Add a flat bottom at zone_bottom height for the interface layer
        original_vertex_count = len(vertices)
        
        # Create bottom vertices at the interface height
        for i in range(original_vertex_count):
            x, y, _ = vertices[i]
            vertices.append([x, y, zone_bottom])
        
        # Add side walls connecting top to bottom where needed
        # This creates a solid printable piece
        rows, cols = x_grid.shape
        
        # Add bottom triangles (full area at zone_bottom height)
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Calculate vertex indices for the bottom face
                v00_bottom = original_vertex_count + (i * cols + j)
                v01_bottom = original_vertex_count + (i * cols + (j + 1))
                v10_bottom = original_vertex_count + ((i + 1) * cols + j)
                v11_bottom = original_vertex_count + ((i + 1) * cols + (j + 1))
                
                # Add bottom triangles (reverse winding for bottom face)
                faces.extend([
                    [v00_bottom, v10_bottom, v01_bottom],
                    [v01_bottom, v10_bottom, v11_bottom]
                ])
        
        # Add side walls around the perimeter
        # Connect the top surface to the bottom surface around edges
        boundary_indices = self._get_ordered_boundary_indices(rows, cols)
        
        for i in range(len(boundary_indices)):
            curr_idx = boundary_indices[i]
            next_idx = boundary_indices[(i + 1) % len(boundary_indices)]
            
            # Connect top to bottom
            top_curr = curr_idx
            top_next = next_idx
            bottom_curr = original_vertex_count + curr_idx
            bottom_next = original_vertex_count + next_idx
            
            # Add side wall triangles
            faces.extend([
                [bottom_curr, top_curr, bottom_next],
                [top_curr, top_next, bottom_next]
            ])
        
        return np.array(vertices), np.array(faces)
    
    def _create_color_layer_mesh(self, x_grid: np.ndarray, y_grid: np.ndarray, 
                                z_top_grid: np.ndarray, z_bottom_grid: np.ndarray, 
                                zone_mask: np.ndarray, target_zone_base: float, 
                                z_grid: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """Create mesh only for areas that belong to this specific color zone."""
        
        rows, cols = x_grid.shape
        vertices = []
        faces = []
        
        # Create vertices only for points that belong to this zone
        vertex_indices_top = np.full((rows, cols), -1, dtype=int)
        vertex_indices_bottom = np.full((rows, cols), -1, dtype=int)
        
        # Add vertices only for zones that belong to this layer
        for i in range(rows):
            for j in range(cols):
                if zone_mask[i, j] and not np.isnan(z_bottom_grid[i, j]):
                    x, y = x_grid[i, j], y_grid[i, j]
                    z_top = z_top_grid[i, j]
                    z_bottom = z_bottom_grid[i, j]
                    
                    # Add top and bottom vertices
                    vertex_indices_top[i, j] = len(vertices)
                    vertices.append([x, y, z_top])
                    
                    vertex_indices_bottom[i, j] = len(vertices)
                    vertices.append([x, y, z_bottom])
        
        # Create faces only for cells that have actual height variation
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Check if all 4 corners have valid vertices
                if (vertex_indices_top[i, j] >= 0 and vertex_indices_top[i, j+1] >= 0 and
                    vertex_indices_top[i+1, j] >= 0 and vertex_indices_top[i+1, j+1] >= 0):
                    
                    
                    # Get vertex indices for this quad
                    v00_top = vertex_indices_top[i, j]
                    v01_top = vertex_indices_top[i, j+1]
                    v10_top = vertex_indices_top[i+1, j]
                    v11_top = vertex_indices_top[i+1, j+1]
                    
                    v00_bottom = vertex_indices_bottom[i, j]
                    v01_bottom = vertex_indices_bottom[i, j+1]
                    v10_bottom = vertex_indices_bottom[i+1, j]
                    v11_bottom = vertex_indices_bottom[i+1, j+1]
                    
                    # Top surface (2 triangles)
                    faces.append([v00_top, v01_top, v10_top])
                    faces.append([v01_top, v11_top, v10_top])
                    
                    # Bottom surface (2 triangles, reverse winding)
                    faces.append([v00_bottom, v10_bottom, v01_bottom])
                    faces.append([v01_bottom, v10_bottom, v11_bottom])
                    
                    # Side walls (4 walls, each with 2 triangles)
                    walls = [(v00_top, v00_bottom, v01_top, v01_bottom),  # Wall 1
                            (v01_top, v01_bottom, v11_top, v11_bottom),   # Wall 2  
                            (v11_top, v11_bottom, v10_top, v10_bottom),   # Wall 3
                            (v10_top, v10_bottom, v00_top, v00_bottom)]   # Wall 4
                    
                    for vt1, vb1, vt2, vb2 in walls:
                        faces.append([vb1, vt1, vb2])
                        faces.append([vt1, vt2, vb2])
        
        return np.array(vertices) if vertices else np.array([]).reshape(0, 3), \
               np.array(faces) if faces else np.array([]).reshape(0, 3)
    
    def validate_layer_intersections(self, meshes: Dict[str, trimesh.Trimesh]) -> bool:
        """Check if any two layers intersect in the same mesh space."""
        
        layer_names = list(meshes.keys())
        intersections_found = False
        
        print("🔍 Validating layer intersections...")
        
        for i in range(len(layer_names)):
            for j in range(i + 1, len(layer_names)):
                layer1_name = layer_names[i]
                layer2_name = layer_names[j]
                mesh1 = meshes[layer1_name]
                mesh2 = meshes[layer2_name]
                
                # Check if bounding boxes overlap
                bbox1 = mesh1.bounds
                bbox2 = mesh2.bounds
                
                # Check for overlap in all three dimensions
                x_overlap = bbox1[0][0] <= bbox2[1][0] and bbox2[0][0] <= bbox1[1][0]
                y_overlap = bbox1[0][1] <= bbox2[1][1] and bbox2[0][1] <= bbox1[1][1]
                z_overlap = bbox1[0][2] <= bbox2[1][2] and bbox2[0][2] <= bbox1[1][2]
                
                if x_overlap and y_overlap and z_overlap:
                    # Bounding boxes overlap, check for detailed intersection
                    overlap_volume = self._calculate_overlap_volume(bbox1, bbox2)
                    
                    print(f"⚠️  Potential intersection between {layer1_name} and {layer2_name}")
                    print(f"   {layer1_name} bounds: {bbox1}")
                    print(f"   {layer2_name} bounds: {bbox2}")
                    print(f"   Overlap volume: {overlap_volume:.3f} mm³")
                    
                    # Check if z-ranges overlap (most critical for layer stacking)
                    z1_min, z1_max = bbox1[0][2], bbox1[1][2]
                    z2_min, z2_max = bbox2[0][2], bbox2[1][2]
                    
                    if z1_min < z2_max and z2_min < z1_max:
                        z_overlap_amount = min(z1_max, z2_max) - max(z1_min, z2_min)
                        print(f"   ❌ Z-axis overlap: {z_overlap_amount:.3f} mm")
                        intersections_found = True
                    else:
                        print(f"   ✅ No Z-axis overlap")
        
        if not intersections_found:
            print("✅ No layer intersections detected!")
        
        return not intersections_found
    
    def _calculate_overlap_volume(self, bbox1, bbox2):
        """Calculate the volume of overlap between two bounding boxes."""
        
        # Calculate overlap in each dimension
        x_overlap = max(0, min(bbox1[1][0], bbox2[1][0]) - max(bbox1[0][0], bbox2[0][0]))
        y_overlap = max(0, min(bbox1[1][1], bbox2[1][1]) - max(bbox1[0][1], bbox2[0][1]))
        z_overlap = max(0, min(bbox1[1][2], bbox2[1][2]) - max(bbox1[0][2], bbox2[0][2]))
        
        return x_overlap * y_overlap * z_overlap
    
    def _create_full_quad_faces(self, corners, vertex_indices_top, vertex_indices_bottom, faces):
        """Create faces for a complete quad."""
        # Sort corners to get correct order
        corners = sorted(corners, key=lambda x: (x[0], x[1]))
        
        v0_top = vertex_indices_top[corners[0]]
        v1_top = vertex_indices_top[corners[1]] 
        v2_top = vertex_indices_top[corners[2]]
        v3_top = vertex_indices_top[corners[3]]
        
        v0_bottom = vertex_indices_bottom[corners[0]]
        v1_bottom = vertex_indices_bottom[corners[1]]
        v2_bottom = vertex_indices_bottom[corners[2]]
        v3_bottom = vertex_indices_bottom[corners[3]]
        
        # Top surface (2 triangles)
        faces.append([v0_top, v1_top, v2_top])
        faces.append([v1_top, v3_top, v2_top])
        
        # Bottom surface (2 triangles, reverse winding)
        faces.append([v0_bottom, v2_bottom, v1_bottom])
        faces.append([v1_bottom, v2_bottom, v3_bottom])
        
        # Side walls (4 walls, each with 2 triangles)
        side_pairs = [(v0_top, v0_bottom, v1_top, v1_bottom),
                     (v1_top, v1_bottom, v3_top, v3_bottom),
                     (v3_top, v3_bottom, v2_top, v2_bottom),
                     (v2_top, v2_bottom, v0_top, v0_bottom)]
        
        for vt1, vb1, vt2, vb2 in side_pairs:
            faces.append([vb1, vt1, vb2])
            faces.append([vt1, vt2, vb2])
    
    def _create_triangle_faces(self, corners, vertex_indices_top, vertex_indices_bottom, faces):
        """Create faces for a triangular section."""
        corners = sorted(corners, key=lambda x: (x[0], x[1]))
        
        v0_top = vertex_indices_top[corners[0]]
        v1_top = vertex_indices_top[corners[1]]
        v2_top = vertex_indices_top[corners[2]]
        
        v0_bottom = vertex_indices_bottom[corners[0]]
        v1_bottom = vertex_indices_bottom[corners[1]]
        v2_bottom = vertex_indices_bottom[corners[2]]
        
        # Top surface triangle
        faces.append([v0_top, v1_top, v2_top])
        
        # Bottom surface triangle (reverse winding)
        faces.append([v0_bottom, v2_bottom, v1_bottom])
        
        # Side walls (3 walls, each with 2 triangles)
        side_pairs = [(v0_top, v0_bottom, v1_top, v1_bottom),
                     (v1_top, v1_bottom, v2_top, v2_bottom),
                     (v2_top, v2_bottom, v0_top, v0_bottom)]
        
        for vt1, vb1, vt2, vb2 in side_pairs:
            faces.append([vb1, vt1, vb2])
            faces.append([vt1, vt2, vb2])
    
    def _create_adaptive_faces(self, valid_corners, vertex_indices_top, 
                             vertex_indices_bottom, faces):
        """Create faces adaptively based on valid corner pattern."""
        
        if len(valid_corners) < 3:
            return
            
        # Sort corners by position for consistent triangulation
        valid_corners = sorted(valid_corners, key=lambda x: (x[0], x[1]))
        
        # Get vertex indices for all valid corners
        top_verts = [vertex_indices_top[i, j] for i, j in valid_corners]
        bottom_verts = [vertex_indices_bottom[i, j] for i, j in valid_corners]
        
        # Triangulate the top surface using fan triangulation from first vertex
        for k in range(1, len(valid_corners) - 1):
            faces.append([top_verts[0], top_verts[k], top_verts[k + 1]])
        
        # Triangulate the bottom surface (reverse winding)
        for k in range(1, len(valid_corners) - 1):
            faces.append([bottom_verts[0], bottom_verts[k + 1], bottom_verts[k]])
        
        # Create side walls connecting top and bottom
        for k in range(len(valid_corners)):
            next_k = (k + 1) % len(valid_corners)
            
            vt1 = top_verts[k]
            vt2 = top_verts[next_k]
            vb1 = bottom_verts[k]
            vb2 = bottom_verts[next_k]
            
            # Two triangles for each side wall
            faces.append([vb1, vt1, vb2])
            faces.append([vt1, vt2, vb2])
    
    def _add_thin_layer_section(self, corner_coords, vertices, faces, add_vertex):
        """Add a thin layer section between top and bottom surfaces."""
        
        if len(corner_coords) < 3:
            return
        
        # For a proper quad (4 corners), create a rectangular thin layer
        if len(corner_coords) == 4:
            # Sort corners to create proper quad topology
            x_coords = [coord[0] for coord in corner_coords]
            y_coords = [coord[1] for coord in corner_coords]
            
            # Create vertices for quad corners in order
            top_vertices = []
            bottom_vertices = []
            
            for x, y, z_top, z_bottom in corner_coords:
                top_vertices.append(add_vertex(x, y, z_top))
                bottom_vertices.append(add_vertex(x, y, z_bottom))
            
            # Create top surface - two triangles for the quad
            faces.append([top_vertices[0], top_vertices[1], top_vertices[2]])
            faces.append([top_vertices[0], top_vertices[2], top_vertices[3]])
            
            # Create bottom surface - two triangles (reverse winding)
            faces.append([bottom_vertices[0], bottom_vertices[2], bottom_vertices[1]])
            faces.append([bottom_vertices[0], bottom_vertices[3], bottom_vertices[2]])
            
            # Create side walls - 4 rectangular sides, each made of 2 triangles
            for i in range(4):
                next_i = (i + 1) % 4
                v1_top = top_vertices[i]
                v1_bottom = bottom_vertices[i]
                v2_top = top_vertices[next_i]
                v2_bottom = bottom_vertices[next_i]
                
                # Two triangles for each side wall
                faces.append([v1_bottom, v1_top, v2_bottom])
                faces.append([v1_top, v2_top, v2_bottom])
        
        else:
            # For triangular or other shapes, use fan triangulation
            top_vertices = []
            bottom_vertices = []
            
            for x, y, z_top, z_bottom in corner_coords:
                top_vertices.append(add_vertex(x, y, z_top))
                bottom_vertices.append(add_vertex(x, y, z_bottom))
            
            # Create top surface triangles using fan triangulation
            for i in range(1, len(top_vertices) - 1):
                faces.append([top_vertices[0], top_vertices[i], top_vertices[i+1]])
            
            # Create bottom surface triangles (reverse winding)
            for i in range(1, len(bottom_vertices) - 1):
                faces.append([bottom_vertices[0], bottom_vertices[i+1], bottom_vertices[i]])
            
            # Create side walls
            for i in range(len(top_vertices)):
                next_i = (i + 1) % len(top_vertices)
                
                v1_top = top_vertices[i]
                v1_bottom = bottom_vertices[i]
                v2_top = top_vertices[next_i]
                v2_bottom = bottom_vertices[next_i]
                
                # Two triangles for the side face
                faces.append([v1_bottom, v1_top, v2_bottom])
                faces.append([v1_top, v2_top, v2_bottom])
    
    def save_multi_color_stls(self, meshes: Dict[str, trimesh.Trimesh], base_filename: str) -> List[str]:
        """Save multiple STL files for multi-color printing in a dedicated output folder."""
        import os
        
        filenames = []
        
        if not meshes:
            return filenames
        
        # Create output directory based on base filename
        base_path = os.path.dirname(base_filename) if os.path.dirname(base_filename) else "."
        base_name = os.path.basename(base_filename)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # Create output folder
        output_dir = os.path.join(base_path, f"{name_without_ext}_output")
        os.makedirs(output_dir, exist_ok=True)
        
        mesh_keys = list(meshes.keys())
        
        for color_name, mesh in meshes.items():
            if len(meshes) == 1:
                # Single color - put in output folder
                filename = os.path.join(output_dir, base_name)
            else:
                # Multi-layer - use sequential numbering in output folder
                name_parts = base_name.rsplit('.', 1)
                if len(name_parts) == 2:
                    filename = os.path.join(output_dir, f"{name_parts[0]}_{color_name}.{name_parts[1]}")
                else:
                    filename = os.path.join(output_dir, f"{base_name}_{color_name}")
            
            mesh.export(filename)
            filenames.append(filename)
        
        return filenames