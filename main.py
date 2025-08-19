# main_app.py
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import cv2 # Make sure cv2 is imported for reading map image dimensions
import numpy as np
import time
import tempfile
import traceback

# Import our utility modules
import geometry_utils
import mask_utils
import comparison_utils
import advanced_comparison

# Import PDF generation module
try:
    from pdf_generator import create_pdf_report, is_pdf_generation_available
    FPDF_AVAILABLE = is_pdf_generation_available()
except ImportError:
    print("WARNING: PDF generator module not found. PDF report generation disabled.")
    FPDF_AVAILABLE = False

# --- Main Helper Functions ---
def get_available_villages():
    """Returns a list of available villages from the maps directory."""
    maps_dir = "maps"
    villages = []
    try:
        for item in os.listdir(maps_dir):
            village_path = os.path.join(maps_dir, item)
            if os.path.isdir(village_path):
                # Check if it has the required structure (dat_folder and panda folder)
                dat_folder = os.path.join(village_path, "dat_folder")
                panda_folders = [f for f in os.listdir(village_path) if f.endswith("_panda")]
                
                if os.path.exists(dat_folder) and panda_folders:
                    villages.append(item)
    except Exception as e:
        print(f"Error scanning villages: {e}")
    
    return villages

def get_village_structure(village_name):
    """Analyzes village structure and returns sub-villages if any."""
    dat_folder = os.path.join("maps", village_name, "dat_folder")
    plots_folder = os.path.join("maps", village_name, "plots")
    
    if not os.path.exists(dat_folder):
        return None, []
    
    # Get all subdirectories in dat_folder
    sub_villages = []
    try:
        for item in os.listdir(dat_folder):
            item_path = os.path.join(dat_folder, item)
            if os.path.isdir(item_path):
                # Check if it has dat and dat_image folders
                dat_subfolder = os.path.join(item_path, "dat")
                dat_image_subfolder = os.path.join(item_path, "dat_image")
                if os.path.exists(dat_subfolder) and os.path.exists(dat_image_subfolder):
                    sub_villages.append(item)
    except Exception as e:
        print(f"Error scanning sub-villages for {village_name}: {e}")
    
    return dat_folder, sorted(sub_villages)

def setup_config():
    """Sets up and returns configuration parameters with village selection."""
    # Get available villages
    available_villages = get_available_villages()
    
    if not available_villages:
        print("No villages found in the maps directory!")
        return None
    
    print("Available villages:")
    for i, village in enumerate(available_villages):
        print(f"{i + 1}. {village}")
    
    # Get user's village selection
    while True:
        try:
            choice = input(f"\nSelect a village (1-{len(available_villages)}): ")
            village_index = int(choice) - 1
            if 0 <= village_index < len(available_villages):
                selected_village = available_villages[village_index]
                break
            else:
                print(f"Please enter a number between 1 and {len(available_villages)}")
        except ValueError:
            print("Please enter a valid number")
        except EOFError:
            print("\nInput cancelled.")
            return None
    
    print(f"\nSelected village: {selected_village}")
    
    # Analyze village structure
    dat_folder_base, sub_villages = get_village_structure(selected_village)
    
    if not sub_villages:
        print(f"No sub-villages found in {selected_village}. This village might not have the expected structure.")
        return None
    
    print(f"Found {len(sub_villages)} sub-villages: {', '.join(sub_villages)}")
    
    # Find the shapefile
    panda_folder = None
    village_path = os.path.join("maps", selected_village)
    for item in os.listdir(village_path):
        if item.endswith("_panda"):
            panda_folder = os.path.join(village_path, item)
            break
    
    if not panda_folder:
        print(f"No panda folder found for {selected_village}")
        return None
    
    # Find the shapefile in the panda folder
    shapefile_path = None
    for file in os.listdir(panda_folder):
        if file.endswith(".shp"):
            shapefile_path = os.path.join(panda_folder, file)
            break
    
    if not shapefile_path:
        print(f"No shapefile found in {panda_folder}")
        return None
    
    # Set up the main map image path (look for map.jpg in first sub-village plots folder)
    full_map_image_path = None
    if sub_villages:
        potential_map_path = os.path.join("maps", selected_village, "plots", sub_villages[0], "map.jpg")
        if os.path.exists(potential_map_path):
            full_map_image_path = potential_map_path
    
    config = {
        "village_name": selected_village,
        "shapefile_path": shapefile_path,
        "full_map_image_path": full_map_image_path,
        "sub_villages": sub_villages,
        "dat_folder_base": dat_folder_base,
        "image_size": 500,
        "padding_ratio": 0.05,
        "original_image_extension": ".png",
        "save_reference_image": True,
        "reference_image_folder": "img_reference",
        "plots_image_extension": ".jpg",
        "top_n_matches": 5,
        "iou_prioritization_tolerance": 0.01,
        "hausdorff_prioritization_tolerance": 2.0,
    }
    
    # Basic validation
    if config["full_map_image_path"] and not os.path.exists(config["full_map_image_path"]):
        print(f"Warning: Full map image path specified but not found: {config['full_map_image_path']}")
        config["full_map_image_path"] = None
    
    return config

