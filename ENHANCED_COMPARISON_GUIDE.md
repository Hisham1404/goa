
# Enhanced Multi-Metric Comparison System - Usage Guide

## Overview
The enhanced comparison system provides comprehensive shape matching using multiple metrics
optimized for land parcel matching. This significantly improves accuracy over the traditional
IoU-only approach.

## Available Comparison Methods

### 1. Standard Method (Original)
Uses IoU and Hausdorff distance.

```python
import comparison_utils

result = comparison_utils.compare_masks(ref_mask, comp_mask)
print(f"IoU: {result['best_iou']:.3f}")
print(f"Hausdorff: {result['best_hausdorff']:.2f}")
```

### 2. Enhanced Method (NEW - Recommended)
Uses 8 comprehensive metrics with weighted composite scoring.

```python
import comparison_utils

result = comparison_utils.compare_masks_enhanced(ref_mask, comp_mask)
print(f"Composite Score: {result['best_score']:.3f}")
print(f"Best Transform: {result['best_transform']}")
print(f"Filtered Out: {result['filtered_out']}")

# Access detailed metrics
if result['metrics']:
    metrics = result['metrics']
    print(f"IoU: {metrics['iou']:.3f}")
    print(f"Dice: {metrics['dice']:.3f}")
    print(f"Boundary F1: {metrics['boundary_f1']:.3f}")
    print(f"SSIM: {metrics['ssim']:.3f}")
```

## API Endpoint Usage

### Enhanced Comparison via REST API

```bash
curl -X POST http://localhost:5000/api/compare   -H "Content-Type: application/json"   -d '{
    "village_name": "ambeli",
    "chosen_index": 0,
    "comparison_method": "enhanced"
  }'
```

Response includes:
- `composite_score`: Overall weighted score (0-1, higher is better)
- `transform`: Best geometric transformation
- `metrics`: Detailed breakdown of all 8 metrics

## Metrics Explained

1. **IoU (Intersection over Union)**: Standard overlap metric
   - Range: 0-1 (higher is better)
   - Weight: 20%

2. **Dice Coefficient**: Better for imbalanced shapes
   - Range: 0-1 (higher is better)
   - Weight: 15%

3. **Boundary F1 Score**: Measures boundary accuracy
   - Range: 0-1 (higher is better)
   - Weight: 20%
   - Critical for land parcel boundaries

4. **SSIM**: Structural similarity
   - Range: -1 to 1 (higher is better)
   - Weight: 10%

5. **Area Ratio**: Quick size comparison
   - Range: 0-1 (higher is better)
   - Weight: 10%

6. **Perimeter Ratio**: Shape outline comparison
   - Range: 0-1 (higher is better)
   - Weight: 10%

7. **Compactness Similarity**: Circularity comparison
   - Range: 0-1 (higher is better)
   - Weight: 5%

8. **Hausdorff Distance**: Maximum boundary deviation
   - Range: 0-∞ (lower is better, normalized in composite)
   - Weight: 10%

## Performance Optimization

### Quick Filter
The enhanced system includes a quick filter that eliminates obvious non-matches
before detailed comparison:

```python
from enhanced_comparison_utils import quick_filter

# Check if shapes are worth comparing in detail
if quick_filter(ref_mask, comp_mask):
    # Proceed with comprehensive comparison
    result = comprehensive_compare(ref_mask, comp_mask)
```

Default thresholds:
- Area ratio: 0.5 (shapes must have similar sizes)
- Perimeter ratio: 0.5 (shapes must have similar perimeters)

## Custom Weights

You can customize metric weights for specific use cases:

```python
from enhanced_comparison_utils import comprehensive_compare

custom_weights = {
    'iou': 0.25,
    'dice': 0.15,
    'boundary_f1': 0.30,  # Increased for high boundary accuracy
    'ssim': 0.05,
    'area_ratio': 0.10,
    'perimeter_ratio': 0.05,
    'compactness': 0.05,
    'hausdorff': 0.05
}

result = comprehensive_compare(ref_mask, comp_mask, weights=custom_weights)
```

## Benefits

✅ **More Accurate**: Multiple metrics catch different shape characteristics
✅ **Better Boundaries**: Boundary F1 specifically measures edge accuracy
✅ **Faster**: Quick filter eliminates obvious non-matches early
✅ **Robust**: Handles shape variations better
✅ **Detailed**: See which metrics contributed to the match
✅ **Backward Compatible**: Existing 'standard' method still works

## Migration Guide

To upgrade from standard to enhanced comparison:

```python
# Old way
result = comparison_utils.compare_masks(ref_mask, comp_mask)
score = result['best_iou']

# New way (recommended)
result = comparison_utils.compare_masks_enhanced(ref_mask, comp_mask)
score = result['best_score']

# Both methods coexist - no breaking changes!
```
