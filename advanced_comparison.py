# advanced_comparison.py
"""
Advanced Image Comparison Module using DINOv2

This module uses Meta's DINOv2 (self-supervised vision transformer) for 
state-of-the-art image feature extraction and similarity comparison.

DINOv2 provides significantly better visual features than VGG16, especially
for fine-grained image matching like land parcel comparison.
"""

import numpy as np
import os
from scipy.spatial.distance import cosine

# Try to import PyTorch and DINOv2
TORCH_AVAILABLE = False
DINOV2_MODEL = None

try:
    import torch
    import torch.nn.functional as F
    from torchvision import transforms
    TORCH_AVAILABLE = True
    print("PyTorch found. DINOv2 will be available.")
except ImportError:
    print("WARNING: PyTorch not found. Install with: pip install torch torchvision")
    print("Falling back to TensorFlow VGG16 if available.")

# Fallback to VGG16 if PyTorch is not available
VGG16_AVAILABLE = False
if not TORCH_AVAILABLE:
    try:
        import tensorflow as tf
        from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
        from tensorflow.keras.models import Model
        from tensorflow.keras.utils import img_to_array
        VGG16_AVAILABLE = True
        print("TensorFlow VGG16 available as fallback.")
    except ImportError:
        print("WARNING: Neither PyTorch nor TensorFlow found. Advanced comparison disabled.")

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not found. Please install it: pip install Pillow")
    Image = None


class DINOv2Comparator:
    """
    Compares images using Meta's DINOv2 features.
    
    DINOv2 is a self-supervised vision transformer that produces
    rich visual features without requiring task-specific training.
    """
    
    def __init__(self, model_name='dinov2_vits14'):
        """
        Initialize the DINOv2 comparator.
        
        Args:
            model_name: One of 'dinov2_vits14', 'dinov2_vitb14', 'dinov2_vitl14', 'dinov2_vitg14'
                       - vits14: Small (21M params) - Fastest
                       - vitb14: Base (86M params) - Good balance
                       - vitl14: Large (300M params) - Better accuracy
                       - vitg14: Giant (1.1B params) - Best accuracy, slowest
        """
        self.model_name = model_name
        self.model = None
        self.device = None
        self.transform = None
        self._load_model()
    
    def _load_model(self):
        """Load the DINOv2 model from torch hub."""
        if not TORCH_AVAILABLE:
            print("PyTorch not available. DINOv2 cannot be loaded.")
            return
        
        try:
            print(f"Loading DINOv2 model ({self.model_name})... This may take a moment on first run.")
            
            # Determine device (GPU if available, else CPU)
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            print(f"Using device: {self.device}")
            
            # Load model from Facebook Research's torch hub
            self.model = torch.hub.load('facebookresearch/dinov2', self.model_name)
            self.model = self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            # DINOv2 expects images normalized with ImageNet stats
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            
            print(f"DINOv2 model loaded successfully!")
            
        except Exception as e:
            print(f"Error loading DINOv2 model: {e}")
            print("Ensure you have an internet connection for the first download.")
            self.model = None
    
    def _preprocess_image(self, pil_img):
        """Preprocess PIL image for DINOv2."""
        if self.model is None or self.transform is None:
            return None
        try:
            # Ensure image is RGB
            img = pil_img.convert('RGB')
            # Apply transforms and add batch dimension
            img_tensor = self.transform(img).unsqueeze(0)
            return img_tensor.to(self.device)
        except Exception as e:
            print(f"Error during image preprocessing: {e}")
            return None
    
    def get_features(self, image_path_or_pil_img):
        """
        Extract features from an image using DINOv2.
        
        Args:
            image_path_or_pil_img: Either a file path string or a PIL Image object.
        
        Returns:
            numpy array of features, or None on error.
        """
        if self.model is None:
            return None
        
        try:
            # Handle both path and PIL image inputs
            if isinstance(image_path_or_pil_img, str):
                if not os.path.exists(image_path_or_pil_img):
                    print(f"Error: Image path does not exist: {image_path_or_pil_img}")
                    return None
                img = Image.open(image_path_or_pil_img)
            elif isinstance(image_path_or_pil_img, Image.Image):
                img = image_path_or_pil_img
            else:
                print("Error: Invalid input. Expecting path or PIL Image.")
                return None
            
            # Preprocess
            img_tensor = self._preprocess_image(img)
            if img_tensor is None:
                return None
            
            # Extract features (no gradient computation needed)
            with torch.no_grad():
                features = self.model(img_tensor)
            
            # Convert to numpy and flatten
            return features.cpu().numpy().flatten()
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
    
    def compare_features(self, features1, features2):
        """
        Compare two feature vectors using cosine similarity.
        
        Args:
            features1: First feature vector (numpy array)
            features2: Second feature vector (numpy array)
        
        Returns:
            Similarity score between 0 and 1 (higher = more similar)
        """
        if features1 is None or features2 is None:
            print("Cannot compare None features.")
            return 0.0
        
        # Check for zero vectors
        if np.all(features1 == 0) or np.all(features2 == 0):
            return 0.0
        
        try:
            # Cosine similarity = 1 - cosine distance
            similarity = 1 - cosine(features1, features2)
            return similarity if not np.isnan(similarity) else 0.0
        except Exception as e:
            print(f"Error calculating cosine similarity: {e}")
            return 0.0