def get_user_selections(config):
    """Loads shapefile and gets user selections for index and method."""
    try:
        data = gpd.read_file(config["shapefile_path"])
        print(f"Shapefile loaded: {config['shapefile_path']}")
        num_geometries = len(data)
        if num_geometries == 0: raise ValueError("Shapefile is empty.")
        print(f"Found {num_geometries} features.")
    except Exception as e:
        print(f"Error reading shapefile: {e}")
        return None, None, None # Return None values on error

    print(f"\nAvailable feature indices: 0 to {num_geometries - 1}")
    chosen_index = -1
    while True: # Loop for index input
        try:
            user_input = input(f"Enter the index of the plot/feature to use as reference (0-{num_geometries - 1}): ")
            chosen_index = int(user_input)
            if 0 <= chosen_index < num_geometries: break
            else: print(f"Error: Index out of range.")
        except ValueError: print("Error: Invalid input.")
        except EOFError: print("\nInput cancelled."); return None, None, None
    print(f"Using feature index {chosen_index} as reference.")

    comparison_method = ''
    while True: # Loop for method input
        user_choice = input("Choose comparison method ('standard' or 'advanced'): ").lower().strip()
        if user_choice in ['standard', 'advanced']:
            comparison_method = user_choice
            break
        else:
            print("Invalid choice. Please enter 'standard' or 'advanced'.")

    return data, chosen_index, comparison_method

def generate_references(data, chosen_index, config):
    """Generates reference mask and potentially saves reference image."""
    reference_mask = None
    reference_image_path = None
    try:
        selected_geometry = data.loc[chosen_index, 'geometry']
        shape_coords = geometry_utils.get_coordinates_from_geometry(selected_geometry)
        if shape_coords is None: raise ValueError("Could not extract coordinates.")
        shape_norm = geometry_utils.normalize_coordinates(shape_coords)
        if shape_norm is None: raise ValueError("Could not normalize coordinates.")
        shape_norm_padded = geometry_utils.pad_normalized_coordinates(shape_norm, config["padding_ratio"])
        if shape_norm_padded is None: raise ValueError("Could not pad coordinates.")

        reference_mask = mask_utils.create_mask_from_coords(shape_norm_padded, config["image_size"])
        if not np.any(reference_mask):
             print(f"Warning: Reference mask for index {chosen_index} is empty.")
             return None, None # Return None if mask is empty

        print(f"Reference mask generated successfully (Size: {reference_mask.shape}).")

        if config["save_reference_image"]:
            os.makedirs(config["reference_image_folder"], exist_ok=True)
            shapefile_basename = os.path.splitext(os.path.basename(config["shapefile_path"]))[0]
            ref_img_filename = f"{shapefile_basename}_ref_idx{chosen_index}.png"
            reference_image_path = os.path.join(config["reference_image_folder"], ref_img_filename)
            try:
                ref_img_display = np.ones((config["image_size"], config["image_size"]), dtype=np.uint8) * 255
                ref_img_display[reference_mask == 1] = 0 # Black shape
                cv2.imwrite(reference_image_path, ref_img_display)
                print(f"Reference image saved to {reference_image_path}")
            except Exception as e:
                print(f"Warning: Could not save reference image: {e}")
                reference_image_path = None # Path is invalid if saving failed
        return reference_mask, reference_image_path
    except Exception as e:
        print(f"Error generating reference data for index {chosen_index}: {e}")
        return None, None

