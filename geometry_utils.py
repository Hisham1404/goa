# geometry_utils.py
import numpy as np
import geopandas as gpd

def get_coordinates_from_geometry(geometry):
    """ Extracts boundary coordinates from a given geometry object. """
    try:
        if hasattr(geometry, 'boundary'):
            # Ensure boundary isn't empty (can happen with invalid geometries)
            if geometry.boundary is None or geometry.boundary.is_empty:
                 # print(f"Warning: Geometry boundary is empty or None for {type(geometry)}") # Optional verbose
                 # Try exterior coords if available
                 if hasattr(geometry, 'exterior') and geometry.exterior is not None:
                     coords = np.array(geometry.exterior.coords)
                     return coords if coords.size > 0 else None
                 else:
                     return None # Cannot get coords
            coords = np.array(geometry.boundary.coords)
            return coords if coords.size > 0 else None
        elif hasattr(geometry, 'coords'): # Handle LineStrings etc.
             coords = np.array(geometry.coords)
             return coords if coords.size > 0 else None
        else:
            print(f"Error: Unsupported geometry type or no coordinates found: {type(geometry)}")
            return None
    except Exception as e:
        print(f"Error extracting coordinates from geometry: {e}")
        return None

def normalize_coordinates(coords):
    """ Normalizes coordinates to the range [0, 1]. """
    if coords is None or coords.shape[0] < 1: # Need at least one point
        # print("Error: Cannot normalize None or empty coordinates.") # Optional verbose
        return None
    min_vals = coords.min(axis=0)
    max_vals = coords.max(axis=0)
    range_vals = max_vals - min_vals
    # Handle zero range (single point or straight line)
    range_vals[range_vals == 0] = 1 # Avoid division by zero, effectively sets normalized to 0 here
    normalized = (coords - min_vals) / range_vals
    # Special handling for single point case -> center it
    if coords.shape[0] == 1:
        return np.array([[0.5, 0.5]])
    # If range was zero in one dim, ensure values are reasonable (e.g., center that dim)
    is_zero_range = (max_vals - min_vals) == 0
    if np.any(is_zero_range):
         normalized[:, is_zero_range] = 0.5 # Center dimensions with zero range

    return normalized


def pad_normalized_coordinates(norm_coords, padding_ratio):
    """ Pads normalized coordinates to add a border by scaling towards center. """
    if norm_coords is None or norm_coords.size == 0:
         # print("Error: Cannot pad None or empty normalized coordinates.") # Optional verbose
         return None
    scale_factor = 1.0 - (2 * padding_ratio) # Scale factor (less than 1)
    if scale_factor < 0: scale_factor = 0 # Avoid negative scaling

    # Shift origin to center (0.5, 0.5), scale, then shift back
    padded_coords = 0.5 + (norm_coords - 0.5) * scale_factor
    padded_coords = np.clip(padded_coords, 0, 1) # Ensure stay within [0, 1]
    return padded_coords