import cv2
import numpy as np
import os


def crop_omr_barcode_and_total_marks(name,image_path, output_dir="cropped_student_blocks"):
    """
    Crops the barcode and total marks part from an OMR sheet.

    Args:
        image_path (str): Path to the input OMR sheet image.
        output_dir (str): Directory to save the cropped images.
    """
    list_of_images_cropped = []
    print(f"Attempting to load image from: {os.path.abspath(image_path)}")
    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"ERROR: Image could not be loaded. Please check the path and ensure the file is a valid image.")
            print(f"       Current working directory: {os.getcwd()}")
            if not os.path.exists(image_path):
                print(f"       '{image_path}' does NOT exist at the specified path.")
            else:
                print(f"       '{image_path}' EXISTS, but OpenCV could not read it (e.g., corrupted, wrong format).")
            return
        h, w, _ = img.shape # Get height and width
        print(f"Image loaded successfully. Original image dimensions: Width={w}, Height={h}")
    except Exception as e:
        print(f"An unexpected error occurred during image loading: {e}")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory '{output_dir}' ensured.")
    # barcode and total marks part is [(85,1840),(1080,1840),(85,2340),(1080,2340)]
    start_x_barcode = 85
    start_y_barcode = 1840
    end_x_barcode = 1080
    end_y_barcode = 2340    
    #crop from original and store into new image with name barcode_originalimagename.jpg
    barcode = img[start_y_barcode:end_y_barcode,start_x_barcode:end_x_barcode]
    cv2.imwrite(f"{output_dir}/barcode_{os.path.basename(image_path)}", barcode)
    list_of_images_cropped.append(f"barcode_{os.path.basename(image_path)}")

    # total marks part is [(865,2020),(1060,2020),(865,2285),(1060,2285)]
    start_x_total_marks = 865
    start_y_total_marks = 2020
    end_x_total_marks = 1060
    end_y_total_marks = 2285    
    #crop from original and store into new image with name total_marks_originalimagename.jpg
    total_marks = img[start_y_total_marks:end_y_total_marks,start_x_total_marks:end_x_total_marks]
    cv2.imwrite(f"{output_dir}/total_marks_{os.path.basename(image_path)}", total_marks)
    list_of_images_cropped.append(f"total_marks_{os.path.basename(image_path)}")

    return list_of_images_cropped