def run_comparison(reference_mask, reference_image_path, comparison_method, config):
    """Runs the chosen comparison method across all sub-villages and returns sorted results list and best match info."""
    comparison_results_list = []
    best_match_found = False
    best_match_base_filename = None
    best_match_score_info = ""

    if comparison_method == 'standard':
        print(f"\nPerforming standard comparison across all sub-villages in: {config['village_name']}")
        
        total_processed_files = 0
        temp_results = []
        
        # Iterate through all sub-villages
        for sub_village in config['sub_villages']:
            comparison_dat_folder = os.path.join(config['dat_folder_base'], sub_village, 'dat')
            print(f"Processing sub-village: {sub_village}")
            
            try:
                all_comparison_files = [f for f in os.listdir(comparison_dat_folder) if f.lower().endswith('.dat')]
                if not all_comparison_files: 
                    print(f"  No .dat files found in {comparison_dat_folder}")
                    continue
                print(f"  Found {len(all_comparison_files)} .dat files in {sub_village}")
            except Exception as e: 
                print(f"  Error accessing comparison folder {comparison_dat_folder}: {e}")
                continue

            processed_files_in_subvillage = 0
            for dat_filename in all_comparison_files:
                comparison_dat_path = os.path.join(comparison_dat_folder, dat_filename)
                comparison_mask = mask_utils.load_dat_as_mask(comparison_dat_path, target_size=(config['image_size'], config['image_size']))
                if comparison_mask is None: 
                    print(f"  Skipping {dat_filename} due to loading error.")
                    continue
                
                result = comparison_utils.compare_masks(
                    reference_mask, comparison_mask,
                    iou_tolerance=config['iou_prioritization_tolerance'],
                    hausdorff_tolerance=config['hausdorff_prioritization_tolerance']
                )
                processed_files_in_subvillage += 1
                total_processed_files += 1
                
                temp_results.append({
                    "filename": dat_filename, 
                    "sub_village": sub_village,
                    "iou": result["best_iou"], 
                    "iou_transform": result["best_iou_transform"],
                    "hausdorff": result["best_hausdorff"], 
                    "hausdorff_transform": result["best_hausdorff_transform"]
                })
            
            print(f"  Processed {processed_files_in_subvillage} files in {sub_village}")
        
        print(f"Standard comparison processing completed for {total_processed_files} files across {len(config['sub_villages'])} sub-villages.")
        
        if temp_results:
            temp_results.sort(key=lambda x: (x["iou"], -x["hausdorff"]), reverse=True)
            comparison_results_list = temp_results # Assign sorted results
            best_match_found = True
            best_match_source_file = comparison_results_list[0]['filename']
            best_match_sub_village = comparison_results_list[0]['sub_village']
            best_match_base_filename = os.path.splitext(best_match_source_file)[0]
            best_match_score_info = f"IoU: {comparison_results_list[0]['iou']:.3f} (Sub-village: {best_match_sub_village})"
        else: 
            print("No standard comparisons were successfully performed.")

    elif comparison_method == 'advanced':
        print(f"\nPerforming advanced comparison using VGG16 across all sub-villages...")
        if reference_image_path is None or not os.path.exists(reference_image_path):
             print(f"Error: Reference image needed for advanced comparison not found at '{reference_image_path}'.")
             return [], False, None, "" # Cannot proceed

        total_comparison_files = []
        
        # Collect all image files from all sub-villages
        for sub_village in config['sub_villages']:
            original_image_folder = os.path.join(config['dat_folder_base'], sub_village, 'dat_image')
            print(f"Processing sub-village: {sub_village}")
            
            try:
                comparison_image_files = [os.path.join(original_image_folder, f)
                                         for f in os.listdir(original_image_folder)
                                         if f.lower().endswith(config['original_image_extension'])]
                if not comparison_image_files:
                    print(f"  No '{config['original_image_extension']}' files found in {original_image_folder}")
                    continue
                
                print(f"  Found {len(comparison_image_files)} image files in {sub_village}")
                # Add sub-village info to each file path for tracking
                for img_path in comparison_image_files:
                    total_comparison_files.append((img_path, sub_village))
                    
            except Exception as e: 
                print(f"  Error accessing original image folder {original_image_folder}: {e}")
                continue

        if not total_comparison_files:
            print("No image files found in any sub-village for advanced comparison.")
            return [], False, None, ""

        print(f"Total image files collected: {len(total_comparison_files)}")
        
        # Extract just the paths for VGG comparison
        image_paths_only = [item[0] for item in total_comparison_files]
        advanced_results_tuples = advanced_comparison.run_vgg16_comparison(reference_image_path, image_paths_only)

        if advanced_results_tuples:
             # Convert to list of dicts and add sub-village info
             for img_path, similarity in advanced_results_tuples:
                 # Find the corresponding sub-village for this image path
                 sub_village_for_path = None
                 for path, sub_village in total_comparison_files:
                     if path == img_path:
                         sub_village_for_path = sub_village
                         break
                 
                 comparison_results_list.append({
                     'img_path': img_path, 
                     'similarity': similarity,
                     'sub_village': sub_village_for_path or 'unknown'
                 })
             
             # Results already sorted by run_vgg16_comparison
             best_match_found = True
             best_match_source_file = comparison_results_list[0]['img_path']
             best_match_sub_village = comparison_results_list[0]['sub_village']
             best_match_base_filename = os.path.splitext(os.path.basename(best_match_source_file))[0]
             best_match_score_info = f"VGG Sim: {comparison_results_list[0]['similarity']:.3f} (Sub-village: {best_match_sub_village})"
        else: 
            print("No advanced comparisons were successfully performed.")

    return comparison_results_list, best_match_found, best_match_base_filename, best_match_score_info

