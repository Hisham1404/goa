"""
Enhanced Comparison Utilities for Land Parcel Matching

Provides multiple metrics for comprehensive shape comparison:
- IoU (Intersection over Union)
- Dice Coefficient
- Boundary F1 Score
- Hausdorff Distance
- Structural Similarity (SSIM)
- Area Ratio
- Shape Context Descriptor
"""

import numpy as np
import cv2
from scipy.spatial.distance import directed_hausdorff
from scipy.ndimage import distance_transform_edt
from skimage.metrics import structural_similarity as ssim
import mask_utils


def calculate_iou(mask1, mask2):
    """
    Calculate Intersection over Union (IoU) for binary masks.
    
    Args:
        mask1: First binary mask (numpy array)
        mask2: Second binary mask (numpy array)
    
    Returns:
        float: IoU score between 0 and 1
    """
    if mask1 is None or mask2 is None or mask1.shape != mask2.shape:
        return 0.0
    try:
        intersection = np.logical_and(mask1, mask2).sum()
        union = np.logical_or(mask1, mask2).sum()
        if union == 0:
            return 1.0 if intersection == 0 else 0.0
        return intersection / union
    except Exception as e:
        print(f"Error calculating IoU: {e}")
        return 0.0


def calculate_dice(mask1, mask2):
    """
    Calculate Dice Coefficient - often better than IoU for imbalanced shapes.
    
    The Dice coefficient is 2 * |intersection| / (|A| + |B|)
    
    Args:
        mask1: First binary mask
        mask2: Second binary mask
    
    Returns:
        float: Dice score between 0 and 1
    """
    if mask1 is None or mask2 is None or mask1.shape != mask2.shape:
        return 0.0
    try:
        intersection = np.logical_and(mask1, mask2).sum()
        total = mask1.sum() + mask2.sum()
        if total == 0:
            return 1.0
        return (2.0 * intersection) / total
    except Exception as e:
        print(f"Error calculating Dice: {e}")
        return 0.0


def calculate_boundary_f1(mask1, mask2, tolerance=2):
    """
    Calculate Boundary F1 Score - measures boundary accuracy.
    
    This is crucial for land parcel matching where boundary precision matters.
    
    Args:
        mask1: First binary mask
        mask2: Second binary mask
        tolerance: Pixel tolerance for boundary matching (default: 2)
    
    Returns:
        float: Boundary F1 score between 0 and 1
    """
    if mask1 is None or mask2 is None or mask1.shape != mask2.shape:
        return 0.0
    
    try:
        # Extract boundaries using Canny edge detection
        boundary1 = cv2.Canny(mask1.astype(np.uint8) * 255, 100, 200)
        boundary2 = cv2.Canny(mask2.astype(np.uint8) * 255, 100, 200)
        
        # Calculate distance transforms
        dist1 = distance_transform_edt(1 - boundary1 / 255)
        dist2 = distance_transform_edt(1 - boundary2 / 255)
        
        # Calculate precision and recall within tolerance
        boundary1_points = boundary1 > 0
        boundary2_points = boundary2 > 0
        
        if boundary1_points.sum() == 0 or boundary2_points.sum() == 0:
            return 0.0
        
        precision = np.mean(dist2[boundary1_points] <= tolerance)
        recall = np.mean(dist1[boundary2_points] <= tolerance)
        
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * precision * recall / (precision + recall)
        return f1
        
    except Exception as e:
        print(f"Error calculating Boundary F1: {e}")
        return 0.0


def calculate_hausdorff(mask1, mask2):
    """
    Calculate Hausdorff Distance - maximum boundary deviation.
    
    Lower values indicate better match.
    
    Args:
        mask1: First binary mask
        mask2: Second binary mask
    
    Returns:
        float: Hausdorff distance (lower is better), inf on error
    """
    if mask1 is None or mask2 is None:
        return float('inf')
    
    try:
        contours1 = mask_utils.find_contours_from_mask(mask1)
        contours2 = mask_utils.find_contours_from_mask(mask2)
        
        if not contours1 or not contours2:
            return float('inf')
        
        points1 = contours1[0].squeeze()
        points2 = contours2[0].squeeze()
        
        # Handle edge cases
        if points1.ndim == 1:
            points1 = points1.reshape(1, -1)
        if points2.ndim == 1:
            points2 = points2.reshape(1, -1)
        
        if points1.shape[0] == 0 or points2.shape[0] == 0:
            return float('inf')
        
        # Calculate symmetric Hausdorff distance
        dist12 = directed_hausdorff(points1, points2)[0]
        dist21 = directed_hausdorff(points2, points1)[0]
        
        return max(dist12, dist21)
        
    except Exception as e:
        print(f"Error calculating Hausdorff: {e}")
        return float('inf')


