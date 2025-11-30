"""
File: image_marker.py
Description: A Tkinter-based GUI to display an image with scrollbars and output 
             clicked coordinates to stdout.
"""

# ==========================================
#              CONFIGURATION
# ==========================================
# Size of the square drawn when clicking
MARKER_SQUARE_SIZE = 60

# Visual style of the marker
MARKER_COLOR = "red"
MARKER_WIDTH = 2

# Window sizing constraints (padding for window decorations)
WINDOW_PADDING = 50

# Output messages (Protocol for communication with main script)
MSG_WINDOW_CLOSED = "WINDOW_CLOSED_MANUALLY"
MSG_NO_IMAGE = "NO_IMAGE_SELECTED"
MSG_NO_CLICK = "NO_CLICK_DATA_AVAILABLE"

# ==========================================
#                  IMPORTS
# ==========================================
import sys
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk


# ==========================================
#                APP LOGIC
# ==========================================
class ImageMarkerApp:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title("Image Click Marker (Scrollable)")
        self.image_path = image_path

        # Get screen dimensions to cap the initial window size
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        self.pil_original_image = None
        self.tk_image = None
        self.current_square_id = None
        self.last_click_coords = None

        # Container for Canvas + Scrollbars
        container_frame = tk.Frame(root)
        container_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container_frame)
        self.v_scrollbar = tk.Scrollbar(container_frame, orient="vertical", command=self.canvas.yview)
        self.h_scrollbar = tk.Scrollbar(container_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Grid layout
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        container_frame.grid_rowconfigure(0, weight=1)
        container_frame.grid_columnconfigure(0, weight=1)

        if not self.load_image():
            error_label = tk.Label(root, text=f"Could not load image: {self.image_path}", fg="red")
            error_label.pack(pady=20)
            self.root.after(3000, self.on_manual_close)
            return

        # Bind events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.root.protocol("WM_DELETE_WINDOW", self.on_manual_close)

    def load_image(self):
        try:
            self.pil_original_image = Image.open(self.image_path)
            img_width, img_height = self.pil_original_image.size

            self.tk_image = ImageTk.PhotoImage(self.pil_original_image)
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
            self.canvas.config(scrollregion=self.canvas.bbox("all"))

            # Determine window size
            window_width = min(img_width, self.screen_width - WINDOW_PADDING)
            window_height = min(img_height, self.screen_height - WINDOW_PADDING)
            self.root.geometry(f"{window_width}x{window_height}")
            
            return True
        except FileNotFoundError:
            print(f"Error: Image file not found at '{self.image_path}'", file=sys.stderr)
            sys.stderr.flush()
            return False
        except Exception as e:
            print(f"An error occurred while loading the image: {e}", file=sys.stderr)
            sys.stderr.flush()
            return False

    def on_canvas_click(self, event):
        if not self.pil_original_image:
            return

        # Account for scroll offsets
        click_x = self.canvas.canvasx(event.x)
        click_y = self.canvas.canvasy(event.y)
        
        self.last_click_coords = (int(click_x), int(click_y))

        if self.current_square_id:
            self.canvas.delete(self.current_square_id)

        half_size = MARKER_SQUARE_SIZE // 2
        x1 = click_x - half_size
        y1 = click_y - half_size
        x2 = click_x + half_size
        y2 = click_y + half_size
        
        self.current_square_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=MARKER_COLOR,
            width=MARKER_WIDTH
        )

        self.output_coordinates()

    def output_coordinates(self):
        if self.last_click_coords:
            print(f"X:{self.last_click_coords[0]},Y:{self.last_click_coords[1]}")
            sys.stdout.flush()
        else:
            print(MSG_NO_CLICK)
            sys.stdout.flush()

    def on_manual_close(self):
        print(MSG_WINDOW_CLOSED)
        sys.stdout.flush()
        self.root.destroy()

# ==========================================
#                   MAIN
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    selected_image_path = None

    if len(sys.argv) > 1:
        selected_image_path = sys.argv[1]
    else:
        # If no argument, ask user
        print("No image path provided. Opening file dialog...", file=sys.stderr)
        sys.stderr.flush()
        root.withdraw()
        selected_image_path = filedialog.askopenfilename(
            title="Select an Image File",
            filetypes=(("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"),
                       ("All files", "*.*"))
        )
        if selected_image_path:
            root.deiconify()
        else:
            root.destroy()

    if selected_image_path:
        try:
            app_instance = ImageMarkerApp(root, selected_image_path)
            if app_instance.pil_original_image:
                root.mainloop()
        except Exception as e:
            print(f"An unhandled exception occurred: {e}", file=sys.stderr)
            sys.stderr.flush()
            if root.winfo_exists():
                root.destroy()
    else:
        print(MSG_NO_IMAGE)
        sys.stdout.flush()