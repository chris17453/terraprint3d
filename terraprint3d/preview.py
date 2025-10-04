import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import trimesh
from pathlib import Path


class PreviewGenerator:
    def __init__(self):
        # Set up matplotlib for high quality output
        plt.rcParams['figure.dpi'] = 150
        plt.rcParams['savefig.dpi'] = 300
        plt.rcParams['font.size'] = 10
    
    def generate_preview(self, mesh: trimesh.Trimesh, output_path: str, 
                        title: str = "Terrain Preview", 
                        view_angle: tuple = (30, 45)) -> None:
        """Generate a PNG preview of the 3D mesh from an angled perspective."""
        
        # Create figure and 3D axis
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Extract vertices and faces
        vertices = mesh.vertices
        faces = mesh.faces
        
        # Create the 3D surface plot
        ax.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2], 
                       triangles=faces, cmap='terrain', alpha=0.9,
                       linewidth=0, antialiased=True, shade=True)
        
        # Set viewing angle
        ax.view_init(elev=view_angle[0], azim=view_angle[1])
        
        # Calculate mesh bounds for proper scaling
        bounds = mesh.bounds
        x_range = bounds[1][0] - bounds[0][0]
        y_range = bounds[1][1] - bounds[0][1]
        z_range = bounds[1][2] - bounds[0][2]
        
        # Set equal aspect ratio
        max_range = max(x_range, y_range, z_range)
        mid_x = (bounds[1][0] + bounds[0][0]) / 2
        mid_y = (bounds[1][1] + bounds[0][1]) / 2
        mid_z = (bounds[1][2] + bounds[0][2]) / 2
        
        ax.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
        ax.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
        ax.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
        
        # Labels and title
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Add grid and improve appearance
        ax.grid(True, alpha=0.3)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        
        # Make pane edges more subtle
        ax.xaxis.pane.set_edgecolor('gray')
        ax.yaxis.pane.set_edgecolor('gray')
        ax.zaxis.pane.set_edgecolor('gray')
        ax.xaxis.pane.set_alpha(0.1)
        ax.yaxis.pane.set_alpha(0.1)
        ax.zaxis.pane.set_alpha(0.1)
        
        # Add some metadata text
        info_text = f"Dimensions: {x_range:.1f} × {y_range:.1f} × {z_range:.1f} mm\n"
        info_text += f"Vertices: {len(vertices):,} | Faces: {len(faces):,}"
        
        fig.text(0.02, 0.02, info_text, fontsize=8, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        # Save with high quality
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1, 
                   facecolor='white', edgecolor='none')
        plt.close()
    
    def generate_elevation_heatmap(self, lat_grid: np.ndarray, lon_grid: np.ndarray, 
                                  elevation_grid: np.ndarray, output_path: str,
                                  title: str = "Elevation Heatmap") -> None:
        """Generate a 2D heatmap of the elevation data."""
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create heatmap
        im = ax.imshow(elevation_grid, cmap='terrain', aspect='equal', 
                      extent=[lon_grid.min(), lon_grid.max(), 
                             lat_grid.min(), lat_grid.max()],
                      origin='lower')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('Elevation (m)', rotation=270, labelpad=20)
        
        # Labels and title
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Add elevation range info
        min_elev = elevation_grid.min()
        max_elev = elevation_grid.max()
        info_text = f"Elevation range: {min_elev:.1f}m to {max_elev:.1f}m"
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
               verticalalignment='top')
        
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1,
                   dpi=300, facecolor='white', edgecolor='none')
        plt.close()
    
    def generate_combined_preview(self, mesh: trimesh.Trimesh, 
                                lat_grid: np.ndarray, lon_grid: np.ndarray, 
                                elevation_grid: np.ndarray, output_path: str,
                                title: str = "Terrain Model") -> None:
        """Generate a combined preview with both 3D model and elevation heatmap."""
        
        fig = plt.figure(figsize=(16, 8))
        
        # 3D plot on the left
        ax1 = fig.add_subplot(121, projection='3d')
        vertices = mesh.vertices
        faces = mesh.faces
        
        ax1.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2], 
                        triangles=faces, cmap='terrain', alpha=0.9,
                        linewidth=0, antialiased=True, shade=True)
        
        ax1.view_init(elev=30, azim=45)
        ax1.set_title('3D Model Preview', fontweight='bold')
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Y (mm)')
        ax1.set_zlabel('Z (mm)')
        
        # 2D heatmap on the right
        ax2 = fig.add_subplot(122)
        im = ax2.imshow(elevation_grid, cmap='terrain', aspect='equal',
                       extent=[lon_grid.min(), lon_grid.max(), 
                              lat_grid.min(), lat_grid.max()],
                       origin='lower')
        
        cbar = plt.colorbar(im, ax=ax2, shrink=0.8)
        cbar.set_label('Elevation (m)', rotation=270, labelpad=20)
        
        ax2.set_title('Elevation Data', fontweight='bold')
        ax2.set_xlabel('Longitude')
        ax2.set_ylabel('Latitude')
        ax2.grid(True, alpha=0.3)
        
        # Overall title
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1,
                   dpi=300, facecolor='white', edgecolor='none')
        plt.close()