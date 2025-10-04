import googlemaps
import math
from typing import Tuple
from terraprint3d.config.parser import BoundsConfig


class GeocodingService:
    def __init__(self, api_key: str):
        self.client = googlemaps.Client(key=api_key)
    
    def address_to_coordinates(self, address: str) -> Tuple[float, float]:
        """Convert address to lat/lon coordinates."""
        result = self.client.geocode(address)
        if not result:
            raise ValueError(f"Could not geocode address: {address}")
        
        location = result[0]['geometry']['location']
        return location['lat'], location['lng']
    
    def coordinates_to_bounds(self, lat: float, lon: float, radius_km: float) -> BoundsConfig:
        """Convert center coordinates and radius to bounding box."""
        # Earth's radius in kilometers
        earth_radius_km = 6371.0
        
        # Convert radius to degrees
        lat_delta = (radius_km / earth_radius_km) * (180 / math.pi)
        lon_delta = (radius_km / earth_radius_km) * (180 / math.pi) / math.cos(math.radians(lat))
        
        return BoundsConfig(
            north=lat + lat_delta,
            south=lat - lat_delta,
            east=lon + lon_delta,
            west=lon - lon_delta
        )
    
    def address_to_bounds(self, address: str, radius_km: float) -> BoundsConfig:
        """Convert address and radius to bounding box."""
        lat, lon = self.address_to_coordinates(address)
        return self.coordinates_to_bounds(lat, lon, radius_km)