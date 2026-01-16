import numpy as np
import matplotlib.pyplot as plt
import cv2
import os

def create_diagram_mask_and_dat_enhanced(image_path, dat_output_path, resize_dim=(500, 500), method='adaptive'):
    """
    Enhanced version that processes an image to isolate a black diagram, creates a binary mask,
    and saves the mask as a .dat file with better shape filling.

    Parameters:
        image_path (str): Path to the input image file.
        dat_output_path (str): Path where the output .dat file will be saved.
        resize_dim (tuple): Dimensions (width, height) to resize the image to.
        method (str): Processing method - 'adaptive', 'otsu', 'original', or 'aggressive'

    Returns:
        numpy.ndarray or None: The binary mask array (0s and 1s) if successful, None otherwise.
    """
    # --- 1. Load and Preprocess Image ---
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Unable to load image at {image_path}")
        return None

    image = cv2.resize(image, resize_dim)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # --- 2. Enhanced Thresholding Based on Method ---
    if method == 'adaptive':
        # Adaptive thresholding for varying lighting conditions
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY_INV, 11, 2)
    elif method == 'otsu':
        # Otsu's automatic thresholding
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    elif method == 'aggressive':
        # Multiple threshold attempts for difficult images
        _, binary1 = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        _, binary2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        binary = cv2.bitwise_or(binary1, binary2)
    else:  # original method
        _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

    # --- 3. Enhanced Morphological Operations ---
    if method == 'aggressive':
        # More aggressive morphological operations for difficult shapes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        # Close gaps and fill holes
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)
        processed = cv2.morphologyEx(processed, cv2.MORPH_DILATE, kernel, iterations=2)
        
        # Flood fill from edges to remove background noise
        h, w = processed.shape
        mask = np.zeros((h+2, w+2), np.uint8)
        
        # Flood fill from corners to remove background
        cv2.floodFill(processed, mask, (0,0), 0)
        cv2.floodFill(processed, mask, (w-1,0), 0)
        cv2.floodFill(processed, mask, (0,h-1), 0)
        cv2.floodFill(processed, mask, (w-1,h-1), 0)
        
        closed = processed
    else:
        # Standard morphological operations
        kernel_size = 7 if method in ['adaptive', 'otsu'] else 5
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        
        # Close small gaps and smooth edges
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        if method in ['adaptive', 'otsu']:
            # Additional processing for better filling
            closed = cv2.morphologyEx(closed, cv2.MORPH_DILATE, kernel, iterations=1)
            closed = cv2.morphologyEx(closed, cv2.MORPH_ERODE, kernel, iterations=1)

    # --- 4. Create Filled Binary Mask with Enhanced Contour Processing ---
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled_mask_255 = np.zeros_like(closed)
    
    if contours:
        if method == 'aggressive':
            # Fill all significant contours
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 50:  # Minimum area threshold
                    cv2.drawContours(filled_mask_255, [contour], -1, 255, thickness=cv2.FILLED)
        else:
            # Standard approach - find largest contour and fill significant ones
            contours_with_area = [(cv2.contourArea(c), c) for c in contours]
            contours_with_area.sort(reverse=True, key=lambda x: x[0])
            
            # Fill the largest contour
            if contours_with_area[0][0] > 100:
                cv2.drawContours(filled_mask_255, [contours_with_area[0][1]], -1, 255, thickness=cv2.FILLED)
            
            # Fill other significant contours
            for area, contour in contours_with_area[1:]:
                if area > max(100, contours_with_area[0][0] * 0.1):  # At least 10% of largest or 100 pixels
                    cv2.drawContours(filled_mask_255, [contour], -1, 255, thickness=cv2.FILLED)

    # Convert to a mask with 1s for the shape and 0s for the background
    filled_mask_01 = (filled_mask_255 / 255).astype(np.uint8)

    # --- 5. Post-processing: Fill remaining holes ---
    if method in ['adaptive', 'otsu', 'aggressive']:
        # Fill holes using morphological closing
        kernel_fill = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        filled_mask_255_post = filled_mask_01 * 255
        filled_mask_255_post = cv2.morphologyEx(filled_mask_255_post, cv2.MORPH_CLOSE, kernel_fill, iterations=2)
        filled_mask_01 = (filled_mask_255_post / 255).astype(np.uint8)

    # --- 6. Save the Mask as .dat ---
    try:
        output_dir = os.path.dirname(dat_output_path)
        if output_dir:
             os.makedirs(output_dir, exist_ok=True)
        np.savetxt(dat_output_path, filled_mask_01, fmt='%d')
        return filled_mask_01
    except Exception as e:
        print(f"Error saving .dat file to {dat_output_path}: {e}")
        return None