def crop_omr_student_blocks_by_pattern(name,image_path, output_dir="cropped_student_blocks"):
    """
    Crops individual student's full blocks from an OMR sheet based on a defined pattern.

    Args:
        image_path (str): Path to the input OMR sheet image.
        output_dir (str): Directory to save the cropped images.
    """
    list_of_images_cropped = []
    # 1. Load the image
    #print(f"Attempting to load image from: {os.path.abspath(image_path)}")
    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"ERROR: Image could not be loaded. Please check the path and ensure the file is a valid image.")
            print(f"       Current working directory: {os.getcwd()}")
            if not os.path.exists(image_path):
                print(f"       '{image_path}' does NOT exist at the specified path.")
            else:
                print(f"       '{image_path}' EXISTS, but OpenCV could not read it (e.g., corrupted, wrong format).")
            return
        h, w, _ = img.shape # Get height and width
        #print(f"Image loaded successfully. Original image dimensions: Width={w}, Height={h}")
    except Exception as e:
        print(f"An unexpected error occurred during image loading: {e}")
        return

    # Create output directory if it doesn't exist
    #os.makedirs(output_dir, exist_ok=True)
    #print(f"Output directory '{output_dir}' ensured.")
    
    # 2. Define the pattern parameters based on your provided coordinates
    start_x = 95  # X-coordinate of the top-left corner of the first block (Row 1, Student 1)
    start_y = 415 # Y-coordinate of the top-left corner of the first block (Row 1, Student 1)

    block_width = 155  # Width of each student block
    block_height = 270 # Height of each student block

    x_step = 170 # Horizontal distance between the start of consecutive student blocks
    y_step = 385 # Vertical distance between the start of consecutive rows

    num_rows = 4
    num_students_per_row = 5 # From visual inspection of the OMR sheet layout

    # 3. Generate Bounding Boxes and Crop Images
    cropped_count = 0
    all_bboxes = [] # To store all calculated bounding boxes for clarity

    for r_idx in range(num_rows):
        # Calculate the y_start for the current row
        current_row_y_start = start_y + r_idx * y_step

        for s_idx in range(num_students_per_row):
            # Calculate the x_start for the current student in the current row
            current_student_x_start = start_x + s_idx * x_step

            # Calculate the x_end and y_end for the current block
            current_x_end = current_student_x_start + block_width
            current_y_end = current_row_y_start + block_height

            # Ensure coordinates are within image boundaries
            # This is crucial to prevent out-of-bounds errors if coordinates are slightly off
            x_start = max(0, current_student_x_start)
            y_start = max(0, current_row_y_start)
            x_end = min(w, current_x_end)
            y_end = min(h, current_y_end)

            bbox = (x_start, y_start, x_end, y_end)
            all_bboxes.append(bbox) # Store for logging/verification

            #print(f"--- Processing Row {r_idx+1}, Student {s_idx+1} ---")
            #print(f"Calculated Crop Region (x_start, y_start, x_end, y_end): {bbox}")

            # Crucial check: Ensure the cropping region has positive dimensions
            if x_end <= x_start or y_end <= y_start:
                print(f"WARNING: Invalid crop region detected (width <= 0 or height <= 0). Skipping this crop.")
                continue

            # Crop the image
            cropped_block = img[y_start:y_end, x_start:x_end]
            cropped_block_with_rollno = img[y_start-70:y_end,x_start:x_end]

            if cropped_block_with_rollno.shape[0] == 0 or cropped_block_with_rollno.shape[1] == 0:
                print(f"WARNING: Cropped image for Row {r_idx+1}, Student {s_idx+1} is empty (0 height or 0 width). Skipping save.")
                continue

            # Verify that the cropped image is not empty before writing
            if cropped_block.shape[0] == 0 or cropped_block.shape[1] == 0:
                print(f"WARNING: Cropped image for Row {r_idx+1}, Student {s_idx+1} is empty (0 height or 0 width). Skipping save.")
                continue

            #print(f"Cropped image dimensions: {cropped_block.shape}")

            # Save the cropped image
            output_filename_rollno = os.path.join(output_dir, f"{os.path.basename(image_path)}_row_{r_idx+1}_student_{s_idx+1}_rollno.jpg")
            try:
                cv2.imwrite(output_filename_rollno, cropped_block_with_rollno)
                cropped_count += 1
                list_of_images_cropped.append(f"{os.path.basename(image_path)}_row_{r_idx+1}_student_{s_idx+1}_rollno.jpg")
                # print(f"Saved: {output_filename_rollno}") # Uncomment for verbose saving log
            except Exception as e:
                print(f"ERROR: Failed to save {output_filename_rollno}. Reason: {e}")
                print(f"Final cropped_block_with_rollno shape before imwrite: {cropped_block_with_rollno.shape}")
            output_filename = os.path.join(output_dir, f"{os.path.basename(image_path)}_row_{r_idx+1}_student_{s_idx+1}_block.jpg")
            try:
                cv2.imwrite(output_filename, cropped_block)
                cropped_count += 1
                list_of_images_cropped.append(f"{os.path.basename(image_path)}_row_{r_idx+1}_student_{s_idx+1}_block.jpg")
                # print(f"Saved: {output_filename}") # Uncomment for verbose saving log
            except Exception as e:
                print(f"ERROR: Failed to save {output_filename}. Reason: {e}")
                print(f"Final cropped_block shape before imwrite: {cropped_block.shape}")


    print(f"\nSuccessfully cropped and saved {cropped_count} student blocks to '{output_dir}'.")
    if cropped_count < (num_rows * num_students_per_row):
        print(f"Note: {num_rows * num_students_per_row - cropped_count} crops were skipped due to invalid dimensions. Check the warnings above.")
    #print("You can now find the cropped images in the specified output directory.")

    return list_of_images_cropped
# # --- How to use the function ---
# if __name__ == "__main__":
#     input_image_file = "0001.jpg" # Ensure this file is in the script's directory or provide its full path
#     output_directory_name = "cropped_student_blocks" # Output folder name


#     crop_omr_student_blocks_by_pattern(input_image_file, output_directory_name)