# mask_utils.py
import numpy as np
import cv2
import os
import imutils # Required by find_contours_from_mask

def create_mask_from_coords(coords, image_size, make_copy=True):
    """ Creates a binary mask (0s and 1s) from normalized & padded coordinates. """
    if coords is None or len(coords) < 3:
        # print("Warning: Need at least 3 coordinates to create a filled mask.") # Optional verbose
        # Return an empty mask
        return np.zeros((image_size, image_size), dtype=np.uint8)

    # Scale coordinates to image size BEFORE converting to int
    scaled_coords = (coords * (image_size - 1))

    if make_copy:
        coords_int = scaled_coords.astype(np.int32).copy() # Ensure copy to avoid modifying original
    else:
        coords_int = scaled_coords.astype(np.int32)

    mask = np.zeros((image_size, image_size), dtype=np.uint8)
    # OpenCV expects a list of polygons
    coords_list = [coords_int]
    try:
        cv2.fillPoly(mask, coords_list, 1) # Fill with 1
    except Exception as e:
        print(f"Error during cv2.fillPoly: {e}. Coords shape: {coords_int.shape}")
        return np.zeros((image_size, image_size), dtype=np.uint8) # Return empty on error
    return mask

def load_dat_as_mask(filename, target_size=(500, 500)):
    """Loads a .dat file, assumes it's a binary mask (0/1), and ensures target size."""
    try:
        data = np.loadtxt(filename, dtype=np.uint8) # Load directly as uint8
        # Check if resizing is needed
        if data.shape != target_size:
            # print(f"Resizing {filename} from {data.shape} to {target_size}") # Optional verbose
            resized_data = cv2.resize(data, target_size, interpolation=cv2.INTER_NEAREST)
        else:
            resized_data = data
        # Ensure it's binary 0 or 1
        resized_data = (resized_data > 0).astype(np.uint8)
        return resized_data
    except Exception as e:
        print(f"Error loading or processing data from {filename}: {e}")
        return None

def find_contours_from_mask(mask):
    """Find contours using OpenCV, return only the largest one."""
    if mask is None or not np.any(mask): # If mask is empty or all zeros
         return [] # Return empty list if no contours can be found
    try:
        mask_uint8 = mask.astype(np.uint8)
        cnts = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(cnts)
        # Convert to list if it's a tuple to ensure we can sort
        if isinstance(contours, tuple):
            contours = list(contours)
        # Sort contours by area descending, keep only the largest one for Hausdorff
        if contours:
             contours.sort(key=cv2.contourArea, reverse=True)
             return [contours[0]] # Return list containing only the largest contour
        else:
             return []
    except Exception as e:
        print(f"Error finding contours: {e}")
        return [] # Return empty list on error