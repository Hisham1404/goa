# comparison_utils.py
import numpy as np
import cv2
from scipy.spatial.distance import directed_hausdorff
# Import functions from our other utility file
import mask_utils # Assumes mask_utils.py is in the same directory

def calculate_iou(mask1, mask2):
    """Calculates Intersection over Union (IoU) for binary masks."""
    if mask1 is None or mask2 is None or mask1.shape != mask2.shape:
        return 0.0 # Return 0 if masks are invalid or incompatible
    try:
        intersection = np.logical_and(mask1, mask2).sum()
        union = np.logical_or(mask1, mask2).sum()
        if union == 0:
            return 1.0 if intersection == 0 else 0.0 # 1.0 if both empty, 0 otherwise
        return intersection / union
    except Exception as e:
        print(f"Error calculating IoU: {e}")
        return 0.0 # Return 0 on error

def calculate_hausdorff(contours1, contours2):
    """ Calculates directed Hausdorff distance between the largest contours. """
    if not contours1 or not contours2:
        # Return float('inf') if either contour list is empty
        return float('inf')

    try:
        # We assume find_contours_from_mask now returns a list with at most one contour (the largest)
        points1 = contours1[0].squeeze()
        points2 = contours2[0].squeeze()

        # Ensure points are 2D arrays, handle potential single-point contours after squeeze
        if points1.ndim == 1: points1 = points1.reshape(1, -1)
        if points2.ndim == 1: points2 = points2.reshape(1, -1)
        # Check for valid shape after potential reshape
        if points1.ndim != 2 or points1.shape[1] != 2 : raise ValueError("Contour 1 points invalid after processing.")
        if points2.ndim != 2 or points2.shape[1] != 2: raise ValueError("Contour 2 points invalid after processing.")


        if points1.shape[0] == 0 or points2.shape[0] == 0:
            return float('inf') # Cannot compare empty point sets

        dist12 = directed_hausdorff(points1, points2)[0]
        dist21 = directed_hausdorff(points2, points1)[0]
        return max(dist12, dist21) # Use max for symmetric Hausdorff distance
    except Exception as e:
        print(f"Error calculating Hausdorff distance: {e}")
        return float('inf') # Return infinity on error


def compare_masks(ref_mask, comp_mask, iou_tolerance=0.01, hausdorff_tolerance=2.0):
    """
    Compares two masks using IoU and Hausdorff, considering flips.
    Prioritizes 'Flipped Vertically' if its score is within tolerance of the best.
    """
    if ref_mask is None or comp_mask is None:
        return {"best_iou": 0.0, "best_hausdorff": float('inf'), "best_transform": "N/A"}

    transformations = {
        "Original": comp_mask,
        "Flipped Horizontally": cv2.flip(comp_mask, 1),
        "Flipped Vertically": cv2.flip(comp_mask, 0),
        "Flipped Both": cv2.flip(comp_mask, -1),
    }

    abs_best_iou = -1.0
    abs_best_iou_transform = "N/A"
    abs_best_hausdorff = float('inf')
    abs_best_hausdorff_transform = "N/A"

    vert_flip_iou = None
    vert_flip_hausdorff = None

    # Find contours for the reference mask once
    # Use the function imported from mask_utils
    ref_contours = mask_utils.find_contours_from_mask(ref_mask)

    for name, transformed_mask in transformations.items():
        # Calculate IoU
        current_iou = calculate_iou(ref_mask, transformed_mask)
        if current_iou > abs_best_iou:
            abs_best_iou = current_iou
            abs_best_iou_transform = name
        # Store vertical flip result specifically
        if name == "Flipped Vertically":
            vert_flip_iou = current_iou

        # Calculate Hausdorff
        # Use the function imported from mask_utils
        comp_contours = mask_utils.find_contours_from_mask(transformed_mask)
        current_hausdorff = calculate_hausdorff(ref_contours, comp_contours)
        if current_hausdorff < abs_best_hausdorff:
            abs_best_hausdorff = current_hausdorff
            abs_best_hausdorff_transform = name
        # Store vertical flip result specifically
        if name == "Flipped Vertically":
            vert_flip_hausdorff = current_hausdorff

    # --- Apply Prioritization Logic ---
    final_best_iou = abs_best_iou
    final_best_iou_transform = abs_best_iou_transform
    final_best_hausdorff = abs_best_hausdorff
    final_best_hausdorff_transform = abs_best_hausdorff_transform

    # Prioritize Flipped Vertically for IoU if within tolerance
    if vert_flip_iou is not None and abs_best_iou >= 0 and (abs_best_iou - vert_flip_iou) <= iou_tolerance:
        if vert_flip_iou >= abs_best_iou or abs_best_iou_transform != "Flipped Vertically":
             final_best_iou = vert_flip_iou
             final_best_iou_transform = "Flipped Vertically"

    # Prioritize Flipped Vertically for Hausdorff if within tolerance (lower is better)
    if vert_flip_hausdorff is not None and vert_flip_hausdorff != float('inf') and abs_best_hausdorff != float('inf'):
        if vert_flip_hausdorff <= (abs_best_hausdorff + hausdorff_tolerance):
            if vert_flip_hausdorff <= abs_best_hausdorff or abs_best_hausdorff_transform != "Flipped Vertically":
                  final_best_hausdorff = vert_flip_hausdorff
                  final_best_hausdorff_transform = "Flipped Vertically"

    return {
        "best_iou": final_best_iou,
        "best_iou_transform": final_best_iou_transform,
        "best_hausdorff": final_best_hausdorff,
        "best_hausdorff_transform": final_best_hausdorff_transform
    }