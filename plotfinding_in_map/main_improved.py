import cv2
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# --- Configuration Parameters ---
VISUALIZE = False        # Set to True to see intermediate visualizations for EACH strategy
VISUALIZE_FINAL = True   # Set to True to see only the final best result
SAVE_RESULT_IMAGE = True # Set to True to save the final highlighted map

# Feature detector parameters
SIFT_N_FEATURES = 0      # 0 means no limit for SIFT
ORB_N_FEATURES = 5000    # Increased from 3000
AKAZE_THRESHOLD = 0.001  # Lower means more features

# Matching parameters
LOWE_RATIO_STRICT = 0.6  # Stricter ratio for initial filtering
LOWE_RATIO_RELAXED = 0.75 # More relaxed for fallback
MIN_MATCH_COUNT = 10     # Lowered from 15 for initial attempt
MIN_INLIER_COUNT = 8     # Lowered from 15 for initial validation
RANSAC_REPROJ_THRESHOLD = 5.0 # Slightly relaxed from 3.0
CONFIDENCE_NORM_FACTOR = 15.0

# Preprocessing parameters
CLAHE_CLIP_LIMIT = 2.0
CLAHE_GRID_SIZE = (8, 8)

def preprocess_image(img, enhance_contrast=True):
    """Preprocess image to improve feature detection."""
    # Convert to grayscale if needed
    if len(img.shape) > 2:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    
    if enhance_contrast:
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_GRID_SIZE)
        gray = clahe.apply(gray)
    
    return gray

def detect_features_multi(img_gray, method='auto'):
    """
    Detect features using multiple methods.
    
    Args:
        img_gray: Grayscale image
        method: 'sift', 'orb', 'akaze', or 'auto' (tries all)
    
    Returns:
        tuple: (keypoints, descriptors, method_used)
    """
    methods_to_try = []
    
    if method == 'auto':
        methods_to_try = ['sift', 'orb', 'akaze']
    else:
        methods_to_try = [method]
    
    best_kp = None
    best_des = None
    best_method = None
    max_features = 0
    
    for m in methods_to_try:
        try:
            if m == 'sift':
                detector = cv2.SIFT_create(nfeatures=SIFT_N_FEATURES)
            elif m == 'orb':
                detector = cv2.ORB_create(nfeatures=ORB_N_FEATURES)
            elif m == 'akaze':
                detector = cv2.AKAZE_create(threshold=AKAZE_THRESHOLD)
            else:
                continue
            
            kp, des = detector.detectAndCompute(img_gray, None)
            
            if des is not None and len(kp) > max_features:
                max_features = len(kp)
                best_kp = kp
                best_des = des
                best_method = m
                
        except Exception as e:
            print(f"Warning: {m.upper()} failed: {e}")
            continue
    
    return best_kp, best_des, best_method

def match_features_adaptive(des1, des2, method):
    """Match features with adaptive parameters based on the method used."""
    if des1 is None or des2 is None:
        return []
    
    # Create appropriate matcher
    if method in ['sift', 'surf']:
        bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    else:  # ORB, AKAZE use Hamming
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    
    try:
        # Try strict ratio first
        matches = bf.knnMatch(des1, des2, k=2)
        good_matches = []
        
        for pair in matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < LOWE_RATIO_STRICT * n.distance:
                    good_matches.append(m)
        
        # If not enough matches, try relaxed ratio
        if len(good_matches) < MIN_MATCH_COUNT:
            print(f"Only {len(good_matches)} matches with strict ratio. Trying relaxed ratio...")
            good_matches = []
            for pair in matches:
                if len(pair) == 2:
                    m, n = pair
                    if m.distance < LOWE_RATIO_RELAXED * n.distance:
                        good_matches.append(m)
        
        return good_matches
        
    except Exception as e:
        print(f"Error in matching: {e}")
        return []

def verify_homography_quality(M, plot_shape, map_shape):
    """Verify if the computed homography makes sense."""
    if M is None:
        return False
    
    h, w = plot_shape[:2]
    # Check if homography preserves reasonable scale
    pts = np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]]).reshape(-1, 1, 2)
    
    try:
        dst_pts = cv2.perspectiveTransform(pts, M)
        
        # Calculate area of transformed rectangle
        area = cv2.contourArea(dst_pts)
        original_area = w * h
        
        # Check if scale is reasonable (between 0.1x and 10x)
        scale_ratio = area / original_area
        if scale_ratio < 0.1 or scale_ratio > 10:
            print(f"Homography scale ratio {scale_ratio:.2f} is unreasonable")
            return False
        
        # Check if transformed points are within map bounds
        map_h, map_w = map_shape[:2]
        for pt in dst_pts:
            x, y = pt[0]
            if x < -map_w*0.1 or x > map_w*1.1 or y < -map_h*0.1 or y > map_h*1.1:
                print("Transformed points are too far outside map bounds")
                return False
        
        return True
        
    except:
        return False

def find_plot_enhanced(plot_img_cv, map_img_cv, method='auto', enhance_contrast=True):
    """
    Enhanced plot finding with multiple strategies.
    
    Args:
        plot_img_cv: OpenCV image of the target plot (BGR)
        map_img_cv: OpenCV image of the map to search within (BGR)
        method: Feature detection method ('sift', 'orb', 'akaze', or 'auto')
        enhance_contrast: Whether to apply contrast enhancement
    
    Returns:
        tuple: (found_status, confidence_score, highlighted_map_image, details_dict)
    """
    print("\n--- Starting Enhanced Plot Detection ---")
    map_img_color_copy = map_img_cv.copy()
    details = {
        'method_used': None,
        'num_features_plot': 0,
        'num_features_map': 0,
        'num_good_matches': 0,
        'num_inliers': 0
    }
    
    # Preprocess images
    plot_gray = preprocess_image(plot_img_cv, enhance_contrast)
    map_gray = preprocess_image(map_img_cv, enhance_contrast)
    
    # Detect features
    print(f"Detecting features using method: {method}")
    kp1, des1, method1 = detect_features_multi(plot_gray, method)
    kp2, des2, method2 = detect_features_multi(map_gray, method)
    
    if des1 is None or des2 is None or len(kp1) == 0 or len(kp2) == 0:
        print("Error: Could not detect features in one or both images")
        return False, 0.0, map_img_color_copy, details
    
    # Ensure same method was used for both
    if method1 != method2:
        print(f"Warning: Different methods used - {method1} vs {method2}")
        return False, 0.0, map_img_color_copy, details
    
    details['method_used'] = method1
    details['num_features_plot'] = len(kp1)
    details['num_features_map'] = len(kp2)
    
    print(f"Detected {len(kp1)} features in plot, {len(kp2)} in map using {method1.upper()}")
    
    # Visualize keypoints if enabled
    if VISUALIZE:
        img_kp1 = cv2.drawKeypoints(plot_img_cv, kp1, None, color=(0, 255, 0), flags=0)
        img_kp2 = cv2.drawKeypoints(map_img_cv, kp2, None, color=(0, 255, 0), flags=0)
        cv2.namedWindow("Plot Keypoints", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Map Keypoints", cv2.WINDOW_NORMAL)
        cv2.imshow("Plot Keypoints", img_kp1)
        cv2.imshow("Map Keypoints", img_kp2)
        print("Showing keypoints. Press any key to continue...")
        cv2.waitKey(0)
    
    # Match features
    good_matches = match_features_adaptive(des1, des2, method1)
    details['num_good_matches'] = len(good_matches)
    print(f"Found {len(good_matches)} good matches")
    
    # Visualize good matches
    if VISUALIZE and good_matches:
        img_matches = cv2.drawMatches(plot_img_cv, kp1, map_img_cv, kp2, good_matches, None,
                                      flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        cv2.namedWindow("Good Matches", cv2.WINDOW_NORMAL)
        cv2.imshow("Good Matches", img_matches)
        print("Showing good matches. Press any key...")
        cv2.waitKey(0)
    
    # Check if we have enough matches
    if len(good_matches) < MIN_MATCH_COUNT:
        print(f"Not enough matches ({len(good_matches)} < {MIN_MATCH_COUNT})")
        return False, 0.0, map_img_color_copy, details
    
    # Extract matched points
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    
    # Compute homography
    print("Computing homography...")
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, RANSAC_REPROJ_THRESHOLD)
    
    if M is None or mask is None:
        print("Homography computation failed")
        return False, 0.0, map_img_color_copy, details
    
    # Verify homography quality
    if not verify_homography_quality(M, plot_gray.shape, map_gray.shape):
        print("Homography quality check failed")
        return False, 0.0, map_img_color_copy, details
    
    num_inliers = np.sum(mask)
    details['num_inliers'] = num_inliers
    print(f"Found {num_inliers} inliers")
    
    # Visualize inliers
    if VISUALIZE and num_inliers > 0:
        matchesMask = mask.ravel().tolist()
        draw_params = dict(matchColor=(0, 255, 0),
                          singlePointColor=None,
                          matchesMask=matchesMask,
                          flags=2)
        img_inliers = cv2.drawMatches(plot_img_cv, kp1, map_img_cv, kp2, good_matches, None, **draw_params)
        cv2.namedWindow("Inlier Matches", cv2.WINDOW_NORMAL)
        cv2.imshow("Inlier Matches", img_inliers)
        print("Showing inlier matches. Press any key...")
        cv2.waitKey(0)
    
    # Check if we have enough inliers
    if num_inliers < MIN_INLIER_COUNT:
        print(f"Not enough inliers ({num_inliers} < {MIN_INLIER_COUNT})")
        return False, 0.0, map_img_color_copy, details
    
    # Calculate confidence
    confidence = min(100.0, (num_inliers / CONFIDENCE_NORM_FACTOR) * 100.0)
    print(f"Match confirmed with confidence: {confidence:.2f}%")
    
    # Draw bounding box
    h, w = plot_gray.shape[:2]
    pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
    
    try:
        dst_corners = cv2.perspectiveTransform(pts, M)
        map_highlighted = cv2.polylines(map_img_color_copy, [np.int32(dst_corners)], 
                                       True, (0, 255, 0), 3, cv2.LINE_AA)
        
        # Add text with details
        cv2.putText(map_highlighted, f"Method: {method1.upper()}, Confidence: {confidence:.1f}%", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
    except Exception as e:
        print(f"Error drawing bounding box: {e}")
        map_highlighted = map_img_color_copy
    
    return True, confidence, map_highlighted, details

def try_multiple_strategies(plot_img, map_img):
    """Try multiple detection strategies and return the best result."""
    best_result = None
    best_confidence = 0
    best_details = None
    
    # Strategies to try
    strategies = [
        ('sift', True),   # SIFT with contrast enhancement
        ('sift', False),  # SIFT without enhancement
        ('orb', True),    # ORB with enhancement
        ('akaze', True),  # AKAZE with enhancement
    ]
    
    for method, enhance in strategies:
        print(f"\n--- Trying {method.upper()} with enhance_contrast={enhance} ---")
        
        try:
            found, confidence, result_img, details = find_plot_enhanced(
                plot_img, map_img, method=method, enhance_contrast=enhance
            )
            
            if found and confidence > best_confidence:
                best_confidence = confidence
                best_result = result_img
                best_details = details
                print(f"New best result: {method.upper()} with confidence {confidence:.2f}%")
                
        except Exception as e:
            print(f"Strategy {method} failed: {e}")
            continue
    
    if best_result is not None:
        return True, best_confidence, best_result, best_details
    else:
        return False, 0, map_img, {}

# --- Main Execution Block ---
if __name__ == "__main__":
    plot_image_path = "../antorieum/plots/24.png"
    map_image_path = "../antorieum/map/1-1.tif"
    
    print(f"Loading plot image: {plot_image_path}")
    plot_img = cv2.imread(plot_image_path)
    print(f"Loading map image: {map_image_path}")
    map_img = cv2.imread(map_image_path)
    
    if plot_img is None:
        print(f"Fatal Error: Could not load plot image at {plot_image_path}")
    elif map_img is None:
        print(f"Fatal Error: Could not load map image at {map_image_path}")
    else:
        print("\nImages loaded successfully.")
        
        # Try multiple strategies
        found_status, confidence, result_map, details = try_multiple_strategies(plot_img, map_img)
        
        print("\n--- Final Result ---")
        if found_status:
            print(f"Plot Found!")
            print(f"Best method: {details.get('method_used', 'Unknown')}")
            print(f"Confidence: {confidence:.2f}%")
            print(f"Features: {details.get('num_features_plot', 0)} (plot), {details.get('num_features_map', 0)} (map)")
            print(f"Matches: {details.get('num_good_matches', 0)} good, {details.get('num_inliers', 0)} inliers")
            
            # Display final result
            final_window_name = "Final Result - Plot Found"
            cv2.namedWindow(final_window_name, cv2.WINDOW_NORMAL)
            cv2.imshow(final_window_name, result_map)
            
            # Save the result
            if SAVE_RESULT_IMAGE:
                save_path = "final_result_enhanced.png"
                try:
                    cv2.imwrite(save_path, result_map)
                    print(f"Result image saved to: {save_path}")
                except Exception as e:
                    print(f"Error saving result image: {e}")
            
            print("Press any key in the result window to exit.")
            cv2.waitKey(0)
        else:
            print("Plot Not Found with any method.")
            # Show original map
            cv2.namedWindow("Original Map", cv2.WINDOW_NORMAL)
            cv2.imshow("Original Map", map_img)
            print("Showing original map. Press any key to exit.")
            cv2.waitKey(0)
    
    cv2.destroyAllWindows() 