def report_and_visualize(config, chosen_index, reference_mask, comparison_method, results_list,
                          best_match_found, best_match_base_filename, best_match_score_info):
    """Handles console reporting and matplotlib visualization."""
    if not best_match_found or not results_list:
        print("\nNo comparison results to report or visualize.")
        if reference_mask is not None:
             plt.figure(figsize=(6, 6)); plt.imshow(reference_mask, cmap='gray'); plt.title(f"Reference Mask (Index {chosen_index})\nNo Match Found"); plt.axis('off');
             print("Displaying reference mask plot. Close the plot window to continue...")
             plt.show()
        return

    # --- Console Report ---
    print(f"\n--- Top {config['top_n_matches']} {comparison_method.capitalize()} Matches for Index {chosen_index} ---")
    for i, res in enumerate(results_list[:config['top_n_matches']]):
        if comparison_method == 'standard':
            print(f"{i+1}. File: {res.get('filename', 'N/A')} (Sub-village: {res.get('sub_village', 'N/A')})")
            print(f"   IoU: {res.get('iou', 0.0):.4f} (Transform: {res.get('iou_transform', 'N/A')})")
            haus_dist = res.get('hausdorff', float('inf'))
            haus_str = f"{haus_dist:.2f}" if haus_dist != float('inf') else "Inf/Error"
            print(f"   Hausdorff Distance: {haus_str} (Transform: {res.get('hausdorff_transform', 'N/A')})")
        elif comparison_method == 'advanced':
             print(f"{i+1}. Image: {os.path.basename(res.get('img_path', 'N/A'))} (Sub-village: {res.get('sub_village', 'N/A')})")
             print(f"   VGG16 Similarity: {res.get('similarity', 0.0):.4f}")
        print("-" * 10)    # --- Matplotlib Visualization ---
    # Find the best match plot image path by determining which sub-village it belongs to
    best_match_sub_village = results_list[0].get('sub_village', 'unknown')
    # Look for the plot image in the corresponding plots sub-folder
    plot_image_path = None
    
    # Try multiple extensions (similar to PDF generation logic)
    extensions_to_try = ['.png', '.jpg', '.jpeg', config['plots_image_extension']]
    # Remove duplicates while preserving order
    extensions_to_try = list(dict.fromkeys(extensions_to_try))
    
    # First try the specific sub-village folder
    for extension in extensions_to_try:
        potential_plots_paths = [
            os.path.join("maps", config['village_name'], "plots", best_match_sub_village, "contours", f"{best_match_base_filename}{extension}"),
            os.path.join("maps", config['village_name'], "plots", best_match_sub_village, "contour", f"{best_match_base_filename}{extension}"),
            os.path.join("maps", config['village_name'], "plots", best_match_sub_village, f"{best_match_base_filename}{extension}"),
            os.path.join("maps", config['village_name'], "plots", best_match_sub_village, "enhanced", f"{best_match_base_filename}{extension}")
        ]
        
        for potential_path in potential_plots_paths:
            if os.path.exists(potential_path):
                plot_image_path = potential_path
                break
        
        if plot_image_path:
            break
    
    # Fallback: search all sub-village plot folders if not found in the specific one
    if plot_image_path is None:
        for sub_village in config['sub_villages']:
            for extension in extensions_to_try:
                for folder_name in ['contours', 'contour', '', 'enhanced']:
                    if folder_name:
                        potential_path = os.path.join("maps", config['village_name'], "plots", sub_village, folder_name, f"{best_match_base_filename}{extension}")
                    else:
                        potential_path = os.path.join("maps", config['village_name'], "plots", sub_village, f"{best_match_base_filename}{extension}")
                    
                    if os.path.exists(potential_path):
                        plot_image_path = potential_path
                        break
                
                if plot_image_path:
                    break
            
            if plot_image_path:
                break

    print(f"\nVisualizing reference mask vs. plot image: {plot_image_path if plot_image_path else 'Not found'}")
    
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1); plt.imshow(reference_mask, cmap='gray'); plt.title(f"Reference Mask (Index {chosen_index})"); plt.axis('off')
    plt.subplot(1, 2, 2)
    
    if plot_image_path and os.path.exists(plot_image_path):
        plot_image = cv2.imread(plot_image_path)
        if plot_image is not None:
            plt.imshow(cv2.cvtColor(plot_image, cv2.COLOR_BGR2RGB))
            plt.title(f"Best Match Plot: {best_match_base_filename}{config['plots_image_extension']}\nSub-village: {best_match_sub_village}\n({best_match_score_info})")
            plt.axis('off')
        else:
            plt.text(0.5, 0.5, f"Error loading image:\n{plot_image_path}", ha='center', va='center', wrap=True)
            plt.title(f"Plot Image Error")
            plt.axis('off')
    else:
        plt.text(0.5, 0.5, f"Plot image not found:\n{best_match_base_filename}{config['plots_image_extension']}\nSub-village: {best_match_sub_village}", ha='center', va='center', wrap=True)
        plt.title(f"Plot Image Missing")
        plt.axis('off')
    
    plt.tight_layout()
    print("Displaying comparison plot. Close the plot window to continue...")
    plt.show() # Blocks execution

