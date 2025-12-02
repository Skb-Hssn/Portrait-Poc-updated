"""
File: texture_fill_and_compare.py
Description: 
    1. Loads a main image and a texture image.
    2. Allows user to draw a polygon.
    3. Fills the INSIDE of the polygon with the texture.
    4. Compares the OUTSIDE of the polygon against the texture.
       If pixels match (within threshold), they are turned black (0,0,0).
    5. Saves the result as 'output_image_textured_final.png'.
"""

# ==========================================
#              CONFIGURATION
# ==========================================

# --- Input Files ---
MAIN_IMAGE_PATH = "frame_1.png"
TEXTURE_IMAGE_PATH = "frame_1.png"
OUTPUT_FILENAME = "output_image_textured_final.png"

# --- Alignment Coordinates ---
# Point (FRAME_ONE_X, FRAME_ONE_Y) in Main Image aligns with 
# Point (FRAME_TWO_X, FRAME_TWO_Y) in Texture Image
FRAME_ONE_X = 504
FRAME_ONE_Y = 431

FRAME_TWO_X = 504
FRAME_TWO_Y = 431

# --- Comparison Logic ---
# Sum of absolute differences (R+G+B) allowed to consider pixels "similar"
SIMILARITY_THRESHOLD = 1 

# --- Drawing/UI Settings ---
DRAW_COLOR = (0, 0, 0)
ERASE_RADIUS = 3

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
    """
    Fills the INSIDE of a polygon by mapping pixels from a texture image.
    Uses a standard scan-line algorithm.
    """
    pixels = image.load()
    
    # Simple bounding box to reduce scan area
    if not vertices: return
    min_y = min(v[1] for v in vertices)
    max_y = max(v[1] for v in vertices)
    
    # Clamp bounds to image size
    min_y = max(0, min_y)
    max_y = min(image.height - 1, max_y)

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
                
                # Clamp x range
                x_start = max(0, x_start)
                x_end = min(image.width - 1, x_end)

                for x in range(x_start, x_end + 1):
                    try:
                        # Calculate texture offset based on alignment points
                        tex_x = (x + FRAME_TWO_X - FRAME_ONE_X)
                        tex_y = (y + FRAME_TWO_Y - FRAME_ONE_Y)
                        
                        if 0 <= tex_x < tex_width and 0 <= tex_y < tex_height:
                           pixels[x, y] = tex_pixels[tex_x, tex_y]
                    except Exception:
                        pass

def compare_and_mask_outside(image, texture_pixels, tex_width, tex_height, vertices):
    """
    Iterates through pixels OUTSIDE the provided polygon vertices.
    Compares the Main Image pixel with the corresponding Texture Image pixel.
    If they are similar, changes the pixel value so the difference 
    relative to the texture is exactly 1.
    """
    print("Processing outside pixels... this may take a moment.")
    width, height = image.size
    pixels = image.load()

    # 1. Create a binary mask of the polygon
    mask_img = Image.new('L', (width, height), 0)
    mask_draw = ImageDraw.Draw(mask_img)
    mask_draw.polygon(vertices, outline=255, fill=255)
    mask_pixels = mask_img.load()

    # 2. Iterate over all pixels
    for y in range(height):
        for x in range(width):
            # Check if pixel is OUTSIDE the polygon (mask value 0)
            if mask_pixels[x, y] == 0:
                # Calculate texture coordinate
                tex_x = (x + FRAME_TWO_X - FRAME_ONE_X)
                tex_y = (y + FRAME_TWO_Y - FRAME_ONE_Y)

                # Check bounds of texture
                if 0 <= tex_x < tex_width and 0 <= tex_y < tex_height:
                    # Get pixel values
                    r1, g1, b1 = pixels[x, y]
                    r2, g2, b2 = texture_pixels[tex_x, tex_y]

                    # Calculate difference (Manhattan distance)
                    diff = abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)

                    # If similar, change value so difference is exactly 1
                    if diff < SIMILARITY_THRESHOLD:
                        # We take the texture pixel (r2, g2, b2) and shift Red by 1.
                        # If Red is maxed (255), subtract 1, otherwise add 1.
                        new_r = r2 - 1 if r2 == 255 else r2 + 1
                        
                        # Assign the almost-identical texture color
                        pixels[x, y] = (new_r, g2, b2)
    
    print("Outside comparison complete.")

# ==========================================
#              GUI APPLICATION
# ==========================================

