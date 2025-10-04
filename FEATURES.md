# TerraPrint3D Features

## Configuration Options

### Basic Terrain Settings
```yaml
terrain:
  resolution_meters: 50        # Sampling resolution (lower = more detail)
  vertical_exaggeration: 2.0   # Height multiplier for dramatic effect
  base_thickness_mm: 5.0       # Base thickness for 3D printing
```

### Height Stepping
Create terraced terrain with discrete elevation levels:
```yaml
terrain:
  height_stepping:
    enabled: true
    step_height_mm: 3.0         # Height of each terrace step
    smooth_transitions: false   # true = gradual, false = sharp steps
```

### Multi-Color Printing (1-6 Colors)
Generate separate STL files for each elevation zone:
```yaml
terrain:
  colors:
    enabled: true
    num_colors: 4               # 1-6 colors for multi-material printers
    color_mode: "elevation"     # "elevation" or "slope" 
    color_names: ["blue", "green", "yellow", "red"]  # Optional custom names
```

## Output Options

### Single Color
- Generates one STL file: `terrain.stl`
- Standard single-material printing

### Multi-Color (2-6 colors)
- Generates multiple STL files: `terrain_blue.stl`, `terrain_green.stl`, etc.
- Each file represents one elevation zone
- Load each file with different colors in your slicer

### Preview Generation
```bash
# 3D angled view
python main.py config.yaml --preview --preview-type 3d

# Elevation heatmap
python main.py config.yaml --preview --preview-type heatmap  

# Combined view (3D + heatmap)
python main.py config.yaml --preview --preview-type combined
```

## Example Configurations

### Basic Single Color
```yaml
location:
  bounds: {north: 47.62, south: 47.60, east: -122.32, west: -122.34}
output:
  filename: "terrain.stl"
  printer_bed_mm: 220
terrain:
  resolution_meters: 100
  vertical_exaggeration: 2.0
  base_thickness_mm: 5.0
```

### 4-Color Elevation Zones
```yaml
location:
  bounds: {north: 47.62, south: 47.60, east: -122.32, west: -122.34}
output:
  filename: "terrain_multicolor.stl"
terrain:
  resolution_meters: 100
  vertical_exaggeration: 3.0
  colors:
    enabled: true
    num_colors: 4
    color_names: ["blue", "green", "yellow", "red"]
```

### Height Stepped Terrain
```yaml
terrain:
  height_stepping:
    enabled: true
    step_height_mm: 2.5
    smooth_transitions: true
  colors:
    enabled: false  # Single color stepped terrain
```

## Command Line Examples

```bash
# Basic terrain generation
python main.py examples/seattle_terrain.yaml --verbose

# Multi-color with preview
python main.py examples/multicolor_seattle.yaml --preview --verbose

# Height stepping without cache
python main.py examples/stepped_terrain.yaml --no-cache --verbose

# Show cache information
python main.py --cache-info examples/small_test.yaml

# Clear elevation cache
python main.py --clear-cache examples/small_test.yaml
```

## Makefile Targets

```bash
# Quick examples
make small-test      # Fast test with small area
make seattle-colors  # 4-color Seattle terrain
make seattle-stepped # Height-stepped terrain

# Generate previews
make preview-3d      # 3D preview
make preview-combined # 3D + heatmap

# Cache management
make cache-info      # Show cache status
make clean           # Remove generated files
```

## Multi-Material Printer Setup

### Prusa i3 MK3S+ (5 colors)
```yaml
colors:
  num_colors: 5
  color_names: ["blue", "green", "yellow", "orange", "red"]
```

### Bambu Lab X1 Carbon (4 colors)
```yaml  
colors:
  num_colors: 4
  color_names: ["blue", "cyan", "yellow", "red"]
```

### Manual Color Changes (2-3 colors)
```yaml
colors:
  num_colors: 2
  color_names: ["base", "peaks"]
```

## Elevation Data Sources
- **Free**: Open-Elevation API (slower, no API key needed)
- **Premium**: Google Elevation API (faster, requires `GOOGLE_MAPS_API_KEY`)

## File Outputs
- **STL files**: 3D printable mesh files
- **PNG previews**: Visual previews of terrain
- **Cache files**: Elevation data cache (in `data/elevation_cache/`)