from croplab import crop_omr_student_blocks_by_pattern
from croplab import crop_omr_barcode_and_total_marks
from imageprocessing import extract_barcode_type
import os
from imageprocessing import extract_number_from_circles_lab
import cv2
from storedata import get_number_of_lab_entries_all

def process_lab_omr(db_name, name, image_file, debug_mode=False):
    number_of_entries = get_number_of_lab_entries_all(db_name)
    if number_of_entries is None:
        print("Error in getting number of lab entries")
        return
    count_of_students_in_each_omr = {}
    for (barcode, number_of_lab_entries) in number_of_entries:
        count_of_students_in_each_omr[barcode] = number_of_lab_entries 

    barcode_and_total_marks_images =  crop_omr_barcode_and_total_marks(name,image_file, "cropped_student_blocks")
    #os.chdir("cropped_student_blocks")
    barcode_image_file = os.path.join("cropped_student_blocks", barcode_and_total_marks_images[0])

    barcode, omr_type = extract_barcode_type(barcode_image_file)
    total_marks_image_file = os.path.join("cropped_student_blocks", barcode_and_total_marks_images[1])
    img = cv2.imread(total_marks_image_file)
    total_marks = extract_number_from_circles_lab(  
        img,
        [10,10,10,10],  # 4 columns: evry column 0-9 (10 circles)
        [(0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)],
        debug=debug_mode,
        param2=11,
        debug_filename=f"total_marks_circles_lab_{name}.png"
    )
    #os.chdir("..")
    list_of_images_cropped =crop_omr_student_blocks_by_pattern(name,image_file, "cropped_student_blocks")
    #os.chdir("cropped_student_blocks")
    marks_of_each_student = []
    number_to_be_processed = count_of_students_in_each_omr.get(barcode, 0)
    if len(list_of_images_cropped) == 40:
        for i in range(1, 2*number_to_be_processed, 2):
            image_file = os.path.join("cropped_student_blocks", list_of_images_cropped[i])
            img = cv2.imread(image_file)
            marks = extract_number_from_circles_lab(
                img,
                [1,2,10,10],  # 4 columns: first column AB, second column 0,1 (2 circles), remaining 0-9 (10 circles)
                [(0,),(0,1),(0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)],
                debug=debug_mode,
                debug_filename=f"total_marks_circles_lab_{list_of_images_cropped[i]}",
                param2=11,
                firstone_optional=True
            )

            marks_of_each_student.append((marks, list_of_images_cropped[i+1]))            
            #print(list_of_images_cropped[i],marks)
    #os.chdir("..")
    return barcode_image_file,barcode,total_marks,marks_of_each_student

    
#print(process_lab_omr("0025", "0025.jpg"))

