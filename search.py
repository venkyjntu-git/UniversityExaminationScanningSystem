import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import os
import psycopg2
from configparser import ConfigParser
from connection import connect_to_db

# --- Image Search Application ---
class ImageSearchApp:
    def __init__(self, master, db_name):
        self.master = tk.Toplevel(master)
        self.db_name = db_name
        self.master.title("Image and Data Search")
        self.master.geometry("1000x800") # Set an initial size

        self.master.grid_rowconfigure(1, weight=1) # Row for image and details frame
        self.master.grid_columnconfigure(0, weight=1) # Full width

        self.all_scripts_data = []  # Stores all fetched script data for Browse
        self.current_script_index = -1 # Index for Browse through all_scripts_data

        self.create_widgets()

    def create_widgets(self):
        # Input Frame
        input_frame = tk.Frame(self.master, bd=2, relief=tk.GROOVE, padx=10, pady=10)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1) # Make entry fields expandable

        tk.Label(input_frame, text="Image Path:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.image_path_entry = tk.Entry(input_frame, width=50, font=("Arial", 10))
        self.image_path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        tk.Button(input_frame, text="Browse", command=self.browse_image_path).grid(row=0, column=2, padx=5, pady=2)

        tk.Label(input_frame, text="OR", font=("Arial", 10, "bold")).grid(row=1, column=1, pady=5)

        tk.Label(input_frame, text="Barcode (Script Info):", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.barcode_entry = tk.Entry(input_frame, width=50, font=("Arial", 10))
        self.barcode_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        tk.Button(input_frame, text="Search", command=self.perform_search, font=("Arial", 10, "bold")).grid(row=3, column=1, pady=10)
        tk.Button(input_frame, text="Show All Scripts", command=self.show_all_scripts, font=("Arial", 10, "bold"), bg="lightgreen").grid(row=4, column=1, pady=10, sticky="ew", columnspan=2)

        # Navigation buttons for "Show All" mode
        self.nav_button_frame = tk.Frame(input_frame)
        self.nav_button_frame.grid(row=5, column=0, columnspan=3, pady=5, sticky="ew")
        self.nav_button_frame.grid_columnconfigure(0, weight=1)
        self.nav_button_frame.grid_columnconfigure(1, weight=1)

        self.prev_script_button = tk.Button(self.nav_button_frame, text="< Previous Script", command=self.show_previous_script, state=tk.DISABLED)
        self.prev_script_button.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.next_script_button = tk.Button(self.nav_button_frame, text="Next Script >", command=self.show_next_script, state=tk.DISABLED)
        self.next_script_button.grid(row=0, column=1, padx=5, sticky="ew")


        # Results Frame
        results_frame = tk.Frame(self.master, bd=2, relief=tk.GROOVE, padx=10, pady=10)
        results_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=3) # Image column
        results_frame.grid_columnconfigure(1, weight=1) # Details column

        # Image Display Area
        self.image_display_frame = tk.Frame(results_frame, bd=1, relief=tk.SOLID)
        self.image_display_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.image_display_frame.grid_rowconfigure(0, weight=1)
        self.image_display_frame.grid_columnconfigure(0, weight=1)
        self.image_label = tk.Label(self.image_display_frame, text="Image will appear here", bg="lightgray")
        self.image_label.grid(row=0, column=0, sticky="nsew")

        # Details Display Area
        self.details_display_frame = tk.Frame(results_frame, bd=1, relief=tk.SOLID)
        self.details_display_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.details_display_frame.grid_rowconfigure(0, weight=1)
        self.details_display_frame.grid_columnconfigure(0, weight=1)
        
        self.details_text = tk.Text(self.details_display_frame, wrap="word", state="disabled", font=("Arial", 10))
        self.details_text.grid(row=0, column=0, sticky="nsew")
        self.details_scrollbar = tk.Scrollbar(self.details_display_frame, command=self.details_text.yview)
        self.details_scrollbar.grid(row=0, column=1, sticky="ns")
        self.details_text.config(yscrollcommand=self.details_scrollbar.set)

    def browse_image_path(self):
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp"), ("All files", "*.*")]
        )
        if file_path:
            self.image_path_entry.delete(0, tk.END)
            self.image_path_entry.insert(0, file_path)

    def perform_search(self):
        image_path = self.image_path_entry.get().strip()
        barcode = self.barcode_entry.get().strip()
        k = image_path.rfind('/')
        if k != -1:
            image_path = image_path[:k] + '\\' +  image_path[k+1:]

        if not image_path and not barcode:
            messagebox.showwarning("No Input", "Please enter either an Image Path or a Barcode to search.")
            return

        self.clear_results()

        conn = None
        try:
            conn = connect_to_db(self.db_name)
            if not conn:
                return

            cur = conn.cursor()
            found_data = None
            omr_type_found = None # To know which table the data came from

            # Prioritize barcode search if provided
            if barcode:
                cur.execute("SELECT * FROM scriptinfo WHERE barcode = %s", (barcode,))
                row = cur.fetchone()
                if row:
                    # Get column names from cursor description
                    colnames = [desc[0] for desc in cur.description]
                    found_data = dict(zip(colnames, row))
                    omr_type_found = "scriptinfo"

            # If no barcode or barcode search didn't yield results, try image_path
            if not found_data and image_path:
                # Try script_info table first for image_path
                cur.execute("SELECT * FROM scriptinfo WHERE image_path = %s", (image_path,))
                row = cur.fetchone()
                if row:
                    colnames = [desc[0] for desc in cur.description]
                    found_data = dict(zip(colnames, row))
                    omr_type_found = "scriptinfo"
                else:
                    # Then try bundle_info table for image_path
                    cur.execute("SELECT * FROM bundleinfo WHERE image_path = %s", (image_path,))
                    row = cur.fetchone()
                    if row:
                        colnames = [desc[0] for desc in cur.description]
                        found_data = dict(zip(colnames, row))
                        omr_type_found = "bundleinfo"
            
            if found_data:
                self.display_results(found_data, omr_type_found)
            else:
                messagebox.showinfo("Not Found", "No matching data found for the provided criteria.")

        except (Exception, psycopg2.Error) as error:
            messagebox.showerror("Database Search Error", f"Error during search:\n{error}")
        finally:
            if conn:
                cur.close() # Close cursor before connection
                conn.close()

    def show_all_scripts(self):
        barcode = self.barcode_entry.get().strip()
        self.clear_results()
        self.image_path_entry.delete(0, tk.END) # Clear specific search fields
        self.barcode_entry.delete(0, tk.END)

        conn = None
        try:
            conn = connect_to_db(self.db_name)
            if not conn:
                return

            cur = conn.cursor()
            # Fetch all script_info, ordered by bundle_number (numeric) then script_number (alphanumeric, might need conversion)
            # We'll order by bundle_number as text first, then try to convert script_number to integer for ordering
            # For script_number, it's safer to order as text if it contains 'ERROR' or other non-numeric strings
            # cur.execute("""
            #     SELECT * FROM scriptinfo
            #     ORDER BY 
            #         bundle_number,
            #         CASE WHEN script_number ~ '^[0-9]+$' THEN LPAD(script_number, 10, '0') ELSE script_number END;
            # """)
            if barcode:
                cur.execute("""
                    SELECT * FROM scriptinfo
                    WHERE bundle_number = %s
                    ORDER BY script_number
                    """, (barcode,))
            else:
                cur.execute("""
                SELECT * FROM scriptinfo
                ORDER BY bundle_number, script_number
                """)
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            
            self.all_scripts_data = []
            for row in rows:
                self.all_scripts_data.append(dict(zip(colnames, row)))
            
            if self.all_scripts_data:
                self.current_script_index = 0
                self.display_current_script()
                messagebox.showinfo("Show All", f"Displaying {len(self.all_scripts_data)} script records.")
            else:
                messagebox.showinfo("Show All", "No script records found in the database.")
                self.current_script_index = -1 # Reset index
            
            self._update_nav_buttons()

        except (Exception, psycopg2.Error) as error:
            messagebox.showerror("Database Error", f"Error fetching all scripts:\n{error}")
        finally:
            if conn:
                cur.close()
                conn.close()

    def display_current_script(self):
        if 0 <= self.current_script_index < len(self.all_scripts_data):
            script_data = self.all_scripts_data[self.current_script_index]
            self.display_results(script_data, "script_info")
        else:
            self.clear_results()
            messagebox.showinfo("End of List", "No more scripts to display.")
        self._update_nav_buttons()

    def show_next_script(self):
        if self.current_script_index < len(self.all_scripts_data) - 1:
            self.current_script_index += 1
            self.display_current_script()
        else:
            messagebox.showinfo("End of List", "This is the last script.")
        self._update_nav_buttons()

    def show_previous_script(self):
        if self.current_script_index > 0:
            self.current_script_index -= 1
            self.display_current_script()
        else:
            messagebox.showinfo("End of List", "This is the first script.")
        self._update_nav_buttons()
    
    def _update_nav_buttons(self):
        if self.all_scripts_data:
            self.prev_script_button.config(state=tk.NORMAL if self.current_script_index > 0 else tk.DISABLED)
            self.next_script_button.config(state=tk.NORMAL if self.current_script_index < len(self.all_scripts_data) - 1 else tk.DISABLED)
        else:
            self.prev_script_button.config(state=tk.DISABLED)
            self.next_script_button.config(state=tk.DISABLED)


    def clear_results(self):
        self.image_label.config(image="", text="Image will appear here")
        self.details_text.config(state="normal")
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state="disabled")
        self.photo = None # Clear reference


    def display_results(self, data, omr_type_found):
        # Display Image
        img_path = data.get('image_path')
        if img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path)

                # --- MODIFICATION START ---
                # Force Tkinter to update the widget's geometry calculations
                # This ensures winfo_width/height return accurate values
                self.image_display_frame.update_idletasks() 

                # Get the actual current dimensions of the image display frame
                # Set a reasonable minimum to prevent division by zero or too small images
                frame_width = self.image_display_frame.winfo_width()
                frame_height = self.image_display_frame.winfo_height()

                # Ensure minimum dimensions if the frame is not yet fully laid out or is too small
                # These minimums ensure the image is at least somewhat visible even if the frame is tiny
                min_width = 400 
                min_height = 400 

                max_width = max(frame_width, min_width)
                max_height = max(frame_height, min_height)

                # Maintain aspect ratio while fitting within max_width, max_height
                img_width, img_height = img.size
                
                # Calculate scaling factor
                # Scale down only if image is larger than the frame dimensions
                if img_width > max_width or img_height > max_height:
                    width_ratio = max_width / img_width
                    height_ratio = max_height / img_height
                    scale_factor = min(width_ratio, height_ratio)

                    new_width = int(img_width * scale_factor)
                    new_height = int(img_height * scale_factor)
                    
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # If image is smaller than frame, no need to scale up (unless desired)
                # If you want to force it to fill the space, you'd use a different logic
                # For 'fit within', thumbnail or resize is good.

                self.photo = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.photo, text="")
                # --- MODIFICATION END ---

            except Exception as e:
                self.image_label.config(image="", text=f"Error loading image: {e}")
                print(f"Error loading image {img_path}: {e}")
        else:
            self.image_label.config(image="", text="Image file not found at specified path.")

        # Display Details (rest of the method remains the same)
        self.details_text.config(state="normal")
        self.details_text.delete(1.0, tk.END)
        
        if self.all_scripts_data:
            self.details_text.insert(tk.END, f"Script {self.current_script_index + 1} of {len(self.all_scripts_data)}\n")
            self.details_text.insert(tk.END, f"---------------------------------\n\n")

        self.details_text.insert(tk.END, f"--- Data from {omr_type_found.replace('_', ' ').title()} Table ---\n\n")
        for key, value in data.items():
            if key not in ['entry_timestamp', 'omr_type']:
                self.details_text.insert(tk.END, f"{key.replace('_', ' ').title()}: {value}\n")
            elif key == 'entry_timestamp' and value:
                self.details_text.insert(tk.END, f"{key.replace('_', ' ').title()}: {value.strftime('%Y-%m-%d %H:%M:%S')}\n")

        self.details_text.config(state="disabled")
    # def display_results(self, data, omr_type_found):
    #     # Display Image
    #     img_path = data.get('image_path')
    #     if img_path and os.path.exists(img_path):
    #         try:
    #             img = Image.open(img_path)
    #             # Dynamically size image to fit frame, max 600px width/height for display
    #             max_width = self.image_display_frame.winfo_width() if self.image_display_frame.winfo_width() > 300 else 600
    #             max_height = self.image_display_frame.winfo_height() if self.image_display_frame.winfo_height() > 300 else 600
            
    #             img.thumbnail((max_width, max_height), Image.LANCZOS)
    #             self.photo = ImageTk.PhotoImage(img)
    #             self.image_label.config(image=self.photo, text="")
    #         except Exception as e:
    #             self.image_label.config(image="", text=f"Error loading image: {e}")
    #             print(f"Error loading image {img_path}: {e}")
    #     else:
    #         self.image_label.config(image="", text="Image file not found at specified path.")

    #     # Display Details
    #     self.details_text.config(state="normal")
    #     self.details_text.delete(1.0, tk.END)
        
    #     # Display current script index if in "Show All" mode
    #     if self.all_scripts_data:
    #         self.details_text.insert(tk.END, f"Script {self.current_script_index + 1} of {len(self.all_scripts_data)}\n")
    #         self.details_text.insert(tk.END, f"---------------------------------\n\n")


    #     self.details_text.insert(tk.END, f"--- Data from {omr_type_found.replace('_', ' ').title()} Table ---\n\n")
    #     for key, value in data.items():
    #         # Exclude internal database columns like timestamp if desired, or format them
    #         if key not in ['entry_timestamp']:
    #             self.details_text.insert(tk.END, f"{key.replace('_', ' ').title()}: {value}\n")
    #         elif key == 'entry_timestamp' and value:
    #             self.details_text.insert(tk.END, f"{key.replace('_', ' ').title()}: {value.strftime('%Y-%m-%d %H:%M:%S')}\n")

    #     self.details_text.config(state="disabled")


# --- Main execution block to run only the ImageSearchApp ---
#if __name__ == "__main__":
    # # Create dummy image files if they don't exist, for testing purposes
    # # You should ensure actual images referenced in your DB exist.
    # if not os.path.exists("sample_control_bundle_omr.jpg"):
    #     try:
    #         img = Image.new('RGB', (800, 1000), color='white')
    #         img.save("sample_control_bundle_omr.jpg")
    #         print("Created dummy sample_control_bundle_omr.jpg")
    #     except ImportError:
    #         print("Pillow not installed. Please install with 'pip install Pillow' to create dummy images for testing.")
    #         print("Or ensure 'sample_control_bundle_omr.jpg' exists in the current directory.")

    # if not os.path.exists("sample_script_omr.jpg"):
    #     try:
    #         img = Image.new('RGB', (800, 1000), color='white')
    #         img.save("sample_script_omr.jpg")
    #         print("Created dummy sample_script_omr.jpg")
    #     except ImportError:
    #         pass

    # root_search = tk.Tk()
    # db_name = "param"
    # app_search = ImageSearchApp(root_search, db_name)
    # root_search.mainloop()

    # print("\n--- Image Search Application Finished ---")