import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
import os
import numpy as np
from pyzbar.pyzbar import decode
import threading
import time
import datetime


# Assuming these are in your project directory
from createdatabasetables import create_database, create_tables
from imageprocessing import extract_barcode_type, process_control_bundle_omr, process_script_omr
from storedata import storeinto_controlbundle_table, storeinto_script_table, storeinto_mismatchbundle_table
from storedata import fetch_failed_bundle_info, fetch_failed_script_info
from doublentry import ManualDataEntryApp
from storedata import identify_mismatch_control_bundle_info, export_data_from_database, write_summary
from storedata import check_and_correct_mismatches_in_scriptnumber
from search import ImageSearchApp
from mismatch import MismatchViewer
from imageprocessing import deskew_using_squares
from labomr import process_lab_omr
from filehandling import process_excel_and_insert
from storedata import store_batch_controlbundle_data, store_batch_mismatchbundle_data, store_batch_script_data
from storedata import store_batch_lab_data

# def process_images_in_directory(directory_path, db_name, progress_var, progress_text_label, status_label, debug_mode=False):
#     outf = open(f'outputtheory{datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}', 'w')
#     current_bundle_no = None
#     previous_bundle_no = None
#     previous_bundle_image_path = None
#     current_bundle_image_path = None

#     current_grand_total = None
#     previous_grand_total = None
#     script_number_with_in_bundle = 0
#     number_of_scripts_number_within_bundle = {}

#     # find the directroy name set as batchcode
#     batchcode = directory_path.split("/")[-1]
#     print(f"Batchcode: {batchcode}", file=outf)
    
#     image_files = [f for f in os.listdir(directory_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
#     total_images = len(image_files)

#     # Initialize progress text
#     progress_text_label.config(text=f"0 / {total_images} images processed")
#     progress_text_label.update_idletasks()

#     for i, filename in enumerate(image_files):
#         # Update status and progress bar
#         current_processed = i + 1
#         status_label.config(text=f"Processing: {filename}")
#         progress_var.set(current_processed / total_images * 100)
#         progress_text_label.config(text=f"{current_processed} / {total_images} images processed")

#         # Force UI update
#         status_label.update_idletasks()
#         progress_var.set(progress_var.get()) # Force redraw
#         progress_text_label.update_idletasks()
#         time.sleep(0.01) # Simulate processing time for demonstration. REMOVE THIS IN PRODUCTION!

#         image_file = os.path.join(directory_path, filename)
#         barcode, omr_type = extract_barcode_type(image_file)
#         print(f"Barcode: {barcode}, OMR Type: {omr_type}, Image: {filename}", file=outf)
#         name = filename.split(".")[0]

#         if omr_type == "ControlbundleOMR":
#             print(f"Control Bundle OMR detected.", file=outf)
#             num_answer_books, grand_total = process_control_bundle_omr(name, image_file, debug_mode=debug_mode)
#             print(f"Number of Answer Books: {num_answer_books}", file=outf)
#             print(f"Grand Total: {grand_total}", file=outf)
#             previous_bundle_no = current_bundle_no
#             current_bundle_no = barcode
#             previous_bundle_image_path = current_bundle_image_path
#             current_bundle_image_path = image_file
#             previous_grand_total = current_grand_total
#             current_grand_total = grand_total

#             number_of_scripts_number_within_bundle[barcode] = num_answer_books

#             if previous_bundle_no is not None and previous_bundle_no in number_of_scripts_number_within_bundle:
#                 if number_of_scripts_number_within_bundle[previous_bundle_no] != script_number_with_in_bundle:
#                     storeinto_mismatchbundle_table(db_name, previous_bundle_no, number_of_scripts_number_within_bundle[previous_bundle_no], script_number_with_in_bundle, previous_grand_total, previous_grand_total, name, previous_bundle_image_path,batchcode)

#             script_number_with_in_bundle = 0
#             storeinto_controlbundle_table(db_name, barcode, num_answer_books, grand_total, name, image_file,batchcode)
#         elif omr_type == "ScriptOMR":
#             print(f"Script OMR detected.", file=outf)
#             (skewed_image_file, status) = deskew_using_squares(name,image_file)
#             if status:
#                 script_number, total_marks = process_script_omr(name, skewed_image_file, debug_mode=debug_mode)
#                 print(f"Total Marks: {total_marks}", file=outf)
#                 print(f"Script Number: {script_number}", file=outf)
#             else:
#                 script_number = -1
#                 total_marks = -1
#                 print(f"Total Marks: {total_marks}", file=outf)
#                 print(f"Script Number: {script_number}", file=outf)
#             script_number_with_in_bundle = script_number_with_in_bundle + 1
#             storeinto_script_table(db_name, barcode, current_bundle_no, script_number, total_marks, name, image_file,batchcode)
#         elif barcode is None:
#             print("No barcode found.", file=outf)
#         else:
#             print("Unknown OMR type based on barcode length.", file=outf)

