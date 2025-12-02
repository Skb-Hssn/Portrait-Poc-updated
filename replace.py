"""
File: texture_fill_and_compare.py
Description: 
    1. Loads a main image and a texture image.
    2. Allows user to draw a polygon via Mouse OR Keyboard.
    3. Fills the INSIDE of the polygon with the texture.
    4. Compares the OUTSIDE of the polygon against the texture.
    5. Saves the result.
"""

# ==========================================
#              CONFIGURATION
# ==========================================

# --- Input Files ---
MAIN_IMAGE_PATH = "frame_1.png"
TEXTURE_IMAGE_PATH = "frame_1.png"
OUTPUT_FILENAME = "output_image_textured_final.png"

# --- Alignment Coordinates ---
FRAME_ONE_X = 504
FRAME_ONE_Y = 431

FRAME_TWO_X = 504
FRAME_TWO_Y = 431

# --- Comparison Logic ---
SIMILARITY_THRESHOLD = 1 

# --- Drawing/UI Settings ---
DRAW_COLOR = (255, 255, 255)
ERASE_RADIUS = 3

# --- Keyboard Cursor Settings ---
CURSOR_COLOR = "red"
CURSOR_SIZE = 20 # Length of crosshair lines
MOVE_STEP = 1    # Pixels to move per key press (increase for speed)

# ==========================================
#                  IMPORTS
# ==========================================
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import sys

# ==========================================
#           IMAGE PROCESSING LOGIC
# ==========================================

