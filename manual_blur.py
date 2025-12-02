import tkinter as tk
from tkinter import filedialog
import math
import os
from PIL import Image, ImageTk

# ==========================================
#              CONFIGURATION
# ==========================================
# The path to the image that contains the "blurred" or "target" pixels.
# MUST be the same dimensions as the image you open via the dialog.
REFERENCE_IMAGE_PATH = "frame_1.png" 

OUTPUT_FILENAME = "poc_output.png"
DRAG_THRESHOLD = 5    # Pixels mouse must move to count as a "Drag"

class ImageEditorApp:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title(f"Pixel Copier - {image_path}")

        # --- 1. Load Main Image ---
        try:
            self.pil_image = Image.open(image_path).convert("RGB")
        except Exception as e:
            print(f"Error loading main image: {e}")
            root.destroy()
            return

        # --- 2. Load Reference Image ---
        if not os.path.exists(REFERENCE_IMAGE_PATH):
            print(f"ERROR: Reference file not found at '{REFERENCE_IMAGE_PATH}'")
            print("Please ensure the hardcoded path is correct.")
            root.destroy()
            return

        try:
            self.ref_image = Image.open(REFERENCE_IMAGE_PATH).convert("RGB")
        except Exception as e:
            print(f"Error loading reference image: {e}")
            root.destroy()
            return

        # --- 3. Validate Dimensions ---
        if self.pil_image.size != self.ref_image.size:
            print(f"ERROR: Dimension Mismatch!")
            print(f"Main Image: {self.pil_image.size}")
            print(f"Ref Image:  {self.ref_image.size}")
            print("Images must have exactly the same width and height.")
            root.destroy()
            return

        # --- State Variables ---
        self.zoom_scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        # Drag handling state
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False

        # --- UI Setup ---
        self.canvas = tk.Canvas(root, bg="#222222", cursor="arrow")
        self.canvas.pack(fill="both", expand=True)

        # --- Bindings ---
        # Zoom
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)    
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)    
        
        # Left Click Handling (Click vs Drag)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Window Close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.tk_image = None 
        self.redraw_image()

        print(f"Loaded. Reference image: {REFERENCE_IMAGE_PATH}")
        print("Left Click (Tap) to copy pixel from Reference to Main.")
        print("Left Click (Hold+Drag) to pan.")

    def redraw_image(self):
        """Resizes and draws the image based on zoom/pan settings."""
        new_width = int(self.pil_image.width * self.zoom_scale)
        new_height = int(self.pil_image.height * self.zoom_scale)

        if new_width <= 0 or new_height <= 0: return

        # Use NEAREST neighbor so pixels are crisp when zoomed in
        resized_pil = self.pil_image.resize((new_width, new_height), Image.Resampling.NEAREST)
        
        self.tk_image = ImageTk.PhotoImage(resized_pil)
        
        self.canvas.delete("all")
        
        # Calculate center position relative to window center + pan offset
        # Fallback to geometry if winfo is not ready
        win_w = self.canvas.winfo_width()
        win_h = self.canvas.winfo_height()
        if win_w < 5: win_w = 800
        if win_h < 5: win_h = 600

        center_x = (win_w // 2) + self.pan_x
        center_y = (win_h // 2) + self.pan_y
        
        self.canvas.create_image(center_x, center_y, anchor="center", image=self.tk_image)
        
        self.current_center_x = center_x
        self.current_center_y = center_y

    def canvas_to_image_coords(self, cx, cy):
        """Converts screen coordinates to actual image pixel coordinates."""
        img_w = int(self.pil_image.width * self.zoom_scale)
        img_h = int(self.pil_image.height * self.zoom_scale)
        
        top_left_x = self.current_center_x - (img_w // 2)
        top_left_y = self.current_center_y - (img_h // 2)

        rel_x = cx - top_left_x
        rel_y = cy - top_left_y

        actual_x = int(rel_x / self.zoom_scale)
        actual_y = int(rel_y / self.zoom_scale)

        return actual_x, actual_y

    # --- Mouse Event Logic ---

    def on_mouse_down(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.is_dragging = False 
        
    def on_mouse_move(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        if self.is_dragging or (math.hypot(dx, dy) > DRAG_THRESHOLD):
            if not self.is_dragging:
                self.is_dragging = True
                self.canvas.config(cursor="fleur") 

            self.pan_x += dx
            self.pan_y += dy
            
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            
            self.redraw_image()

    def on_mouse_up(self, event):
        self.canvas.config(cursor="arrow") 

        if not self.is_dragging:
            self.apply_pixel_swap(event)
        
        self.is_dragging = False

    def on_mouse_wheel(self, event):
        scale_factor = 1.1
        if event.num == 5 or event.delta < 0:
            self.zoom_scale /= scale_factor
        else:
            self.zoom_scale *= scale_factor
        self.redraw_image()

    # --- Pixel Logic ---

    def apply_pixel_swap(self, event):
        ix, iy = self.canvas_to_image_coords(event.x, event.y)

        # Bounds check
        if 0 <= ix < self.pil_image.width and 0 <= iy < self.pil_image.height:
            
            # --- THE CHANGE: GET PIXEL FROM REFERENCE IMAGE ---
            try:
                # 1. Get the color from the reference image at the exact same coordinate
                source_color = self.ref_image.getpixel((ix, iy))
                
                # 2. Update the main image
                self.pil_image.putpixel((ix, iy), source_color)
                
                print(f"Copied pixel at ({ix}, {iy}): {source_color} from reference.")
                self.redraw_image()
            except Exception as e:
                print(f"Error swapping pixel: {e}")

    def on_close(self):
        print("Closing window...")
        try:
            self.pil_image.save(OUTPUT_FILENAME)
            print(f"SUCCESS: Image saved as '{OUTPUT_FILENAME}'")
        except Exception as e:
            print(f"ERROR: Could not save image: {e}")
        finally:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")

    file_path = filedialog.askopenfilename(
        title="Select Main Image",
        filetypes=(("Images", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*"))
    )

    if file_path:
        app = ImageEditorApp(root, file_path)
        root.mainloop()
    else:
        root.destroy()