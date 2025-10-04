import yaml
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class BoundsConfig:
    north: float
    south: float
    east: float
    west: float


@dataclass
class LocationConfig:
    address: Optional[str] = None
    radius_km: Optional[float] = None
    bounds: Optional[BoundsConfig] = None


@dataclass
class OutputConfig:
    filename: str
    printer_bed_mm: int = 220
    format: str = "stl"  # "stl", "3mf", "amf", "obj"


@dataclass
class HeightSteppingConfig:
    enabled: bool = False
    step_height_mm: float = 2.0  # Height of each step
    smooth_transitions: bool = True  # Smooth step edges vs sharp


@dataclass
class ColorConfig:
    enabled: bool = False
    num_colors: int = 1  # 1-6 colors for multi-color printing
    color_mode: str = "elevation"  # "elevation" or "slope"
    color_names: list = None  # Optional color names for file output
    layer_thickness_mm: float = 2.0  # Thickness of color layers in mm


@dataclass
class TerrainConfig:
    resolution_meters: int = 30
    vertical_exaggeration: float = 2.0
    base_thickness_mm: float = 5.0
    height_stepping: HeightSteppingConfig = None
    colors: ColorConfig = None


@dataclass
class Config:
    location: LocationConfig
    output: OutputConfig
    terrain: TerrainConfig

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'Config':
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        location_data = data['location']
        
        bounds = None
        if 'bounds' in location_data:
            bounds = BoundsConfig(**location_data['bounds'])
        
        location = LocationConfig(
            address=location_data.get('address'),
            radius_km=location_data.get('radius_km'),
            bounds=bounds
        )
        
        output = OutputConfig(**data['output'])
        
        # Parse terrain config with optional nested configs
        terrain_data = data['terrain'].copy()
        
        # Parse height stepping config
        height_stepping = None
        if 'height_stepping' in terrain_data:
            height_stepping = HeightSteppingConfig(**terrain_data.pop('height_stepping'))
        else:
            height_stepping = HeightSteppingConfig()
        
        # Parse color config
        colors = None
        if 'colors' in terrain_data:
            color_data = terrain_data.pop('colors')
            colors = ColorConfig(**color_data)
        else:
            colors = ColorConfig()
        
        terrain = TerrainConfig(
            **terrain_data,
            height_stepping=height_stepping,
            colors=colors
        )
        
        return cls(location=location, output=output, terrain=terrain)
    
    def validate(self) -> None:
        if self.location.address is None and self.location.bounds is None:
            raise ValueError("Either address or bounds must be specified")
        
        if self.location.address and self.location.radius_km is None:
            raise ValueError("radius_km must be specified when using address")
        
        if self.location.bounds and self.location.address:
            raise ValueError("Cannot specify both address and bounds")
        
        if self.location.bounds:
            b = self.location.bounds
            if b.north <= b.south:
                raise ValueError("North bound must be greater than south bound")
            if b.east <= b.west:
                raise ValueError("East bound must be greater than west bound")
        
        # Validate color configuration
        if self.terrain.colors.enabled:
            if not (1 <= self.terrain.colors.num_colors <= 6):
                raise ValueError("Number of colors must be between 1 and 6")
            if self.terrain.colors.color_mode not in ["elevation", "slope"]:
                raise ValueError("Color mode must be 'elevation' or 'slope'")
        
        # Validate height stepping
        if self.terrain.height_stepping.enabled:
            if self.terrain.height_stepping.step_height_mm <= 0:
                raise ValueError("Step height must be positive")
        
        # Validate output format
        valid_formats = ["stl", "3mf", "amf", "obj"]
        if self.output.format.lower() not in valid_formats:
            raise ValueError(f"Output format must be one of: {valid_formats}")