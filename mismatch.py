import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
import os
import psycopg2
from configparser import ConfigParser 
from connection import connect_to_db


class MismatchViewer:
    def __init__(self, master, db_name):
        self.master = tk.Toplevel(master)
        self.master.title("Mismatched Control Bundle Info")
        self.master.geometry("1200x650")

        # Configure master grid - FIXED: Proper weight distribution
        self.master.grid_rowconfigure(0, weight=1)  # Tree area expands
        self.master.grid_rowconfigure(1, weight=0)  # Button area fixed height
        self.master.grid_columnconfigure(0, weight=1)

        self.db_name = db_name

        # Store internal state of 'ignore' checkboxes for Treeview
        # Format: {image_path: Boolean (True/False)}
        self.ignore_states = {}

        self.create_widgets()
        self.load_mismatched_data()

    def create_widgets(self):
        # Frame to hold Treeview and scrollbars - FIXED: Removed border for cleaner look
        tree_frame = tk.Frame(self.master)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))
        
        # Configure the grid within tree_frame
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Define Treeview columns
        self.columns = (
            "Bundle Number", "Scripts (Bundle)", "Scripts (Actual)",
            "Marks (Bundle)", "Marks (Actual)", "Batch Code", "Image Path", "Ignore"
        )
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings")

        # Configure column headings and properties
        self.tree.heading("Bundle Number", text="Bundle Number", anchor=tk.W)
        self.tree.heading("Scripts (Bundle)", text="Scripts (Bundle)", anchor=tk.E)
        self.tree.heading("Scripts (Actual)", text="Scripts (Actual)", anchor=tk.E)
        self.tree.heading("Marks (Bundle)", text="Marks (Bundle)", anchor=tk.E)
        self.tree.heading("Marks (Actual)", text="Marks (Actual)", anchor=tk.E)
        self.tree.heading("Batch Code", text="Batch Code", anchor=tk.W)
        self.tree.heading("Image Path", text="Image Path", anchor=tk.W)
        self.tree.heading("Ignore", text="Ignore", anchor=tk.CENTER)

        # Configure column widths
        self.tree.column("Bundle Number", width=100, minwidth=80, stretch=tk.NO)
        self.tree.column("Scripts (Bundle)", width=100, minwidth=80, stretch=tk.NO)
        self.tree.column("Scripts (Actual)", width=100, minwidth=80, stretch=tk.NO)
        self.tree.column("Marks (Bundle)", width=100, minwidth=80, stretch=tk.NO)
        self.tree.column("Marks (Actual)", width=100, minwidth=80, stretch=tk.NO)
        self.tree.column("Batch Code", width=100, minwidth=80, stretch=tk.NO)
        self.tree.column("Image Path", width=350, minwidth=200, stretch=tk.YES)
        self.tree.column("Ignore", width=70, minwidth=60, stretch=tk.NO, anchor=tk.CENTER)

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=hsb.set)

        # Bind click event for the "Ignore" column
        self.tree.bind("<Button-1>", self._on_tree_click)

        # FIXED: Save Changes Button with better positioning and visibility
        button_frame = tk.Frame(self.master)
        button_frame.grid(row=1, column=0, sticky="ew", padx=6, pady=(10, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        
        save_button = tk.Button(button_frame, text="Save Changes", command=self.save_ignore_status, 
                                bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                                height=2, relief="raised", bd=2)
        save_button.grid(row=0, column=0, sticky="ew")

    def load_mismatched_data(self):
        conn = None
        try:
            conn = connect_to_db(self.db_name)
            if not conn:
                return

            cur = conn.cursor()
            cur.execute("SELECT * FROM mismatchcontrolbundleinfo ORDER BY bundle_number, image_path;")
            
            # Clear existing data in Treeview
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.ignore_states = {}

            # Fetch data and insert into Treeview
            for row_data in cur.fetchall():
                # Assuming the order from DB query: 
                # image_path, bundle_number, scripts_bundle, actual_scripts, marks_bundle, actual_marks, batchcode, ignore_status
                image_path = row_data[0]
                bundle_number = row_data[1]
                scripts_bundle = row_data[2]
                actual_scripts = row_data[3]
                marks_bundle = row_data[4]
                actual_marks = row_data[5]
                batchcode = row_data[6]
                ignore_status = row_data[7]

                # Store the initial ignore status
                self.ignore_states[image_path] = ignore_status

                # Prepare values for Treeview insertion using unicode checkbox characters
                checkbox_char = u"\u2611" if ignore_status else u"\u2610"

                values = (
                    bundle_number,
                    scripts_bundle,
                    actual_scripts,
                    marks_bundle,
                    actual_marks,
                    batchcode,
                    image_path,
                    checkbox_char 
                )
                
                # Insert row into Treeview, using image_path as item ID for easy lookup
                self.tree.insert("", "end", iid=image_path, values=values)
                
                # Apply alternating row colors for readability
                if self.tree.index(image_path) % 2 == 0:
                    self.tree.item(image_path, tags=('evenrow',))
                else:
                    self.tree.item(image_path, tags=('oddrow',))
            
            # Configure row tags for alternating colors
            self.tree.tag_configure('evenrow', background='#E8E8E8')
            self.tree.tag_configure('oddrow', background='#F8F8F8')

        except (Exception, psycopg2.Error) as error:
            messagebox.showerror("Database Error", f"Error loading mismatched data:\n{error}")
        finally:
            if conn:
                cur.close()
                conn.close()

    def _on_tree_click(self, event):
        """
        Handles clicks within the Treeview, specifically for the 'Ignore' column.
        Toggles the internal state of the checkbox and updates the Treeview display.
        """
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item_id = self.tree.identify_row(event.y)

            # Check if the click is on the 'Ignore' column (last column)
            if self.tree.column(column, option="id") == "Ignore":
                if item_id:
                    current_values = self.tree.item(item_id, "values")
                    image_path = item_id

                    # Get the current internal ignore status
                    current_status = self.ignore_states.get(image_path)
                    
                    # Toggle the status
                    new_status = not current_status
                    self.ignore_states[image_path] = new_status

                    # Update the checkbox character in the Treeview display
                    checkbox_char = u"\u2611" if new_status else u"\u2610"
                    
                    # Create a mutable list from current_values tuple and update the 'Ignore' column
                    mutable_values = list(current_values)
                    mutable_values[len(self.columns) - 1] = checkbox_char
                    
                    self.tree.item(item_id, values=mutable_values)

    def save_ignore_status(self):
        """
        Saves all current 'ignore' checkbox statuses from self.ignore_states to the database.
        This is called by the "Save Changes" button.
        """
        conn = None
        try:
            conn = connect_to_db(self.db_name)
            if not conn:
                return

            cur = conn.cursor()
            updates_made = False
            for image_path, new_ignore_status in self.ignore_states.items():
                # Fetch the original status from the database to avoid unnecessary updates
                cur.execute("SELECT ignore FROM mismatchcontrolbundleinfo WHERE image_path = %s;", (image_path,))
                db_result = cur.fetchone()
                
                if db_result is None:
                    print(f"Warning: Image path '{image_path}' not found in database for update.")
                    continue
                
                db_ignore_status = db_result[0]
                
                if db_ignore_status != new_ignore_status:
                    cur.execute("UPDATE mismatchcontrolbundleinfo SET ignore = %s WHERE image_path = %s;",
                                (new_ignore_status, image_path))
                    updates_made = True
            
            if updates_made:
                conn.commit()
                messagebox.showinfo("Success", "Ignore statuses updated successfully!")
            else:
                messagebox.showinfo("No Changes", "No changes were made to save.")

        except (Exception, psycopg2.Error) as error:
            messagebox.showerror("Database Error", f"Error saving changes:\n{error}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                cur.close()
                conn.close()


# Example usage (for testing purposes, assumes a main Tkinter app)
# if __name__ == "__main__":
#     root = tk.Tk()
#     root.withdraw()
#
#     mismatch_viewer_instance = MismatchViewer(root, 'your_database_name')
#     root.mainloop()