# Multi-Color 3D Printing Guide

## Important: STL Files Don't Contain Color

STL files only contain 3D geometry, not color information. For multi-color printing, you need to:

1. **Load each color STL as a separate object**
2. **Assign different filaments to each object**
3. **Ensure proper layer alignment**

## Bambu Lab Studio Setup

### Step 1: Import All Color Files
```
File → Import → Select all color STL files
Example files: terrain_blue.stl, terrain_green.stl, terrain_yellow.stl, terrain_red.stl
```

### Step 2: Position Objects
- All terrain parts should be in the **exact same position** (they're pre-aligned)
- Don't move them - they're designed to stack/overlap correctly

### Step 3: Assign Filaments
1. Select `terrain_blue.stl` → Assign to **Filament 1** (Blue)
2. Select `terrain_green.stl` → Assign to **Filament 2** (Green)  
3. Select `terrain_yellow.stl` → Assign to **Filament 3** (Yellow)
4. Select `terrain_red.stl` → Assign to **Filament 4** (Red)

### Step 4: Check Layer View
- Switch to **Layer View** to see color changes by elevation
- Each color should appear at different Z-heights
- Blue = lowest elevations, Red = highest elevations

## Prusa Slicer Setup

### Multi-Material Unit (MMU)
1. **Import all STL files**
2. **Right-click each object** → Change Filament → Select color
3. **Ensure objects are aligned** (don't move them)
4. **Check layer preview** for color transitions

### Manual Color Changes
1. **Load only 2-3 color STLs** (for manual changes)
2. **Note Z-heights** where colors change
3. **Add manual color change G-code** at those heights

## Simplify3D / Other Slicers

### Process Setup
1. **Create separate processes** for each color STL
2. **Use same base settings** but different extruders/colors
3. **Combine processes** in print queue
4. **Verify layer alignment**

## Alternative: Single STL with Height-Based Coloring

For slicers that support height-based color changes:

```yaml
# Use height stepping instead of multi-color STLs
terrain:
  height_stepping:
    enabled: true
    step_height_mm: 5.0  # Change color every 5mm
    smooth_transitions: false
  colors:
    enabled: false  # Generate single STL
```

Then in your slicer:
- **Add color changes** at each step height (5mm, 10mm, 15mm, etc.)
- **Manually change filament** at each pause

## Troubleshooting Multi-Color Issues

### Objects Don't Align
- **Don't move imported objects** - they're pre-positioned
- **Check that all STLs are from the same generation run**
- **Verify base thickness is consistent**

### Missing Color Zones
- **Check elevation range** in your area
- **Reduce num_colors** if terrain is mostly flat
- **Increase vertical_exaggeration** for more dramatic height differences

### Filament Waste
- **Use fewer colors** (2-3) for efficient printing
- **Group similar elevations** into single colors
- **Consider height stepping** instead of pure multi-color

## Recommended Color Schemes

### Topographic (4 colors)
```yaml
color_names: ["blue", "green", "yellow", "red"]
# Blue = water/low areas
# Green = valleys/forests  
# Yellow = hills/plains
# Red = peaks/mountains
```

### Ocean to Mountain (6 colors)
```yaml
color_names: ["navy", "blue", "cyan", "green", "yellow", "red"]
# Navy = deep water
# Blue = shallow water
# Cyan = coastline
# Green = lowlands
# Yellow = hills
# Red = peaks
```

### Simple Contrast (2 colors)
```yaml
color_names: ["dark", "light"]
# Dark = lower elevations
# Light = higher elevations
```

## Example Workflow

1. **Generate multi-color terrain**:
   ```bash
   python main.py examples/multicolor_seattle.yaml --verbose
   ```

2. **Files created**:
   - `seattle_multicolor_blue.stl`
   - `seattle_multicolor_green.stl` 
   - `seattle_multicolor_yellow.stl`
   - `seattle_multicolor_red.stl`

3. **Import all 4 files** into Bambu Studio

4. **Assign filament colors**:
   - Blue STL → Filament 1 (Blue PLA)
   - Green STL → Filament 2 (Green PLA)
   - Yellow STL → Filament 3 (Yellow PLA)
   - Red STL → Filament 4 (Red PLA)

5. **Slice and print** with automatic color changes