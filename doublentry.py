import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import copy
import random
from storedata import insert_verified_data_to_db

class ManualDataEntryApp:
    def __init__(self, master, failed_cases_data, omr_type,db_name):
        self.master = tk.Toplevel(master)
        self.db_name = db_name
        self.master.title(f"Manual Data Entry - {omr_type.replace('_', ' ').title()}")
        self.omr_type = omr_type

        #self.original_failed_cases_data = failed_cases_data

        self.original_failed_cases_data = []
        for i, case_data in enumerate(failed_cases_data):
            case_copy = copy.deepcopy(case_data) # Create a deep copy to avoid modifying external data
            case_copy['_original_index'] = i
            self.original_failed_cases_data.append(case_copy)
        
        # This will hold the cases currently being processed (initial passes or discrepancy resolution passes)
        self.current_processing_cases = []
        self.all_cases_for_entry = [] # This will hold the _unique_id of all cases to be processed in the current phase

        self.current_case_index = 0
        self.entered_data_storage = {} # Stores all submitted data, keyed by _unique_id

        self.is_resolving_discrepancies = False # Flag to indicate if we are in discrepancy resolution mode

        self.create_widgets()
        self._start_initial_entry_phase() # Start the first phase of entry

        self.master.bind('<Right>', lambda event: self.submit_and_next())
        self.master.bind('<Left>', lambda event: self.load_previous_case())
        self.master.bind('<Return>', lambda event: self.submit_and_next())

    def _prepare_cases_for_double_entry(self, cases, is_discrepancy_resolution=False):
        """
        Duplicates each case for a double-entry pass and adds metadata.
        Can be used for initial entry or discrepancy resolution.
        """
        prepared_cases = []
        for i, case in enumerate(cases):
            original_index = case.get('_original_index', i) # Use existing original_index for discrepancy cases
            
            # First pass
            first_pass_case = copy.deepcopy(case)
            first_pass_case['_entry_pass'] = 1
            first_pass_case['_original_index'] = original_index
            first_pass_case['_unique_id'] = f"orig_{original_index}_pass_1_{'res' if is_discrepancy_resolution else 'initial'}"
            first_pass_case['_is_discrepancy_resolution'] = is_discrepancy_resolution
            prepared_cases.append(first_pass_case)

            # Second pass
            second_pass_case = copy.deepcopy(case)
            second_pass_case['_entry_pass'] = 2
            second_pass_case['_original_index'] = original_index
            second_pass_case['_unique_id'] = f"orig_{original_index}_pass_2_{'res' if is_discrepancy_resolution else 'initial'}"
            second_pass_case['_is_discrepancy_resolution'] = is_discrepancy_resolution
            prepared_cases.append(second_pass_case)
        return prepared_cases

    def _start_initial_entry_phase(self):
        """Prepares and starts the initial double-entry phase for all failed cases."""
        self.is_resolving_discrepancies = False
        self.current_processing_cases = self._prepare_cases_for_double_entry(self.original_failed_cases_data)
        random.shuffle(self.current_processing_cases) # Shuffle the list of cases to process
        
        # Reset current case index and data storage relevant to this phase
        self.current_case_index = 0
        # self.entered_data_storage will accumulate data from all phases

        # Load the first case of the current phase
        self.load_current_case()

    def _start_discrepancy_resolution_phase(self, discrepancy_cases_data):
        """Prepares and starts the discrepancy resolution phase."""

        self.is_resolving_discrepancies = True
        print("\nDEBUG: Discrepancy Resolution Phase Starting.")
        print(f"DEBUG: Input discrepancy_cases_data (first 2 cases): {discrepancy_cases_data[:2]}")
        # Verify the original_index and image_path in these input cases
        for i, case_item in enumerate(discrepancy_cases_data):
            print(f"DEBUG: discrepancy_cases_data[{i}] original_index: {case_item.get('_original_index')}, image_path: {case_item.get('image_path')}")
            if i >= 1: break # Just print first few to avoid too much output

        self.current_processing_cases = self._prepare_cases_for_double_entry(discrepancy_cases_data, is_discrepancy_resolution=True)
        random.shuffle(self.current_processing_cases) # Shuffle discrepancy cases for resolution
        
        print(f"DEBUG: current_processing_cases after preparation (first 2 entries):")
        for i, proc_case in enumerate(self.current_processing_cases[:4]): # Show more as there are 2 passes per case
            print(f"  Entry {i}: unique_id={proc_case['_unique_id']}, original_index={proc_case['_original_index']}, entry_pass={proc_case['_entry_pass']}, image_path={proc_case.get('image_path')}")
        # Reset current case index for the new phase

        # Reset current case index for the new phase
        self.current_case_index = 0
        # entered_data_storage will already contain previous entries, which is fine
        # We need to make sure new entries for resolved discrepancies overwrite previous ones
        messagebox.showinfo("Discrepancy Resolution", f"Starting Discrepancy Resolution for {len(discrepancy_cases_data)} cases.")
        self.load_current_case()


    def create_widgets(self):
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

        # --- Image Display Frame ---
        self.image_frame = tk.Frame(self.master, bd=2, relief=tk.GROOVE)
        self.image_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.image_frame.grid_rowconfigure(0, weight=1)
        self.image_frame.grid_columnconfigure(0, weight=1)

        self.image_label = tk.Label(self.image_frame)
        self.image_label.grid(row=0, column=0, sticky="nsew")

        # --- Data Entry Frame ---
        self.data_entry_frame = tk.Frame(self.master, bd=2, relief=tk.GROOVE)
        self.data_entry_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.data_entry_frame.grid_columnconfigure(0, weight=1)
        self.data_entry_frame.grid_columnconfigure(1, weight=1)

        # Status Labels
        tk.Label(self.data_entry_frame, text="Case Progress:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=5, sticky="w")
        self.case_counter_label = tk.Label(self.data_entry_frame, text="", font=("Arial", 10))
        self.case_counter_label.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")

        tk.Label(self.data_entry_frame, text="Entry Pass:", font=("Arial", 10, "bold")).grid(row=2, column=0, columnspan=2, pady=5, sticky="w")
        self.entry_pass_label = tk.Label(self.data_entry_frame, text="", font=("Arial", 10, "italic"), fg="blue")
        self.entry_pass_label.grid(row=3, column=0, columnspan=2, pady=5, sticky="w")

        # Dynamic phase indicator
        self.phase_indicator_label = tk.Label(self.data_entry_frame, text="Initial Entry Phase", font=("Arial", 12, "underline"), fg="purple")
        self.phase_indicator_label.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")

        # Fields based on OMR type
        self.fields = {}
        field_configs = []
        if self.omr_type == "control_bundle_info":
            field_configs = [
                {"label": "Bundle Number:", "key": "bundle_number"},
                {"label": "Number of Scripts:", "key": "number_of_scripts"},
                {"label": "Grand Total Marks:", "key": "grand_total_marks"}
            ]
        elif self.omr_type == "script_info":
            field_configs = [
                {"label": "Barcode:", "key": "barcode"},
                {"label": "Bundle Number:", "key": "bundle_number"},
                {"label": "Marks:", "key": "marks"},         # Marks first
                {"label": "Script Number:", "key": "script_number"} # Then Script Number
            ]
        else:
            raise ValueError("Invalid OMR type specified. Use 'control_bundle_info' or 'script_info'.")

        self.field_keys = [config["key"] for config in field_configs]
        self.entry_widgets_order = []
        for i, config in enumerate(field_configs):
            tk.Label(self.data_entry_frame, text=config["label"], font=("Arial", 10)).grid(row=i + 5, column=0, sticky=tk.W, padx=5, pady=2) # Adjusted row for new label
            entry = tk.Entry(self.data_entry_frame, width=30, font=("Arial", 10))
            entry.grid(row=i + 5, column=1, sticky="ew", padx=5, pady=2)
            self.fields[config["key"]] = entry
            self.entry_widgets_order.append(entry)

        # Navigation Buttons
        self.button_frame = tk.Frame(self.data_entry_frame)
        self.button_frame.grid(row=len(field_configs) + 5, column=0, columnspan=2, pady=10, sticky="ew")
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_columnconfigure(2, weight=1)

        self.prev_button = tk.Button(self.button_frame, text="< Previous (←)", command=self.load_previous_case, font=("Arial", 10))
        self.prev_button.grid(row=0, column=0, padx=5, sticky="e")

        self.submit_button = tk.Button(self.button_frame, text="Submit & Next (→ / Enter)", command=self.submit_and_next, font=("Arial", 10, "bold"))
        self.submit_button.grid(row=0, column=1, padx=15, sticky="ew")

        self.finish_button = tk.Button(self.button_frame, text="Finish Current Phase", command=self.finish_current_phase, font=("Arial", 10))
        self.finish_button.grid(row=0, column=2, padx=5, sticky="w")


    def load_current_case(self):
        if not self.current_processing_cases:
            messagebox.showinfo("No Cases", "No cases left to process in this phase.")
            self.master.destroy()
            return

        if self.current_case_index < 0:
            self.current_case_index = 0
        elif self.current_case_index >= len(self.current_processing_cases):
            self.current_case_index = len(self.current_processing_cases) - 1



        case_metadata = self.current_processing_cases[self.current_case_index]

        print(f"\nDEBUG: load_current_case called. Current index: {self.current_case_index}")
        print(f"DEBUG: case_metadata from current_processing_cases:")
        print(f"  _unique_id: {case_metadata.get('_unique_id')}")
        print(f"  _original_index: {case_metadata.get('_original_index')}")
        print(f"  _entry_pass: {case_metadata.get('_entry_pass')}")
        print(f"  _is_discrepancy_resolution: {case_metadata.get('_is_discrepancy_resolution')}")
        # Optionally, print the image_path directly from case_metadata here too
        print(f"  image_path (from case_metadata): {case_metadata.get('image_path', 'N/A')}")

        original_case_from_db = self.original_failed_cases_data[case_metadata['_original_index']]
        print(f"DEBUG: original_case_from_db fetched for original_index {case_metadata['_original_index']}:")
        print(f"  image_path (from original_failed_cases_data): {original_case_from_db.get('image_path', 'N/A')}")

        # Update phase indicator label
        if self.is_resolving_discrepancies:
            self.phase_indicator_label.config(text="Discrepancy Resolution Phase", fg="red")
        else:
            self.phase_indicator_label.config(text="Initial Entry Phase", fg="purple")

        self.case_counter_label.config(text=f"Original Case #{case_metadata['_original_index'] + 1} ({self.current_case_index + 1} / {len(self.current_processing_cases)})")
        self.entry_pass_label.config(text=f"Pass {case_metadata['_entry_pass']}  {case_metadata.get('image_path', 'N/A')}")

        for field in self.fields.values():
            field.delete(0, tk.END)

        original_case_from_db = self.original_failed_cases_data[case_metadata['_original_index']]
        
        first_empty_field_found = False
        for key, entry_widget in self.fields.items():
            value_to_prepopulate = None

            if self.is_resolving_discrepancies:
                # In discrepancy resolution, try to show the previous conflicting entries
                prev_pass1_id = f"orig_{case_metadata['_original_index']}_pass_1_initial"
                prev_pass2_id = f"orig_{case_metadata['_original_index']}_pass_2_initial"

                prev_pass1_data = self.entered_data_storage.get(prev_pass1_id)
                prev_pass2_data = self.entered_data_storage.get(prev_pass2_id)

                value_from_db = str(original_case_from_db.get(key))
                # Prioritize showing the actual previous entries for the discrepant field
                if prev_pass1_data and prev_pass2_data and prev_pass1_data.get(key) != prev_pass2_data.get(key):
                    # Show previous conflicting values, e.g., "P1: [val1] | P2: [val2]"
                   # value_to_prepopulate = f"P1: {prev_pass1_data.get(key, '')} | P2: {prev_pass2_data.get(key, '')}"
                    value_to_prepopulate = ""
                elif value_from_db not in ["-1", None, ""]:
                    # If not a discrepant field, but original data was good, show original
                    value_to_prepopulate = value_from_db
                else:
                    # Otherwise, it's a field that needs fresh input
                    value_to_prepopulate = "" # Show empty box
            else:
                # Initial entry phase: Pre-populate only good data from DB, otherwise empty
                value_from_db =str(original_case_from_db.get(key))
                if value_from_db is not None and value_from_db != "-1" and value_from_db != "":
                    value_to_prepopulate = value_from_db
                else:
                    value_to_prepopulate = "" # Show empty box

            # Insert the determined value
            entry_widget.insert(0, value_to_prepopulate)
            
            # Set focus to the first empty field or the first field if all are pre-filled
            if not first_empty_field_found and value_to_prepopulate == "":
                 entry_widget.focus_set()
                 first_empty_field_found = True

        if not first_empty_field_found and self.entry_widgets_order:
            self.entry_widgets_order[0].focus_set()

        #image_path = case_metadata['image_path']
        image_path = original_case_from_db.get('image_path')

        print(f"DEBUG: Attempting to load image from: {image_path}")

        if os.path.exists(image_path):
            img = Image.open(image_path)
            # Resize image to fit, maintaining aspect ratio based on frame size
            # Use a default reasonable size if frame not yet rendered
            max_width = self.image_frame.winfo_width() if self.image_frame.winfo_width() > 10 else 700
            max_height = self.image_frame.winfo_height() if self.image_frame.winfo_height() > 10 else 900
            
            img.thumbnail((max_width, max_height), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.photo)
        else:
            self.image_label.config(text="Image not found", image="")
            messagebox.showerror("Image Error", f"Image not found: {image_path}")

    def validate_and_get_input(self):
        input_data = {}
        for key, entry_widget in self.fields.items():
            value = entry_widget.get().strip()
            # If in discrepancy resolution, and the field was showing "P1: ... | P2: ...",
            # the user MUST change it. If it still contains "P1:", it means they didn't input.
            if self.is_resolving_discrepancies and value.startswith("P1:"):
                messagebox.showwarning("Incomplete Resolution", f"Please enter a new value for '{key.replace('_', ' ').title()}'. It still shows the conflicting previous entries.")
                return None
            if not value: # This check applies to both phases
                messagebox.showwarning("Incomplete Input", f"Please fill in all fields. '{key.replace('_', ' ').title()}' is empty.")
                return None
            input_data[key] = value
        return input_data

    def submit_and_next(self):
        input_data = self.validate_and_get_input()
        if input_data is not None:
            current_case_metadata = self.current_processing_cases[self.current_case_index]
            self.entered_data_storage[current_case_metadata['_unique_id']] = input_data

            if self.current_case_index < len(self.current_processing_cases) - 1:
                self.current_case_index += 1
                self.load_current_case()
            else:
                self.finish_current_phase() # All cases in current phase processed

    def load_previous_case(self):
        if self.current_case_index > 0:
            input_data = self.validate_and_get_input()
            if input_data is not None:
                current_case_metadata = self.current_processing_cases[self.current_case_index]
                self.entered_data_storage[current_case_metadata['_unique_id']] = input_data

            self.current_case_index -= 1
            self.load_current_case()
        else:
            messagebox.showinfo("Navigation", "This is the first case in the current phase. Cannot go back further.")

    def finish_current_phase(self):
        # Ensure the current case's data is saved if it was the last one and submitted
        input_data = self.validate_and_get_input()
        if input_data is not None:
            current_case_metadata = self.current_processing_cases[self.current_case_index]
            self.entered_data_storage[current_case_metadata['_unique_id']] = input_data
        
        # Collect all submitted entries for comparison, filtering by the current phase's unique IDs
        all_submitted_entries_for_comparison = []
        for case_metadata in self.current_processing_cases: # Only consider cases from the current phase
            unique_id = case_metadata['_unique_id']
            if unique_id in self.entered_data_storage:
                combined_entry = {**case_metadata, **self.entered_data_storage[unique_id]}
                all_submitted_entries_for_comparison.append(combined_entry)

        if not all_submitted_entries_for_comparison:
            messagebox.showinfo("Phase Complete", "No data was entered in this phase for comparison.")
            self.master.destroy()
            return

        comparison_results = self._compare_double_entries(all_submitted_entries_for_comparison, self.is_resolving_discrepancies)

        if comparison_results['verified_data']:
            insert_verified_data_to_db(self.db_name, comparison_results['verified_data'], self.omr_type)

        if comparison_results['discrepancies']:
            discrepancy_details = "\n".join([
                f"Original Case #{d['original_index'] + 1}, Field: {d['field']}\n  Pass 1: '{d['value1']}'\n  Pass 2: '{d['value2']}'"
                for d in comparison_results['discrepancies']
            ])
            messagebox.showwarning("Discrepancies Found!",
                                   f"Discrepancies detected in {len(comparison_results['discrepancies'])} fields across {len(comparison_results['discrepancies'])} cases.\n\nDetails:\n{discrepancy_details}\n\n**Please resolve these discrepancies.**")
            
            # Start a new phase for discrepancy resolution
            discrepancy_cases_for_re_entry = [
                self.original_failed_cases_data[idx] for idx in comparison_results['discrepancy_cases_original_indices']
            ]
            self._start_discrepancy_resolution_phase(discrepancy_cases_for_re_entry)
            
            print("\n--- Discrepancy Details (Requiring Re-entry) ---")
            for d in comparison_results['discrepancies']:
                print(d)

        else:
            if self.is_resolving_discrepancies:
                messagebox.showinfo("Resolution Complete", "All discrepancies have been successfully resolved! Data is consistent.")
            else:
                messagebox.showinfo("Initial Entry Complete", "No discrepancies found in initial entries! Data is consistent.")

            # print("\n--- Final Verified Data ---")
            # for data in comparison_results['verified_data']:
            #     print(data)
                
            #insert_verified_data_to_db(self.db_name, comparison_results['verified_data'], self.omr_type)

            self.master.destroy() # Close the GUI after all phases are complete


    def _compare_double_entries(self, entries_from_current_phase, is_resolution_phase=False):
        """
        Compares the data from the first and second entry passes for each original case.
        Returns a dictionary with verified data and discrepancies.
        `entries_from_current_phase` should only contain entries processed in the current phase.
        """
        verified_data = []
        discrepancies = []
        # Stores original_index of cases that have discrepancies in THIS comparison
        discrepancy_cases_original_indices = set() 

        # Group entries by their original case index
        grouped_entries = {} # Key: original_index, Value: [pass1_data_dict, pass2_data_dict]
        for entry in entries_from_current_phase:
            original_idx = entry['_original_index']
            # Crucial: Ensure we're grouping based on the correct pass type (initial vs. resolution)
            unique_id_base = f"orig_{original_idx}_pass_{entry['_entry_pass']}_"
            
            # Find the corresponding entry in the global storage
            # This is complex because a previous pass for the same original_idx might exist from initial entry
            # So, we need to check if the current entry's unique_id matches the one in storage for the current phase
            if is_resolution_phase:
                # In resolution phase, we group the resolution pass entries
                pass_suffix = f"res"
            else:
                # In initial phase, we group the initial pass entries
                pass_suffix = f"initial"

            pass_unique_id = f"orig_{original_idx}_pass_{entry['_entry_pass']}_{pass_suffix}"
            
            # Check if this pass was actually submitted in this current phase
            if self.entered_data_storage.get(pass_unique_id):
                if original_idx not in grouped_entries:
                    grouped_entries[original_idx] = [None, None]
                grouped_entries[original_idx][entry['_entry_pass'] - 1] = self.entered_data_storage[pass_unique_id]


        for original_idx in sorted(grouped_entries.keys()):
            pass1_data_from_this_phase, pass2_data_from_this_phase = grouped_entries[original_idx]

            if pass1_data_from_this_phase is None or pass2_data_from_this_phase is None:
                # This should ideally not happen if all cases in `current_processing_cases` were submitted,
                # but adding a safeguard.
                print(f"Warning: Only one pass found for original case index {original_idx} in current phase. Cannot compare.")
                discrepancies.append({
                    'original_index': original_idx,
                    'field': 'N/A',
                    'value1': 'Missing Pass 1' if pass1_data_from_this_phase is None else 'Present',
                    'value2': 'Missing Pass 2' if pass2_data_from_this_phase is None else 'Present',
                    'note': 'One entry pass was not completed for this case in the current phase.'
                })
                discrepancy_cases_original_indices.add(original_idx)
                continue

            case_has_discrepancy = False
            verified_case_data = {
                'image_path': self.original_failed_cases_data[original_idx]['image_path'],
                '_original_index': original_idx,
                'batchcode': self.original_failed_cases_data[original_idx]['batchcode']
            }

            for key in self.field_keys:
                value1 = pass1_data_from_this_phase.get(key)
                value2 = pass2_data_from_this_phase.get(key)

                if value1 != value2:
                    print(f"DEBUG: Discrepancy detected! Original Index: {original_idx}, Field: {key}")
                    print(f"DEBUG: Pass 1 Value: '{value1}', Pass 2 Value: '{value2}'")
                    print(f"DEBUG: Original case image path for this index: {self.original_failed_cases_data[original_idx].get('image_path', 'N/A')}")
                    discrepancies.append({
                        'original_index': original_idx,
                        'field': key,
                        'value1': value1,
                        'value2': value2
                    })
                    case_has_discrepancy = True
                    if original_idx not in discrepancy_cases_original_indices:
                        discrepancy_cases_original_indices.add(original_idx)
                
                # If they match, this is the verified value. If they don't, this value is currently discrepant.
                verified_case_data[key] = value1 

            if not case_has_discrepancy:
                verified_data.append(verified_case_data)
            
        return {
            'verified_data': verified_data,
            'discrepancies': discrepancies,
            'discrepancy_cases_original_indices': list(discrepancy_cases_original_indices) # List of original indices with discrepancies
        }



