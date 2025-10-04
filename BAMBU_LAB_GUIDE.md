# Bambu Lab Multi-Color Printing Guide

## ⚠️ Confirmed: 3MF Colors Don't Work with Bambu Lab

**Tested and confirmed**: While TerraPrint3D generates 3MF files with embedded vertex colors, **Bambu Lab Studio imports them as geometry only - no colors**. The 3MF specification supports colors, but Bambu Lab doesn't implement vertex color recognition.

## Recommended Workflow for Bambu Lab

### Option 1: Separate STL Files (Recommended)
Use the separate STL approach for the most reliable multi-color printing:

```yaml
# Use this configuration for Bambu Lab
output:
  filename: "seattle_terrain.stl"
  format: "stl"  # This generates multiple STL files
terrain:
  colors:
    enabled: true
    num_colors: 4
    color_names: ["blue", "green", "yellow", "red"]
```

**Result**: 4 separate files:
- `seattle_terrain_blue.stl` (lowest elevations)
- `seattle_terrain_green.stl` 
- `seattle_terrain_yellow.stl`
- `seattle_terrain_red.stl` (highest elevations)

**Bambu Studio Workflow**:
1. Import all 4 STL files
2. They will stack perfectly (same position)
3. Assign each STL to a different filament slot:
   - Blue STL → Filament 1 (Blue PLA)
   - Green STL → Filament 2 (Green PLA)
   - Yellow STL → Filament 3 (Yellow PLA)
   - Red STL → Filament 4 (Red PLA)
4. Slice and print with automatic color changes

### Option 2: Height-Based Color Changes
Use a single STL with manual color changes:

```yaml
terrain:
  height_stepping:
    enabled: true
    step_height_mm: 5.0  # Change color every 5mm
    smooth_transitions: false
  colors:
    enabled: false  # Single STL output
```

**Bambu Studio Workflow**:
1. Import single STL file
2. Add **manual color changes** at specific Z-heights:
   - 5mm → Change to green
   - 10mm → Change to yellow  
   - 15mm → Change to red
3. Printer will pause at each height for filament change

## Generated Files

All examples now include PNG previews:

```bash
make seattle-colors    # Generates STLs + preview PNG
make seattle-3mf       # Generates 3MF + preview PNG + color reference
make seattle-stepped   # Generates stepped STL + preview PNG
```

**Files Created**:
- `terrain_model.stl` (or multiple colored STLs)
- `terrain_model_preview.png` (3D visualization)
- `terrain_model_colors.png` (color reference chart for multi-color)

## Why 3MF Colors Don't Work

1. **Different Implementations**: Each slicer interprets 3MF color data differently
2. **Vertex vs Face Colors**: Some slicers expect face colors, others vertex colors
3. **Material Mapping**: Bambu Studio expects materials/filaments, not just colors
4. **Standards Variance**: 3MF color specification is implemented inconsistently

## Best Results: Separate STLs

The separate STL approach gives you:
- ✅ **Guaranteed compatibility** with Bambu Lab
- ✅ **Perfect alignment** (files are pre-positioned)  
- ✅ **Clear material assignment** (one STL = one filament)
- ✅ **Preview images** to see expected results
- ✅ **Color reference charts** showing elevation zones

## Example Commands

```bash
# Generate 4-color terrain for Bambu Lab (separate STLs)
make seattle-colors

# View what was created
ls *.stl *.png
# seattle_multicolor_blue.stl
# seattle_multicolor_green.stl  
# seattle_multicolor_yellow.stl
# seattle_multicolor_red.stl
# seattle_multicolor_preview.png

# Generate 3MF for testing (may not show colors in Bambu Studio)
make seattle-3mf
```

## Pro Tips

1. **Use 2-4 colors** for best print efficiency
2. **Check the preview PNG** to see color distribution
3. **Use the color reference chart** to understand elevation mapping
4. **Test with small areas first** (`make small-test`)
5. **Consider height stepping** for dramatic terraced effects

The separate STL approach is currently the most reliable way to get multi-color terrain prints with Bambu Lab printers!