class VGG16ComparatorFallback:
    """Fallback comparator using VGG16 when PyTorch is not available."""
    
    def __init__(self):
        self.model = self._load_model()
    
    def _load_model(self):
        if not VGG16_AVAILABLE:
            return None
        try:
            print("Loading VGG16 model (fallback)...")
            base_model = VGG16(weights='imagenet', include_top=False, 
                              input_shape=(224, 224, 3), pooling='avg')
            model = Model(inputs=base_model.input, outputs=base_model.output)
            print("VGG16 model loaded successfully.")
            return model
        except Exception as e:
            print(f"Error loading VGG16: {e}")
            return None
    
    def get_features(self, image_path_or_pil_img):
        if self.model is None:
            return None
        try:
            if isinstance(image_path_or_pil_img, str):
                if not os.path.exists(image_path_or_pil_img):
                    return None
                img = Image.open(image_path_or_pil_img)
            elif isinstance(image_path_or_pil_img, Image.Image):
                img = image_path_or_pil_img
            else:
                return None
            
            img = img.convert('RGB').resize((224, 224))
            img_array = img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            
            features = self.model.predict(img_array, verbose=0)
            return features.flatten()
        except Exception as e:
            print(f"Error extracting VGG16 features: {e}")
            return None
    
    def compare_features(self, features1, features2):
        if features1 is None or features2 is None:
            return 0.0
        if np.all(features1 == 0) or np.all(features2 == 0):
            return 0.0
        try:
            similarity = 1 - cosine(features1, features2)
            return similarity if not np.isnan(similarity) else 0.0
        except:
            return 0.0


# Factory function to get the best available comparator
def get_image_comparator():
    """
    Returns the best available image comparator.
    
    Prefers DINOv2 (if PyTorch available), falls back to VGG16.
    """
    if TORCH_AVAILABLE:
        comparator = DINOv2Comparator(model_name='dinov2_vits14')  # Use small model for speed
        if comparator.model is not None:
            return comparator
        print("DINOv2 failed to load, trying VGG16 fallback...")
    
    if VGG16_AVAILABLE:
        return VGG16ComparatorFallback()
    
    print("ERROR: No image comparison model available!")
    return None


# Keep the old function name for backwards compatibility
def run_vgg16_comparison(reference_image_path, comparison_image_paths):
    """
    Performs image comparison between a reference image and comparison images.
    
    Uses DINOv2 if available, falls back to VGG16.
    
    Args:
        reference_image_path (str): Path to the reference image.
        comparison_image_paths (list): List of paths to comparison images.

    Returns:
        list: Sorted list of tuples (comparison_path, similarity_score).
              Returns empty list on major errors.
    """
    if Image is None:
        print("Cannot run comparison: Pillow not available.")
        return []
    
    # Get the best available comparator
    comparator = get_image_comparator()
    if comparator is None:
        print("No comparison model available. Aborting.")
        return []
    
    # Identify which model we're using
    model_name = "DINOv2" if isinstance(comparator, DINOv2Comparator) else "VGG16"
    print(f"Using {model_name} for image comparison.")
    
    # Extract reference features
    print("Extracting features for reference image...")
    ref_features = comparator.get_features(reference_image_path)
    if ref_features is None:
        print(f"Failed to get features for reference image: {reference_image_path}. Aborting.")
        return []
    print(f"Reference features extracted (dimension: {len(ref_features)}).")
    
    # Compare with all images
    similarities = []
    total_files = len(comparison_image_paths)
    print(f"Comparing with {total_files} images (using vertical flip)...")
    
    for i, comp_path in enumerate(comparison_image_paths):
        # Progress update every 10 images
        if (i + 1) % 10 == 0 or i == total_files - 1:
            print(f"Processing comparison image {i+1}/{total_files}...")
        
        try:
            comp_img = Image.open(comp_path)
            # Flip comparison image vertically (as in original implementation)
            flipped_comp_img = comp_img.transpose(Image.FLIP_TOP_BOTTOM)
            
            # Get features for the flipped image
            comp_features = comparator.get_features(flipped_comp_img)
            
            if comp_features is not None:
                similarity = comparator.compare_features(ref_features, comp_features)
                similarities.append((comp_path, similarity))
            else:
                print(f"Could not get features for: {comp_path}")
                similarities.append((comp_path, 0.0))
                
        except FileNotFoundError:
            print(f"Comparison image not found: {comp_path}. Skipping.")
            similarities.append((comp_path, 0.0))
        except Exception as e:
            print(f"Error processing {comp_path}: {e}")
            similarities.append((comp_path, 0.0))
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    print(f"Advanced comparison finished using {model_name}.")
    return similarities


# Alias for the new function name
run_dinov2_comparison = run_vgg16_comparison
run_advanced_comparison = run_vgg16_comparison


if __name__ == "__main__":
    # Quick test
    print("\n=== Advanced Comparison Module Test ===")
    print(f"PyTorch available: {TORCH_AVAILABLE}")
    print(f"VGG16 fallback available: {VGG16_AVAILABLE}")
    
    comparator = get_image_comparator()
    if comparator:
        print(f"Active comparator: {type(comparator).__name__}")
    else:
        print("No comparator available!")