def manual_fill_polygon(image, vertices, tex_pixels, tex_width, tex_height):
    """Fills the INSIDE of a polygon by mapping pixels from a texture image."""
    pixels = image.load()
    if not vertices: return
    
    # Clamp bounds to image size
    min_y = min(v[1] for v in vertices)
    max_y = max(v[1] for v in vertices)
    min_y = max(0, min_y)
    max_y = min(image.height - 1, max_y)

    for y in range(image.height):
        for x in range(image.width):
            # Calculate texture coordinate
            tex_x = (x + FRAME_TWO_X - FRAME_ONE_X)
            tex_y = (y + FRAME_TWO_Y - FRAME_ONE_Y)

            if 0 <= tex_x < tex_width and 0 <= tex_y < tex_height:
                r1, g1, b1 = pixels[x, y]
                r2, g2, b2 = tex_pixels[tex_x, tex_y]
                diff = abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)

                if diff < SIMILARITY_THRESHOLD:
                    new_r = r2 - 1 if r2 == 255 else r2 + 1
                    pixels[x, y] = (new_r, g2, b2)
                    

    # 1. Fill Inside Polygon
    for y in range(min_y, max_y + 1):
        intersections = []
        for i in range(len(vertices)):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % len(vertices)]
            if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
                if p1[1] != p2[1]:
                    x = p1[0] + (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                    intersections.append(x)
        intersections.sort()
        
        for i in range(0, len(intersections), 2):
            if i + 1 < len(intersections):
                x_start = round(intersections[i])
                x_end = round(intersections[i+1])
                x_start = max(0, x_start)
                x_end = min(image.width - 1, x_end)

                for x in range(x_start+1, x_end):
                    try:
                        tex_x = (x + FRAME_TWO_X - FRAME_ONE_X)
                        tex_y = (y + FRAME_TWO_Y - FRAME_ONE_Y)
                        if 0 <= tex_x < tex_width and 0 <= tex_y < tex_height:
                           pixels[x, y] = tex_pixels[tex_x, tex_y]
                    except Exception:
                        pass

# ==========================================
#              GUI APPLICATION
# ==========================================

class TexturizerApp:
    def __init__(self, root, main_img_path, tex_img_path):
        self.root = root
        self.root.title("Image Texturizer (Keyboard Supported)")
        
        # --- Load Images ---
        try:
            self.img_orig = Image.open(main_img_path).convert('RGB')
            self.out_img = self.img_orig.copy() 
            
            self.tex_img = Image.open(tex_img_path).convert('RGB')
            self.tex_pixels = self.tex_img.load()
            self.tex_width, self.tex_height = self.tex_img.size
        except Exception as e:
            print(f"Error loading images: {e}")
            sys.exit(1)

        # --- State ---
        self.drawn_points = []
        self.current_mode = "draw"
        
        # Cursor State
        self.cursor_x = self.img_orig.width // 2
        self.cursor_y = self.img_orig.height // 2
        self.cursor_items = [] # Stores canvas IDs for the crosshair

        # --- Layout ---
        self._setup_ui()
        self._update_canvas()
        self._draw_cursor() # Initial draw

        print(f"Loaded '{main_img_path}'.")
        print("Controls:")
        print("  - Mouse Click: Add Point")
        print("  - Arrow Keys: Move Cursor")
        print("  - Enter Key: Add Point at Cursor")

    def _setup_ui(self):
        # Button Frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(side="top", fill="x", pady=5)

        tk.Button(btn_frame, text="Draw Mode", command=self.set_mode_draw).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Erase Mode", command=self.set_mode_erase).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Draw Lines (Preview)", command=self.draw_lines).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Fill & Compare", command=self.process_image, bg="#ddffdd").pack(side=tk.LEFT, padx=10)

        # Scrollable Canvas Container
        container = tk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, cursor="arrow")
        v_scroll = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        h_scroll = tk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # --- Bindings ---
        # Mouse
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        
        # Keyboard (Bind to root to catch events globally within app)
        self.root.bind("<Left>", lambda e: self.move_cursor(-MOVE_STEP, 0))
        self.root.bind("<Right>", lambda e: self.move_cursor(MOVE_STEP, 0))
        self.root.bind("<Up>", lambda e: self.move_cursor(0, -MOVE_STEP))
        self.root.bind("<Down>", lambda e: self.move_cursor(0, MOVE_STEP))
        self.root.bind("<Return>", self.on_enter_key)

        # Window Sizing
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = min(self.img_orig.width, sw - 50)
        h = min(self.img_orig.height, sh - 100)
        self.root.geometry(f"{w}x{h}")

    def _update_canvas(self):
        """Redraws the image. NOTE: This wipes the canvas items."""
        self.tk_image = ImageTk.PhotoImage(self.out_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # After updating the image, we must redraw the cursor or it disappears behind the image
        self._draw_cursor()

    # --- Cursor Logic ---
    
    def _draw_cursor(self):
        """Draws a vertical line where the top tip is the active point (cx, cy)."""
        # Remove old cursor
        for item in self.cursor_items:
            self.canvas.delete(item)
        self.cursor_items.clear()

        cx, cy = self.cursor_x, self.cursor_y
        length = CURSOR_SIZE 
        
        # Draw Vertical Line starting at (cx, cy) and going down
        l1 = self.canvas.create_line(cx, cy, cx, cy + length, fill=CURSOR_COLOR, width=1)
        
        self.cursor_items = [l1]


    def move_cursor(self, dx, dy):
        """Updates cursor position and redraws it."""
        new_x = self.cursor_x + dx
        new_y = self.cursor_y + dy
        
        # Clamp to image bounds
        new_x = max(0, min(self.out_img.width - 1, new_x))
        new_y = max(0, min(self.out_img.height - 1, new_y))
        
        self.cursor_x = new_x
        self.cursor_y = new_y
        
        self._draw_cursor()
        
        # Optional: Auto-scroll to keep cursor in view
        # (Simplified logic, depends on if user wants auto-scroll)

    def on_enter_key(self, event):
        """Simulate click at current cursor position."""
        self._add_point_at(self.cursor_x, self.cursor_y)

    def on_mouse_click(self, event):
        """Handle mouse click."""
        # Convert window coords to canvas coords
        cx = int(self.canvas.canvasx(event.x))
        cy = int(self.canvas.canvasy(event.y))
        
        # Update cursor position to match mouse click
        self.cursor_x = cx
        self.cursor_y = cy
        self._draw_cursor()

        self._add_point_at(cx, cy)

    def _add_point_at(self, cx, cy):
        """Core logic to add/remove points at specific coordinates."""
        pixels = self.out_img.load()
        modified = False

        if self.current_mode == "draw":
            self.drawn_points.append((cx, cy))
            if 0 <= cx < self.out_img.width and 0 <= cy < self.out_img.height:
                pixels[cx, cy] = DRAW_COLOR
                modified = True
                print(f"Point added at: {cx}, {cy}")
        
        elif self.current_mode == "erase":
            r = ERASE_RADIUS
            to_remove = [p for p in self.drawn_points 
                         if (cx - r <= p[0] <= cx + r) and (cy - r <= p[1] <= cy + r)]
            
            for p in to_remove:
                self.drawn_points.remove(p)
                orig_px = self.img_orig.getpixel(p)
                pixels[p[0], p[1]] = orig_px
                modified = True
                print(f"Point erased at: {p}")

        if modified:
            self._update_canvas()

    # --- Mode & Processing Logic ---

    def set_mode_draw(self):
        self.current_mode = "draw"
        print("Mode: DRAW")

    def set_mode_erase(self):
        self.current_mode = "erase"
        print("Mode: ERASE")

    def draw_lines(self):
        if not self.drawn_points: return
        preview_img = self.out_img.copy() 
        draw = ImageDraw.Draw(preview_img)
        h = preview_img.height
        pts = self.drawn_points
        
        first_ground = (pts[0][0], h - 1)
        last_ground = (pts[-1][0], h - 1)
        
        draw.line((pts[0], first_ground), fill=DRAW_COLOR, width=1)
        if len(pts) > 1:
            draw.line(pts, fill=DRAW_COLOR, width=1)
            draw.line((pts[-1], last_ground), fill=DRAW_COLOR, width=1)
        
        self.tk_image = ImageTk.PhotoImage(preview_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self._draw_cursor() # Keep cursor visible

    def process_image(self):
        if len(self.drawn_points) < 2:
            print("Need at least 2 points to define a region.")
            return

        print("Starting processing...")
        h = self.out_img.height
        poly_vertices = list(self.drawn_points)
        poly_vertices.append((self.drawn_points[-1][0], h - 1))
        poly_vertices.append((self.drawn_points[0][0], h - 1))

        manual_fill_polygon(
            self.out_img, 
            poly_vertices, 
            self.tex_pixels, 
            self.tex_width, 
            self.tex_height
        )

        self._update_canvas()
        
        try:
            self.out_img.save(OUTPUT_FILENAME)
            print(f"Success! Image saved to: {OUTPUT_FILENAME}")
        except Exception as e:
            print(f"Error saving image: {e}")

# ==========================================
#                   MAIN
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = TexturizerApp(root, MAIN_IMAGE_PATH, TEXTURE_IMAGE_PATH)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Terminated.")