class TexturizerApp:
    def __init__(self, root, main_img_path, tex_img_path):
        self.root = root
        self.root.title("Image Texturizer (Scrollable)")
        
        # --- Load Images ---
        try:
            self.img_orig = Image.open(main_img_path).convert('RGB')
            self.out_img = self.img_orig.copy() # Working copy
            
            self.tex_img = Image.open(tex_img_path).convert('RGB')
            self.tex_pixels = self.tex_img.load()
            self.tex_width, self.tex_height = self.tex_img.size
        except Exception as e:
            print(f"Error loading images: {e}")
            sys.exit(1)

        # --- State ---
        self.drawn_points = []
        self.current_mode = "draw"

        # --- Layout ---
        self._setup_ui()
        self._update_canvas()

        # --- Initial Console Output ---
        print(f"Loaded '{main_img_path}' and '{tex_img_path}'.")
        print("Draw points, then click 'Fill & Compare'.")

    def _setup_ui(self):
        # Button Frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(side="top", fill="x", pady=5)

        tk.Button(btn_frame, text="Draw Mode", command=self.set_mode_draw).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Erase Mode", command=self.set_mode_erase).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Draw Lines (Preview)", command=self.draw_lines).pack(side=tk.LEFT, padx=10)
        
        # The main action button
        tk.Button(btn_frame, text="Fill & Compare", command=self.process_image, bg="#ddffdd").pack(side=tk.LEFT, padx=10)

        # Scrollable Canvas Container
        container = tk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container)
        v_scroll = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        h_scroll = tk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Bind Click
        self.canvas.bind("<Button-1>", self.on_click)

        # Window Sizing
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = min(self.img_orig.width, sw - 50)
        h = min(self.img_orig.height, sh - 100)
        self.root.geometry(f"{w}x{h}")

    def _update_canvas(self):
        self.tk_image = ImageTk.PhotoImage(self.out_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def set_mode_draw(self):
        self.current_mode = "draw"
        self.canvas.config(cursor="arrow")
        print("Mode: DRAW")

    def set_mode_erase(self):
        self.current_mode = "erase"
        self.canvas.config(cursor="dotbox")
        print("Mode: ERASE")

    def draw_lines(self):
        """Visual preview of the polygon lines."""
        if not self.drawn_points: return
        
        # Draw on a temp copy to not permanently fuse lines before fill
        preview_img = self.out_img.copy() 
        draw = ImageDraw.Draw(preview_img)
        
        h = preview_img.height
        pts = self.drawn_points
        
        # Connect to ground logic
        first_ground = (pts[0][0], h - 1)
        last_ground = (pts[-1][0], h - 1)
        
        draw.line((pts[0], first_ground), fill=DRAW_COLOR, width=1)
        if len(pts) > 1:
            draw.line(pts, fill=DRAW_COLOR, width=1)
            draw.line((pts[-1], last_ground), fill=DRAW_COLOR, width=1)
        
        # Update display temporarily
        self.tk_image = ImageTk.PhotoImage(preview_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    def on_click(self, event):
        cx = int(self.canvas.canvasx(event.x))
        cy = int(self.canvas.canvasy(event.y))
        
        pixels = self.out_img.load()
        modified = False

        if self.current_mode == "draw":
            self.drawn_points.append((cx, cy))
            if 0 <= cx < self.out_img.width and 0 <= cy < self.out_img.height:
                pixels[cx, cy] = DRAW_COLOR
                modified = True
        
        elif self.current_mode == "erase":
            r = ERASE_RADIUS
            # Filter points to remove
            to_remove = [p for p in self.drawn_points 
                         if (cx - r <= p[0] <= cx + r) and (cy - r <= p[1] <= cy + r)]
            
            for p in to_remove:
                self.drawn_points.remove(p)
                # Restore original pixel
                orig_px = self.img_orig.getpixel(p)
                pixels[p[0], p[1]] = orig_px
                modified = True

        if modified:
            self._update_canvas()

    def process_image(self):
        """
        1. Fills polygon with texture.
        2. Compares outside pixels.
        3. Saves final image.
        """
        if len(self.drawn_points) < 2:
            print("Need at least 2 points to define a region.")
            return

        print("Starting processing...")
        
        # 1. Define Polygon Vertices (including ground points)
        h = self.out_img.height
        poly_vertices = list(self.drawn_points)
        # Add bottom-right projection of last point
        poly_vertices.append((self.drawn_points[-1][0], h - 1))
        # Add bottom-left projection of first point
        poly_vertices.append((self.drawn_points[0][0], h - 1))

        # 2. Fill Inside
        manual_fill_polygon(
            self.out_img, 
            poly_vertices, 
            self.tex_pixels, 
            self.tex_width, 
            self.tex_height
        )

        # 3. Compare Outside
        compare_and_mask_outside(
            self.out_img,
            self.tex_pixels,
            self.tex_width,
            self.tex_height,
            poly_vertices
        )

        # 4. Update View and Save
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