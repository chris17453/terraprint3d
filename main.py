import click
import os
from terraprint3d.config.parser import Config
from terraprint3d.geocoding.service import GeocodingService
from terraprint3d.elevation.fetcher import ElevationFetcher
from terraprint3d.mesh.generator import MeshGenerator
from terraprint3d.mesh.simple_multicolor import SimpleMultiColorMeshGenerator
from terraprint3d.mesh.colored_export import ColoredMeshExporter
from terraprint3d.cache import ElevationCache
from terraprint3d.preview import PreviewGenerator


@click.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--google-api-key', envvar='GOOGLE_MAPS_API_KEY', help='Google Maps API key for geocoding and elevation data')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--no-cache', is_flag=True, help='Disable elevation data caching')
@click.option('--clear-cache', is_flag=True, help='Clear elevation cache and exit')
@click.option('--cache-info', is_flag=True, help='Show cache information and exit')
@click.option('--preview', is_flag=True, help='Generate PNG preview of the terrain model')
@click.option('--preview-type', type=click.Choice(['3d', 'heatmap', 'combined']), default='3d', help='Type of preview to generate')
def main(config_file, google_api_key, verbose, no_cache, clear_cache, cache_info, preview, preview_type):
    """Generate 3D printable terrain from YAML configuration."""
    
    try:
        # Handle cache management commands
        if clear_cache:
            cache = ElevationCache()
            cache.clear_cache()
            click.echo("✓ Elevation cache cleared")
            return
        
        if cache_info:
            cache = ElevationCache()
            info = cache.get_cache_info()
            click.echo(f"Cache directory: {info['cache_dir']}")
            click.echo(f"Cached files: {info['cache_files']}")
            click.echo(f"Total size: {info['total_size_mb']:.2f} MB")
            return
        
        if verbose:
            click.echo(f"Loading configuration from {config_file}")
        
        # Load and validate configuration
        config = Config.from_yaml(config_file)
        config.validate()
        
        if verbose:
            click.echo("Configuration loaded and validated successfully")
        
        # Initialize services
        geocoding_service = GeocodingService(google_api_key) if google_api_key else None
        elevation_fetcher = ElevationFetcher(google_api_key, cache_enabled=not no_cache)
        
        # Choose appropriate mesh generator based on output format and colors
        if config.output.format.lower() in ['3mf', 'amf', 'obj'] and config.terrain.colors.enabled:
            # Use colored export for formats that support embedded colors
            colored_exporter = ColoredMeshExporter(config)
            mesh_generator = MeshGenerator(config)
            use_colored_export = True
        elif config.terrain.colors.enabled or config.terrain.height_stepping.enabled:
            # Use simple multi-color generator for separate STL files
            mesh_generator = SimpleMultiColorMeshGenerator(config)
            use_colored_export = False
        else:
            # Standard single mesh
            mesh_generator = MeshGenerator(config)
            use_colored_export = False
        
        # Determine bounds
        bounds = config.location.bounds
        
        if config.location.address:
            if not google_api_key:
                raise click.ClickException("Google API key required for address geocoding")
            
            if verbose:
                click.echo(f"Geocoding address: {config.location.address}")
            
            bounds = geocoding_service.address_to_bounds(
                config.location.address, 
                config.location.radius_km
            )
            
            if verbose:
                click.echo(f"Bounds: N={bounds.north:.4f}, S={bounds.south:.4f}, E={bounds.east:.4f}, W={bounds.west:.4f}")
        
        # Fetch elevation data
        if verbose:
            click.echo("Fetching elevation data...")
        
        lat_grid, lon_grid, elevation_grid = elevation_fetcher.fetch_elevation_grid(
            bounds, 
            config.terrain.resolution_meters
        )
        
        if verbose:
            click.echo(f"Elevation data shape: {elevation_grid.shape}")
            click.echo(f"Elevation range: {elevation_grid.min():.1f}m to {elevation_grid.max():.1f}m")
        
        # Generate mesh(es)
        if verbose:
            click.echo("Generating 3D mesh...")
        
        if use_colored_export:
            # Single mesh with embedded colors (3MF, AMF, OBJ)
            mesh = colored_exporter.create_colored_mesh(lat_grid, lon_grid, elevation_grid)
            
            if verbose:
                click.echo(f"Colored mesh generated: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
            
            # Save colored mesh
            output_path = config.output.filename
            if verbose:
                click.echo(f"Saving colored {config.output.format.upper()} to {output_path}")
            
            final_filename = colored_exporter.export_colored_mesh(mesh, output_path)
            click.echo(f"✓ Colored terrain model saved to {final_filename}")
            
            # Warning about 3MF compatibility
            if config.output.format.lower() == '3mf':
                click.echo("⚠️  Note: Bambu Lab may import this as geometry only (no colors)")
                click.echo("   For guaranteed multi-color printing, use separate STL files:")
                click.echo("   Set format: 'stl' and colors: enabled: true")
            
            # Save color reference chart
            if verbose:
                color_ref = colored_exporter.save_color_reference(final_filename)
                if color_ref:
                    click.echo(f"✓ Color reference saved to {color_ref}")
        
        elif isinstance(mesh_generator, SimpleMultiColorMeshGenerator):
            # Multi-color generation (separate STL files)
            meshes = mesh_generator.generate_multi_color_meshes(lat_grid, lon_grid, elevation_grid)
            
            if verbose:
                total_vertices = sum(len(mesh.vertices) for mesh in meshes.values())
                total_faces = sum(len(mesh.faces) for mesh in meshes.values())
                click.echo(f"Generated {len(meshes)} color zones: {total_vertices} vertices, {total_faces} faces total")
            
            # Save STL files
            output_path = config.output.filename
            if verbose:
                click.echo(f"Saving STL files...")
            
            filenames = mesh_generator.save_multi_color_stls(meshes, output_path)
            
            if len(filenames) == 1:
                click.echo(f"✓ Terrain model saved to {filenames[0]}")
            else:
                click.echo(f"✓ Multi-color terrain saved to {len(filenames)} files:")
                for filename in filenames:
                    click.echo(f"  - {filename}")
            
            # Use first mesh for preview and dimensions
            mesh = list(meshes.values())[0]
        else:
            # Single color generation
            mesh = mesh_generator.generate_mesh(lat_grid, lon_grid, elevation_grid)
            
            if verbose:
                click.echo(f"Mesh generated: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
            
            # Save file
            output_path = config.output.filename
            if verbose:
                click.echo(f"Saving {config.output.format.upper()} to {output_path}")
            
            mesh_generator.save_stl(mesh, output_path)
            click.echo(f"✓ Terrain model saved to {output_path}")
        
        # Generate preview if requested
        if preview:
            preview_generator = PreviewGenerator()
            # Handle different file extensions for preview naming
            if output_path.endswith('.3mf'):
                preview_path = output_path.replace('.3mf', '_preview.png')
            elif output_path.endswith('.amf'):
                preview_path = output_path.replace('.amf', '_preview.png')
            elif output_path.endswith('.obj'):
                preview_path = output_path.replace('.obj', '_preview.png')
            else:
                preview_path = output_path.replace('.stl', '_preview.png')
            
            if verbose:
                click.echo(f"Generating {preview_type} preview...")
            
            try:
                if preview_type == '3d':
                    preview_generator.generate_preview(mesh, preview_path, 
                                                     title=f"Terrain Preview - {os.path.basename(output_path)}")
                elif preview_type == 'heatmap':
                    preview_generator.generate_elevation_heatmap(lat_grid, lon_grid, elevation_grid, 
                                                               preview_path, title="Elevation Heatmap")
                elif preview_type == 'combined':
                    preview_generator.generate_combined_preview(mesh, lat_grid, lon_grid, elevation_grid,
                                                              preview_path, title="Terrain Model")
                
                click.echo(f"✓ Preview saved to {preview_path}")
            except Exception as e:
                if verbose:
                    click.echo(f"Warning: Preview generation failed: {e}")
                else:
                    click.echo("Warning: Preview generation failed")
        
        if verbose:
            # Calculate print dimensions
            bounds_3d = mesh.bounds
            width = bounds_3d[1][0] - bounds_3d[0][0]
            depth = bounds_3d[1][1] - bounds_3d[0][1]
            height = bounds_3d[1][2] - bounds_3d[0][2]
            
            click.echo(f"Print dimensions: {width:.1f}mm × {depth:.1f}mm × {height:.1f}mm")
        
    except Exception as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