def cleanup_reference_image(config, reference_image_path):
    """Deletes the saved reference image if applicable."""
    if config.get('save_reference_image', False) and reference_image_path is not None: # Use .get for safety
        # print(f"\nCleaning up reference image: {reference_image_path}") # Optional Verbose
        try:
            if os.path.exists(reference_image_path):
                os.remove(reference_image_path)
                # print("Reference image deleted successfully.") # Optional Verbose
        except Exception as e:
            print(f"Error deleting reference image file {reference_image_path}: {e}")
    # else: print("\nSkipping reference image cleanup.") # Optional verbose


# --- New Main Orchestration Function ---
def run_main_workflow():
    """Orchestrates the main application workflow."""
    config = setup_config()
    reference_image_path_for_cleanup = None # Keep track of path for final cleanup

    try:
        data, chosen_index, comparison_method = get_user_selections(config)
        if data is None: return # Exit if user cancelled or error during input

        reference_mask, reference_image_path = generate_references(data, chosen_index, config)
        if reference_mask is None: return # Exit if ref generation failed
        reference_image_path_for_cleanup = reference_image_path # Store path if generated

        results_list, best_match_found, best_match_base_filename, best_match_score_info = run_comparison(
            reference_mask, reference_image_path, comparison_method, config
        )

        # Report and Visualize first (Matplotlib blocks)
        report_and_visualize(config, chosen_index, reference_mask, comparison_method, results_list,
                             best_match_found, best_match_base_filename, best_match_score_info)
        
        # Generate PDF Report (Call the existing function)
        if best_match_found and results_list:
             # Find the best match sub-village and set up plots folder
             best_match_sub_village = results_list[0].get('sub_village', 'unknown')
             potential_plots_folders = [
                 os.path.join("maps", config['village_name'], "plots", best_match_sub_village, "contours"),
                 os.path.join("maps", config['village_name'], "plots", best_match_sub_village),
                 os.path.join("maps", config['village_name'], "plots", best_match_sub_village, "enhanced")
             ]
             
             plots_folder_for_pdf = None
             for folder in potential_plots_folders:
                 if os.path.exists(folder):
                     plots_folder_for_pdf = folder
                     break
             
             if plots_folder_for_pdf is None:
                 plots_folder_for_pdf = os.path.join("maps", config['village_name'], "plots", best_match_sub_village)
             
             # Create pdf_reports folder if it doesn't exist
             pdf_reports_folder = "pdf_reports"
             if not os.path.exists(pdf_reports_folder):
                 os.makedirs(pdf_reports_folder)
                 print(f"Created folder: {pdf_reports_folder}")
             
             pdf_output_filename = f"comparison_report_{config['village_name']}_idx{chosen_index}_{comparison_method}.pdf"
             pdf_output_path = os.path.join(pdf_reports_folder, pdf_output_filename)
             
             create_pdf_report( # Assumes create_pdf_report is defined above or imported
                 pdf_filename=pdf_output_path,
                 chosen_index=chosen_index,
                 full_map_image_path=config.get("full_map_image_path"), # Use .get for optional keys
                 reference_image_path=reference_image_path, # Pass generated ref img path
                 best_match_found=best_match_found,
                 best_match_base_filename=best_match_base_filename,
                 best_match_score_info=best_match_score_info,
                 comparison_method=comparison_method,
                 top_results_list=results_list, # Pass the populated list
                 plots_folder=plots_folder_for_pdf,
                 plots_image_extension=config["plots_image_extension"],
                 top_n_matches=config["top_n_matches"],
                 village_name=config["village_name"]
             )
        else:
             print("\nSkipping PDF report generation (no best match found or no results).")


    except Exception as e:
        print(f"\n>> An unexpected error occurred in the main workflow: {e}")
        # Print detailed traceback for debugging unexpected errors
        traceback.print_exc()

    finally:
        # Cleanup always attempts if path was generated
        cleanup_reference_image(config, reference_image_path_for_cleanup)

    print("\nScript finished.")


if __name__ == "__main__":
    # Check for optional dependencies
    tf_available = False; pillow_available = False; fpdf_available = FPDF_AVAILABLE
    try: import tensorflow; tf_available = True
    except ImportError: print("WARNING: TensorFlow not found.")
    try: from PIL import Image; pillow_available = True
    except ImportError: print("WARNING: Pillow not found.")

    if not (tf_available and pillow_available): print("--- Advanced comparison disabled due to missing libraries. ---")
    if not fpdf_available: print("--- PDF report generation disabled due to missing FPDF2 library. ---")

    run_main_workflow() # Call the new orchestrator function