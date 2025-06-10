import cv2
import numpy as np
from pyzbar.pyzbar import decode
from pyzbar import pyzbar
import logging
import warnings
from PIL import Image, ImageEnhance
import os
from typing import List, Tuple, Optional, Dict, Any
from collections import Counter # Moved import here for clarity

# Suppress warnings
warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)

class UniversalBarcodeDetector:
    def __init__(self, target_symbols: List = None):
        """
        Initialize the detector with optional target barcode symbols.
        
        Args:
            target_symbols: List of pyzbar.ZBarSymbol types to detect.
                            If None, detects all supported types.
                            Example: [pyzbar.ZBarSymbol.CODE39, pyzbar.ZBarSymbol.CODE128]
        """
        self.failed_images = []
        self.confidence_scores = []
        self.target_symbols = target_symbols  # None means detect all types
        # Removed explicit preprocessing_methods list here as they will be called in order
        # in comprehensive_decode for better control.
    
    def basic_barcode_validation(self, barcode_data: str, barcode_type: str) -> bool:
        """
        Basic validation that works for any barcode type.
        Can be overridden for specific validation needs.
        """
        try:
            # Basic checks
            if not barcode_data:
                return False
            
            # Check for reasonable length (adjust as needed)
            if len(barcode_data) < 1 or len(barcode_data) > 200:
                return False
            
            # Check for printable characters (basic ASCII validation)
            if not all(32 <= ord(c) <= 126 or c in '\t\n\r' for c in barcode_data):
                return False
            
            return True
        except:
            return False
    
    def calculate_confidence_score(self, image, barcode_result) -> float:
        """Calculate confidence score based on image quality and barcode properties"""
        try:
            # Image quality metrics
            # Ensure image is grayscale for Laplacian and std
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 
            elif len(image.shape) == 2:
                gray = image
            else: # Handle unexpected image shapes
                return 0.1 # Very low confidence if image format is unusual
            
            # Sharpness (Laplacian variance) - ensure variance is not zero to avoid division by zero if it were used
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Contrast (standard deviation of pixel intensities)
            contrast = gray.std()
            
            # Brightness consistency (how close average brightness is to mid-gray)
            brightness = np.mean(gray)
            brightness_score = 1.0 - abs(brightness - 128) / 128 # 128 is mid-range for 0-255
            
            # Barcode-specific metrics
            try:
                barcode_data = barcode_result.data.decode('utf-8', errors='ignore')
                barcode_length = len(barcode_data)
            except:
                barcode_length = len(str(barcode_result.data)) # Fallback for non-decodable data
            
            # Barcode quality metrics based on its bounding box
            rect = barcode_result.rect
            # Normalize area relative to a reasonable size (e.g., 100x100 pixels)
            area_score = min((rect.width * rect.height) / 10000.0, 1.0)  
            
            # Normalize scores - adjust divisors based on expected ranges for your images
            sharpness_score = min(sharpness / 500.0, 1.0) # Assume 500 is a good sharpness
            contrast_score = min(contrast / 100.0, 1.0)   # Assume 100 is good contrast std dev
            length_score = min(barcode_length / 20.0, 1.0) # Assume 20 chars is good length
            
            # Combined confidence score - adjust weights as desired
            confidence = (sharpness_score * 0.25 + 
                          contrast_score * 0.25 + 
                          brightness_score * 0.2 + 
                          length_score * 0.15 +
                          area_score * 0.15)
            
            return confidence
        except Exception as e:
            # print(f"Error calculating confidence: {e}") # For debugging purposes
            return 0.1  # Default very low confidence if calculation fails
    
    def decode_barcodes(self, image):
        """Decode barcodes using specified symbol types or all types"""
        try:
            # Pyzbar requires a grayscale image for best results, even if it handles RGB internally
            if len(image.shape) == 3:
                image_for_decode = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                image_for_decode = image

            if self.target_symbols:
                decoded_objects = pyzbar.decode(image_for_decode, symbols=self.target_symbols)
            else:
                decoded_objects = pyzbar.decode(image_for_decode)
            
            valid_results = []
            for obj in decoded_objects:
                try:
                    try:
                        barcode_data = obj.data.decode('utf-8')
                    except UnicodeDecodeError:
                        barcode_data = obj.data.decode('latin-1')
                    
                    barcode_type = obj.type
                    
                    if self.basic_barcode_validation(barcode_data, barcode_type):
                        confidence = self.calculate_confidence_score(image, obj) # Use original 'image' for confidence if possible
                        valid_results.append({
                            'object': obj,
                            'confidence': confidence,
                            'data': barcode_data,
                            'type': barcode_type
                        })
                except Exception as e:
                    # print(f"Error processing a decoded object: {e}") # Enable for debugging specific decode object issues
                    continue
            
            if valid_results:
                valid_results.sort(key=lambda x: x['confidence'], reverse=True)
                return [valid_results[0]['object']]
            
            return []
        except Exception as e:
            # print(f"Error in decode_barcodes: {e}") # Enable for general decode errors
            return []
    
    def basic_preprocessing(self, image):
        """Basic grayscale conversion"""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
    
    def adaptive_threshold_preprocessing(self, image):
        """Adaptive thresholding for varying lighting conditions"""
        gray = self.basic_preprocessing(image)
        # Block size should be odd and greater than 1. C is a constant subtracted from the mean.
        return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
    
    def otsu_threshold_preprocessing(self, image):
        """Otsu's thresholding"""
        gray = self.basic_preprocessing(image)
        # Otsu's automatically finds the optimal threshold
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    
    def gaussian_blur_preprocessing(self, image):
        """Gaussian blur to reduce noise"""
        gray = self.basic_preprocessing(image)
        # Smaller kernel for minimal blurring, primarily noise reduction
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        # Thresholding after blur to make barcode lines distinct
        _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
        return thresh
    
    def morphological_preprocessing(self, image):
        """Morphological operations to clean up image"""
        gray = self.basic_preprocessing(image)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Define kernels for closing (filling small holes) and opening (removing small objects)
        kernel = np.ones((2, 2), np.uint8) # Small kernel
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
        return processed
    
    def contrast_enhancement_preprocessing(self, image):
        """Enhance contrast using CLAHE"""
        gray = self.basic_preprocessing(image)
        # CLAHE (Contrast Limited Adaptive Histogram Equalization) is good for local contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        # Applying a simple binary threshold after CLAHE
        _, thresh = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
        return thresh
    
    def edge_enhancement_preprocessing(self, image):
        """Edge enhancement preprocessing (Unsharp Masking)"""
        gray = self.basic_preprocessing(image)
        # Unsharp masking: original_image * (1 + amount) + blurred_image * (-amount)
        blurred = cv2.GaussianBlur(gray, (0, 0), 3) # Gaussian blur with auto kernel size
        unsharp = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0) # 1.5 is amount for original, -0.5 for blurred
        _, thresh = cv2.threshold(unsharp, 127, 255, cv2.THRESH_BINARY)
        return thresh
    
    def rotation_correction_preprocessing(self, image):
        """Attempt to correct skewed barcodes by trying small rotations"""
        gray = self.basic_preprocessing(image)
        
        best_result_image = None
        best_decoded_objects = []
        best_overall_confidence = 0
        
        # Try a wider range of angles, but still in small increments
        # -5 to 5 degrees might be more robust
        for angle in [-5, -3, -1, 0, 1, 3, 5]: # More refined angles or wider range
            if angle == 0:
                test_image = gray
            else:
                height, width = gray.shape
                center = (width // 2, height // 2)
                # getRotationMatrix2D takes angle in degrees
                rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                # warpAffine needs the output size (width, height)
                test_image = cv2.warpAffine(gray, rotation_matrix, (width, height), 
                                            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            
            decoded_objs = self.decode_barcodes(test_image)
            if decoded_objs:
                # Assuming decode_barcodes returns a list containing the single best object
                current_confidence = self.calculate_confidence_score(test_image, decoded_objs[0])
                if current_confidence > best_overall_confidence:
                    best_overall_confidence = current_confidence
                    best_decoded_objects = decoded_objs
                    best_result_image = test_image # Store the processed image that yielded best result
        
        # Return the decoded objects from the best rotation, not the image itself
        # The main comprehensive_decode will then work with these objects
        return best_decoded_objects # Return the actual pyzbar objects

    def resize_image(self, image, scale_factors=[1.0, 1.5, 2.0, 0.5]):
        """Try different image sizes"""
        results = []
        best_decoded_objects = []
        best_confidence = 0
        
        # Ensure image is BGR if it has 3 channels for consistent decoding, or grayscale if 1.
        # decode_barcodes handles its own grayscale conversion if needed, but it's good to be consistent.
        
        for scale in scale_factors:
            height, width = image.shape[:2]
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Avoid resizing to zero dimensions
            if new_width == 0 or new_height == 0:
                continue

            resized = cv2.resize(image, (new_width, new_height), 
                                 interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
            
            decoded_objs = self.decode_barcodes(resized)
            if decoded_objs:
                confidence = self.calculate_confidence_score(resized, decoded_objs[0])
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_decoded_objects = decoded_objs
        
        return best_decoded_objects # Return the actual pyzbar objects
    
    def detect_with_opencv(self, image):
        """Alternative detection using OpenCV's barcode detector if available"""
        try:
            if hasattr(cv2, 'barcode') and cv2.barcode.BarcodeDetector is not None:
                detector = cv2.barcode.BarcodeDetector()
                # OpenCV's detectAndDecode returns a tuple: success flag, decoded_info, decoded_type, points
                retval, decoded_info, decoded_type, points = detector.detectAndDecode(image)
                
                if retval: # retval is True if any barcode is detected
                    results = []
                    # iterate over found barcodes, assuming parallel arrays
                    for i in range(len(decoded_info)):
                        info = decoded_info[i]
                        barcode_type_str = decoded_type[i] # This is a string like "QR_CODE" or "EAN_13"
                        
                        if info:  # Only add non-empty results
                            class MockResult:
                                """A mock object to make OpenCV results compatible with pyzbar's structure."""
                                def __init__(self, data, type_name, points):
                                    self.data = data.encode('utf-8') # OpenCV decodes to string, pyzbar expects bytes
                                    # Convert OpenCV type string to pyzbar.ZBarSymbol enum if possible, else keep string
                                    # This requires a mapping, which might be complex. For simplicity, just store string.
                                    self.type = barcode_type_str 
                                    
                                    # Create a mock rect from points
                                    if points is not None and len(points[i]) == 4:
                                        # points are usually [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                                        # For rect, we need x, y, width, height
                                        pts = points[i].astype(int)
                                        x_coords = pts[:, 0]
                                        y_coords = pts[:, 1]
                                        x = np.min(x_coords)
                                        y = np.min(y_coords)
                                        width = np.max(x_coords) - x
                                        height = np.max(y_coords) - y
                                        self.rect = type('Rect', (), {'left': x, 'top': y, 'width': width, 'height': height})()
                                    else:
                                        # Fallback to a generic mock rect if points are not useful
                                        self.rect = type('Rect', (), {'left':0, 'top':0, 'width': 100, 'height': 50})()
                                    self.polygon = points[i].tolist() if points is not None else []
                                
                            results.append(MockResult(info, barcode_type_str, points))
                    return results
        except AttributeError:
            # cv2.barcode might not be available in all OpenCV builds
            # print("OpenCV barcode detector not available. Skipping.") 
            pass
        except Exception as e:
            # print(f"Error in OpenCV barcode detection: {e}")
            pass
        
        return []
    
    def comprehensive_decode(self, image_path: str) -> List:
        """Comprehensive barcode detection with multiple strategies"""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Could not load image: {image_path}")
            return []
        
        all_candidates = []  # Store all found barcodes with confidence scores
        
        # Helper function to add a candidate and check for early exit
        def add_candidate_and_check_early_exit(results_list, current_image, decoded_objects, method_name, confidence_threshold=0.6):
            if decoded_objects: # Check if decoding was successful
                # Assuming decoded_objects is a list of pyzbar objects and we take the first
                confidence = self.calculate_confidence_score(current_image, decoded_objects[0])
                barcode_type = decoded_objects[0].type
                results_list.append({
                    'result': decoded_objects, # Store the actual pyzbar objects
                    'confidence': confidence,
                    'method': method_name,
                    'type': barcode_type
                })
                # Early return if confidence is high enough
                if confidence >= confidence_threshold: # Use >= for threshold
                    #print(f"Early exit: Found high confidence {barcode_type} barcode with confidence: {confidence:.3f}, method: {method_name}")
                    return decoded_objects
            return None # Indicate no early exit

        # --- REORDERED STRATEGIES ---

        # 1. Strategy: Original image with different sizes (most efficient, often accurate for good images)
        #print("Strategy 1/10: Original image with different sizes...")
        result = self.resize_image(image, scale_factors=[1.0, 1.5, 0.75]) # Try 1.0 first, then slightly up/down
        early_exit_result = add_candidate_and_check_early_exit(all_candidates, image, result, 'resize_original', confidence_threshold=0.8) # Higher threshold for direct match
        if early_exit_result: return early_exit_result

        # 2. Strategy: Adaptive Thresholding (highly effective for varying lighting)
        #print("Strategy 2/10: Adaptive Thresholding...")
        try:
            processed_image = self.adaptive_threshold_preprocessing(image)
            result = self.decode_barcodes(processed_image)
            early_exit_result = add_candidate_and_check_early_exit(all_candidates, processed_image, result, 'adaptive_threshold')
            if early_exit_result: return early_exit_result
        except Exception as e: pass

        # 3. Strategy: Contrast Enhancement (CLAHE - crucial for low contrast)
        #print("Strategy 3/10: Contrast Enhancement (CLAHE)...")
        try:
            processed_image = self.contrast_enhancement_preprocessing(image)
            result = self.decode_barcodes(processed_image)
            early_exit_result = add_candidate_and_check_early_exit(all_candidates, processed_image, result, 'contrast_enhancement')
            if early_exit_result: return early_exit_result
        except Exception as e: pass

        # 4. Strategy: Otsu's Thresholding (good general thresholding)
        #print("Strategy 4/10: Otsu's Thresholding...")
        try:
            processed_image = self.otsu_threshold_preprocessing(image)
            result = self.decode_barcodes(processed_image)
            early_exit_result = add_candidate_and_check_early_exit(all_candidates, processed_image, result, 'otsu_threshold')
            if early_exit_result: return early_exit_result
        except Exception as e: pass

        # 5. Strategy: Gaussian Blur + Threshold (for noise reduction)
        #print("Strategy 5/10: Gaussian Blur + Threshold...")
        try:
            processed_image = self.gaussian_blur_preprocessing(image)
            result = self.decode_barcodes(processed_image)
            early_exit_result = add_candidate_and_check_early_exit(all_candidates, processed_image, result, 'gaussian_blur')
            if early_exit_result: return early_exit_result
        except Exception as e: pass

        # 6. Strategy: Morphological Operations (for cleaning up barcode lines)
        #print("Strategy 6/10: Morphological Operations...")
        try:
            processed_image = self.morphological_preprocessing(image)
            result = self.decode_barcodes(processed_image)
            early_exit_result = add_candidate_and_check_early_exit(all_candidates, processed_image, result, 'morphological')
            if early_exit_result: return early_exit_result
        except Exception as e: pass

        # 7. Strategy: Edge Enhancement (Unsharp Masking - for slightly blurry images)
        #print("Strategy 7/10: Edge Enhancement...")
        try:
            processed_image = self.edge_enhancement_preprocessing(image)
            result = self.decode_barcodes(processed_image)
            early_exit_result = add_candidate_and_check_early_exit(all_candidates, processed_image, result, 'edge_enhancement')
            if early_exit_result: return early_exit_result
        except Exception as e: pass

        # 8. Strategy: PIL Enhancements (Brightness and Contrast - alternative enhancement path)
        #print("Strategy 8/10: PIL Enhancements (Brightness/Contrast)...")
        try:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            enhancer_brightness = ImageEnhance.Brightness(pil_image)
            for brightness_factor in [0.7, 1.3, 1.5]: # Reduced iterations for speed
                enhanced = enhancer_brightness.enhance(brightness_factor)
                enhanced_cv = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
                result = self.decode_barcodes(enhanced_cv)
                early_exit_result = add_candidate_and_check_early_exit(all_candidates, enhanced_cv, result, f'pil_brightness_{brightness_factor}')
                if early_exit_result: return early_exit_result
            
            enhancer_contrast = ImageEnhance.Contrast(pil_image)
            for contrast_factor in [0.7, 1.3, 1.5]: # Reduced iterations for speed
                enhanced = enhancer_contrast.enhance(contrast_factor)
                enhanced_cv = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
                result = self.decode_barcodes(enhanced_cv)
                early_exit_result = add_candidate_and_check_early_exit(all_candidates, enhanced_cv, result, f'pil_contrast_{contrast_factor}')
                if early_exit_result: return early_exit_result
                    
        except Exception as e:
            pass

        # 9. Strategy: Rotation Correction (expensive, but necessary for skewed images)
        # Note: rotation_correction_preprocessing already returns the decoded objects
        #print("Strategy 9/10: Rotation Correction...")
        try:
            # rotation_correction_preprocessing directly performs decode and returns best pyzbar objects
            result = self.rotation_correction_preprocessing(image) 
            if result: # If rotation correction found something
                # We need to re-calculate confidence on the original image for consistency, or the rotated best image
                # Let's calculate on the image that yielded the result within rotation_correction
                # For simplicity, if rotation_correction returns a result, we treat it as a strong candidate.
                # The confidence calculation inside rotation_correction is good.
                # Re-add to candidates and check early exit.
                # Note: `rotation_correction_preprocessing` returns decoded objects, not an image.
                # So we pass a dummy image for `calculate_confidence_score` if the internal image isn't accessible.
                # A better design would be for `rotation_correction_preprocessing` to return (best_image, best_decoded_objects)
                # For now, let's assume the confidence calculated inside is sufficient, or pass the original image
                # as a placeholder for confidence calculation if the rotated image isn't easy to get back.
                
                # A better way to integrate rotation_correction:
                # Modify rotation_correction_preprocessing to return the (decoded_objects, optimal_rotated_image)
                # For this current structure, we need to adapt:
                
                # A more robust integration might involve a separate logic path for rotation
                # which keeps track of the optimal rotated image.
                # For now, we'll use a placeholder image for confidence calculation if the original is passed.
                
                # Assuming result is decoded_objects, need an image to calculate confidence
                # This is a bit of a hack, ideal would be to get the rotated image back.
                # Or, calculate confidence inside rotation_correction and return it with the result.
                
                # Let's refine `rotation_correction_preprocessing` to return `(decoded_objects, confidence)`
                # or just the best decoded_objects and calculate confidence here.
                
                # Current `rotation_correction_preprocessing` returns `best_decoded_objects` directly.
                # So we can just pass the original image to `add_candidate_and_check_early_exit`
                # (since `calculate_confidence_score` takes an image and a barcode_result)
                early_exit_result = add_candidate_and_check_early_exit(all_candidates, image, result, 'rotation_correction')
                if early_exit_result: return early_exit_result

        except Exception as e: pass

        # 10. Strategy: Region-based Detection (last resort for difficult images)
        #print("Strategy 10/10: Region-based Detection...")
        height, width = image.shape[:2]
        regions = [
            (0, 0, width, height//2),  # Top half
            (0, height//2, width, height),  # Bottom half
            (0, 0, width//2, height),  # Left half
            (width//2, 0, width, height),  # Right half
            (width//4, height//4, 3*width//4, 3*height//4),  # Center region
        ]
        
        for i, (x, y, x2, y2) in enumerate(regions):
            try:
                roi = image[y:y2, x:x2]
                if roi.size > 0 and roi.shape[0] > 0 and roi.shape[1] > 0: # Ensure ROI is valid
                    result = self.decode_barcodes(roi)
                    early_exit_result = add_candidate_and_check_early_exit(all_candidates, roi, result, f'region_{i}')
                    if early_exit_result: return early_exit_result
            except Exception as e:
                pass
        
        # Strategy (Fallback): OpenCV detector (as a last resort if pyzbar strategies fail)
        # This is outside the main "ordered strategies" because it's an entirely different library.
        # It's a good final attempt if nothing else works.
        #print("Fallback Strategy: OpenCV detector...")
        opencv_result = self.detect_with_opencv(image)
        if opencv_result:
            # For OpenCV results, assign a reasonable default confidence.
            # You might want to fine-tune this value.
            confidence_opencv = 0.65 
            all_candidates.append({
                'result': opencv_result,
                'confidence': confidence_opencv,
                'method': 'opencv_detector',
                'type': opencv_result[0].type if opencv_result else "UNKNOWN"
            })
            # Even if it's a fallback, if it found something, prioritize it if it's the only one
            # or if its confidence is deemed acceptable.
            # We don't use an early exit here as it's meant to be a final check before selecting best from all_candidates.
        
        # Select the best candidate based on confidence score if no early exit occurred
        if all_candidates:
            all_candidates.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Additional validation: check for consistency among top candidates
            # Consider candidates with confidence > 0.7 for consistency check
            top_candidates = [c for c in all_candidates if c['confidence'] > 0.7]
            
            if top_candidates:
                top_data = []
                # Consider top 3 (or fewer if less available) high-confidence results for consistency
                for c in top_candidates[:3]:
                    try:
                        data = c['result'][0].data.decode('utf-8', errors='ignore')
                        top_data.append(data)
                    except:
                        top_data.append(str(c['result'][0].data))
                
                data_counts = Counter(top_data)
                most_common_data, count = data_counts.most_common(1)[0]
                
                # If majority (at least 2, or single high-confidence result) agree
                if count >= 2 or len(top_candidates) == 1:
                    best_candidate = None
                    for c in top_candidates:
                        try:
                            candidate_data = c['result'][0].data.decode('utf-8', errors='ignore')
                        except:
                            candidate_data = str(c['result'][0].data)
                        
                        if candidate_data == most_common_data:
                            best_candidate = c
                            break
                    
                    if best_candidate:
                        #print(f"Final Selection: {best_candidate['type']} barcode with confidence: {best_candidate['confidence']:.3f}, method: {best_candidate['method']}")
                        return best_candidate['result']
            
            # If no high-confidence results or no strong agreement, return the single best available
            #print(f"Final Selection (Best Available): {all_candidates[0]['type']} result with confidence: {all_candidates[0]['confidence']:.3f}, method: {all_candidates[0]['method']}")
            return all_candidates[0]['result']
        
        # If all strategies fail
        self.failed_images.append(image_path)
        print(f"✗ No barcodes found for {os.path.basename(image_path)} after all strategies.")
        return []
    
    def batch_process(self, image_folder: str, image_extensions: List[str] = None) -> Dict[str, Any]:
        """Process all images in a folder"""
        if image_extensions is None:
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        
        results = {}
        total_images = 0
        successful_detections = 0
        validation_failures = 0
        barcode_types_count = {}
        
        for filename in os.listdir(image_folder):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                total_images += 1
                image_path = os.path.join(image_folder, filename)
                
                print(f"Processing {filename}...")
                decoded_objects = self.comprehensive_decode(image_path)
                
                if decoded_objects:
                    successful_detections += 1
                    
                    try:
                        barcode_data = decoded_objects[0].data.decode('utf-8', errors='ignore')
                    except:
                        barcode_data = str(decoded_objects[0].data)
                    
                    barcode_type = decoded_objects[0].type
                    
                    is_valid = self.basic_barcode_validation(barcode_data, barcode_type)
                    
                    if is_valid:
                        results[filename] = [{
                            'data': barcode_data,
                            'type': barcode_type
                        }]
                        # print(f"✓ Found valid {barcode_type}: {barcode_data}") # Commented to reduce excessive output
                        
                        barcode_types_count[barcode_type] = barcode_types_count.get(barcode_type, 0) + 1
                    else:
                        validation_failures += 1
                        results[filename] = [{
                            'data': f"INVALID_{barcode_type}: {barcode_data}",
                            'type': barcode_type
                        }]
                        # print(f"⚠ Found invalid {barcode_type}: {barcode_data}") # Commented to reduce excessive output
                else:
                    results[filename] = []
                    # print(f"✗ No barcodes found") # Commented to reduce excessive output
        
        print(f"\n--- Batch Processing Summary ---")
        print(f"Total images processed: {total_images}")
        print(f"Successful detections: {successful_detections}")
        print(f"Valid barcodes: {successful_detections - validation_failures}")
        
        if barcode_types_count:
            print("Barcode types successfully found:")
            for barcode_type, count in sorted(barcode_types_count.items()):
                print(f"  - {barcode_type}: {count}")
        
        print(f"Invalid barcodes (detected but failed validation): {validation_failures}")
        print(f"Overall Success rate: {successful_detections/total_images*100:.1f}%")
        print(f"Valid barcode detection rate: {(successful_detections - validation_failures)/total_images*100:.1f}%")
        print(f"Images with no barcode found: {len(self.failed_images)}")
        
        if self.failed_images:
            print("\nImages where no barcode was found:")
            for img in self.failed_images:
                print(f"  - {os.path.basename(img)}")
        
        return results

# # Usage examples
# if __name__ == "__main__":
#     # Example 1: Detect all barcode types (universal)
#     detector = UniversalBarcodeDetector()
    
#     # Example 2: Detect only specific barcode types
#     # detector = UniversalBarcodeDetector(target_symbols=[
#     #     pyzbar.ZBarSymbol.CODE39,
#     #     pyzbar.ZBarSymbol.QRCODE # Example for QR code
#     # ])
    
#     #For single image
#     #Make sure to replace with an actual image path
#     single_image_path = "D:\\OMRScanner\\input\\xyz\\0599.jpg" 
#     print(f"\n--- Processing single image: {os.path.basename(single_image_path)} ---")
#     result = detector.comprehensive_decode(single_image_path)
#     if result:
#         print(f"Decoded: {result[0].data.decode('utf-8', errors='ignore')} (Type: {result[0].type})")
#     else:
#         print("No barcode found for this image.")
    
#     # For batch processing
#     # Create a dummy folder with some images for testing
#     # Example: Create a folder named 'sample_barcode_images' in the same directory as your script
#     # and put some barcode images inside.
#     # You can download sample barcode images online or create some.
#     image_folder_path = "sample_barcode_images" 
#     if not os.path.exists(image_folder_path):
#         print(f"\nPlease create a folder named '{image_folder_path}' and place some barcode images inside for batch processing.")
#         print("Example: `mkdir sample_barcode_images` and copy images into it.")
#     else:
#         print(f"\n--- Starting Batch Processing for folder: {image_folder_path} ---")
#         batch_results = detector.batch_process(image_folder_path)
#         print("\nDetailed Batch Processing Results:")
#         for filename, barcodes in batch_results.items():
#             if barcodes:
#                 print(f"  {filename}: {barcodes[0]['data']} (Type: {barcodes[0]['type']})")
#             else:
#                 print(f"  {filename}: No barcode found")
    
#     # Save results to file
#     # import json
#     # output_json_path = "barcode_batch_results.json"
#     # with open(output_json_path, "w") as f:
#     #     json.dump(batch_results, f, indent=2)
#     # print(f"\nBatch processing results saved to: {output_json_path}")



#Previous Implementation 29-05-2025

# import cv2
# import numpy as np
# from pyzbar.pyzbar import decode
# from pyzbar import pyzbar
# import logging
# import warnings
# from PIL import Image, ImageEnhance
# import os
# from typing import List, Tuple, Optional, Dict, Any
# import re

# # Suppress warnings
# warnings.filterwarnings("ignore")
# logging.getLogger().setLevel(logging.ERROR)

# class UniversalBarcodeDetector:
#     def __init__(self, target_symbols: List = None):
#         """
#         Initialize the detector with optional target barcode symbols.
        
#         Args:
#             target_symbols: List of pyzbar.ZBarSymbol types to detect.
#                           If None, detects all supported types.
#                           Example: [pyzbar.ZBarSymbol.CODE39, pyzbar.ZBarSymbol.CODE128]
#         """
#         self.failed_images = []
#         self.confidence_scores = []
#         self.target_symbols = target_symbols  # None means detect all types
#         self.preprocessing_methods = [
#             self.basic_preprocessing,
#             self.adaptive_threshold_preprocessing,
#             self.otsu_threshold_preprocessing,
#             self.gaussian_blur_preprocessing,
#             self.morphological_preprocessing,
#             self.contrast_enhancement_preprocessing,
#             self.edge_enhancement_preprocessing,
#             self.rotation_correction_preprocessing
#         ]
    
#     def basic_barcode_validation(self, barcode_data: str, barcode_type: str) -> bool:
#         """
#         Basic validation that works for any barcode type.
#         Can be overridden for specific validation needs.
#         """
#         try:
#             # Basic checks
#             if not barcode_data:
#                 return False
            
#             # Check for reasonable length (adjust as needed)
#             if len(barcode_data) < 1 or len(barcode_data) > 200:
#                 return False
            
#             # Check for printable characters (basic ASCII validation)
#             if not all(32 <= ord(c) <= 126 or c in '\t\n\r' for c in barcode_data):
#                 return False
            
#             return True
#         except:
#             return False
    
#     def calculate_confidence_score(self, image, barcode_result) -> float:
#         """Calculate confidence score based on image quality and barcode properties"""
#         try:
#             # Image quality metrics
#             gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
#             # Sharpness (Laplacian variance)
#             sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
#             # Contrast
#             contrast = gray.std()
            
#             # Brightness consistency
#             brightness = np.mean(gray)
#             brightness_score = 1.0 - abs(brightness - 128) / 128
            
#             # Barcode-specific metrics
#             try:
#                 barcode_data = barcode_result.data.decode('utf-8', errors='ignore')
#                 barcode_length = len(barcode_data)
#             except:
#                 barcode_length = len(str(barcode_result.data))
            
#             # Barcode quality metrics
#             rect = barcode_result.rect
#             area_score = min((rect.width * rect.height) / 10000, 1.0)  # Normalize area
            
#             # Normalize scores
#             sharpness_score = min(sharpness / 500, 1.0)
#             contrast_score = min(contrast / 100, 1.0)
#             length_score = min(barcode_length / 20, 1.0)
            
#             # Combined confidence score
#             confidence = (sharpness_score * 0.25 + 
#                          contrast_score * 0.25 + 
#                          brightness_score * 0.2 + 
#                          length_score * 0.15 +
#                          area_score * 0.15)
            
#             return confidence
#         except:
#             return 0.5  # Default medium confidence
    
#     def decode_barcodes(self, image):
#         """Decode barcodes using specified symbol types or all types"""
#         try:
#             if self.target_symbols:
#                 # Decode only specified barcode types
#                 decoded_objects = pyzbar.decode(image, symbols=self.target_symbols)
#             else:
#                 # Decode all supported barcode types
#                 decoded_objects = pyzbar.decode(image)
            
#             # Filter and validate results
#             valid_results = []
#             for obj in decoded_objects:
#                 try:
#                     # Try to decode as UTF-8, fallback to latin-1 for binary data
#                     try:
#                         barcode_data = obj.data.decode('utf-8')
#                     except UnicodeDecodeError:
#                         barcode_data = obj.data.decode('latin-1')
                    
#                     barcode_type = obj.type
                    
#                     # Apply basic validation
#                     if self.basic_barcode_validation(barcode_data, barcode_type):
#                         confidence = self.calculate_confidence_score(image, obj)
#                         valid_results.append({
#                             'object': obj,
#                             'confidence': confidence,
#                             'data': barcode_data,
#                             'type': barcode_type
#                         })
#                 except Exception as e:
#                     continue
            
#             # Sort by confidence and return the best result
#             if valid_results:
#                 valid_results.sort(key=lambda x: x['confidence'], reverse=True)
#                 return [valid_results[0]['object']]
            
#             return []
#         except:
#             return []
    
#     def basic_preprocessing(self, image):
#         """Basic grayscale conversion"""
#         if len(image.shape) == 3:
#             return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         return image
    
#     def adaptive_threshold_preprocessing(self, image):
#         """Adaptive thresholding for varying lighting conditions"""
#         gray = self.basic_preprocessing(image)
#         return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
#                                    cv2.THRESH_BINARY, 11, 2)
    
#     def otsu_threshold_preprocessing(self, image):
#         """Otsu's thresholding"""
#         gray = self.basic_preprocessing(image)
#         _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#         return thresh
    
#     def gaussian_blur_preprocessing(self, image):
#         """Gaussian blur to reduce noise"""
#         gray = self.basic_preprocessing(image)
#         blurred = cv2.GaussianBlur(gray, (3, 3), 0)
#         _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
#         return thresh
    
#     def morphological_preprocessing(self, image):
#         """Morphological operations to clean up image"""
#         gray = self.basic_preprocessing(image)
#         _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
#         # Morphological operations
#         kernel = np.ones((2, 2), np.uint8)
#         processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
#         processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
#         return processed
    
#     def contrast_enhancement_preprocessing(self, image):
#         """Enhance contrast using CLAHE"""
#         gray = self.basic_preprocessing(image)
#         clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
#         enhanced = clahe.apply(gray)
#         _, thresh = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
#         return thresh
    
#     def edge_enhancement_preprocessing(self, image):
#         """Edge enhancement preprocessing"""
#         gray = self.basic_preprocessing(image)
#         # Apply unsharp masking
#         blurred = cv2.GaussianBlur(gray, (9, 9), 10.0)
#         unsharp = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
#         _, thresh = cv2.threshold(unsharp, 127, 255, cv2.THRESH_BINARY)
#         return thresh
    
#     def rotation_correction_preprocessing(self, image):
#         """Attempt to correct skewed barcodes"""
#         gray = self.basic_preprocessing(image)
        
#         # Try small rotations
#         best_result = None
#         best_confidence = 0
        
#         for angle in [-3, -2, -1, 0, 1, 2, 3]:
#             if angle == 0:
#                 test_image = gray
#             else:
#                 height, width = gray.shape
#                 center = (width // 2, height // 2)
#                 rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
#                 test_image = cv2.warpAffine(gray, rotation_matrix, (width, height))
            
#             result = self.decode_barcodes(test_image)
#             if result:
#                 confidence = self.calculate_confidence_score(test_image, result[0])
#                 if confidence > best_confidence:
#                     best_confidence = confidence
#                     best_result = test_image
        
#         return best_result if best_result is not None else gray
    
#     def resize_image(self, image, scale_factors=[1.0, 1.5, 2.0, 0.5]):
#         """Try different image sizes"""
#         results = []
#         best_result = None
#         best_confidence = 0
        
#         for scale in scale_factors:
#             height, width = image.shape[:2]
#             new_width = int(width * scale)
#             new_height = int(height * scale)
            
#             resized = cv2.resize(image, (new_width, new_height), 
#                                interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
            
#             result = self.decode_barcodes(resized)
#             if result:
#                 confidence = self.calculate_confidence_score(resized, result[0])
#                 if confidence > best_confidence:
#                     best_confidence = confidence
#                     best_result = result
        
#         return best_result if best_result else []
    
#     def detect_with_opencv(self, image):
#         """Alternative detection using OpenCV's barcode detector if available"""
#         try:
#             if hasattr(cv2, 'barcode'):
#                 detector = cv2.barcode.BarcodeDetector()
#                 retval, decoded_info, decoded_type, points = detector.detectAndDecode(image)
                
#                 if retval:
#                     # Convert to pyzbar-like format
#                     results = []
#                     for info, barcode_type in zip(decoded_info, decoded_type):
#                         if info:  # Only add non-empty results
#                             # Create a mock object similar to pyzbar's output
#                             class MockResult:
#                                 def __init__(self, data, type_name):
#                                     self.data = data.encode() if isinstance(data, str) else data
#                                     self.type = type_name
#                                     self.rect = type('Rect', (), {'width': 100, 'height': 50})()  # Mock rect
                            
#                             results.append(MockResult(info, barcode_type))
#                     return results
#         except Exception as e:
#             pass
        
#         return []
    
#     def comprehensive_decode(self, image_path: str) -> List:
#         """Comprehensive barcode detection with multiple strategies"""
#         # Load image
#         image = cv2.imread(image_path)
#         if image is None:
#             print(f"Could not load image: {image_path}")
#             return []
        
#         all_candidates = []  # Store all found barcodes with confidence scores
        
#         # Strategy 1: Try original image with different sizes
#         result = self.resize_image(image)
#         if result:
#             confidence = self.calculate_confidence_score(image, result[0])
#             barcode_type = result[0].type
#             all_candidates.append({
#                 'result': result,
#                 'confidence': confidence,
#                 'method': 'resize_original',
#                 'type': barcode_type
#             })
#             if confidence > 0.6:
#                 return result
        
#         # Strategy 2: Try different preprocessing methods
#         for i, preprocessing_method in enumerate(self.preprocessing_methods):
#             try:
#                 processed_image = preprocessing_method(image)
                
#                 # Try the processed image at different sizes
#                 result = self.resize_image(processed_image)
#                 if result:
#                     confidence = self.calculate_confidence_score(processed_image, result[0])
#                     barcode_type = result[0].type
#                     all_candidates.append({
#                         'result': result,
#                         'confidence': confidence,
#                         'method': f'preprocessing_{i}',
#                         'type': barcode_type
#                     })
#                     if confidence > 0.6:
#                         return result
                    
#             except Exception as e:
#                 continue
        
#         # Strategy 3: Try with PIL enhancements
#         try:
#             pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
#             # Enhance brightness
#             enhancer = ImageEnhance.Brightness(pil_image)
#             for brightness in [0.7, 1.3, 1.5]:
#                 enhanced = enhancer.enhance(brightness)
#                 enhanced_cv = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
#                 result = self.decode_barcodes(enhanced_cv)
#                 if result:
#                     confidence = self.calculate_confidence_score(enhanced_cv, result[0])
#                     barcode_type = result[0].type
#                     all_candidates.append({
#                         'result': result,
#                         'confidence': confidence,
#                         'method': f'brightness_{brightness}',
#                         'type': barcode_type
#                     })
#                     if confidence > 0.6:
#                          return result
            
#             # Enhance contrast
#             enhancer = ImageEnhance.Contrast(pil_image)
#             for contrast in [0.7, 1.3, 1.5, 2.0]:
#                 enhanced = enhancer.enhance(contrast)
#                 enhanced_cv = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
#                 result = self.decode_barcodes(enhanced_cv)
#                 if result:
#                     confidence = self.calculate_confidence_score(enhanced_cv, result[0])
#                     barcode_type = result[0].type
#                     all_candidates.append({
#                         'result': result,
#                         'confidence': confidence,
#                         'method': f'contrast_{contrast}',
#                         'type': barcode_type
#                     })
#                     if confidence > 0.6:
#                         return result
                    
#         except Exception as e:
#             pass
        
#         # Strategy 4: Region-based detection (crop different parts)
#         height, width = image.shape[:2]
#         regions = [
#             (0, 0, width, height//2),  # Top half
#             (0, height//2, width, height),  # Bottom half
#             (0, 0, width//2, height),  # Left half
#             (width//2, 0, width, height),  # Right half
#             (width//4, height//4, 3*width//4, 3*height//4),  # Center region
#         ]
        
#         for i, (x, y, x2, y2) in enumerate(regions):
#             try:
#                 roi = image[y:y2, x:x2]
#                 if roi.size > 0:
#                     result = self.decode_barcodes(roi)
#                     if result:
#                         confidence = self.calculate_confidence_score(roi, result[0])
#                         barcode_type = result[0].type
#                         all_candidates.append({
#                             'result': result,
#                             'confidence': confidence,
#                             'method': f'region_{i}',
#                             'type': barcode_type
#                         })
#                         if confidence > 0.6:
#                             return result
#             except:
#                 continue
        
#         # Strategy 5: Try OpenCV detector as fallback
#         opencv_result = self.detect_with_opencv(image)
#         if opencv_result:
#             all_candidates.append({
#                 'result': opencv_result,
#                 'confidence': 0.6,  # Default confidence for OpenCV results
#                 'method': 'opencv_detector',
#                 'type': opencv_result[0].type
#             })
#             if confidence > 0.6:
#                 return opencv_result 
        
#         # Select the best candidate based on confidence score
#         if all_candidates:
#             # Sort by confidence score (highest first)
#             all_candidates.sort(key=lambda x: x['confidence'], reverse=True)
            
#             # Additional validation: check for consistency among top candidates
#             top_candidates = [c for c in all_candidates if c['confidence'] > 0.7]
            
#             if top_candidates:
#                 # Check if top candidates agree on the barcode data
#                 top_data = []
#                 for c in top_candidates[:3]:
#                     try:
#                         data = c['result'][0].data.decode('utf-8', errors='ignore')
#                         top_data.append(data)
#                     except:
#                         top_data.append(str(c['result'][0].data))
                
#                 # If majority agree, return the highest confidence result
#                 from collections import Counter
#                 data_counts = Counter(top_data)
#                 most_common_data, count = data_counts.most_common(1)[0]
                
#                 if count >= 2 or len(top_candidates) == 1:  # Majority agreement or single high-confidence result
#                     best_candidate = None
#                     for c in top_candidates:
#                         try:
#                             candidate_data = c['result'][0].data.decode('utf-8', errors='ignore')
#                         except:
#                             candidate_data = str(c['result'][0].data)
                        
#                         if candidate_data == most_common_data:
#                             best_candidate = c
#                             break
                    
#                     if best_candidate:
#                         print(f"Selected {best_candidate['type']} barcode with confidence: {best_candidate['confidence']:.3f}, method: {best_candidate['method']}")
#                         return best_candidate['result']
            
#             # If no high-confidence results, return the best available
#             print(f"Low confidence {all_candidates[0]['type']} result: {all_candidates[0]['confidence']:.3f}, method: {all_candidates[0]['method']}")
#             return all_candidates[0]['result']
        
#         # If all strategies fail, add to failed list
#         self.failed_images.append(image_path)
#         return []
    
#     def batch_process(self, image_folder: str, image_extensions: List[str] = None) -> Dict[str, Any]:
#         """Process all images in a folder"""
#         if image_extensions is None:
#             image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        
#         results = {}
#         total_images = 0
#         successful_detections = 0
#         validation_failures = 0
#         barcode_types_count = {}
        
#         for filename in os.listdir(image_folder):
#             if any(filename.lower().endswith(ext) for ext in image_extensions):
#                 total_images += 1
#                 image_path = os.path.join(image_folder, filename)
                
#                 print(f"Processing {filename}...")
#                 decoded_objects = self.comprehensive_decode(image_path)
                
#                 if decoded_objects:
#                     successful_detections += 1
                    
#                     try:
#                         barcode_data = decoded_objects[0].data.decode('utf-8', errors='ignore')
#                     except:
#                         barcode_data = str(decoded_objects[0].data)
                    
#                     barcode_type = decoded_objects[0].type
                    
#                     # Apply validation
#                     is_valid = self.basic_barcode_validation(barcode_data, barcode_type)
                    
#                     if is_valid:
#                         results[filename] = [{
#                             'data': barcode_data,
#                             'type': barcode_type
#                         }]
#                         print(f"✓ Found valid {barcode_type}: {barcode_data}")
                        
#                         # Count by type
#                         barcode_types_count[barcode_type] = barcode_types_count.get(barcode_type, 0) + 1
#                     else:
#                         validation_failures += 1
#                         results[filename] = [{
#                             'data': f"INVALID_{barcode_type}: {barcode_data}",
#                             'type': barcode_type
#                         }]
#                         print(f"⚠ Found invalid {barcode_type}: {barcode_data}")
#                 else:
#                     results[filename] = []
#                     print(f"✗ No barcodes found")
        
#         print(f"\nSummary:")
#         print(f"Total images: {total_images}")
#         print(f"Successful detections: {successful_detections}")
#         print(f"Valid barcodes: {successful_detections - validation_failures}")
        
#         if barcode_types_count:
#             print("Barcode types found:")
#             for barcode_type, count in sorted(barcode_types_count.items()):
#                 print(f"  - {barcode_type}: {count}")
        
#         print(f"Invalid barcodes: {validation_failures}")
#         print(f"Success rate: {successful_detections/total_images*100:.1f}%")
#         print(f"Valid barcode rate: {(successful_detections - validation_failures)/total_images*100:.1f}%")
#         print(f"Failed images: {len(self.failed_images)}")
        
#         if self.failed_images:
#             print("\nFailed images:")
#             for img in self.failed_images:
#                 print(f"  - {os.path.basename(img)}")
        
#         return results

#Usage examples
# if __name__ == "__main__":
#     # Example 1: Detect all barcode types (universal)
#     detector = UniversalBarcodeDetector()
    
#     # Example 2: Detect only specific barcode types
#     # detector = UniversalBarcodeDetector(target_symbols=[
#     #     pyzbar.ZBarSymbol.CODE39,
#     #     pyzbar.ZBarSymbol.CODE128
#     # ])
    
#     #For single image
#     result = detector.comprehensive_decode("D:\\OMRScanner\\input\\xyz\\0002.jpg")
#     print(result)
    
#     # For batch processing
#     # results = detector.batch_process("path/to/your/image/folder")
    
#     # Save results to file
#     # import json
#     # with open("barcode_results.json", "w") as f:
#     #     json.dump(results, f, indent=2)





# # Previous Implementation
# #  20/05/2025
# #
# #

# # import cv2
# # import numpy as np
# # from pyzbar.pyzbar import decode
# # import logging
# # import warnings
# # from PIL import Image, ImageEnhance
# # import os
# # from typing import List, Tuple, Optional

# # # Suppress warnings
# # warnings.filterwarnings("ignore",category=UserWarning)
# # logging.getLogger().setLevel(logging.ERROR)

# # class EnhancedBarcodeDetector:
# #     def __init__(self):
# #         self.failed_images = []
# #         self.preprocessing_methods = [
# #             self.basic_preprocessing,
# #             self.adaptive_threshold_preprocessing,
# #             self.otsu_threshold_preprocessing,
# #             self.gaussian_blur_preprocessing,
# #             self.morphological_preprocessing,
# #             self.contrast_enhancement_preprocessing,
# #             self.edge_enhancement_preprocessing,
# #             self.rotation_correction_preprocessing
# #         ]
    
# #     def basic_preprocessing(self, image):
# #         """Basic grayscale conversion"""
# #         if len(image.shape) == 3:
# #             return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
# #         return image
    
# #     def adaptive_threshold_preprocessing(self, image):
# #         """Adaptive thresholding for varying lighting conditions"""
# #         gray = self.basic_preprocessing(image)
# #         return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
# #                                    cv2.THRESH_BINARY, 11, 2)
    
# #     def otsu_threshold_preprocessing(self, image):
# #         """Otsu's thresholding"""
# #         gray = self.basic_preprocessing(image)
# #         _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
# #         return thresh
    
# #     def gaussian_blur_preprocessing(self, image):
# #         """Gaussian blur to reduce noise"""
# #         gray = self.basic_preprocessing(image)
# #         blurred = cv2.GaussianBlur(gray, (3, 3), 0)
# #         _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
# #         return thresh
    
# #     def morphological_preprocessing(self, image):
# #         """Morphological operations to clean up image"""
# #         gray = self.basic_preprocessing(image)
# #         _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
# #         # Morphological operations
# #         kernel = np.ones((2, 2), np.uint8)
# #         processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
# #         processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
# #         return processed
    
# #     def contrast_enhancement_preprocessing(self, image):
# #         """Enhance contrast using CLAHE"""
# #         gray = self.basic_preprocessing(image)
# #         clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
# #         enhanced = clahe.apply(gray)
# #         _, thresh = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
# #         return thresh
    
# #     def edge_enhancement_preprocessing(self, image):
# #         """Edge enhancement preprocessing"""
# #         gray = self.basic_preprocessing(image)
# #         # Apply unsharp masking
# #         blurred = cv2.GaussianBlur(gray, (9, 9), 10.0)
# #         unsharp = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
# #         _, thresh = cv2.threshold(unsharp, 127, 255, cv2.THRESH_BINARY)
# #         return thresh
    
# #     def rotation_correction_preprocessing(self, image):
# #         """Attempt to correct skewed barcodes"""
# #         gray = self.basic_preprocessing(image)
        
# #         # Try small rotations
# #         for angle in [-2, -1, 1, 2]:
# #             height, width = gray.shape
# #             center = (width // 2, height // 2)
# #             rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
# #             rotated = cv2.warpAffine(gray, rotation_matrix, (width, height))
# #             result = decode(rotated)
# #             if result:
# #                 return rotated
        
# #         return gray
    
# #     def resize_image(self, image, scale_factors=[1.0, 1.5, 2.0, 0.5]):
# #         """Try different image sizes"""
# #         results = []
# #         original_result = decode(image)
# #         if original_result:
# #             return original_result
        
# #         for scale in scale_factors:
# #             if scale == 1.0:
# #                 continue
            
# #             height, width = image.shape[:2]
# #             new_width = int(width * scale)
# #             new_height = int(height * scale)
            
# #             resized = cv2.resize(image, (new_width, new_height), 
# #                                interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
            
# #             result = decode(resized)
# #             if result:
# #                 return result
        
# #         return []
    
# #     def detect_with_opencv(self, image):
# #         """Alternative detection using OpenCV's barcode detector"""
# #         try:
# #             detector = cv2.barcode.BarcodeDetector()
# #             retval, decoded_info, decoded_type, points = detector.detectAndDecode(image)
            
# #             if retval:
# #                 # Convert to pyzbar-like format
# #                 results = []
# #                 for info, barcode_type in zip(decoded_info, decoded_type):
# #                     if info:  # Only add non-empty results
# #                         # Create a mock object similar to pyzbar's output
# #                         class MockResult:
# #                             def __init__(self, data, type_name):
# #                                 self.data = data.encode() if isinstance(data, str) else data
# #                                 self.type = type_name
                        
# #                         results.append(MockResult(info, barcode_type))
# #                 return results
# #         except Exception as e:
# #             pass
        
# #         return []
    
# #     def comprehensive_decode(self, image_path: str) -> List:
# #         """Comprehensive barcode detection with multiple strategies"""
# #         # Load image
# #         image = cv2.imread(image_path)
# #         if image is None:
# #             print(f"Could not load image: {image_path}")
# #             return []
        
# #         # Strategy 1: Try original image with different sizes
# #         # result = self.resize_image(image)
# #         # if result:
# #         #     return result
        
# #         # Strategy 2: Try different preprocessing methods
# #         for i, preprocessing_method in enumerate(self.preprocessing_methods):
# #             try:
# #                 processed_image = preprocessing_method(image)
                
# #                 # Try the processed image at different sizes
# #                 result = self.resize_image(processed_image)
# #                 if result:
# #                     return result
                    
# #             except Exception as e:
# #                 continue
        
# #         # Strategy 3: Try OpenCV detector
# #         result = self.detect_with_opencv(image)
# #         if result:
# #             return result
        
# #         # Strategy 4: Try with PIL enhancements
# #         # try:
# #         #     pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
# #         #     # Enhance brightness
# #         #     enhancer = ImageEnhance.Brightness(pil_image)
# #         #     for brightness in [0.7, 1.3, 1.5]:
# #         #         enhanced = enhancer.enhance(brightness)
# #         #         enhanced_cv = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
# #         #         result = decode(enhanced_cv)
# #         #         if result:
# #         #             return result
            
# #         #     # Enhance contrast
# #         #     enhancer = ImageEnhance.Contrast(pil_image)
# #         #     for contrast in [0.7, 1.3, 1.5, 2.0]:
# #         #         enhanced = enhancer.enhance(contrast)
# #         #         enhanced_cv = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
# #         #         result = decode(enhanced_cv)
# #         #         if result:
# #         #             return result
                    
# #         # except Exception as e:
# #         #     pass
        
# #         # # Strategy 5: Region-based detection (crop different parts)
# #         # height, width = image.shape[:2]
# #         # regions = [
# #         #     (0, 0, width, height//2),  # Top half
# #         #     (0, height//2, width, height),  # Bottom half
# #         #     (0, 0, width//2, height),  # Left half
# #         #     (width//2, 0, width, height),  # Right half
# #         #     (width//4, height//4, 3*width//4, 3*height//4),  # Center region
# #         # ]
        
# #         # for x, y, x2, y2 in regions:
# #         #     try:
# #         #         roi = image[y:y2, x:x2]
# #         #         if roi.size > 0:
# #         #             result = decode(roi)
# #         #             if result:
# #         #                 return result
# #         #     except:
# #         #         continue
        
# #         # If all strategies fail, add to failed list
# #         self.failed_images.append(image_path)
# #         return []
    
# #     def batch_process(self, image_folder: str, image_extensions: List[str] = None) -> dict:
# #         """Process all images in a folder"""
# #         if image_extensions is None:
# #             image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        
# #         results = {}
# #         total_images = 0
# #         successful_detections = 0
        
# #         for filename in os.listdir(image_folder):
# #             if any(filename.lower().endswith(ext) for ext in image_extensions):
# #                 total_images += 1
# #                 image_path = os.path.join(image_folder, filename)
                
# #                 print(f"Processing {filename}...")
# #                 decoded_objects = self.comprehensive_decode(image_path)
                
# #                 if decoded_objects:
# #                     successful_detections += 1
# #                     results[filename] = [obj.data.decode('utf-8') if hasattr(obj.data, 'decode') else str(obj.data) 
# #                                        for obj in decoded_objects]
# #                     print(f"✓ Found {len(decoded_objects)} barcode(s)")
# #                 else:
# #                     results[filename] = []
# #                     print(f"✗ No barcodes found")
        
# #         print(f"\nSummary:")
# #         print(f"Total images: {total_images}")
# #         print(f"Successful detections: {successful_detections}")
# #         print(f"Success rate: {successful_detections/total_images*100:.1f}%")
# #         print(f"Failed images: {len(self.failed_images)}")
        
# #         if self.failed_images:
# #             print("\nFailed images:")
# #             for img in self.failed_images:
# #                 print(f"  - {os.path.basename(img)}")
        
# #         return results

# # # Usage example
# # if __name__ == "__main__":
# #     detector = EnhancedBarcodeDetector()
    
# #     #For single image
# #     result = detector.comprehensive_decode("D:\\OMRScanner\\input\\xyz\\0599.jpg")
# #     print(result)
    
# # #     # For batch processing
# # #     results = detector.batch_process("D:\\OMRScanner\\input\\T2591\\T2591\\R2032012401")
    
# # #     # Save results to file
# # #     import json
# # #     with open("barcode_results.json", "w") as f:
# # #         json.dump(results, f, indent=2)