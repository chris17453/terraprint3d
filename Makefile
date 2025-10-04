# TerraPrint3D Makefile - Examples and common tasks
# Usage: make [target]

.PHONY: help clean examples single-color multi-color stepped preview cache

# Python command
PYTHON = uv run python

# Default target
help:
	@echo "TerraPrint3D - 3D Printable Terrain Generator"
	@echo ""
	@echo "Available targets:"
	@echo "  help          - Show this help message"
	@echo "  examples      - Generate all example terrains"
	@echo "  single-color  - Generate single color examples"
	@echo "  multi-color   - Generate multi-color examples"
	@echo "  stepped       - Generate height-stepped examples"
	@echo "  preview       - Generate examples with previews"
	@echo "  cache-info    - Show elevation cache information"
	@echo "  clean         - Clean generated files"
	@echo ""
	@echo "Quick Examples:"
	@echo "  make small-test      - Fast test with small area"
	@echo "  make seattle-basic   - Basic Seattle terrain"
	@echo "  make seattle-colors  - 4-color Seattle (BEST for Bambu Lab)"
	@echo "  make seattle-stepped - Height-stepped Seattle"
	@echo "  make seattle-6color  - 6-color Seattle (full range)"
	@echo ""
	@echo "For Bambu Lab multi-color printing, use seattle-colors (separate STLs)"

# Quick test examples (with previews)
small-test:
	@echo "Generating small test terrain with preview..."
	$(PYTHON) main.py examples/small_test.yaml --preview --preview-type combined --verbose

seattle-basic:
	@echo "Generating basic Seattle terrain with preview..."
	$(PYTHON) main.py examples/seattle_terrain.yaml --preview --preview-type 3d --verbose

seattle-colors:
	@echo "Generating 4-color Seattle terrain with preview..."
	$(PYTHON) main.py examples/multicolor_seattle.yaml --preview --preview-type combined --verbose

seattle-stepped:
	@echo "Generating height-stepped Seattle terrain with preview..."
	$(PYTHON) main.py examples/stepped_terrain.yaml --preview --preview-type 3d --verbose

seattle-6color:
	@echo "Generating 6-color Seattle terrain with preview..."
	$(PYTHON) main.py examples/six_color_terrain.yaml --preview --preview-type combined --verbose

# Colored format examples (with previews)
seattle-3mf:
	@echo "Generating 3MF with embedded colors (for Bambu Lab) with preview..."
	$(PYTHON) main.py examples/colored_3mf.yaml --preview --preview-type combined --verbose

seattle-amf:
	@echo "Generating AMF with embedded colors with preview..."
	$(PYTHON) main.py examples/colored_amf.yaml --preview --preview-type combined --verbose

# Example collections
single-color:
	@echo "Generating single-color examples..."
	$(PYTHON) main.py examples/small_test.yaml --verbose
	$(PYTHON) main.py examples/seattle_terrain.yaml --verbose
	$(PYTHON) main.py examples/example_bounds.yaml --verbose

multi-color:
	@echo "Generating multi-color examples..."
	$(PYTHON) main.py examples/multicolor_seattle.yaml --verbose
	$(PYTHON) main.py examples/six_color_terrain.yaml --verbose

colored-formats:
	@echo "Generating colored format examples..."
	$(PYTHON) main.py examples/colored_3mf.yaml --verbose
	$(PYTHON) main.py examples/colored_amf.yaml --verbose

stepped:
	@echo "Generating height-stepped examples..."
	$(PYTHON) main.py examples/stepped_terrain.yaml --verbose

# Preview examples
preview:
	@echo "Generating examples with previews..."
	$(PYTHON) main.py examples/small_test.yaml --preview --preview-type combined --verbose
	$(PYTHON) main.py examples/multicolor_seattle.yaml --preview --preview-type 3d --verbose

examples: single-color multi-color stepped
	@echo "All examples generated!"

# Preview types
preview-3d:
	$(PYTHON) main.py examples/small_test.yaml --preview --preview-type 3d --verbose

preview-heatmap:
	$(PYTHON) main.py examples/small_test.yaml --preview --preview-type heatmap --verbose

preview-combined:
	$(PYTHON) main.py examples/small_test.yaml --preview --preview-type combined --verbose

# Cache management
cache-info:
	@echo "Elevation cache information:"
	$(PYTHON) main.py --cache-info examples/small_test.yaml

cache-clear:
	@echo "Clearing elevation cache..."
	$(PYTHON) main.py --clear-cache examples/small_test.yaml

# Test with different API configurations
test-no-cache:
	@echo "Testing without cache..."
	$(PYTHON) main.py examples/small_test.yaml --no-cache --verbose

# Development targets
install:
	@echo "Installing dependencies..."
	uv sync

# Demonstrate all features
demo: small-test seattle-colors preview-combined cache-info
	@echo ""
	@echo "Demo complete! Generated files:"
	@ls -la *.stl *.png 2>/dev/null || echo "No output files found"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -f *.stl
	rm -f *.png
	rm -f *_preview.png
	@echo "Cleaned STL and PNG files"

clean-cache:
	@echo "Cleaning cache and generated files..."
	rm -rf data/elevation_cache/*
	rm -f *.stl
	rm -f *.png
	@echo "Cleaned cache and output files"

# Configuration examples
show-configs:
	@echo "=== Single Color Configuration ==="
	@cat examples/small_test.yaml
	@echo ""
	@echo "=== Multi-Color Configuration ==="
	@cat examples/multicolor_seattle.yaml
	@echo ""
	@echo "=== Height Stepping Configuration ==="
	@cat examples/stepped_terrain.yaml

# Performance testing
perf-test:
	@echo "Performance test with different resolutions..."
	@echo "High resolution (30m):"
	@time $(PYTHON) main.py examples/seattle_terrain.yaml --verbose
	@echo "Medium resolution (100m):"
	@time $(PYTHON) main.py examples/multicolor_seattle.yaml --verbose