#     status_label.config(text="Extracting Information from Images Completed.")
#     outf.close()
#     messagebox.showinfo("Processing Complete", "Image processing finished successfully!")

def process_images_in_directory_modular(directory_path, db_name, progress_var, progress_text_label, status_label, debug_mode=False):
    """
    Processes images in a directory, extracts OMR data, and collects it into lists.
    Then, it calls separate functions to perform batch insertions, with each store function
    managing its own database connection.

    Args:
        directory_path (str): The path to the directory containing images.
        db_name (str): The name of the database to connect to.
        progress_var (tk.DoubleVar): Tkinter variable for progress bar value.
        progress_text_label (tk.Label): Tkinter label to display progress text.
        status_label (tk.Label): Tkinter label to display current status.
        debug_mode (bool): If True, enables debug features in OMR processing.
    """
    outf = open(f'outputtheory{datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}', 'w')
    
    # Lists to store data for batch insertion
    controlbundle_data_to_insert = []
    script_data_to_insert = []
    mismatchbundle_data_to_insert = []

    current_bundle_no = None
    previous_bundle_no = None
    previous_bundle_image_path = None
    current_bundle_image_path = None

    current_grand_total = None
    previous_grand_total = None
    script_number_with_in_bundle = 0
    number_of_scripts_number_within_bundle = {}

    batchcode = directory_path.split("/")[-1]
    print(f"Batchcode: {batchcode}", file=outf)

    image_files = [f for f in os.listdir(directory_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
    total_images = len(image_files)

    progress_text_label.config(text=f"0 / {total_images} images processed")
    progress_text_label.update_idletasks()

    for i, filename in enumerate(image_files):
        current_processed = i + 1
        status_label.config(text=f"Processing: {filename}")
        progress_var.set(current_processed / total_images * 100)
        progress_text_label.config(text=f"{current_processed} / {total_images} images processed")

        status_label.update_idletasks()
        progress_var.set(progress_var.get())
        progress_text_label.update_idletasks()

        image_file_path = os.path.join(directory_path, filename)
        barcode, omr_type = extract_barcode_type(image_file_path)
        print(f"Barcode: {barcode}, OMR Type: {omr_type}, Image: {filename}", file=outf)
        name = filename.split(".")[0]

        if omr_type == "ControlbundleOMR":
            print(f"Control Bundle OMR detected.", file=outf)
            num_answer_books, grand_total = process_control_bundle_omr(name, image_file_path, debug_mode=debug_mode)
            print(f"Number of Answer Books: {num_answer_books}", file=outf)
            print(f"Grand Total: {grand_total}", file=outf)

            previous_bundle_no = current_bundle_no
            current_bundle_no = barcode
            previous_bundle_image_path = current_bundle_image_path
            current_bundle_image_path = image_file_path
            previous_grand_total = current_grand_total
            current_grand_total = grand_total

            number_of_scripts_number_within_bundle[barcode] = num_answer_books

            if previous_bundle_no is not None and previous_bundle_no in number_of_scripts_number_within_bundle:
                if number_of_scripts_number_within_bundle[previous_bundle_no] != script_number_with_in_bundle:
                    mismatchbundle_data_to_insert.append((
                        previous_bundle_no,
                        number_of_scripts_number_within_bundle[previous_bundle_no],
                        script_number_with_in_bundle,
                        previous_grand_total,
                        previous_grand_total,
                        name, # Original filename
                        previous_bundle_image_path,
                        batchcode
                    ))

            script_number_with_in_bundle = 0
            controlbundle_data_to_insert.append((barcode, num_answer_books, grand_total, name, image_file_path, batchcode))

        elif omr_type == "ScriptOMR":
            print(f"Script OMR detected.", file=outf)
            (skewed_image_file, status) = deskew_using_squares(name, image_file_path)
            if status:
                script_number, total_marks = process_script_omr(name, skewed_image_file, debug_mode=debug_mode)
                print(f"Total Marks: {total_marks}", file=outf)
                print(f"Script Number: {script_number}", file=outf)
            else:
                script_number = -1
                total_marks = -1
                print(f"Total Marks: {total_marks}", file=outf)
                print(f"Script Number: {script_number}", file=outf)
            
            script_number_with_in_bundle = script_number_with_in_bundle + 1
            script_data_to_insert.append((barcode, current_bundle_no, script_number, total_marks, name, image_file_path, batchcode))
        
        elif barcode is None:
            print("No barcode found.", file=outf)
        else:
            print("Unknown OMR type based on barcode length.", file=outf)

    outf.close()

    # --- Call store functions after data collection is complete ---
    try:
        store_batch_controlbundle_data(db_name, controlbundle_data_to_insert)
        store_batch_script_data(db_name, script_data_to_insert)
        store_batch_mismatchbundle_data(db_name, mismatchbundle_data_to_insert)
        
        status_label.config(text="Extracting Information from Images Completed.")
        messagebox.showinfo("Processing Complete", "Image processing finished successfully!")

    except Exception as error:
        print(f"An error occurred during batch database insertions: {error}")
        status_label.config(text="Processing Failed!")
        messagebox.showerror("Processing Error", f"An error occurred: {error}")



def process_lab_omr_images_in_directory(directory_path, db_name, progress_var, progress_text_label, status_label, debug_mode=False):
    image_files = [f for f in os.listdir(directory_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
    total_images = len(image_files)
    outf = open(f"outputlab{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt", "w")
    # Initialize progress text
    progress_text_label.config(text=f"0 / {total_images} images processed")
    progress_text_label.update_idletasks()

    batchcode = directory_path.split("/")[-1]
    print(f"Batchcode: {batchcode}", file=outf)

    lab_data_to_insert = []
    for i, filename in enumerate(image_files):
        # Update status and progress bar
        current_processed = i + 1
        status_label.config(text=f"Processing: {filename}")
        progress_var.set(current_processed / total_images * 100)
        progress_text_label.config(text=f"{current_processed} / {total_images} images processed")

        # Force UI update
        status_label.update_idletasks()
        progress_var.set(progress_var.get()) # Force redraw
        progress_text_label.update_idletasks()
        time.sleep(0.01) # Simulate processing time for demonstration. REMOVE THIS IN PRODUCTION!

        image_file = os.path.join(directory_path, filename)
        name = filename.split(".")[0]
        (skewed_image_file, status) = deskew_using_squares(name,image_file)
        if status:
            barcode_image_file, barcode, total_marks, marks_of_students = process_lab_omr(db_name,name, skewed_image_file, debug_mode=debug_mode)
            print(f"Total Marks: {total_marks}", file=outf)
            print(f"Barcode: {barcode}", file=outf)
        else:
            barcode_image_file,barcode, total_marks, marks_of_students = process_lab_omr(db_name,name, image_file, debug_mode=debug_mode)
            print(f"Total Marks: {total_marks}", file=outf)
            print(f"Barcode: {barcode}", file=outf)

        lab_data_to_insert.append((barcode_image_file,barcode, total_marks, marks_of_students))
    

    try:
        store_batch_lab_data(db_name, batchcode,lab_data_to_insert)
        status_label.config(text="Extracting Information from Images Completed.")
        messagebox.showinfo("Processing Complete", "Image processing finished successfully!")

    except Exception as error:
        print(f"An error occurred during batch database insertions: {error}")
        status_label.config(text="Processing Failed!")
        messagebox.showerror("Processing Error", f"An error occurred: {error}")


        


    

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("JNTUGV University Examination Scanning System")
        #self.center_window(380, 560) # Center the main window
        self.directory_path = tk.StringVar()
        self.file_path = tk.StringVar()
        self.exam_name = tk.StringVar()
        self.add_heading()
        self.add_logo()
        self.create_tabs() # Call create_tabs instead of create_buttons

    def center_window(self, window):
        # Update the window to ensure all widgets are rendered and their sizes calculated
        window.update_idletasks()

        # Get the window's width and height
        window_width = window.winfo_width()
        window_height = window.winfo_height()

        # Get the screen's width and height
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # Calculate the x and y coordinates for centering
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        # Set the window's geometry
        window.geometry(f'{window_width}x{window_height}+{x}+{y}')
    # def center_window(self, width, height):
    #     screen_width = self.root.winfo_screenwidth()
    #     screen_height = self.root.winfo_screenheight()
    #     x = (screen_width / 2) - (width / 2)
    #     y = (screen_height / 2) - (height / 2)
    #     self.root.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    def add_heading(self):
        heading_text = "JNTUGV University Examination Scanning System"
        self.heading = ttk.Label(self.root, text=heading_text, font=("Arial", 16, "bold"), wraplength=330, justify="center")
        self.heading.pack(pady=10)

    def add_logo(self):
        try:
            img = Image.open("Logo.jpg")
            img = img.resize((110, 110), Image.Resampling.LANCZOS) # Resize for better aesthetics
            self.logo_img = ImageTk.PhotoImage(img)
            self.logo_label = tk.Label(self.root, image=self.logo_img, bd=0) # bd=0 for no border
            self.logo_label.pack(pady=5)
        except FileNotFoundError:
            messagebox.showerror("Error", "Logo.jpg not found. Please ensure it's in the same directory as the script.")
            self.logo_label = ttk.Label(self.root, text="Logo Not Found", font=("Arial", 12, "italic"), foreground="red", pady=10)
            self.logo_label.pack()

    def create_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True, fill="both")

        # Create frames for each tab
        self.theory_tab = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.lab_tab = ttk.Frame(self.notebook, padding="10 10 10 10")

        self.notebook.add(self.theory_tab, text="Theory Data Operations")
        self.notebook.add(self.lab_tab, text="Lab Data Operations")

        self._populate_theory_tab()
        self._populate_lab_tab()

        # Add the Exit button outside the notebook
        ttk.Button(self.root, text="Exit", command=self.root.quit, style="Red.TButton").pack(pady=7, fill="x", padx=10) # Red Exit button


    def _populate_theory_tab(self):
        # Configure button style for a modern look with BLACK text
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10, "bold"), padding=7, relief="flat", background="#4CAF50", foreground="black") # Changed foreground to black
        style.map("TButton",
                  background=[('active', '#45a049')], # Darker green on hover
                  foreground=[('active', 'black')]) # Keep text black on hover

        ttk.Button(self.theory_tab, text="Import Theory Data", command=self.open_import_window).pack(pady=7, fill="x")
        ttk.Button(self.theory_tab, text="Double Entry", command=self.double_entry).pack(pady=7, fill="x")
        ttk.Button(self.theory_tab, text="Handle Mismatch Data", command=self.handle_mismatches).pack(pady=7, fill="x")
        ttk.Button(self.theory_tab, text="Search", command=self.search).pack(pady=7, fill="x")
        ttk.Button(self.theory_tab, text="Generate Summary", command=self.generate_summary).pack(pady=7, fill="x")
        ttk.Button(self.theory_tab, text="Export Data", command=self.export_data).pack(pady=7, fill="x")

    def _populate_lab_tab(self):
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10, "bold"), padding=7, relief="flat", background="#4CAF50", foreground="black") # Changed foreground to black
        style.map("TButton",
                  background=[('active', '#45a049')], # Darker green on hover
                  foreground=[('active', 'black')]) # Keep text black on hover

        ttk.Button(self.lab_tab, text="Import Lab Data", command=self.open_import_lab_window).pack(pady=7, fill="x")
        # Shared buttons for Lab Data
        ttk.Button(self.lab_tab, text="Double Entry", command=self.double_entry).pack(pady=7, fill="x")
        ttk.Button(self.lab_tab, text="Handle Mismatch Data", command=self.handle_mismatches).pack(pady=7, fill="x")
        ttk.Button(self.lab_tab, text="Search", command=self.search).pack(pady=7, fill="x")
        ttk.Button(self.lab_tab, text="Generate Summary", command=self.generate_summary).pack(pady=7, fill="x")
        ttk.Button(self.lab_tab, text="Export Data", command=self.export_data).pack(pady=7, fill="x")


    def browse_path(self, path_entry):
        selected_directory = filedialog.askdirectory()
        if selected_directory:
            self.directory_path.set(selected_directory)
            path_entry.delete(0, tk.END)
            path_entry.insert(0, selected_directory)


    def open_import_window(self):
        import_window = tk.Toplevel(self.root)
        import_window.title("Import Examination Data")
        #self.center_window(import_window)
        #self.center_window(450, 420) # Center the import window and slightly increase height

        # Logo in import window
        try:
            img = Image.open("Logo.jpg")
            img = img.resize((110, 110), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(import_window, image=logo)
            logo_label.image = logo
            logo_label.pack(pady=7)
        except FileNotFoundError:
            pass # Already handled in main window

        ttk.Label(import_window, text="Import Scanned Images", font=("Arial", 14, "bold")).pack(pady=10)

        # Frame for Exam Name
        exam_frame = ttk.Frame(import_window, padding="10 0 10 0")
        exam_frame.pack(pady=5, fill="x")
        ttk.Label(exam_frame, text="Examination Name:").pack(side="left", padx=5)
        exam_entry = ttk.Entry(exam_frame, textvariable=self.exam_name, width=30)
        exam_entry.pack(side="right", expand=True, fill="x", padx=5)

        # Frame for Directory Path
        path_frame = ttk.Frame(import_window, padding="10 0 10 0")
        path_frame.pack(pady=5, fill="x")
        ttk.Label(path_frame, text="Scanned Images Path:").pack(side="left", padx=5)
        path_entry = ttk.Entry(path_frame, textvariable=self.directory_path, width=40)
        path_entry.pack(side="left", expand=True, fill="x", padx=5)
        browse_button = ttk.Button(path_frame, text="Browse", command=lambda: self.browse_path(path_entry))
        browse_button.pack(side="right", padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(import_window, variable=self.progress_var, maximum=100, length=300, mode='determinate')
        self.progress_bar.pack(pady=(10,0)) # Adjusted padding

        # Progress text label (below progress bar)
        self.progress_text_label = ttk.Label(import_window, text="0 / 0 images processed", font=("Arial", 10))
        self.progress_text_label.pack(pady=(0,5))

        # Status label
        self.status_label = ttk.Label(import_window, text="Ready to process images...", font=("Arial", 10, "italic"))
        self.status_label.pack(pady=5)

        # Process button
        import_button = ttk.Button(import_window, text="Process Images", command=self.start_processing)
        import_button.pack(pady=15)
        self.center_window(import_window)

    def select_file(self,entry):
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        print("Selected file:", file)
        self.file_path.set(file) 
        entry.delete(0, tk.END)
        entry.insert(0, file)


    def open_import_lab_window(self):
        import_lab_window = tk.Toplevel(self.root)
        import_lab_window.title("Import Lab Data")
        #self.center_window(450, 420) # Center the import window and slightly increase height
        try:
            img = Image.open("Logo.jpg")
            img = img.resize((110, 110), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(import_lab_window, image=logo)
            logo_label.image = logo
            logo_label.pack(pady=7)
        except FileNotFoundError:
            pass # Already handled in main window

        ttk.Label(import_lab_window, text="Import Lab Data", font=("Arial", 14, "bold")).pack(pady=10)

        # Frame for Exam Name
        lab_frame = ttk.Frame(import_lab_window, padding="10 0 10 0")
        lab_frame.pack(pady=5, fill="x")
        ttk.Label(lab_frame, text="Examination Name:").pack(side="left", padx=5)
        lab_entry = ttk.Entry(lab_frame, textvariable=self.exam_name, width=30)
        lab_entry.pack(side="right", expand=True, fill="x", padx=5)

        # Frame for directory path
        path_frame = ttk.Frame(import_lab_window, padding="10 0 10 0")
        path_frame.pack(pady=5, fill="x")
        ttk.Label(path_frame, text="Scanned Images Path:").pack(side="left", padx=5)
        path_entry = ttk.Entry(path_frame, textvariable=self.directory_path, width=40)
        path_entry.pack(side="left", expand=True, fill="x", padx=5)
        browse_button = ttk.Button(path_frame, text="Browse", command=lambda: self.browse_path(path_entry))
        browse_button.pack(side="right", padx=5)

        # File name
        file_frame = ttk.Frame(import_lab_window, padding="10 0 10 0")
        file_frame.pack(pady=5, fill="x")
        ttk.Label(file_frame, text="Excel File (Lab):").pack(side="left", padx=5)
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path, width=40)
        file_entry.pack(side="left", expand=True, fill="x", padx=5)
        browse_button = ttk.Button(file_frame, text="Browse", command=lambda: self.select_file(file_entry))
        browse_button.pack(side="right", padx=5)


        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(import_lab_window, variable=self.progress_var, maximum=100, length=300, mode='determinate')
        self.progress_bar.pack(pady=(10,0)) # Adjusted padding

        # Progress text label (below progress bar)
        self.progress_text_label = ttk.Label(import_lab_window, text="0 / 0 images processed", font=("Arial", 10))
        self.progress_text_label.pack(pady=(0,5))

        # Status label
        self.status_label = ttk.Label(import_lab_window, text="Ready to process images...", font=("Arial", 10, "italic"))
        self.status_label.pack(pady=5)

        # Process button
        import_lab_button = ttk.Button(import_lab_window, text="Process Lab", command=self.start_processing_lab)
        import_lab_button.pack(pady=15)
        self.center_window(import_lab_window)


    def start_processing(self):
        exam_name = self.exam_name.get().strip()
        path = self.directory_path.get().strip()

        if not exam_name:
            messagebox.showerror("Input Error", "Please enter the Examination Name.")
            return
        if not path:
            messagebox.showerror("Input Error", "Please select the directory of scanned images.")
            return
        if not os.path.isdir(path):
            messagebox.showerror("Path Error", "The selected directory does not exist.")
            return

        db_name = exam_name.replace(" ", "_").lower()

        # Create database and tables
        create_database(db_name)
        create_tables(db_name)

        # Change directory if it doesn't exist
        original_dir = os.getcwd()
        if not os.path.isdir(db_name):
            os.mkdir(db_name)
        os.chdir(db_name)

        # Run processing in a separate thread to keep UI responsive
        self.status_label.config(text="Starting image processing...")
        # Pass the new progress_text_label to the threaded function
        processing_thread = threading.Thread(target=self._process_images_threaded, args=(path, db_name, original_dir))
        processing_thread.start()

    def start_processing_lab(self):
        lab_name = self.exam_name.get().strip()
        path = self.directory_path.get().strip()
        excelfile = self.file_path.get().strip()

        if not lab_name:
            messagebox.showerror("Input Error", "Please enter the Examination Name.")
            return
        if not path:
            messagebox.showerror("Input Error", "Please select the directory of scanned images.")
            return
        if not os.path.isdir(path):
            messagebox.showerror("Path Error", "The selected directory does not exist.")
            return
        if not excelfile:
            messagebox.showerror("Input Error", "Please select the Excel file.")
            return

        db_name = lab_name.replace(" ", "_").lower()

        # Create database and tables
        create_database(db_name)
        create_tables(db_name)

        # Change directory if it doesn't exist
        original_dir = os.getcwd()
        if not os.path.isdir(db_name):
            os.mkdir(db_name)
        os.chdir(db_name)
      
        # call process excel file function
        process_excel_and_insert(excelfile, db_name) 
        print("Excel file processed and next images to be processed")
      
        #Run processing in a separate thread to keep UI responsive
        self.status_label.config(text="Starting image processing...")
        # Pass the new progress_text_label to the threaded function
        processing_thread = threading.Thread(target=self._process_lab_omr_images_threaded, args=(path, db_name, original_dir))
        processing_thread.start()

    def _process_lab_omr_images_threaded(self, path, db_name, original_dir):
        try:
            # Pass all necessary UI update elements
            
            process_lab_omr_images_in_directory(path, db_name, self.progress_var, self.progress_text_label, self.status_label)
        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred during image processing: {e}")
        finally:
            os.chdir(original_dir) # Change back to original directory after processing

    def _process_images_threaded(self, path, db_name, original_dir):
        try:
            # Pass all necessary UI update elements
            process_images_in_directory_modular(path, db_name, self.progress_var, self.progress_text_label, self.status_label)
            #process_images_in_directory(path, db_name, self.progress_var, self.progress_text_label, self.status_label)
        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred during image processing: {e}")
        finally:
            os.chdir(original_dir) # Change back to original directory after processing

    def process_double_entry_data(self):
        exam_name = self.exam_name.get().strip()
        if not exam_name:
            messagebox.showerror("Input Error", "Please enter the Examination Name to proceed with Double Entry.")
            return

        db_name = exam_name.replace(" ", "_").lower()
        original_dir = os.getcwd()

        try:
            if not os.path.isdir(db_name):
                messagebox.showerror("Error", f"Database directory '{db_name}' not found. Please import data first.")
                return
            os.chdir(db_name)

            self.root.config(cursor="wait") # Change cursor to wait
            self.root.update_idletasks()

            check_and_correct_mismatches_in_scriptnumber(db_name)
            failed_bundle_info = fetch_failed_bundle_info(db_name)
            if failed_bundle_info:
                ManualDataEntryApp(self.root, failed_bundle_info, "control_bundle_info", db_name)
            failed_script_info = fetch_failed_script_info(db_name)
            if failed_script_info or failed_bundle_info:
                ManualDataEntryApp(self.root, failed_script_info, "script_info", db_name)
            else:
                messagebox.showinfo("Double Entry", "Double entry not required")
            # number_of_mismatches = identify_mismatch_control_bundle_info(db_name)
            # if number_of_mismatches >= 0:
            #     messagebox.showinfo("Double Entry", f"Double entry process completed. Number of Control Bundle mismatches identified: {number_of_mismatches}")
            # else:
            #     messagebox.showinfo("Double Entry", "Double entry process completed.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during double entry: {e}")
        finally:
            os.chdir(original_dir)
            self.root.config(cursor="") # Restore cursor

    def double_entry(self):
        select_double_entry_window = tk.Toplevel(self.root)
        select_double_entry_window.title("Double Entry Data")

        ttk.Label(select_double_entry_window, text="Enter Examination Name", font=("Arial", 12, "bold")).pack(pady=20)

        exam_frame = ttk.Frame(select_double_entry_window, padding="10 0 10 0")
        exam_frame.pack(pady=5, fill="x")
        ttk.Label(exam_frame, text="Examination Name:").pack(side="left", padx=5)
        ttk.Entry(exam_frame, textvariable=self.exam_name, width=30).pack(side="right", expand=True, fill="x", padx=5)

        start_button = ttk.Button(select_double_entry_window, text="Start Double Entry", command=self.process_double_entry_data)
        start_button.pack(pady=15)
        self.center_window(select_double_entry_window) # Center double entry window


    def process_export_data(self):
        exam_name = self.exam_name.get().strip()
        if not exam_name:
            messagebox.showerror("Input Error", "Please enter the Examination Name to proceed with Export.")
            return

        db_name = exam_name.replace(" ", "_").lower()
        original_dir = os.getcwd()

        try:
            if not os.path.isdir(db_name):
                messagebox.showerror("Error", f"Database directory '{db_name}' not found. Please import data first.")
                return
            os.chdir(db_name)

            self.root.config(cursor="wait")
            self.root.update_idletasks()

            check_and_correct_mismatches_in_scriptnumber(db_name)
            failed_bundle_info = fetch_failed_bundle_info(db_name)
            if failed_bundle_info:
            #display error message double entry needs to be done
                messagebox.showerror("Error", "Double entry needs to be done before exporting data. Please proceed with Double Entry.")    
            failed_script_info = fetch_failed_script_info(db_name)
            if failed_script_info:
            #display error message double entry needs to be done
                messagebox.showerror("Error", "Double entry needs to be done before exporting data. Please proceed with Double Entry.")
            
            if failed_bundle_info or failed_script_info:
                return
            
            number_bundle_mismatches = identify_mismatch_control_bundle_info(db_name)
            if number_bundle_mismatches > 0:
                messagebox.showerror("Error", f"Check Control Bundle mismatches in file missmatch_control_bundle_info.txt. Number of mismatches: {number_bundle_mismatches}")
                return

            export_data_from_database(db_name)
            messagebox.showinfo("Export Complete", "Data exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during data export: {e}")
        finally:
            os.chdir(original_dir)
            self.root.config(cursor="")

    def export_data(self):
        select_export_window = tk.Toplevel(self.root)
        select_export_window.title("Export Data")
        #self.center_window(400, 200)

        ttk.Label(select_export_window, text="Enter Examination Name", font=("Arial", 12, "bold")).pack(pady=20)

        exam_frame = ttk.Frame(select_export_window, padding="10 0 10 0")
        exam_frame.pack(pady=5, fill="x")
        ttk.Label(exam_frame, text="Examination Name:").pack(side="left", padx=5)
        ttk.Entry(exam_frame, textvariable=self.exam_name, width=30).pack(side="right", expand=True, fill="x", padx=5)

        start_button = ttk.Button(select_export_window, text="Start Export", command=self.process_export_data)
        start_button.pack(pady=15)
        self.center_window(select_export_window)

    def process_generate_summary(self):
        exam_name = self.exam_name.get().strip()
        if not exam_name:
            messagebox.showerror("Input Error", "Please enter the Examination Name to generate a summary.")
            return

        db_name = exam_name.replace(" ", "_").lower()
        original_dir = os.getcwd()

        try:
            if not os.path.isdir(db_name):
                messagebox.showerror("Error", f"Database directory '{db_name}' not found. Please import data first.")
                return
            os.chdir(db_name)

            self.root.config(cursor="wait")
            self.root.update_idletasks()
            check_and_correct_mismatches_in_scriptnumber(db_name)
            failed_bundle_info = fetch_failed_bundle_info(db_name)
            if failed_bundle_info:
                #display error message double entry needs to be done
                messagebox.showerror("Error", "Double entry needs to be done before generating summary.")
                
            failed_script_info = fetch_failed_script_info(db_name)
            if failed_script_info:
                #display error message double entry needs to be done
                messagebox.showerror("Error", "Double entry needs to be done before generating summary.")
                
            if failed_bundle_info or failed_script_info:
                return

            number_bundle_mismatches = identify_mismatch_control_bundle_info(db_name)
            if number_bundle_mismatches > 0:
                messagebox.showerror("Error", f"Check Control Bundle mismatches in file missmatch_control_bundle_info.txt. Number of mismatches: {number_bundle_mismatches}")
                return

            write_summary(db_name)
            messagebox.showinfo("Summary Generated", "Summary report generated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during summary generation: {e}")
        finally:
            os.chdir(original_dir)
            self.root.config(cursor="")

    def generate_summary(self):
        select_summary_window = tk.Toplevel(self.root)
        select_summary_window.title("Generate Summary")
        #self.center_window(select_summary_window)

        ttk.Label(select_summary_window, text="Enter Examination Name", font=("Arial", 12, "bold")).pack(pady=20)

        exam_frame = ttk.Frame(select_summary_window, padding="10 0 10 0")
        exam_frame.pack(pady=5, fill="x")
        ttk.Label(exam_frame, text="Examination Name:").pack(side="left", padx=5)
        ttk.Entry(exam_frame, textvariable=self.exam_name, width=30).pack(side="right", expand=True, fill="x", padx=5)

        start_button = ttk.Button(select_summary_window, text="Generate Summary", command=self.process_generate_summary)
        start_button.pack(pady=15)
        self.center_window(select_summary_window)

    def double_entry(self):
        select_double_entry_window = tk.Toplevel(self.root)
        select_double_entry_window.title("Double Entry Data")
        #self.center_window(select_double_entry_window) # Center double entry window

        ttk.Label(select_double_entry_window, text="Enter Examination Name", font=("Arial", 12, "bold")).pack(pady=20)

        exam_frame = ttk.Frame(select_double_entry_window, padding="10 0 10 0")
        exam_frame.pack(pady=5, fill="x")
        ttk.Label(exam_frame, text="Examination Name:").pack(side="left", padx=5)
        ttk.Entry(exam_frame, textvariable=self.exam_name, width=30).pack(side="right", expand=True, fill="x", padx=5)

        start_button = ttk.Button(select_double_entry_window, text="Start Double Entry", command=self.process_double_entry_data)
        start_button.pack(pady=15)
        self.center_window(select_double_entry_window)

    def search(self):
        select_window = tk.Toplevel(self.root)
        select_window.title("Search Data")
        #self.center_window(select_window) # Center double entry window

        ttk.Label(select_window, text="Enter Examination Name", font=("Arial", 12, "bold")).pack(pady=20)

        exam_frame = ttk.Frame(select_window, padding="10 0 10 0")
        exam_frame.pack(pady=5, fill="x")
        ttk.Label(exam_frame, text="Examination Name:").pack(side="left", padx=5)
        ttk.Entry(exam_frame, textvariable=self.exam_name, width=30).pack(side="right", expand=True, fill="x", padx=5)

        start_button = ttk.Button(select_window, text="Search", command=self.process_search_data)
        start_button.pack(pady=15)
        self.center_window(select_window)
    
    def process_search_data(self):
        exam_name = self.exam_name.get().strip()
        if not exam_name:
            messagebox.showerror("Input Error", "Please enter the Examination Name to search.")
            return

        db_name = exam_name.replace(" ", "_").lower()
        original_dir = os.getcwd()

        try:
            if not os.path.isdir(db_name):
                messagebox.showerror("Error", f"Database directory '{db_name}' not found. Please import data first.")
                return
            os.chdir(db_name)

            self.root.config(cursor="wait")
            self.root.update_idletasks()
            ImageSearchApp(self.root, db_name)
            #search_data(db_name)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during search: {e}")
        finally:
            os.chdir(original_dir)
            self.root.config(cursor="")

    def handle_mismatches(self):
        select_window = tk.Toplevel(self.root)
        select_window.title("handle Mismatch Data")
        #self.center_window(select_window) # Center double entry window

        ttk.Label(select_window, text="Enter Examination Name", font=("Arial", 12, "bold")).pack(pady=20)

        exam_frame = ttk.Frame(select_window, padding="10 0 10 0")
        exam_frame.pack(pady=5, fill="x")
        ttk.Label(exam_frame, text="Examination Name:").pack(side="left", padx=5)
        ttk.Entry(exam_frame, textvariable=self.exam_name, width=30).pack(side="right", expand=True, fill="x", padx=5)

        start_button = ttk.Button(select_window, text="handle mismatches", command=self.process_mismatch_data)
        start_button.pack(pady=15)
        self.center_window(select_window)
    
    def process_mismatch_data(self):
        exam_name = self.exam_name.get().strip()
        if not exam_name:
            messagebox.showerror("Input Error", "Please enter the Examination Name to handle mismatches.")
            return

        db_name = exam_name.replace(" ", "_").lower()
        original_dir = os.getcwd()

        try:
            if not os.path.isdir(db_name):
                messagebox.showerror("Error", f"Database directory '{db_name}' not found. Please import data first.")
                return
            os.chdir(db_name)

            self.root.config(cursor="wait")
            self.root.update_idletasks()

            check_and_correct_mismatches_in_scriptnumber(db_name)
            failed_bundle_info = fetch_failed_bundle_info(db_name)
            if failed_bundle_info:
                #display error message double entry needs to be done
                messagebox.showerror("Error", "Double entry needs to be done before generating summary.")
                
            failed_script_info = fetch_failed_script_info(db_name)
            if failed_script_info:
                #display error message double entry needs to be done
                messagebox.showerror("Error", "Double entry needs to be done before generating summary.")
                
            if failed_bundle_info or failed_script_info:
                return

            number_bundle_mismatches = identify_mismatch_control_bundle_info(db_name)
            if number_bundle_mismatches > 0:
                MismatchViewer(self.root, db_name)
            else:
                messagebox.showinfo("Mismatches", "No mismatches other than ignored.")
            #search_data(db_name)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during search: {e}")
        finally:
            os.chdir(original_dir)
            self.root.config(cursor="")
        


class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.style = ttk.Style()
        self.configure_styles()

    def configure_styles(self):
        # General button style with black text
        self.style.configure("TButton",
                             font=("Helvetica", 10, "bold"),
                             padding=8,
                             relief="flat",
                             background="#4CAF50", # Default green
                             foreground="black") # Changed foreground to black
        self.style.map("TButton",
                       background=[('active', '#45a049')], # Darker green on hover
                       foreground=[('active', 'black')]) # Keep text black on hover

        # Specific style for the "Exit" button with black text
        self.style.configure("Red.TButton",
                             background="#f44336", # Red
                             foreground="black") # Changed foreground to black
        self.style.map("Red.TButton",
                       background=[('active', '#da190b')], # Darker red on hover
                       foreground=[('active', 'black')]) # Keep text black on hover

        self.style.configure("TCombobox",
                             font=("Helvetica", 12),
                             padding=5,
                             width=25)

        # Style for Labels and Entry fields in sub-windows
        self.style.configure("TLabel", font=("Arial", 11))
        self.style.configure("TEntry", font=("Arial", 11))

        # Style for the Notebook tabs
        self.style.configure("TNotebook", background="#f0f0f0") # Background of the notebook itself
        self.style.configure("TNotebook.Tab",
                             font=("Arial", 10, "bold"),
                             padding=[10, 5],
                             background="#dcdcdc", # Default tab background
                             foreground="black")
        self.style.map("TNotebook.Tab",
                       background=[('selected', '#e0e0e0'), ('active', '#c0c0c0')], # Selected/active tab background
                       foreground=[('selected', 'black'), ('active', 'black')])


    def run(self):
        MainWindow(self.root)
        self.root.mainloop()

if __name__ == "__main__":
    app = Application()
    app.run()