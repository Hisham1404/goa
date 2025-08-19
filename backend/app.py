from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import traceback
import tempfile
import geopandas as gpd
import pandas as pd
import numpy as np
import base64
import io
from datetime import datetime
import cv2
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Import our utility modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend connectivity

# Global configuration
CONFIG_BASE = {
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

# Helper functions adapted from main.py
def get_available_villages():
    """Returns a list of available villages from the maps directory."""
    maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dat_folder = os.path.join(base_dir, "maps", village_name, "dat_folder")
    
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

def setup_config_for_village(village_name):
    """Sets up configuration for a specific village."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Analyze village structure
    dat_folder_base, sub_villages = get_village_structure(village_name)
    
    if not sub_villages:
        raise ValueError(f"No sub-villages found in {village_name}")
    
    # Find the shapefile
    panda_folder = None
    village_path = os.path.join(base_dir, "maps", village_name)
    for item in os.listdir(village_path):
        if item.endswith("_panda"):
            panda_folder = os.path.join(village_path, item)
            break
    
    if not panda_folder:
        raise ValueError(f"No panda folder found for {village_name}")
    
    # Find the shapefile in the panda folder
    shapefile_path = None
    for file in os.listdir(panda_folder):
        if file.endswith(".shp"):
            shapefile_path = os.path.join(panda_folder, file)
            break
    
    if not shapefile_path:
        raise ValueError(f"No shapefile found in {panda_folder}")
    
    # Set up the main map image path
    full_map_image_path = None
    if sub_villages:
        potential_map_path = os.path.join(base_dir, "maps", village_name, "plots", sub_villages[0], "map.jpg")
        if os.path.exists(potential_map_path):
            full_map_image_path = potential_map_path
    
    config = CONFIG_BASE.copy()
    config.update({
        "village_name": village_name,
        "shapefile_path": shapefile_path,
        "full_map_image_path": full_map_image_path,
        "sub_villages": sub_villages,
        "dat_folder_base": dat_folder_base,
    })
    
    return config

def generate_references_api(data, chosen_index, config):
    """Generates reference mask and potentially saves reference image."""
    reference_mask = None
    reference_image_path = None
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        selected_geometry = data.loc[chosen_index, 'geometry']
        shape_coords = geometry_utils.get_coordinates_from_geometry(selected_geometry)
        if shape_coords is None: 
            raise ValueError("Could not extract coordinates.")
        
        shape_norm = geometry_utils.normalize_coordinates(shape_coords)
        if shape_norm is None: 
            raise ValueError("Could not normalize coordinates.")
        
        shape_norm_padded = geometry_utils.pad_normalized_coordinates(shape_norm, config["padding_ratio"])
        if shape_norm_padded is None: 
            raise ValueError("Could not pad coordinates.")

        reference_mask = mask_utils.create_mask_from_coords(shape_norm_padded, config["image_size"])
        if not np.any(reference_mask):
            raise ValueError(f"Reference mask for index {chosen_index} is empty.")

        if config["save_reference_image"]:
            ref_folder = os.path.join(base_dir, config["reference_image_folder"])
            os.makedirs(ref_folder, exist_ok=True)
            shapefile_basename = os.path.splitext(os.path.basename(config["shapefile_path"]))[0]
            ref_img_filename = f"{shapefile_basename}_ref_idx{chosen_index}.png"
            reference_image_path = os.path.join(ref_folder, ref_img_filename)
            
            ref_img_display = np.ones((config["image_size"], config["image_size"]), dtype=np.uint8) * 255
            ref_img_display[reference_mask == 1] = 0  # Black shape
            cv2.imwrite(reference_image_path, ref_img_display)
            
        return reference_mask, reference_image_path
        
    except Exception as e:
        raise ValueError(f"Error generating reference data for index {chosen_index}: {e}")

def run_comparison_api(reference_mask, reference_image_path, comparison_method, config):
    """Runs the chosen comparison method across all sub-villages."""
    comparison_results_list = []
    best_match_found = False
    best_match_base_filename = None
    best_match_score_info = ""

    if comparison_method == 'standard':
        total_processed_files = 0
        temp_results = []
        
        # Iterate through all sub-villages
        for sub_village in config['sub_villages']:
            comparison_dat_folder = os.path.join(config['dat_folder_base'], sub_village, 'dat')
            
            try:
                all_comparison_files = [f for f in os.listdir(comparison_dat_folder) if f.lower().endswith('.dat')]
                if not all_comparison_files: 
                    continue
            except Exception as e: 
                continue

            for dat_filename in all_comparison_files:
                comparison_dat_path = os.path.join(comparison_dat_folder, dat_filename)
                comparison_mask = mask_utils.load_dat_as_mask(comparison_dat_path, target_size=(config['image_size'], config['image_size']))
                if comparison_mask is None: 
                    continue
                
                result = comparison_utils.compare_masks(
                    reference_mask, comparison_mask,
                    iou_tolerance=config['iou_prioritization_tolerance'],
                    hausdorff_tolerance=config['hausdorff_prioritization_tolerance']
                )
                total_processed_files += 1
                
                temp_results.append({
                    "filename": dat_filename, 
                    "sub_village": sub_village,
                    "iou": result["best_iou"], 
                    "iou_transform": result["best_iou_transform"],
                    "hausdorff": result["best_hausdorff"], 
                    "hausdorff_transform": result["best_hausdorff_transform"]
                })
        
        if temp_results:
            temp_results.sort(key=lambda x: (x["iou"], -x["hausdorff"]), reverse=True)
            comparison_results_list = temp_results
            best_match_found = True
            best_match_source_file = comparison_results_list[0]['filename']
            best_match_sub_village = comparison_results_list[0]['sub_village']
            best_match_base_filename = os.path.splitext(best_match_source_file)[0]
            best_match_score_info = f"IoU: {comparison_results_list[0]['iou']:.3f} (Sub-village: {best_match_sub_village})"

    elif comparison_method == 'advanced':
        if reference_image_path is None or not os.path.exists(reference_image_path):
            raise ValueError("Reference image needed for advanced comparison not found")

        total_comparison_files = []
        
        # Collect all image files from all sub-villages
        for sub_village in config['sub_villages']:
            original_image_folder = os.path.join(config['dat_folder_base'], sub_village, 'dat_image')
            
            try:
                comparison_image_files = [os.path.join(original_image_folder, f)
                                         for f in os.listdir(original_image_folder)
                                         if f.lower().endswith(config['original_image_extension'])]
                if not comparison_image_files:
                    continue
                
                for img_path in comparison_image_files:
                    total_comparison_files.append((img_path, sub_village))
                    
            except Exception as e: 
                continue

        if not total_comparison_files:
            raise ValueError("No image files found for advanced comparison")
        
        # Extract just the paths for VGG comparison
        image_paths_only = [item[0] for item in total_comparison_files]
        advanced_results_tuples = advanced_comparison.run_vgg16_comparison(reference_image_path, image_paths_only)

        if advanced_results_tuples:
            for img_path, similarity in advanced_results_tuples:
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
             
            best_match_found = True
            best_match_source_file = comparison_results_list[0]['img_path']
            best_match_sub_village = comparison_results_list[0]['sub_village']
            best_match_base_filename = os.path.splitext(os.path.basename(best_match_source_file))[0]
            best_match_score_info = f"VGG Sim: {comparison_results_list[0]['similarity']:.3f} (Sub-village: {best_match_sub_village})"

    return comparison_results_list, best_match_found, best_match_base_filename, best_match_score_info

# API Routes
@app.route('/api/villages', methods=['GET'])
def get_villages():
    """Get available villages."""
    try:
        villages = get_available_villages()
        return jsonify({
            'success': True,
            'villages': villages
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/village/<village_name>/structure', methods=['GET'])
def get_village_info(village_name):
    """Get village structure information."""
    try:
        config = setup_config_for_village(village_name)
        
        # Load shapefile to get feature count
        data = gpd.read_file(config["shapefile_path"])
        num_features = len(data)
        
        return jsonify({
            'success': True,
            'village_name': village_name,
            'sub_villages': config['sub_villages'],
            'num_features': num_features,
            'has_full_map': config['full_map_image_path'] is not None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/village/<village_name>/survey-numbers', methods=['GET'])
def get_survey_numbers(village_name):
    """Get survey numbers (shapefile feature indices) for a specific village."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Find the shapefile
        village_path = os.path.join(base_dir, "maps", village_name)
        if not os.path.exists(village_path):
            return jsonify({
                'success': False,
                'error': f'Village {village_name} not found'
            }), 404
        
        panda_folder = None
        for item in os.listdir(village_path):
            if item.endswith("_panda"):
                panda_folder = os.path.join(village_path, item)
                break
        
        if not panda_folder:
            return jsonify({
                'success': False,
                'error': f'No panda folder found for {village_name}'
            }), 404
        
        # Find the shapefile in the panda folder
        shapefile_path = None
        for file in os.listdir(panda_folder):
            if file.endswith(".shp"):
                shapefile_path = os.path.join(panda_folder, file)
                break
        
        if not shapefile_path:
            return jsonify({
                'success': False,
                'error': f'No shapefile found in {panda_folder}'
            }), 404
        
        # Read the shapefile and get feature information
        data = gpd.read_file(shapefile_path)
        num_features = len(data)
        
        if num_features == 0:
            return jsonify({
                'success': False,
                'error': 'Shapefile is empty'
            }), 400
        
        # Create survey numbers list with feature indices and any available attributes
        survey_numbers = []
        for i in range(num_features):
            feature_info = {"index": i}
            
            # Try to get some identifying information from the shapefile attributes
            row = data.iloc[i]
            for col in data.columns:
                if col.lower() != 'geometry' and col.lower() in ['id', 'plot_id', 'survey_no', 'plot_no', 'number', 'name']:
                    feature_info[col.lower()] = str(row[col]) if pd.notna(row[col]) else None
                    break
            
            survey_numbers.append(feature_info)
        
        return jsonify({
            'success': True,
            'village_name': village_name,
            'survey_numbers': survey_numbers,
            'total_features': num_features,
            'shapefile_path': shapefile_path
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/compare', methods=['POST'])
def run_comparison():
    """Main comparison endpoint."""
    try:
        data = request.json
        village_name = data.get('village_name')
        chosen_index = data.get('chosen_index')
        comparison_method = data.get('comparison_method', 'standard')
        
        if not all([village_name, chosen_index is not None, comparison_method]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: village_name, chosen_index, comparison_method'
            }), 400
        
        # Setup configuration
        config = setup_config_for_village(village_name)
        
        # Load shapefile and validate index
        shapefile_data = gpd.read_file(config["shapefile_path"])
        if chosen_index < 0 or chosen_index >= len(shapefile_data):
            return jsonify({
                'success': False,
                'error': f'Index {chosen_index} out of range. Available: 0-{len(shapefile_data)-1}'
            }), 400
        
        # Generate references
        reference_mask, reference_image_path = generate_references_api(shapefile_data, chosen_index, config)
        
        # Run comparison
        results_list, best_match_found, best_match_base_filename, best_match_score_info = run_comparison_api(
            reference_mask, reference_image_path, comparison_method, config
        )
        
        # Prepare response
        response_data = {
            'success': True,
            'best_match_found': best_match_found,
            'best_match_info': {
                'filename': best_match_base_filename,
                'score_info': best_match_score_info
            } if best_match_found else None,
            'results': results_list[:config['top_n_matches']],
            'comparison_method': comparison_method,
            'chosen_index': chosen_index,
            'village_name': village_name
        }
        
        # Store results for PDF generation
        session_id = f"{village_name}_{chosen_index}_{comparison_method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Store session data in a simple file-based cache (for production, use Redis or database)
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        session_data = {
            'config': config,
            'chosen_index': chosen_index,
            'comparison_method': comparison_method,
            'results_list': results_list,
            'best_match_found': best_match_found,
            'best_match_base_filename': best_match_base_filename,
            'best_match_score_info': best_match_score_info,
            'reference_image_path': reference_image_path
        }
        
        with open(os.path.join(cache_dir, f'{session_id}.json'), 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            if reference_mask is not None:
                session_data['reference_mask'] = reference_mask.tolist()
            json.dump(session_data, f)
        
        response_data['session_id'] = session_id
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/generate-pdf/<session_id>', methods=['POST'])
def generate_pdf(session_id):
    """Generate PDF report for a comparison session."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(base_dir, 'cache')
        session_file = os.path.join(cache_dir, f'{session_id}.json')
        
        if not os.path.exists(session_file):
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Load session data
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        config = session_data['config']
        chosen_index = session_data['chosen_index']
        comparison_method = session_data['comparison_method']
        results_list = session_data['results_list']
        best_match_found = session_data['best_match_found']
        best_match_base_filename = session_data['best_match_base_filename']
        best_match_score_info = session_data['best_match_score_info']
        reference_image_path = session_data['reference_image_path']
        
        if not best_match_found or not results_list:
            return jsonify({
                'success': False,
                'error': 'No results to generate PDF'
            }), 400
        
        # Find the best match sub-village and set up plots folder
        best_match_sub_village = results_list[0].get('sub_village', 'unknown')
        potential_plots_folders = [
            os.path.join(base_dir, "maps", config['village_name'], "plots", best_match_sub_village, "contours"),
            os.path.join(base_dir, "maps", config['village_name'], "plots", best_match_sub_village),
            os.path.join(base_dir, "maps", config['village_name'], "plots", best_match_sub_village, "enhanced")
        ]
        
        plots_folder_for_pdf = None
        for folder in potential_plots_folders:
            if os.path.exists(folder):
                plots_folder_for_pdf = folder
                break
        
        if plots_folder_for_pdf is None:
            plots_folder_for_pdf = os.path.join(base_dir, "maps", config['village_name'], "plots", best_match_sub_village)
        
        # Create pdf_reports folder if it doesn't exist
        pdf_reports_folder = os.path.join(base_dir, "pdf_reports")
        if not os.path.exists(pdf_reports_folder):
            os.makedirs(pdf_reports_folder)
        
        pdf_output_filename = f"comparison_report_{config['village_name']}_idx{chosen_index}_{comparison_method}.pdf"
        pdf_output_path = os.path.join(pdf_reports_folder, pdf_output_filename)
        
        # Generate PDF
        create_pdf_report(
            pdf_filename=pdf_output_path,
            chosen_index=chosen_index,
            full_map_image_path=config.get("full_map_image_path"),
            reference_image_path=reference_image_path,
            best_match_found=best_match_found,
            best_match_base_filename=best_match_base_filename,
            best_match_score_info=best_match_score_info,
            comparison_method=comparison_method,
            top_results_list=results_list,
            plots_folder=plots_folder_for_pdf,
            plots_image_extension=config["plots_image_extension"],
            top_n_matches=config["top_n_matches"],
            village_name=config["village_name"]
        )
        
        return jsonify({
            'success': True,
            'pdf_path': pdf_output_path,
            'pdf_filename': pdf_output_filename
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/download-pdf/<filename>', methods=['GET'])
def download_pdf(filename):
    """Download PDF file."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_path = os.path.join(base_dir, "pdf_reports", filename)
        
        if not os.path.exists(pdf_path):
            return jsonify({
                'success': False,
                'error': 'PDF file not found'
            }), 404
        
        return send_file(pdf_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    tf_available = False
    pillow_available = False
    
    try: 
        import tensorflow
        tf_available = True
    except ImportError: 
        pass
    
    try: 
        from PIL import Image
        pillow_available = True
    except ImportError: 
        pass
    
    return jsonify({
        'success': True,
        'status': 'healthy',
        'dependencies': {
            'tensorflow': tf_available,
            'pillow': pillow_available,
            'fpdf': FPDF_AVAILABLE
        },
        'advanced_comparison_available': tf_available and pillow_available,
        'pdf_generation_available': FPDF_AVAILABLE
    })

if __name__ == '__main__':
    print("Starting Map Comparison Backend...")
    print(f"TensorFlow available: {False}")
    print(f"Pillow available: {False}")
    print(f"PDF generation available: {FPDF_AVAILABLE}")
    
    try:
        import tensorflow
        print("TensorFlow available: True")
    except ImportError:
        print("TensorFlow available: False")
    
    try:
        from PIL import Image
        print("Pillow available: True")
    except ImportError:
        print("Pillow available: False")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