def calculate_ssim(mask1, mask2):
    """
    Calculate Structural Similarity Index (SSIM).
    
    Captures structural patterns in the shapes.
    
    Args:
        mask1: First binary mask
        mask2: Second binary mask
    
    Returns:
        float: SSIM score between -1 and 1 (higher is better)
    """
    if mask1 is None or mask2 is None or mask1.shape != mask2.shape:
        return 0.0
    try:
        return ssim(mask1.astype(np.float64), mask2.astype(np.float64), data_range=1.0)
    except Exception as e:
        print(f"Error calculating SSIM: {e}")
        return 0.0


def calculate_area_ratio(mask1, mask2):
    """
    Calculate ratio of areas - should be close to 1 for matching shapes.
    
    Quick filter to eliminate obviously different shapes.
    
    Args:
        mask1: First binary mask
        mask2: Second binary mask
    
    Returns:
        float: Area ratio between 0 and 1
    """
    if mask1 is None or mask2 is None:
        return 0.0
    
    area1 = mask1.sum()
    area2 = mask2.sum()
    
    if area1 == 0 or area2 == 0:
        return 0.0
    
    return min(area1, area2) / max(area1, area2)


def calculate_centroid_distance(mask1, mask2):
    """
    Calculate normalized distance between shape centroids.
    
    Args:
        mask1: First binary mask
        mask2: Second binary mask
    
    Returns:
        float: Normalized centroid distance (lower is better)
    """
    def get_centroid(mask):
        y, x = np.where(mask > 0)
        if len(y) == 0:
            return None
        return np.array([x.mean(), y.mean()])
    
    if mask1 is None or mask2 is None:
        return float('inf')
    
    c1 = get_centroid(mask1)
    c2 = get_centroid(mask2)
    
    if c1 is None or c2 is None:
        return float('inf')
    
    # Normalize by image diagonal
    diagonal = np.sqrt(mask1.shape[0]**2 + mask1.shape[1]**2)
    dist = np.linalg.norm(c1 - c2) / diagonal
    
    return dist


def calculate_perimeter_ratio(mask1, mask2):
    """
    Calculate ratio of perimeters.
    
    Args:
        mask1: First binary mask
        mask2: Second binary mask
    
    Returns:
        float: Perimeter ratio between 0 and 1
    """
    if mask1 is None or mask2 is None:
        return 0.0
    
    try:
        contours1 = mask_utils.find_contours_from_mask(mask1)
        contours2 = mask_utils.find_contours_from_mask(mask2)
        
        if not contours1 or not contours2:
            return 0.0
        
        perimeter1 = cv2.arcLength(contours1[0], True)
        perimeter2 = cv2.arcLength(contours2[0], True)
        
        if perimeter1 == 0 or perimeter2 == 0:
            return 0.0
        
        return min(perimeter1, perimeter2) / max(perimeter1, perimeter2)
        
    except Exception as e:
        print(f"Error calculating perimeter ratio: {e}")
        return 0.0


def calculate_compactness_similarity(mask1, mask2):
    """
    Calculate similarity of compactness (circularity) between shapes.
    
    Compactness = 4 * pi * area / perimeter^2
    
    Args:
        mask1: First binary mask
        mask2: Second binary mask
    
    Returns:
        float: Compactness similarity between 0 and 1
    """
    def get_compactness(mask):
        contours = mask_utils.find_contours_from_mask(mask)
        if not contours:
            return 0
        area = cv2.contourArea(contours[0])
        perimeter = cv2.arcLength(contours[0], True)
        if perimeter == 0:
            return 0
        return 4 * np.pi * area / (perimeter ** 2)
    
    if mask1 is None or mask2 is None:
        return 0.0
    
    try:
        c1 = get_compactness(mask1)
        c2 = get_compactness(mask2)
        
        if c1 == 0 or c2 == 0:
            return 0.0
        
        return min(c1, c2) / max(c1, c2)
        
    except Exception as e:
        print(f"Error calculating compactness: {e}")
        return 0.0


