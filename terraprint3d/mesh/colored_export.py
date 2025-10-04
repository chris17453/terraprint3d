import numpy as np
import trimesh
from typing import Dict, List, Tuple
from terraprint3d.config.parser import Config


class ColoredMeshExporter:
    def __init__(self, config: Config):
        self.config = config
        self.color_palette = self._get_color_palette()
    
    def create_colored_mesh(self, lat_grid: np.ndarray, lon_grid: np.ndarray, 
                           elevation_grid: np.ndarray) -> trimesh.Trimesh:
        """Create a single mesh with vertex colors based on elevation."""
        
        from terraprint3d.mesh.generator import MeshGenerator
        mesh_gen = MeshGenerator(self.config)
        
        # Generate the base mesh
        mesh = mesh_gen.generate_mesh(lat_grid, lon_grid, elevation_grid)
        
        if not self.config.terrain.colors.enabled:
            return mesh
        
        # Apply vertex colors based on elevation
        vertex_colors = self._calculate_vertex_colors(mesh.vertices, elevation_grid, lat_grid, lon_grid)
        mesh.visual.vertex_colors = vertex_colors
        
        return mesh
    
    def _get_color_palette(self) -> List[Tuple[int, int, int, int]]:
        """Get RGBA color palette for elevation zones."""
        if self.config.terrain.colors.color_names:
            colors = []
            color_map = {
                'red': (255, 0, 0, 255),
                'green': (0, 255, 0, 255),
                'blue': (0, 0, 255, 255),
                'yellow': (255, 255, 0, 255),
                'orange': (255, 165, 0, 255),
                'purple': (128, 0, 128, 255),
                'cyan': (0, 255, 255, 255),
                'magenta': (255, 0, 255, 255),
                'brown': (139, 69, 19, 255),
                'pink': (255, 192, 203, 255),
                'navy': (0, 0, 128, 255),
                'dark': (64, 64, 64, 255),
                'light': (192, 192, 192, 255),
                'white': (255, 255, 255, 255),
                'black': (0, 0, 0, 255)
            }
            
            for color_name in self.config.terrain.colors.color_names:
                color_name_lower = color_name.lower()
                if color_name_lower in color_map:
                    colors.append(color_map[color_name_lower])
                else:
                    # Default to a generated color
                    colors.append(self._generate_color(len(colors)))
            
            return colors
        else:
            # Generate default elevation-based colors
            return self._generate_elevation_colors()
    
    def _generate_elevation_colors(self) -> List[Tuple[int, int, int, int]]:
        """Generate default terrain colors (blue to red gradient)."""
        num_colors = self.config.terrain.colors.num_colors
        colors = []
        
        # Create a gradient from blue (low) to red (high)
        for i in range(num_colors):
            # Interpolate between blue and red
            ratio = i / (num_colors - 1) if num_colors > 1 else 0
            
            # Blue to green to yellow to red gradient
            if ratio < 0.33:
                # Blue to green
                r = int(0 * (1 - ratio/0.33))
                g = int(255 * (ratio/0.33))
                b = int(255 * (1 - ratio/0.33))
            elif ratio < 0.66:
                # Green to yellow
                r = int(255 * ((ratio - 0.33)/0.33))
                g = 255
                b = 0
            else:
                # Yellow to red
                r = 255
                g = int(255 * (1 - (ratio - 0.66)/0.34))
                b = 0
            
            colors.append((r, g, b, 255))
        
        return colors
    
    def _generate_color(self, index: int) -> Tuple[int, int, int, int]:
        """Generate a color for unknown color names."""
        # Simple hue rotation
        hue = (index * 60) % 360
        return self._hsv_to_rgb(hue, 1.0, 1.0)
    
    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[int, int, int, int]:
        """Convert HSV to RGB."""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h/360.0, s, v)
        return (int(r*255), int(g*255), int(b*255), 255)
    
    def _calculate_vertex_colors(self, vertices: np.ndarray, elevation_grid: np.ndarray, 
                                lat_grid: np.ndarray, lon_grid: np.ndarray) -> np.ndarray:
        """Calculate colors for each vertex based on elevation."""
        
        # Get elevation range from the original grid
        min_elev = np.min(elevation_grid)
        max_elev = np.max(elevation_grid)
        elev_range = max_elev - min_elev
        
        if elev_range == 0:
            # Flat terrain - use first color
            color = self.color_palette[0]
            return np.full((len(vertices), 4), color, dtype=np.uint8)
        
        # Get the Z coordinates from vertices (subtract base thickness)
        z_coords = vertices[:, 2] - self.config.terrain.base_thickness_mm
        
        # Normalize Z coordinates to elevation range
        z_min = np.min(z_coords)
        z_max = np.max(z_coords)
        z_range = z_max - z_min
        
        if z_range == 0:
            # All at same height
            color = self.color_palette[0]
            return np.full((len(vertices), 4), color, dtype=np.uint8)
        
        # Map Z coordinates to 0-1 range, then to color zones
        normalized_z = (z_coords - z_min) / z_range
        
        # Calculate color zones
        num_colors = len(self.color_palette)
        zone_indices = np.clip(np.floor(normalized_z * num_colors).astype(int), 0, num_colors - 1)
        
        # Apply colors
        vertex_colors = np.zeros((len(vertices), 4), dtype=np.uint8)
        for i, zone_idx in enumerate(zone_indices):
            vertex_colors[i] = self.color_palette[zone_idx]
        
        return vertex_colors
    
    def export_colored_mesh(self, mesh: trimesh.Trimesh, filename: str) -> str:
        """Export mesh with colors in the specified format."""
        
        format_ext = self.config.output.format.lower()
        
        # Ensure filename has correct extension
        if not filename.lower().endswith(f'.{format_ext}'):
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            filename = f"{base_name}.{format_ext}"
        
        try:
            if format_ext == '3mf':
                # Try to export with colors for 3MF
                print(f"Exporting 3MF with {len(mesh.visual.vertex_colors)} vertex colors")
                print(f"Color range: {mesh.visual.vertex_colors.min()} to {mesh.visual.vertex_colors.max()}")
                mesh.export(filename)
                return filename
            
            elif format_ext == 'amf':
                # AMF format supports colors and materials
                mesh.export(filename)
                return filename
            
            elif format_ext == 'obj':
                # OBJ format with MTL material file
                mesh.export(filename)
                return filename
            
            else:
                # STL format (fallback, no colors)
                mesh.export(filename)
                return filename
                
        except Exception as e:
            print(f"Warning: Color export failed ({e}), falling back to multi-STL approach")
            # Fallback: generate separate STL files instead
            from terraprint3d.mesh.multicolor import MultiColorMeshGenerator
            fallback_gen = MultiColorMeshGenerator(self.config)
            
            # We need the original elevation data for this, so this is a limitation
            # For now, just export without colors
            mesh_copy = mesh.copy()
            mesh_copy.visual = trimesh.visual.ColorVisuals()  # Remove colors
            mesh_copy.export(filename)
            return filename
    
    def save_color_reference(self, filename: str) -> str:
        """Save a color reference chart showing elevation zones and colors."""
        
        if not self.config.terrain.colors.enabled:
            return None
        
        import matplotlib.pyplot as plt
        
        # Create color reference
        fig, ax = plt.subplots(figsize=(8, 6))
        
        colors = self.color_palette
        color_names = self.config.terrain.colors.color_names or [f"Zone {i+1}" for i in range(len(colors))]
        
        # Convert colors to matplotlib format (0-1 range)
        mpl_colors = [(r/255, g/255, b/255) for r, g, b, a in colors]
        
        # Create color bars
        y_positions = range(len(colors))
        bars = ax.barh(y_positions, [1] * len(colors), color=mpl_colors, height=0.8)
        
        # Add labels
        ax.set_yticks(y_positions)
        ax.set_yticklabels([f"{name}\n(Zone {i+1})" for i, name in enumerate(color_names)])
        ax.set_xlabel('Elevation (Low → High)')
        ax.set_title('Terrain Color Reference\n(Bottom = Lowest Elevation, Top = Highest)')
        
        # Remove x-axis ticks
        ax.set_xticks([])
        
        # Add elevation zone labels
        zone_labels = ['Lowest', 'Low', 'Medium', 'High', 'Higher', 'Highest']
        for i, (bar, label) in enumerate(zip(bars, zone_labels[:len(colors)])):
            ax.text(0.5, bar.get_y() + bar.get_height()/2, label, 
                   ha='center', va='center', fontweight='bold', color='white')
        
        plt.tight_layout()
        
        # Save color reference
        color_ref_filename = filename.replace('.3mf', '_colors.png').replace('.amf', '_colors.png').replace('.obj', '_colors.png')
        plt.savefig(color_ref_filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        return color_ref_filename