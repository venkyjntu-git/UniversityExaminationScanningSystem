import pandas as pd
#from storedata import insert_into_labprintomrentryinfo
#from storedata import insert_into_labprintomrinfo
from storedata import insert_batch_labprintomrentryinfo
from storedata import insert_batch_labprintomrinfo

# read excel file using pandas
# the header of excel file is the column names of the dataframe
#SLNO	HALLTICKET	STUDENT_NA	SUBJECT_CO	SUBJECT_NA	DEGREE	
# REGULATION	BRANCH_COD	BRANCH_NAM	EXAMINATIO	EXAM_TYPE	MONTH_AND_	
# DATE_OF_EX	COLLEGE_CO	COLLEGE_NA	COLLEGE_DI	RPRI	SNO	BARCODE

def process_excel_file_data_collection(excelfile):
    """
    Reads an Excel file and collects data into lists suitable for batch insertion.

    Args:
        excelfile (str): The path to the Excel file.

    Returns:
        tuple: A tuple containing two lists:
               - labprintomrentryinfo_data (list of tuples for labprintomrentryinfo table)
               - labprintomrinfo_data (list of tuples for labprintomrinfo table)
    """
    df = pd.read_excel(excelfile)

    labprintomrentryinfo_data = []
    # Use a dictionary to easily update counts and ensure unique barcodes for labprintomrinfo
    labprintomrinfo_temp_data = {} 

    barcodetocollegecode = {}
    barcodetosubjectcode = {}
    collegecodetocollegename = {}
    number_of_lab_entries = {}

    for index, row in df.iterrows():
        barcode = row['BARCODE']
        college_code_current_row = row['COLLEGE_CO']
        subject_code_current_row = row['SUBJECT_CO']
        college_name_current_row = row['COLLEGE_NA']
        hall_ticket_number = row['HALLTICKET']
        hall_ticket_sno_in_omr = row['SNO']

        
        # Collect data for labprintomrentryinfo
        if hall_ticket_number and '*' not in str(hall_ticket_number):
            # Populate lookup dictionaries and count entries
            if barcode not in barcodetocollegecode:
                barcodetocollegecode[barcode] = college_code_current_row
        
            if barcode not in number_of_lab_entries:
                number_of_lab_entries[barcode] = 1
            else:
                number_of_lab_entries[barcode] += 1
        
            if college_code_current_row not in collegecodetocollegename:
                collegecodetocollegename[college_code_current_row] = college_name_current_row
        
            if barcode not in barcodetosubjectcode:
                barcodetosubjectcode[barcode] = subject_code_current_row
        
            # Store as (barcode, hall_ticket_sno_in_omr, hall_ticket_number, subject_code_current_row)
            labprintomrentryinfo_data.append((barcode, hall_ticket_sno_in_omr, hall_ticket_number, subject_code_current_row))
    
    # After iterating through the Excel, prepare data for labprintomrinfo
    for barcode in barcodetocollegecode:
        college_code = barcodetocollegecode[barcode]
        college_name = collegecodetocollegename.get(college_code, "Unknown College")
        subject_code = barcodetosubjectcode[barcode]
        number_entries = number_of_lab_entries[barcode]
        # Store as (barcode, college_code, college_name, subject_code, number_entries)
        labprintomrinfo_temp_data[barcode] = (barcode, college_code, college_name, subject_code, number_entries)

    # Convert the dictionary values to a list for executemany
    labprintomrinfo_data = list(labprintomrinfo_temp_data.values())

    print(f"Collected {len(labprintomrentryinfo_data)} entries for labprintomrentryinfo.")
    print(f"Collected {len(labprintomrinfo_data)} unique entries for labprintomrinfo.")

    return labprintomrentryinfo_data, labprintomrinfo_data
def process_excel_and_insert(excelfile, db_name):
    """
    Orchestrates the process of reading an Excel file and inserting data
    into the database using batch operations across multiple functions.

    Args:
        excelfile (str): The path to the Excel file.
        db_name (str): The name of the database to connect to.
    """
    print(f"Processing Excel file: {excelfile}")
        # Step 1: Collect data from Excel
    labprintomrentryinfo_data, labprintomrinfo_data = process_excel_file_data_collection(excelfile)

        
        # Step 2: Perform batch inserts
    insert_batch_labprintomrentryinfo(db_name, labprintomrentryinfo_data)
    insert_batch_labprintomrinfo(db_name, labprintomrinfo_data)

    print("Excel file processed and data inserted into the database successfully.")


# def process_excel_file(excelfile, db_name):
#     df = pd.read_excel(excelfile)
#     # read respective columns and store into labprintomrentryinfo
#     barcodetocollegecode = {}
#     barcodetosubjectcode = {}
#     collegecodetocollegename = {}
#     number_of_lab_entries = {}
#     for index, row in df.iterrows():
#         barcode = row['BARCODE']
#         if barcode not in barcodetocollegecode:
#             barcodetocollegecode[barcode] = row['COLLEGE_CO']
#         if barcode not in number_of_lab_entries:
#             number_of_lab_entries[barcode] = 1
#         else:
#             number_of_lab_entries[barcode] += 1
#         if row['COLLEGE_CO'] not in collegecodetocollegename:
#             collegecodetocollegename[row['COLLEGE_CO']] = row['COLLEGE_NA']
#         # insert into labprintomrinfo
#         if barcode not in barcodetosubjectcode:
#             barcodetosubjectcode[barcode] = row['SUBJECT_CO']

#         hall_ticket_number = row['HALLTICKET']
#         subject_code = row['SUBJECT_CO']
#         hall_ticket_sno_in_omr = row['SNO']
#         if hall_ticket_number and '*' not in hall_ticket_number:
#             # insert into labprintomrentryinfo
#             insert_into_labprintomrentryinfo(db_name, barcode, hall_ticket_sno_in_omr, hall_ticket_number, subject_code)
    
#     for barcode in barcodetocollegecode:
#         college_code = barcodetocollegecode[barcode]
#         college_name = collegecodetocollegename[college_code]
#         subject_code = barcodetosubjectcode[barcode]
#         number_entries = number_of_lab_entries[barcode]
#         insert_into_labprintomrinfo(db_name, barcode, college_code, college_name, subject_code, number_entries)

#     print("Excel file processed successfully.")