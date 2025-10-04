import requests
import numpy as np
import googlemaps
from typing import Tuple, Optional
from terraprint3d.config.parser import BoundsConfig
from terraprint3d.cache import ElevationCache


class ElevationFetcher:
    def __init__(self, google_api_key: Optional[str] = None, cache_enabled: bool = True):
        self.google_client = googlemaps.Client(key=google_api_key) if google_api_key else None
        self.open_elevation_url = "https://api.open-elevation.com/api/v1/lookup"
        self.cache = ElevationCache() if cache_enabled else None
    
    def fetch_elevation_grid(self, bounds: BoundsConfig, resolution_meters: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Fetch elevation data for the given bounds and return lat, lon, elevation grids."""
        # Determine API source for caching
        api_source = "google" if self.google_client else "open_elevation"
        
        # Check cache first
        if self.cache:
            cached_data = self.cache.get_cached_elevation(bounds, resolution_meters, api_source)
            if cached_data is not None:
                print(f"Using cached elevation data for {api_source} API")
                return cached_data
        
        # Calculate grid points based on resolution
        lat_points = self._calculate_grid_points(bounds.south, bounds.north, resolution_meters, True)
        lon_points = self._calculate_grid_points(bounds.west, bounds.east, resolution_meters, False)
        
        # Create coordinate grids
        lon_grid, lat_grid = np.meshgrid(lon_points, lat_points)
        elevation_grid = np.zeros_like(lat_grid)
        
        # Use Google Elevation API if available, otherwise fall back to open-elevation
        print(f"Fetching elevation data from {api_source} API...")
        if self.google_client:
            elevation_grid = self._fetch_with_google(lat_grid, lon_grid)
        else:
            elevation_grid = self._fetch_with_open_elevation(lat_grid, lon_grid)
        
        # Cache the results
        if self.cache:
            print("Caching elevation data for future use...")
            self.cache.cache_elevation_data(bounds, resolution_meters, api_source, lat_grid, lon_grid, elevation_grid)
        
        return lat_grid, lon_grid, elevation_grid
    
    def _fetch_with_google(self, lat_grid: np.ndarray, lon_grid: np.ndarray) -> np.ndarray:
        """Fetch elevation data using Google Elevation API."""
        elevation_grid = np.zeros_like(lat_grid)
        
        # Google API supports up to 512 locations per request
        batch_size = 500
        locations = []
        
        for i in range(lat_grid.shape[0]):
            for j in range(lat_grid.shape[1]):
                locations.append({
                    'lat': lat_grid[i, j],
                    'lng': lon_grid[i, j],
                    'i': i,
                    'j': j
                })
        
        # Process in batches
        for batch_start in range(0, len(locations), batch_size):
            batch = locations[batch_start:batch_start + batch_size]
            batch_coords = [{'lat': loc['lat'], 'lng': loc['lng']} for loc in batch]
            
            try:
                results = self.google_client.elevation(batch_coords)
                
                for loc, result in zip(batch, results):
                    elevation_grid[loc['i'], loc['j']] = result['elevation']
                    
            except Exception as e:
                print(f"Warning: Failed to fetch Google elevation batch: {e}")
                # Fill with zeros on error
                for loc in batch:
                    elevation_grid[loc['i'], loc['j']] = 0
        
        return elevation_grid
    
    def _fetch_with_open_elevation(self, lat_grid: np.ndarray, lon_grid: np.ndarray) -> np.ndarray:
        """Fetch elevation data using open-elevation API."""
        elevation_grid = np.zeros_like(lat_grid)
        
        # Open elevation supports smaller batches
        batch_size = 100
        locations = []
        
        for i in range(lat_grid.shape[0]):
            for j in range(lat_grid.shape[1]):
                locations.append({
                    'latitude': lat_grid[i, j],
                    'longitude': lon_grid[i, j],
                    'i': i,
                    'j': j
                })
        
        # Process in batches
        for batch_start in range(0, len(locations), batch_size):
            batch = locations[batch_start:batch_start + batch_size]
            batch_coords = [{'latitude': loc['latitude'], 'longitude': loc['longitude']} for loc in batch]
            
            try:
                response = requests.post(self.open_elevation_url, json={'locations': batch_coords})
                response.raise_for_status()
                results = response.json()['results']
                
                for loc, result in zip(batch, results):
                    elevation_grid[loc['i'], loc['j']] = result['elevation']
                    
            except requests.RequestException as e:
                print(f"Warning: Failed to fetch elevation batch: {e}")
                # Fill with zeros on error
                for loc in batch:
                    elevation_grid[loc['i'], loc['j']] = 0
        
        return elevation_grid
    
    def _calculate_grid_points(self, start: float, end: float, resolution_meters: int, is_latitude: bool) -> np.ndarray:
        """Calculate grid points based on resolution in meters."""
        # Approximate conversion from meters to degrees
        if is_latitude:
            # 1 degree latitude ≈ 111,320 meters
            resolution_degrees = resolution_meters / 111320.0
        else:
            # 1 degree longitude varies by latitude, using rough approximation
            resolution_degrees = resolution_meters / 85000.0  # Conservative estimate
        
        num_points = max(2, int((end - start) / resolution_degrees) + 1)
        return np.linspace(start, end, num_points)