def comprehensive_compare(ref_mask, comp_mask, weights=None):
    """
    Comprehensive comparison using multiple metrics.
    
    Returns a weighted composite score combining all metrics.
    
    Args:
        ref_mask: Reference binary mask
        comp_mask: Comparison binary mask
        weights: Dictionary of metric weights (optional)
    
    Returns:
        dict: Contains 'composite_score' and detailed 'metrics'
    """
    if weights is None:
        # Default weights optimized for land parcel matching
        weights = {
            'iou': 0.20,
            'dice': 0.15,
            'boundary_f1': 0.20,
            'ssim': 0.10,
            'area_ratio': 0.10,
            'perimeter_ratio': 0.10,
            'compactness': 0.05,
            'hausdorff': 0.10  # Inverted - lower is better
        }
    
    # Calculate all metrics
    metrics = {
        'iou': calculate_iou(ref_mask, comp_mask),
        'dice': calculate_dice(ref_mask, comp_mask),
        'boundary_f1': calculate_boundary_f1(ref_mask, comp_mask),
        'ssim': calculate_ssim(ref_mask, comp_mask),
        'area_ratio': calculate_area_ratio(ref_mask, comp_mask),
        'perimeter_ratio': calculate_perimeter_ratio(ref_mask, comp_mask),
        'compactness': calculate_compactness_similarity(ref_mask, comp_mask),
        'hausdorff': calculate_hausdorff(ref_mask, comp_mask)
    }
    
    # Normalize Hausdorff (lower is better, max reasonable value ~100 pixels)
    hausdorff_normalized = max(0, 1 - metrics['hausdorff'] / 100) if metrics['hausdorff'] != float('inf') else 0
    
    # Calculate weighted composite score
    composite_score = (
        weights['iou'] * metrics['iou'] +
        weights['dice'] * metrics['dice'] +
        weights['boundary_f1'] * metrics['boundary_f1'] +
        weights['ssim'] * max(0, metrics['ssim']) +  # SSIM can be negative
        weights['area_ratio'] * metrics['area_ratio'] +
        weights['perimeter_ratio'] * metrics['perimeter_ratio'] +
        weights['compactness'] * metrics['compactness'] +
        weights['hausdorff'] * hausdorff_normalized
    )
    
    return {
        'composite_score': composite_score,
        'metrics': metrics
    }


def compare_with_transformations(ref_mask, comp_mask, include_rotations=False):
    """
    Compare masks with all geometric transformations.
    
    Finds the best matching transformation (flip, rotation).
    
    Args:
        ref_mask: Reference binary mask
        comp_mask: Comparison binary mask
        include_rotations: Whether to include 90-degree rotations
    
    Returns:
        dict: Contains 'best_score', 'best_transform', and 'metrics'
    """
    transformations = {
        'original': comp_mask,
        'flip_horizontal': cv2.flip(comp_mask, 1),
        'flip_vertical': cv2.flip(comp_mask, 0),
        'flip_both': cv2.flip(comp_mask, -1),
    }
    
    if include_rotations:
        transformations.update({
            'rotate_90': cv2.rotate(comp_mask, cv2.ROTATE_90_CLOCKWISE),
            'rotate_180': cv2.rotate(comp_mask, cv2.ROTATE_180),
            'rotate_270': cv2.rotate(comp_mask, cv2.ROTATE_90_COUNTERCLOCKWISE),
        })
    
    best_score = -1
    best_transform = 'original'
    best_metrics = None
    all_results = {}
    
    for name, transformed_mask in transformations.items():
        result = comprehensive_compare(ref_mask, transformed_mask)
        all_results[name] = result
        
        if result['composite_score'] > best_score:
            best_score = result['composite_score']
            best_transform = name
            best_metrics = result['metrics']
    
    return {
        'best_score': best_score,
        'best_transform': best_transform,
        'metrics': best_metrics,
        'all_transforms': all_results
    }


def quick_filter(ref_mask, comp_mask, area_threshold=0.5, perimeter_threshold=0.5):
    """
    Quick filter to eliminate obviously non-matching shapes.
    
    Use this before comprehensive comparison to save computation time.
    
    Args:
        ref_mask: Reference binary mask
        comp_mask: Comparison binary mask
        area_threshold: Minimum area ratio to pass
        perimeter_threshold: Minimum perimeter ratio to pass
    
    Returns:
        bool: True if shapes might match, False if definitely don't match
    """
    area_ratio = calculate_area_ratio(ref_mask, comp_mask)
    if area_ratio < area_threshold:
        return False
    
    perimeter_ratio = calculate_perimeter_ratio(ref_mask, comp_mask)
    if perimeter_ratio < perimeter_threshold:
        return False
    
    return True
