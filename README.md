# TerraPrint3D

A Python application for generating 3D printable terrain models from elevation data with multi-color layer support.

## Overview

TerraPrint3D converts geographic elevation data into 3D mesh files suitable for multi-color 3D printing. The application supports various output formats including STL, 3MF, AMF, and OBJ, with specialized support for multi-color printing through separate layer files.

## Features

- Elevation data fetching from multiple sources
- Multi-color terrain generation with configurable layer thickness
- Support for multiple output formats (STL, 3MF, AMF, OBJ)
- Configurable terrain parameters including resolution and vertical exaggeration
- Built-in mesh validation and repair
- Caching system for elevation data
- Preview generation capabilities
- Bambu Lab Studio compatibility

## Installation

### Requirements

- Python 3.8 or higher
- UV package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd TerraPrint3D
```

2. Install dependencies:
```bash
uv sync
```

3. (Optional) Set up Google Maps API key for geocoding:
```bash
export GOOGLE_MAPS_API_KEY=your_api_key_here
```

## Configuration

Create a YAML configuration file specifying the terrain parameters:

```yaml
location:
  bounds:
    north: 47.6200
    south: 47.6000
    east: -122.3200
    west: -122.3400

output:
  filename: "terrain_model.stl"
  printer_bed_mm: 220
  format: "stl"

terrain:
  resolution_meters: 100
  vertical_exaggeration: 3.0
  base_thickness_mm: 4.0
  
  colors:
    enabled: true
    num_colors: 4
    color_mode: "elevation"
    layer_thickness_mm: 3.0
```

## Usage

### Basic Command

```bash
uv run python main.py config.yaml
```

### Command Line Options

- `--verbose, -v`: Enable detailed output
- `--no-cache`: Disable elevation data caching
- `--clear-cache`: Clear cached elevation data
- `--cache-info`: Display cache statistics
- `--preview`: Generate PNG preview
- `--preview-type`: Specify preview type (3d, heatmap, combined)
- `--google-api-key`: Provide Google Maps API key

### Examples

Generate terrain with verbose output:
```bash
uv run python main.py examples/multicolor_test.yaml --verbose
```

Generate with preview:
```bash
uv run python main.py config.yaml --preview --preview-type combined
```

Clear elevation cache:
```bash
uv run python main.py config.yaml --clear-cache
```

## Output Formats

### Multi-Color STL Files

When multi-color is enabled, the application generates separate STL files for each elevation zone:
- `terrain_model_layer00.stl` - Base layer
- `terrain_model_layer01.stl` - Lowest elevation zone
- `terrain_model_layer02.stl` - Second elevation zone
- etc.

### Single File Formats

For 3MF, AMF, and OBJ formats with colors enabled, a single file with embedded color information is generated.

## Configuration Parameters

### Location

- `bounds`: Geographic boundaries (north, south, east, west in decimal degrees)
- `address`: Alternative to bounds - specify address with radius
- `radius_km`: Search radius when using address

### Output

- `filename`: Output file name
- `printer_bed_mm`: Printer bed size for scaling
- `format`: Output format (stl, 3mf, amf, obj)

### Terrain

- `resolution_meters`: Grid resolution for elevation sampling
- `vertical_exaggeration`: Height scaling factor
- `base_thickness_mm`: Thickness of the base layer

### Colors

- `enabled`: Enable multi-color generation
- `num_colors`: Number of color zones
- `color_mode`: Color assignment method (elevation)
- `layer_thickness_mm`: Thickness of each color layer

## Architecture

### Core Components

- **ElevationFetcher**: Retrieves elevation data from external APIs
- **MeshGenerator**: Creates 3D meshes from elevation grids
- **SimpleMultiColorMeshGenerator**: Specialized generator for multi-color terrain
- **ColoredMeshExporter**: Handles colored mesh export formats
- **PreviewGenerator**: Creates visualization previews

### Multi-Color Processing

The multi-color system divides terrain into elevation zones and generates separate meshes for each zone. Boundary detection ensures proper connectivity between layers while minimizing geometric conflicts.

## Troubleshooting

### Common Issues

1. **API Rate Limiting**: Use caching to reduce API calls
2. **Large File Sizes**: Reduce resolution_meters value
3. **Memory Usage**: Lower resolution for large geographic areas
4. **Mesh Validation Errors**: Check terrain bounds and resolution

### Debug Information

Enable verbose mode to access detailed processing information including:
- Zone boundary analysis
- Mesh statistics
- Face creation summaries
- Border conflict detection

### Cache Management

The application maintains a cache of elevation data to improve performance:
- Cache location: User-specific cache directory
- Use `--cache-info` to view cache statistics
- Use `--clear-cache` to reset cached data

## Contributing

1. Follow existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure compatibility with existing configuration files

## License

[License information to be added]

## Support

For issues and feature requests, please use the project issue tracker.