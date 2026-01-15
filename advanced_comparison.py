# advanced_comparison.py
import numpy as np
import tensorflow as tf
try:
    from tensorflow.keras.applications.efficientnet_v2 import EfficientNetV2S, preprocess_input
    from tensorflow.keras.models import Model
    from tensorflow.keras.utils import img_to_array
except ImportError:
    print("ERROR: TensorFlow/Keras not found. Please install it: pip install tensorflow")
    EfficientNetV2S = None
    preprocess_input = None

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not found. Please install it: pip install Pillow")
    Image = None

from scipy.spatial.distance import cosine
import os

class ImageComparator:
    """Enhanced Image Comparator using EfficientNetV2-S (replaces VGG16)"""
    
    def __init__(self):
        """Initialize with EfficientNetV2-S"""
        self.input_size = 384
        self.model = self._load_model()
    
    def _load_model(self):
        """Load EfficientNetV2-S model"""
        if EfficientNetV2S is None:
            print("EfficientNetV2 model cannot be loaded due to missing TensorFlow/Keras.")
            return None
        try:
            print("Loading EfficientNetV2-S model (this may take a moment)...")
            
            base_model = EfficientNetV2S(
                weights='imagenet',
                include_top=False,
                pooling='avg',
                input_shape=(self.input_size, self.input_size, 3)
            )
            
            print("EfficientNetV2-S model loaded successfully.")
            return base_model
            
        except Exception as e:
            print(f"Error loading EfficientNetV2 model: {e}")
            print("Ensure you have an internet connection for the first download.")
            return None
    
    def _preprocess_pil_image(self, pil_img):
        """Preprocess PIL image for EfficientNetV2"""
        if self.model is None or preprocess_input is None:
            return None
        try:
            img = pil_img.convert('RGB').resize((self.input_size, self.input_size))
            img_array = img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            return img_array
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
    Performs advanced deep learning-based comparison between a reference image 
    and vertically flipped versions of comparison images.
    
    Currently uses EfficientNetV2-S for feature extraction.
    
    Args:
        reference_image_path (str): Path to the reference image.
        comparison_image_paths (list): List of paths to comparison images.
    
    Returns:
        list: Sorted list of tuples (comparison_path, similarity_score).
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
        if (i + 1) % 10 == 0 or i == total_files - 1:
            print(f"Processing comparison image {i+1}/{total_files}...")
        try:
            comp_img = Image.open(comp_path)
            flipped_comp_img = comp_img.transpose(Image.FLIP_TOP_BOTTOM)
            comp_features_flipped = comparator.get_features(flipped_comp_img)

            if comp_features_flipped is not None:
                similarity = comparator.compare_features(ref_features, comp_features_flipped)
                similarities.append((comp_path, similarity))
            else:
                print(f"Could not get features for (flipped) {comp_path}")
                similarities.append((comp_path, 0.0))

        except FileNotFoundError:
            print(f"Comparison image not found: {comp_path}. Skipping.")
            similarities.append((comp_path, 0.0))
        except Exception as e:
            print(f"Error processing comparison image {comp_path}: {e}")
            similarities.append((comp_path, 0.0))

    similarities.sort(key=lambda x: x[1], reverse=True)
    print("Advanced comparison finished.")
    return similarities

# Backward compatibility alias
run_vgg16_comparison = run_advanced_comparison