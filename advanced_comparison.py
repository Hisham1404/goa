# advanced_comparison.py
import numpy as np
import tensorflow as tf
try:
    from tensorflow.keras.applications import EfficientNetV2S
    from tensorflow.keras.applications.efficientnet_v2 import preprocess_input
    from tensorflow.keras.models import Model
    from tensorflow.keras.utils import img_to_array
except ImportError:
    print("ERROR: TensorFlow/Keras not found. Please install it: pip install tensorflow")
    # You might exit here or disable the advanced feature
    EfficientNetV2S = None # Set to None to allow checking later

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not found. Please install it: pip install Pillow")
    Image = None # Set to None

from scipy.spatial.distance import cosine
import os

class ImageComparator:
    """Enhanced Image Comparator using EfficientNetV2-S (replaces VGG16)"""
    
    def __init__(self):
        """
        Initialize with EfficientNetV2-S model.
        Uses the 'S' (small) variant with 21M parameters for optimal speed/accuracy balance.
        """
        self.model_size = 'S'
        self.input_size = 384  # EfficientNetV2-S optimal input size
        self.model = self._load_model()
    
    def _load_model(self):
        """Load EfficientNetV2 model"""
        if EfficientNetV2S is None: # Check if import failed
            print("EfficientNetV2 model cannot be loaded due to missing TensorFlow/Keras.")
            return None
        try:
            print(f"Loading EfficientNetV2-{self.model_size} model (this may take a moment)...")
            
            base_model = EfficientNetV2S(
                weights='imagenet',
                include_top=False,
                pooling='avg',
                input_shape=(self.input_size, self.input_size, 3)
            )
            
            print(f"EfficientNetV2-{self.model_size} model loaded successfully.")
            print(f"  - Parameters: ~21M (vs 138M for VGG16)")
            print(f"  - Input size: {self.input_size}x{self.input_size}")
            return base_model
            
        except Exception as e:
            print(f"Error loading EfficientNetV2 model: {e}")
            print("Ensure you have an internet connection for the first download.")
            return None
    
    def _preprocess_pil_image(self, pil_img):
        """Preprocess PIL image for EfficientNetV2"""
        if self.model is None:
            return None
        try:
            img = pil_img.convert('RGB').resize((self.input_size, self.input_size))
            img_array = img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            return preprocess_input(img_array)
        except Exception as e:
            print(f"Error during image preprocessing: {e}")
            return None
    
    def get_features(self, image_path_or_pil_img):
        """Extract features from an image (path or PIL object)"""
        if self.model is None:
            return None
        try:
            if isinstance(image_path_or_pil_img, str):
                if not os.path.exists(image_path_or_pil_img):
                    print(f"Error: Image path does not exist: {image_path_or_pil_img}")
                    return None
                img = Image.open(image_path_or_pil_img)
            elif isinstance(image_path_or_pil_img, Image.Image):
                img = image_path_or_pil_img
            else:
                print("Error: Invalid input for get_features. Expecting path or PIL Image.")
                return None

            img_array = self._preprocess_pil_image(img)
            if img_array is None:
                return None

            features = self.model.predict(img_array, verbose=0)
            return features.flatten()
        except Exception as e:
            print(f"Error extracting features from image: {e}")
            return None
    
    def compare_features(self, features1, features2):
        """Compare two feature vectors using cosine similarity."""
        if features1 is None or features2 is None:
            print("Cannot compare None features.")
            return 0.0
        if np.all(features1 == 0) or np.all(features2 == 0):
            return 0.0
        try:
            similarity = 1 - cosine(features1, features2)
            return similarity if not np.isnan(similarity) else 0.0
        except Exception as e:
            print(f"Error calculating cosine similarity: {e}")
            return 0.0

def run_advanced_comparison(reference_image_path, comparison_image_paths):
    """
    Performs EfficientNetV2 comparison between a reference image and 
    vertically flipped versions of comparison images.

    Args:
        reference_image_path (str): Path to the reference image.
        comparison_image_paths (list): List of paths to comparison images.

    Returns:
        list: Sorted list of tuples (comparison_path, similarity_score).
              Returns empty list on major errors (e.g., model load failure).
    """
    if Image is None or EfficientNetV2S is None:
        print("Cannot run advanced comparison due to missing libraries (Pillow or TensorFlow).")
        return []

    comparator = ImageComparator()
    if comparator.model is None:
        print("Failed to initialize EfficientNetV2 model. Aborting advanced comparison.")
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

# Backward compatibility alias
run_vgg16_comparison = run_advanced_comparison