def create_diagram_mask_and_dat(image_path, dat_output_path, resize_dim=(500, 500)):
    """
    Original function maintained for backward compatibility.
    """
    # --- 1. Load and Preprocess Image ---
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Unable to load image at {image_path}")
        return None

    image = cv2.resize(image, resize_dim)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Threshold to isolate the black diagram (make it white, background black)
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

    # Morphological closing to fill small holes and smooth edges
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # --- 2. Create Filled Binary Mask (1s for shape, 0s for background) ---
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled_mask_255 = np.zeros_like(closed)
    cv2.drawContours(filled_mask_255, contours, -1, (255), thickness=cv2.FILLED)

    # Convert to a mask with 1s for the shape and 0s for the background
    filled_mask_01 = (filled_mask_255 / 255).astype(np.uint8)

    # --- 3. Save the Mask as .dat ---
    try:
        output_dir = os.path.dirname(dat_output_path)
        if output_dir:
             os.makedirs(output_dir, exist_ok=True)
        np.savetxt(dat_output_path, filled_mask_01, fmt='%d')
        return filled_mask_01
    except Exception as e:
        print(f"Error saving .dat file to {dat_output_path}: {e}")
        return None

def create_black_shape_image_from_dat(dat_input_path, image_output_path):
    """
    Loads a binary mask from a .dat file and creates an image with a black shape on white background.
    """
    try:
        loaded_mask_01 = np.loadtxt(dat_input_path, dtype=np.uint8)
    except Exception as e:
        print(f"Error loading .dat file from {dat_input_path}: {e}")
        return None

    height, width = loaded_mask_01.shape
    output_image = np.ones((height, width), dtype=np.uint8) * 255

    output_image[loaded_mask_01 == 1] = 0

    try:
        output_dir = os.path.dirname(image_output_path)
        if output_dir:
             os.makedirs(output_dir, exist_ok=True)
        cv2.imwrite(image_output_path, output_image)
        return output_image
    except Exception as e:
        print(f"Error saving image file to {image_output_path}: {e}")
        return None

def find_corners_on_image(image_array, corner_threshold_ratio=0.01):
    """
    Finds corners on a given image array using the Harris corner detector.
    """
    if image_array is None:
        return []

    gray_for_corners = np.float32(image_array)
    dst = cv2.cornerHarris(gray_for_corners, blockSize=2, ksize=3, k=0.04)
    dst = cv2.dilate(dst, None)

    threshold_val = corner_threshold_ratio * dst.max()
    if threshold_val == 0:
         return []
    corner_coords = np.where(dst > threshold_val)

    corners = list(zip(corner_coords[1], corner_coords[0]))
    return corners

def auto_detect_best_method(image_path, resize_dim=(500, 500)):
    """
    Automatically detects the best processing method for an image.
    Returns the recommended method based on image characteristics.
    """
    image = cv2.imread(image_path)
    if image is None:
        return 'original'
    
    image = cv2.resize(image, resize_dim)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Analyze image characteristics
    mean_intensity = np.mean(gray)
    std_intensity = np.std(gray)
    
    # Check for varying lighting (high std suggests adaptive might be better)
    if std_intensity > 50:
        return 'adaptive'
    # Check for very dark images (low mean suggests otsu might be better)
    elif mean_intensity < 100:
        return 'otsu'
    # Check for complex images (might need aggressive processing)
    elif std_intensity > 30 and mean_intensity < 150:
        return 'aggressive'
    else:
        return 'original'

