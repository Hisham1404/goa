import numpy as np
import matplotlib.pyplot as plt
import cv2
import os

# --- Functions (create_diagram_mask_and_dat, create_black_shape_image_from_dat, find_corners_on_image) ---
# Keep the functions exactly as they were in the previous version.
# I'll omit them here for brevity, but make sure they are included above the
# __main__ block in your actual script.

def create_diagram_mask_and_dat(image_path, dat_output_path, resize_dim=(500, 500)):
    """
    Processes an image to isolate a black diagram, creates a binary mask,
    and saves the mask as a .dat file.

    Parameters:
        image_path (str): Path to the input image file.
        dat_output_path (str): Path where the output .dat file will be saved.
        resize_dim (tuple): Dimensions (width, height) to resize the image to.

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

    # Threshold to isolate the black diagram (make it white, background black)
    # Adjust the threshold value (e.g., 50) if needed based on your images
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

    # Morphological closing to fill small holes and smooth edges
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # --- 2. Create Filled Binary Mask (1s for shape, 0s for background) ---
    # Find contours to ensure the shape is solid
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Create a mask filled with zeros (black)
    filled_mask_255 = np.zeros_like(closed)
    # Draw filled contours onto the mask (shape becomes white)
    cv2.drawContours(filled_mask_255, contours, -1, (255), thickness=cv2.FILLED)

    # Convert to a mask with 1s for the shape and 0s for the background
    filled_mask_01 = (filled_mask_255 / 255).astype(np.uint8)

    # --- 3. Save the Mask as .dat ---
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(dat_output_path)
        if output_dir: # Create directory only if path is not just a filename
             os.makedirs(output_dir, exist_ok=True)
        # Save the 0/1 mask to the .dat file
        np.savetxt(dat_output_path, filled_mask_01, fmt='%d')
        # Quieter output for batch processing:
        # print(f"Successfully saved mask to {dat_output_path}")
        return filled_mask_01
    except Exception as e:
        print(f"Error saving .dat file to {dat_output_path}: {e}")
        return None

def create_black_shape_image_from_dat(dat_input_path, image_output_path):
    """
    Loads a binary mask from a .dat file (expecting 0s and 1s) and creates
    an image with a black shape (where mask is 1) on a white background.

    Parameters:
        dat_input_path (str): Path to the input .dat file.
        image_output_path (str): Path where the output image will be saved.

    Returns:
        numpy.ndarray or None: The created black-on-white image array if successful, None otherwise.
    """
    # --- 1. Load Mask from .dat ---
    try:
        loaded_mask_01 = np.loadtxt(dat_input_path, dtype=np.uint8)
    except Exception as e:
        print(f"Error loading .dat file from {dat_input_path}: {e}")
        return None

    # --- 2. Create Black Shape on White Background Image ---
    # Create a white canvas with the same shape as the mask
    height, width = loaded_mask_01.shape
    output_image = np.ones((height, width), dtype=np.uint8) * 255 # 255 is white

    # Where the mask is 1 (representing the shape), set the output image to 0 (black)
    output_image[loaded_mask_01 == 1] = 0

    # --- 3. Save the Image ---
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(image_output_path)
        if output_dir: # Create directory only if path is not just a filename
             os.makedirs(output_dir, exist_ok=True)
        cv2.imwrite(image_output_path, output_image)
        # Quieter output for batch processing:
        # print(f"Successfully saved reconstructed image to {image_output_path}")
        return output_image
    except Exception as e:
        print(f"Error saving image file to {image_output_path}: {e}")
        return None

def find_corners_on_image(image_array, corner_threshold_ratio=0.01):
    """
    Finds corners on a given image array using the Harris corner detector.
    (Note: This function only finds corners, it doesn't save any images)

    Parameters:
        image_array (numpy.ndarray): The input image (grayscale expected).
        corner_threshold_ratio (float): Ratio of max Harris response for thresholding.

    Returns:
        list: List of corner points [(x1, y1), (x2, y2), ...].
    """
    if image_array is None:
        # Don't print error here, let the caller handle None image
        # print("Error: Input image array is None for corner detection.")
        return []

    # Harris corner detector needs float32 input
    gray_for_corners = np.float32(image_array)
    dst = cv2.cornerHarris(gray_for_corners, blockSize=2, ksize=3, k=0.04)

    # Dilate to mark the corners
    dst = cv2.dilate(dst, None)

    # Threshold for an optimal value
    threshold_val = corner_threshold_ratio * dst.max()
    # Handle potential case where dst is all zeros (no corners)
    if threshold_val == 0:
         return []
    corner_coords = np.where(dst > threshold_val) # Gives (row_indices, col_indices) -> (y, x)


    # Format as (x, y)
    corners = list(zip(corner_coords[1], corner_coords[0]))

    # Quieter output for batch processing:
    # print(f"Detected {len(corners)} potential corners.")
    return corners


# --- Main Execution Block ---
if __name__ == "__main__":
    # --- Configuration for Latambarcem Structure ---
    base_plots_dir = "../maps/ambeli/plots"  # Base directory containing all sub-areas
    base_output_dir = "../maps/ambeli/dat_folder"  # Base output directory
    
    # Supported image extensions
    supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')

    print(f"Starting automated batch processing for Latambarcem village")
    print(f"Base plots directory: {base_plots_dir}")
    print(f"Base output directory: {base_output_dir}")

    total_processed = 0
    total_errors = 0
    processed_areas = 0

    # Check if base plots directory exists
    if not os.path.exists(base_plots_dir):
        print(f"Error: Base plots directory '{base_plots_dir}' not found.")
        print("Make sure you're running this script from the image_to_dat folder.")
        exit()

    # --- Loop through all sub-areas in latambarcem/plots ---
    try:
        all_subdirs = [d for d in os.listdir(base_plots_dir) 
                      if os.path.isdir(os.path.join(base_plots_dir, d))]
        all_subdirs.sort()  # Sort to process in order
    except Exception as e:
        print(f"Error accessing base plots directory: {e}")
        exit()

    print(f"Found {len(all_subdirs)} sub-areas: {', '.join(all_subdirs)}")
    
    for subdir in all_subdirs:
        print(f"\n🔄 Processing area {subdir}...")
        
        # Define paths for this sub-area
        input_folder = os.path.join(base_plots_dir, subdir, "enhanced")
        output_dat_dir = os.path.join(base_output_dir, subdir, "dat")
        output_image_dir = os.path.join(base_output_dir, subdir, "dat_image")
        
        # Check if enhanced folder exists for this sub-area
        if not os.path.exists(input_folder):
            print(f"    ⚠️ SKIPPED: No 'enhanced' folder found in area {subdir}")
            continue
        
        # Create output directories
        os.makedirs(output_dat_dir, exist_ok=True)
        os.makedirs(output_image_dir, exist_ok=True)
        
        area_processed = 0
        area_errors = 0

        # --- Loop through files in the enhanced folder ---
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
            
            # --- Generate Output Filenames ---
            base_filename = os.path.splitext(filename)[0]  # Get name without extension
            dat_file = os.path.join(output_dat_dir, f"{base_filename}.dat")
            reconstructed_image_file = os.path.join(output_image_dir, f"{base_filename}.png")

            # Check if files already exist (skip silently if they do)
            if os.path.exists(dat_file) and os.path.exists(reconstructed_image_file):
                area_processed += 1
                continue

            # --- Step 1: Create the .dat file from the image ---
            diagram_mask = create_diagram_mask_and_dat(input_image_path, dat_file)

            if diagram_mask is None:
                print(f"    ❌ FAILED: Could not create .dat file for {filename}")
                area_errors += 1
                continue

            # --- Step 2: Create the black-on-white reconstructed image from the .dat file ---
            reconstructed_image = create_black_shape_image_from_dat(dat_file, reconstructed_image_file)

            if reconstructed_image is None:
                print(f"    ❌ FAILED: Could not create reconstructed image for {filename}")
                area_errors += 1
                continue

            # --- Step 3 (Optional): Find and print corners (silent) ---
            corners = find_corners_on_image(reconstructed_image)
            # Only process corners silently, no output needed

            area_processed += 1

        # Only show summary if there were errors or if area was processed
        if area_errors > 0 or area_processed > 0:
            if area_errors > 0:
                print(f"  📊 Area {subdir}: {area_processed} processed, {area_errors} failed")
            # If no errors, process silently
        
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
    
    if total_processed > 0:
        print(f"\nOutput structure created:")
        print(f"  DAT files: {base_output_dir}/{{area_name}}/dat/")
        print(f"  Images: {base_output_dir}/{{area_name}}/dat_image/")
    else:
        print(f"\nNo files were processed. Please check:")
        print(f"  - Enhanced folders exist in sub-areas")
        print(f"  - Image files are present in enhanced folders")
        print(f"  - File paths are correct")