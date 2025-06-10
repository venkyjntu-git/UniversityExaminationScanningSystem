import cv2
import numpy as np
from pyzbar.pyzbar import decode
import os
from barcodedetect import UniversalBarcodeDetector
from pyzbar import pyzbar


def extract_barcode_type(image_path):
    """
    Extracts the barcode from an image and determines its type.

    Args:
        image_path (str): The path to the image file.

    Returns:
        tuple: A tuple containing the barcode (str or None) and its type (str or None).
               Returns (None, None) if no barcode is found.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not open or find the image at {image_path}")
            return None, None

        #gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        #processed = preprocess_image(img)
        # barcodes = decode(img)
        #detector = UniversalBarcodeDetector()
        detector = UniversalBarcodeDetector(target_symbols=[
        pyzbar.ZBarSymbol.CODE39,
        pyzbar.ZBarSymbol.CODE128
    ])
    
        result = detector.comprehensive_decode(image_path)
        if result is []:
            print("No barcodes found",image_path)
            return None, None
        barcodes = result[0]
        if barcodes:
            obj = barcodes
            barcode_data = obj.data.decode('utf-8') if hasattr(obj.data, 'decode') else str(obj.data)
            #barcode_data = barcodes[0].data.decode('utf-8')
            if len(barcode_data) >= 9 and barcode_data.isdigit():
                return barcode_data, "ControlbundleOMR"
            else:
                return barcode_data, "ScriptOMR"
        else:
            return None, None
    except Exception as e:
        print(f"An error occurred during barcode extraction: {e}")
        return None, None

def crop_region_cm(img, start_cm, end_cm, dpi=200):
    """
    Crops a region of the image based on centimeter coordinates.

    Args:
        img (numpy.ndarray): The input image.
        start_cm (tuple): The (x, y) coordinates of the top-left corner in cm.
        end_cm (tuple): The (x, y) coordinates of the bottom-right corner in cm.
        dpi (float): Dots per inch (the correct DPI for your images).

    Returns:
        numpy.ndarray or None: The cropped image region, or None if coordinates are invalid.
    """
    try:
        x1_px = int(start_cm[0] * dpi / 2.54)
        y1_px = int(start_cm[1] * dpi / 2.54)
        x2_px = int(end_cm[0] * dpi / 2.54)
        y2_px = int(end_cm[1] * dpi / 2.54)

        height, width = img.shape[:2]
        if 0 <= x1_px < width and 0 <= y1_px < height and 0 <= x2_px <= width and 0 <= y2_px <= height and x1_px < x2_px and y1_px < y2_px:
            return img[y1_px:y2_px, x1_px:x2_px]
        else:
            print("Error: Invalid centimeter coordinates for cropping.")
            return None
    except Exception as e:
        print(f"An error occurred during image cropping: {e}")
        return None

def extract_number_from_circles_theory(cropped_img, expected_circles_per_column, columns_config, debug=True, debug_filename="circles_debug.png",param2=18, firstone_optional=False):
    """
    Extracts a number from a cropped image region containing bubbled circles.

    Args:
        cropped_img (numpy.ndarray): The cropped image containing the circles.
        expected_circles_per_column (list): A list containing the expected number
                                             of circles in each column.
        columns_config (list): A list of tuples, where each tuple defines the digits
                               in each column (top to bottom).
        debug (bool): If True, saves an image with detected circles highlighted.
        debug_filename (str): The filename for the debug image.

    Returns:
        int or -1: The extracted number, or -1 if the number of circles is incorrect
                     or if multiple bubbles are detected in a column.
    """
    try:
        #debug = True
        outf = open('debug.txt', 'a')
        gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
        # Apply binary thresholding
        # Threshold value 180 means pixels below 180 become black (0), above become white (255)
        #_, bw_image = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1, 20,
                                   param1=50, param2=param2, minRadius=7, maxRadius=15)

        if circles is None or len(circles[0]) != sum(expected_circles_per_column):
            if debug:
                #cv2.imwrite(debug_filename, cropped_img) # Save original cropped image if no circles found
                print(f"Debug: Expected {sum(expected_circles_per_column)} circles, but found {len(circles[0]) if circles is not None else 0}. Saved to {debug_filename}", file=outf)
            circles_int = np.round(circles[0, :]).astype("int")
            circle_positions = [(x, y) for x, y, r in circles_int]
            debug_img = cropped_img.copy()
            for x, y, r in circles_int:
                cv2.circle(debug_img, (x, y), r, (255, 0, 0), 2)
            cv2.imwrite(debug_filename, debug_img)
            print(f"Debug: Detected circles highlighted and saved to {debug_filename}",file=outf)
            return -1

        circles_int = np.round(circles[0, :]).astype("int")
        circle_positions = [(x, y) for x, y, r in circles_int]

        if debug:
            debug_img = cropped_img.copy()
            for x, y, r in circles_int:
                cv2.circle(debug_img, (x, y), r, (0, 255, 0), 2)
            cv2.imwrite(debug_filename, debug_img)
            print(f"Debug: Detected circles highlighted and saved to {debug_filename}")

        # Sort circles by x-coordinate to group by column
        circle_positions.sort(key=lambda pos: pos[0])

        extracted_digits = []
        circle_index = 0
        first_one = 0
        for i, expected_count in enumerate(expected_circles_per_column):
            column_circles = sorted(circle_positions[circle_index : circle_index + expected_count], key=lambda pos: pos[1])
            circle_index += expected_count

            bubbled_index = -1
            bubbled_count = 0
            for j, (cx, cy) in enumerate(column_circles):
                # Extract a small region around the circle and check the average intensity
                mask = np.zeros_like(gray)
                cv2.circle(mask, (cx, cy), 10, 255, -1)
                masked_region = cv2.bitwise_and(gray, gray, mask=mask)
                avg_intensity = np.mean(masked_region[mask > 0])

                # Adjust threshold based on image conditions
                if avg_intensity < 120:  # Lower intensity indicates a filled bubble
                    bubbled_index = j
                    bubbled_count += 1
            first_one = first_one + 1
            if bubbled_count != 1:
                return -1  # Expect exactly one bubbled circle per column

            extracted_digits.append(columns_config[i][bubbled_index])

        # Construct the number from the extracted digits
        extracted_number = 0
        power = 1
        for digit in reversed(extracted_digits):
            extracted_number += digit * power
            power *= 10

        return extracted_number

    except Exception as e:
        print(f"An error occurred during number extraction: {e}")
        return -1

def process_control_bundle_omr(name,image_path, debug_mode=False):
    """
    Processes a ControlbundleOMR image to extract the number of answer books and grand total.

    Args:
        image_path (str): The path to the image file.
        debug_mode (bool): If True, enables saving debug images.

    Returns:
        tuple: A tuple containing the number of answer books (int or -1) and the
               grand total (int or -1). Returns (None, None) if barcode is not
               ControlbundleOMR or if any extraction fails.
    """
    # barcode, omr_type = extract_barcode_type(image_path)
    # if omr_type != "ControlbundleOMR":
    #     print("Not a ControlbundleOMR.")
    #     return None, None

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not open or find the image at {image_path}")
        return None, None

    # Define the regions of interest in centimeters
    num_answer_books_roi_cm = [(1.4, 4.4), (2.7, 8.8)]
    grand_total_roi_cm = [(2.7, 4.4), (4.7, 8.8)]

    # Crop the regions
    num_answer_books_cropped = crop_region_cm(img, num_answer_books_roi_cm[0], num_answer_books_roi_cm[1])
    grand_total_cropped = crop_region_cm(img, grand_total_roi_cm[0], grand_total_roi_cm[1])

    num_answer_books = -1
    if num_answer_books_cropped is not None:
        num_answer_books = extract_number_from_circles_theory(
            num_answer_books_cropped,
            [5, 10],  # First column 0-4 (5 circles), second column 0-9 (10 circles)
            [(0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)],
            debug=debug_mode,
            debug_filename=f"num_answer_books_circles{name}.png"
        )

    grand_total = -1
    if grand_total_cropped is not None:
        grand_total = extract_number_from_circles_theory(
            grand_total_cropped,
            [4, 10, 10, 10],  # First column 0-3 (4 circles), remaining 0-9 (10 circles)
            [(0, 1, 2, 3), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)],
            debug=debug_mode,
            debug_filename=f"grand_total_circles{name}.png"
        )

    return num_answer_books, grand_total

def process_script_omr(name,image_path, debug_mode=False):
    """
    Processes a ScriptOMR image to extract the number of answer books and grand total.

    Args:
        image_path (str): The path to the image file.
        debug_mode (bool): If True, enables saving debug images.

    Returns:
        tuple: A tuple containing the number of answer books (int or -1) and the
               grand total (int or -1). Returns (None, None) if barcode is not
               ScriptOMR or if any extraction fails.
    """
    # Add your logic for processing Script OMR here
    # barcode, omr_type = extract_barcode_type(image_path)
    # if omr_type != "ScriptOMR":
    #     print("Not a ScriptOMR.")
    #     return None, None
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not open or find the image at {image_path}")
        return None, None
    
    total_marks_roi = [(11.7, 2.6), (13, 6.9)]
    total_marks_cropped = crop_region_cm(img, total_marks_roi[0], total_marks_roi[1])
    total_marks = extract_number_from_circles_theory(
        total_marks_cropped,
        [10,10],  # First column 0-9 (10 circles), remaining 0-9 (10 circles)
        [(0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)],
        debug=debug_mode,
        debug_filename=f"total_marks_circles{name}.png"
    )

    script_number_roi = [(13.3, 2.6), (14.7, 6.9)]
    script_number_cropped = crop_region_cm(img, script_number_roi[0], script_number_roi[1])
    script_number = extract_number_from_circles_theory(
        script_number_cropped,
        [5,10],  # First column 0-4 (5 circles), remaining 0-9 (10 circles)
        [(0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)],
        debug=debug_mode,
        debug_filename=f"script_number_circles{name}.png"
    )

    return script_number, total_marks


def extract_number_from_circles_lab(cropped_img, expected_circles_per_column, columns_config, debug=False, debug_filename="circles_debug.png",param2=18, firstone_optional=False):
    """
    Extracts a number from a cropped image region containing bubbled circles.

    Args:
        cropped_img (numpy.ndarray): The cropped image containing the circles.
        expected_circles_per_column (list): A list containing the expected number
                                             of circles in each column.
        columns_config (list): A list of tuples, where each tuple defines the digits
                               in each column (top to bottom).
        debug (bool): If True, saves an image with detected circles highlighted.
        debug_filename (str): The filename for the debug image.

    Returns:
        int or -1: The extracted number, or -1 if the number of circles is incorrect
                     or if multiple bubbles are detected in a column.
    """
    try:
        debug = True
        outf = open('debug.txt', 'a')
        gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
        # Apply binary thresholding
        # Threshold value 180 means pixels below 180 become black (0), above become white (255)
        #_, bw_image = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1, 20,
                                   param1=50, param2=param2, minRadius=4, maxRadius=10)

        if circles is None or len(circles[0]) != sum(expected_circles_per_column):
            if debug:
                #cv2.imwrite(debug_filename, cropped_img) # Save original cropped image if no circles found
                print(f"Debug: Expected {sum(expected_circles_per_column)} circles, but found {len(circles[0]) if circles is not None else 0}. Saved to {debug_filename}", file=outf)
            circles_int = np.round(circles[0, :]).astype("int")
            circle_positions = [(x, y) for x, y, r in circles_int]
            debug_img = cropped_img.copy()
            for x, y, r in circles_int:
                cv2.circle(debug_img, (x, y), r, (255, 0, 0), 2)
            debug_filename = os.path.join("cropped_student_blocks", debug_filename)
            cv2.imwrite(debug_filename, debug_img)
            print(f"Debug: Detected circles highlighted and saved to {debug_filename}",file=outf)
            return -1

        circles_int = np.round(circles[0, :]).astype("int")
        circle_positions = [(x, y) for x, y, r in circles_int]

        if debug:
            debug_img = cropped_img.copy()
            for x, y, r in circles_int:
                cv2.circle(debug_img, (x, y), r, (0, 255, 0), 2)
            debug_filename = os.path.join("cropped_student_blocks", debug_filename)
            cv2.imwrite(debug_filename, debug_img)
            print(f"Debug: Detected circles highlighted and saved to {debug_filename}")

        # Sort circles by x-coordinate to group by column
        circle_positions.sort(key=lambda pos: pos[0])

        extracted_digits = []
        circle_index = 0
        first_one = 0
        absent = False
        for i, expected_count in enumerate(expected_circles_per_column):
            column_circles = sorted(circle_positions[circle_index : circle_index + expected_count], key=lambda pos: pos[1])
            circle_index += expected_count

            bubbled_index = -1
            bubbled_count = 0
            for j, (cx, cy) in enumerate(column_circles):
                # Extract a small region around the circle and check the average intensity
                mask = np.zeros_like(gray)
                cv2.circle(mask, (cx, cy), 10, 255, -1)
                masked_region = cv2.bitwise_and(gray, gray, mask=mask)
                avg_intensity = np.mean(masked_region[mask > 0])

                # Adjust threshold based on image conditions
                if avg_intensity < 150:  # Lower intensity indicates a filled bubble
                    bubbled_index = j
                    bubbled_count += 1
            first_one = first_one + 1
            print(bubbled_count)
            if firstone_optional and first_one == 1:
                if bubbled_count == 1:
                    absent = True
                continue               
            if bubbled_count != 1 and absent == False:
                return -1  # Expect exactly one bubbled circle per column
            elif bubbled_count == 1:
                extracted_digits.append(columns_config[i][bubbled_index])

        print(extracted_digits)
        # check extracted_digits is empty 
        if firstone_optional and absent: 
            if len(extracted_digits) == 0:
                return -2
            else:
                return -1
        
        # Construct the number from the extracted digits
        extracted_number = 0
        power = 1
        for digit in reversed(extracted_digits):
            extracted_number += digit * power
            power *= 10

        return extracted_number

    except Exception as e:
        print(f"An error occurred during number extraction: {e}")
        return -1



import math
def deskew_using_squares(name,image_path):
    OFFSET_Y_TOP = -5
    OFFSET_Y_BOTTOM = -5
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return

    #cv2.imshow("Original Image", image)
    #cv2.waitKey(0)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255,
                                   cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 10)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    squares = []
    min_square_area = 300
    max_square_area = 5000
    square_aspect_ratio_min = 0.85
    square_aspect_ratio_max = 1.15

    temp_squares_display = image.copy() 

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if min_square_area < area < max_square_area:
            approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)
                if square_aspect_ratio_min < aspect_ratio < square_aspect_ratio_max:
                    squares.append((x, y, w, h, area))
                    cv2.rectangle(temp_squares_display, (x,y), (x+w, y+h), (0,255,0), 2)

    # cv2.imshow("Potential Squares Detected (on Original)", temp_squares_display)
    # cv2.waitKey(0)

    squares = sorted(squares, key=lambda x: x[4], reverse=True)[:4]

    if len(squares) != 4:
        #print(f"Failed to detect exactly 4 square markers for alignment. Found {len(squares)}. Cannot deskew or crop.")
        #output_path = f'failed_deskew_no_squares_{output_name}.jpg'
        #cv2.imwrite(output_path, image)
        #print(f"Fallback (original) image saved to {output_path}")
        #cv2.destroyAllWindows()
        return (image_path,False) 

    points = [(x + w // 2, y + h // 2) for x, y, w, h, a in squares]
    points = sorted(points, key=lambda p: (p[1], p[0])) 

    tl, tr = sorted(points[:2], key=lambda p: p[0])    # Top-left, Top-right
    bl, br = sorted(points[2:], key=lambda p: p[0]) # Bottom-left, Bottom-right

    # Calculate angles. The 'dx' (horizontal difference) is the width of the OMR segment.
    # The 'dy' (vertical difference) is what indicates skew relative to a horizontal line.
    # The OFFSET_Y_TOP/BOTTOM are only needed if the OMR itself is intentionally non-horizontal
    # between these points, which you've clarified is not the case for Y alignment.
    
    # Calculate effective dy after accounting for potential designed vertical offsets
    effective_dy_top = (tr[1] - tl[1]) - OFFSET_Y_TOP
    dx_top = tr[0] - tl[0]

    effective_dy_bottom = (br[1] - bl[1]) - OFFSET_Y_BOTTOM
    dx_bottom = br[0] - bl[0]

    # Add a small epsilon to dx if it's very close to zero, to avoid division by zero
    # or extremely large angles if points are nearly vertically aligned (unlikely for these markers)
    epsilon = 1e-6
    if abs(dx_top) < epsilon: dx_top = epsilon * np.sign(dx_top) if np.sign(dx_top) != 0 else epsilon
    if abs(dx_bottom) < epsilon: dx_bottom = epsilon * np.sign(dx_bottom) if np.sign(dx_bottom) != 0 else epsilon

    angle_top = math.degrees(math.atan2(effective_dy_top, dx_top))
    angle_bottom = math.degrees(math.atan2(effective_dy_bottom, dx_bottom))

    skew_angle_deg = (angle_top + angle_bottom) / 2.0

    # print(f"TL: {tl}, TR: {tr}, BL: {bl}, BR: {br}") # Print actual coordinates for debugging
    # # print(f"Observed dy_top: {tr[1] - tl[1]}, dx_top: {dx_top}, Effective dy_top (corrected for design): {effective_dy_top}")
    # # print(f"Observed dy_bottom: {br[1] - bl[1]}, dx_bottom: {dx_bottom}, Effective dy_bottom (corrected for design): {effective_dy_bottom}")
    # # print(f"Angle of top edge (corrected): {angle_top:.2f} degrees")
    # # print(f"Angle of bottom edge (corrected): {angle_bottom:.2f} degrees")
    print(f"Calculated skew angle: {skew_angle_deg:.2f} degrees for {image_path}")

    if skew_angle_deg > 1.0:
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, skew_angle_deg, 1.0)
        deskewed_image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        #print("Image deskewed.")
        deskewed_image_path = f'{name}_deskewed.jpg'
        cv2.imwrite(deskewed_image_path,deskewed_image)
        return (deskewed_image_path, True)
        #cv2.imshow("Deskewed Image (using squares, with offset correction)", deskewed_image)
        #cv2.waitKey(0)
    else:
        #print("Image not deskewed.")
        return (image_path,True)
        #deskewed_image = image.copy()
        

    #cv2.imshow("Deskewed Image (using squares, with offset correction)", deskewed_image)
    #cv2.waitKey(0)

   




# if __name__ == "__main__":
#     directory_path = "D:\\OMRRead\\images\\R1632012301"  # Replace with the actual path to your image
#     debug_mode = True  # Set to True to save debug images
#     outb  = open('output.txt','w')
#     for filename in os.listdir(directory_path):
#         # Check if the file is an image by extension
#         if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
#             # Construct the full file path
#             image_file = os.path.join(directory_path, filename)
#             barcode, omr_type = extract_barcode_type(image_file)
#             print(f"Barcode: {barcode}, OMR Type: {omr_type}, Image: {filename}", file = outb)
#             name = filename.split(".")[0]
#             if omr_type == "ControlbundleOMR":
#                 num_answer_books, grand_total = process_control_bundle_omr(name,image_file, debug_mode=debug_mode)
#                 print(f"Number of Answer Books: {num_answer_books}", file=outb)
#                 print(f"Grand Total: {grand_total}", file=outb)
#             elif omr_type == "ScriptOMR":
#                 print("Script OMR detected.")
#                 script_number, total_marks = process_script_omr(name,image_file, debug_mode=debug_mode)
#                 print(f"Total Marks: {total_marks}",file=outb)
#                 print(f"Script Number: {script_number}",file=outb)
#         # Add your logic for processing Script OMR here
#             elif barcode is None:
#                 print("No barcode found.",file=outb)
#             else:
#                 print("Unknown OMR type based on barcode length.",file=outb)

# if __name__ == "__main__":
#     image_path = "D:\\OMRScanner\\input\\T2591\\T2591\\R2032012401\\0623.jpg"
#     name = "0623"
#     (image_file, status) = deskew_using_squares(name, image_path) 
#     debug_mode = True  # Set to True to save debug images
#     if status == True:
#         #print("Image deskewed.")
#         script_number, total_marks = process_script_omr(name,image_file, debug_mode=debug_mode)
#         print(f"Total Marks: {total_marks}")
#         print(f"Script Number: {script_number}")
#     else:
#         print("Image not deskewed.")
    