import os
import pickle
import hashlib
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from terraprint3d.config.parser import BoundsConfig


class ElevationCache:
    def __init__(self, cache_dir: str = "data/elevation_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_cache_key(self, bounds: BoundsConfig, resolution_meters: int, api_source: str) -> str:
        """Generate a unique cache key for the given parameters."""
        key_data = f"{bounds.north}_{bounds.south}_{bounds.east}_{bounds.west}_{resolution_meters}_{api_source}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cached_elevation(self, bounds: BoundsConfig, resolution_meters: int, api_source: str) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """Retrieve cached elevation data if it exists."""
        cache_key = self._generate_cache_key(bounds, resolution_meters, api_source)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    return cached_data['lat_grid'], cached_data['lon_grid'], cached_data['elevation_grid']
            except Exception as e:
                print(f"Warning: Failed to load cached data: {e}")
                # Remove corrupted cache file
                cache_file.unlink(missing_ok=True)
        
        return None
    
    def cache_elevation_data(self, bounds: BoundsConfig, resolution_meters: int, api_source: str, 
                           lat_grid: np.ndarray, lon_grid: np.ndarray, elevation_grid: np.ndarray) -> None:
        """Cache elevation data for future use."""
        cache_key = self._generate_cache_key(bounds, resolution_meters, api_source)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        cache_data = {
            'bounds': bounds,
            'resolution_meters': resolution_meters,
            'api_source': api_source,
            'lat_grid': lat_grid,
            'lon_grid': lon_grid,
            'elevation_grid': elevation_grid,
            'cache_version': '1.0'
        }
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            print(f"Warning: Failed to cache elevation data: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached elevation data."""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
    
    def get_cache_info(self) -> dict:
        """Get information about cached data."""
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_files': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }