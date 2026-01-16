import cv2
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# Import the functions from main_improved
import sys
sys.path.append('.')
from main_improved import preprocess_image, detect_features_multi, match_features_adaptive, verify_homography_quality

def find_plot_quick(plot_img_cv, map_img_cv):
    """Quick plot detection using only SIFT with enhancement, no visualizations."""
    print("\n--- Quick Plot Detection (SIFT) ---")
    
    # Preprocess with contrast enhancement
    plot_gray = preprocess_image(plot_img_cv, enhance_contrast=True)
    map_gray = preprocess_image(map_img_cv, enhance_contrast=True)
    
    # Detect features using SIFT
    print("Detecting features with SIFT...")
    kp1, des1, _ = detect_features_multi(plot_gray, method='sift')
    kp2, des2, _ = detect_features_multi(map_gray, method='sift')
    
    if des1 is None or des2 is None:
        print("Error: Could not detect features")
        return False, 0.0, map_img_cv
    
    print(f"Features: {len(kp1)} in plot, {len(kp2)} in map")
    
    # Match features
    good_matches = match_features_adaptive(des1, des2, 'sift')
    print(f"Good matches: {len(good_matches)}")
    
    if len(good_matches) < 10:
        print("Not enough matches")
        return False, 0.0, map_img_cv
    
    # Extract points and compute homography
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    
    if M is None or mask is None:
        print("Homography failed")
        return False, 0.0, map_img_cv
    
    # Verify homography
    if not verify_homography_quality(M, plot_gray.shape, map_gray.shape):
        print("Homography quality check failed")
        return False, 0.0, map_img_cv
    
    num_inliers = np.sum(mask)
    print(f"Inliers: {num_inliers}")
    
    if num_inliers < 8:
        print("Not enough inliers")
        return False, 0.0, map_img_cv
    
    # Calculate confidence
    confidence = min(100.0, (num_inliers / 15.0) * 100.0)
    
    # Draw result
    map_result = map_img_cv.copy()
    h, w = plot_gray.shape[:2]
    pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
    
    try:
        dst_corners = cv2.perspectiveTransform(pts, M)
        cv2.polylines(map_result, [np.int32(dst_corners)], True, (0, 255, 0), 3, cv2.LINE_AA)
        cv2.putText(map_result, f"SIFT - Confidence: {confidence:.1f}%", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    except:
        pass
    
    return True, confidence, map_result

if __name__ == "__main__":
    plot_img = cv2.imread("../antorieum/plots/1.png")
    map_img = cv2.imread("../antorieum/map/1-1.tif")
    
    if plot_img is None or map_img is None:
        print("Error loading images")
    else:
        found, confidence, result = find_plot_quick(plot_img, map_img)
        
        if found:
            print(f"\n✓ Plot Found! Confidence: {confidence:.2f}%")
            cv2.imwrite("quick_result.png", result)
            print("Result saved to quick_result.png")
            
            # Show result
            cv2.namedWindow("Result", cv2.WINDOW_NORMAL)
            cv2.imshow("Result", result)
            print("Press any key to close...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("\n✗ Plot Not Found") 