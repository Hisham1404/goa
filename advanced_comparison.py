# advanced_comparison.py
import numpy as np
import tensorflow as tf
try:
    from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import GlobalAveragePooling2D
    from tensorflow.keras.utils import img_to_array
except ImportError:
    print("ERROR: TensorFlow/Keras not found. Please install it: pip install tensorflow")
    # You might exit here or disable the advanced feature
    VGG16 = None # Set to None to allow checking later

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not found. Please install it: pip install Pillow")
    Image = None # Set to None

from scipy.spatial.distance import cosine
import os

class ImageComparator:
    """Compares images using VGG16 features."""
    def __init__(self):
        self.model = self._load_vgg16_model()

    def _load_vgg16_model(self):
        """Loads the VGG16 model."""
        if VGG16 is None: # Check if import failed
            print("VGG16 model cannot be loaded due to missing TensorFlow/Keras.")
            return None
        try:
            print("Loading VGG16 model (this may take a moment)...")
            # Using pooling='avg' simplifies the model creation slightly
            base_model = VGG16(weights='imagenet', include_top=False, input_shape=(224, 224, 3), pooling='avg')
            # The model directly outputs the GAP features now
            model = Model(inputs=base_model.input, outputs=base_model.output)
            print("VGG16 model loaded successfully.")
            return model
        except Exception as e:
            print(f"Error loading VGG16 model: {e}")
            print("Ensure you have an internet connection for the first download.")
            return None

    def _preprocess_pil_image(self, pil_img):
        """Preprocess PIL image for VGG16"""
        if self.model is None: return None
        try:
            # Ensure image is RGB and correct size
            img = pil_img.convert('RGB').resize((224, 224))
            img_array = img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            return preprocess_input(img_array)
        except Exception as e:
             print(f"Error during image preprocessing: {e}")
             return None

    def get_features(self, image_path_or_pil_img):
        """Extract features from an image (path or PIL object) using VGG16"""
        if self.model is None: return None
        try:
            if isinstance(image_path_or_pil_img, str): # If it's a path
                 if not os.path.exists(image_path_or_pil_img):
                      print(f"Error: Image path does not exist: {image_path_or_pil_img}")
                      return None
                 img = Image.open(image_path_or_pil_img)
            elif isinstance(image_path_or_pil_img, Image.Image): # If it's a PIL image
                 img = image_path_or_pil_img
            else:
                 print("Error: Invalid input for get_features. Expecting path or PIL Image.")
                 return None

            img_array = self._preprocess_pil_image(img)
            if img_array is None: return None

            features = self.model.predict(img_array, verbose=0)
            return features.flatten()
        except Exception as e:
            print(f"Error extracting features from image: {e}")
            return None

    def compare_features(self, features1, features2):
        """Compare two feature vectors using cosine similarity."""
        if features1 is None or features2 is None:
            print("Cannot compare None features.")
            return 0.0 # Return lowest similarity if features missing
        # Ensure vectors are not zero vectors before calculating cosine similarity
        if np.all(features1 == 0) or np.all(features2 == 0):
            # print("Warning: One or both feature vectors are all zeros.")
            return 0.0 # Or handle as appropriate (e.g., 1.0 if both are zero?)
        try:
             # Cosine distance is 1 - similarity
             similarity = 1 - cosine(features1, features2)
             # Handle potential NaN result if vectors somehow are invalid after checks
             return similarity if not np.isnan(similarity) else 0.0
        except Exception as e:
             print(f"Error calculating cosine similarity: {e}")
             return 0.0

def run_vgg16_comparison(reference_image_path, comparison_image_paths):
    """
    Performs VGG16 comparison between a reference image and vertically
    flipped versions of comparison images.

    Args:
        reference_image_path (str): Path to the reference image.
        comparison_image_paths (list): List of paths to comparison images.

    Returns:
        list: Sorted list of tuples (comparison_path, similarity_score).
              Returns empty list on major errors (e.g., model load failure).
    """
    if Image is None or VGG16 is None:
        print("Cannot run advanced comparison due to missing libraries (Pillow or TensorFlow).")
        return []

    comparator = ImageComparator()
    if comparator.model is None:
        print("Failed to initialize VGG16 model. Aborting advanced comparison.")
        return []

    print("Extracting features for reference image...")
    ref_features = comparator.get_features(reference_image_path)
    if ref_features is None:
        print(f"Failed to get features for reference image: {reference_image_path}. Aborting.")
        return []
    print("Reference features extracted.")

    similarities = []
    total_files = len(comparison_image_paths)
    print(f"Comparing with {total_files} images (using vertical flip)...")

    for i, comp_path in enumerate(comparison_image_paths):
        # Provide progress update
        if (i + 1) % 10 == 0 or i == total_files - 1:
             print(f"Processing comparison image {i+1}/{total_files}...")
        try:
            comp_img = Image.open(comp_path)
            # Flip comparison image vertically IN MEMORY
            flipped_comp_img = comp_img.transpose(Image.FLIP_TOP_BOTTOM)
            # Get features for the flipped image
            comp_features_flipped = comparator.get_features(flipped_comp_img)

            if comp_features_flipped is not None:
                similarity = comparator.compare_features(ref_features, comp_features_flipped)
                similarities.append((comp_path, similarity))
            else:
                 print(f"Could not get features for (flipped) {comp_path}")
                 similarities.append((comp_path, 0.0)) # Assign 0 similarity on feature error

        except FileNotFoundError:
            print(f"Comparison image not found: {comp_path}. Skipping.")
            similarities.append((comp_path, 0.0))
        except Exception as e:
            print(f"Error processing comparison image {comp_path}: {e}")
            similarities.append((comp_path, 0.0)) # Assign 0 similarity on other errors

    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    print("Advanced comparison finished.")
    return similarities