# --- Main Execution Block ---
if __name__ == "__main__":
    # --- Configuration ---
    base_plots_dir = "../maps/ambeli/plots"
    base_output_dir = "../maps/ambeli/dat_folder"
    
    # Processing options
    USE_ENHANCED_PROCESSING = True  # Set to False to use original method
    AUTO_DETECT_METHOD = True       # Set to False to use fixed method
    FIXED_METHOD = 'adaptive'       # Used when AUTO_DETECT_METHOD is False
    
    supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')

    print(f"Starting automated batch processing for Ambeli village")
    print(f"Enhanced processing: {'ENABLED' if USE_ENHANCED_PROCESSING else 'DISABLED'}")
    print(f"Auto method detection: {'ENABLED' if AUTO_DETECT_METHOD else 'DISABLED'}")
    if not AUTO_DETECT_METHOD:
        print(f"Fixed method: {FIXED_METHOD}")
    print(f"Base plots directory: {base_plots_dir}")
    print(f"Base output directory: {base_output_dir}")

    total_processed = 0
    total_errors = 0
    processed_areas = 0
    method_stats = {'original': 0, 'adaptive': 0, 'otsu': 0, 'aggressive': 0}

    if not os.path.exists(base_plots_dir):
        print(f"Error: Base plots directory '{base_plots_dir}' not found.")
        exit()

    try:
        all_subdirs = [d for d in os.listdir(base_plots_dir) 
                      if os.path.isdir(os.path.join(base_plots_dir, d))]
        all_subdirs.sort()
    except Exception as e:
        print(f"Error accessing base plots directory: {e}")
        exit()

    print(f"Found {len(all_subdirs)} sub-areas: {', '.join(all_subdirs)}")
    
    for subdir in all_subdirs:
        print(f"\n🔄 Processing area {subdir}...")
        
        input_folder = os.path.join(base_plots_dir, subdir, "enhanced")
        output_dat_dir = os.path.join(base_output_dir, subdir, "dat")
        output_image_dir = os.path.join(base_output_dir, subdir, "dat_image")
        
        if not os.path.exists(input_folder):
            print(f"    ⚠️ SKIPPED: No 'enhanced' folder found in area {subdir}")
            continue
        
        os.makedirs(output_dat_dir, exist_ok=True)
        os.makedirs(output_image_dir, exist_ok=True)
        
        area_processed = 0
        area_errors = 0

        try:
            all_files = os.listdir(input_folder)
        except FileNotFoundError:
            print(f"    ❌ ERROR: Enhanced folder not accessible in area {subdir}")
            continue

        image_files = [f for f in all_files if f.lower().endswith(supported_extensions)]

        if len(image_files) == 0:
            print(f"    ⚠️ SKIPPED: No image files found in area {subdir}/enhanced/")
            continue

        for filename in image_files:
            input_image_path = os.path.join(input_folder, filename)
            
            base_filename = os.path.splitext(filename)[0]
            dat_file = os.path.join(output_dat_dir, f"{base_filename}.dat")
            reconstructed_image_file = os.path.join(output_image_dir, f"{base_filename}.png")

            # Check if files already exist
            if os.path.exists(dat_file) and os.path.exists(reconstructed_image_file):
                area_processed += 1
                continue

            # Choose processing method
            if USE_ENHANCED_PROCESSING:
                if AUTO_DETECT_METHOD:
                    method = auto_detect_best_method(input_image_path)
                else:
                    method = FIXED_METHOD
                
                method_stats[method] += 1
                diagram_mask = create_diagram_mask_and_dat_enhanced(input_image_path, dat_file, method=method)
            else:
                method_stats['original'] += 1
                diagram_mask = create_diagram_mask_and_dat(input_image_path, dat_file)

            if diagram_mask is None:
                print(f"    ❌ FAILED: Could not create .dat file for {filename}")
                area_errors += 1
                continue

            reconstructed_image = create_black_shape_image_from_dat(dat_file, reconstructed_image_file)

            if reconstructed_image is None:
                print(f"    ❌ FAILED: Could not create reconstructed image for {filename}")
                area_errors += 1
                continue

            corners = find_corners_on_image(reconstructed_image)
            area_processed += 1

        if area_errors > 0 or area_processed > 0:
            if area_errors > 0:
                print(f"  📊 Area {subdir}: {area_processed} processed, {area_errors} failed")
        
        total_processed += area_processed
        total_errors += area_errors
        
        if area_processed > 0:
            processed_areas += 1

    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Total sub-areas processed: {processed_areas}/{len(all_subdirs)}")
    print(f"Total images successfully processed: {total_processed}")
    print(f"Total failed/skipped: {total_errors}")
    
    if USE_ENHANCED_PROCESSING:
        print(f"\nMethod usage statistics:")
        for method, count in method_stats.items():
            if count > 0:
                print(f"  {method}: {count} images")
    
    if total_processed > 0:
        print(f"\nOutput structure created:")
        print(f"  DAT files: {base_output_dir}/{{area_name}}/dat/")
        print(f"  Images: {base_output_dir}/{{area_name}}/dat_image/")
    else:
        print(f"\nNo files were processed. Please check:")
        print(f"  - Enhanced folders exist in sub-areas")
        print(f"  - Image files are present in enhanced folders")
        print(f"  - File paths are correct")
