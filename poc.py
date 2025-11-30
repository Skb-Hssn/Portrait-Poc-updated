"""
File: poc.py
Description: Main script to compare two images based on a user-selected reference point.
             It performs pixel extraction, searching, and visualization of differences.
"""

# ==========================================
#              CONFIGURATION
# ==========================================

# --- Input Files ---
IMAGE_1_PATH = 'images/Imu_1.jpg'
IMAGE_2_PATH = 'images/Imu_2.jpg'
MARKER_SCRIPT_FILENAME = "image_marker.py"

# --- Matching Logic Constants ---
# The size of the square used for pixel comparison (width/height)
MATCH_BLOCK_SIZE = 60 

# How far to search in pixels around the click point (X axis)
SEARCH_RANGE_X = 40 

# How far to search in pixels around the click point (Y axis)
SEARCH_RANGE_Y = 20 

# Maximum allowed difference per RGB channel sum to consider a pixel a "match"
PIXEL_DIFF_THRESHOLD = 15 

# Stop searching a specific block if mismatch count exceeds this
MAX_MISMATCH_TOLERANCE = 1000 

# --- Visualization & Processing ---
# Gaussian blur radius for preprocessing/visuals
BLUR_RADIUS = 5 

# Color and width of the square drawn on the result image
RESULT_SQUARE_COLOR = "blue"
RESULT_SQUARE_WIDTH = 2

# ==========================================
#                  IMPORTS
# ==========================================
import os
import subprocess
import sys
import time
import math
from functools import wraps
from PIL import Image, ImageDraw
from rich.console import Console

# ==========================================
#           UTILITY & DECORATORS
# ==========================================

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"'{func.__name__}' executed in: {elapsed_time:.4f} seconds")
        return result
    return wrapper

def printHex(pixel):
    print(f'{"".join([f"{channel_value:02x}" for channel_value in pixel])}', end=" ")

# ==========================================
#           MATH & BLUR ALGORITHMS
# ==========================================

def gaussian_kernel(radius, sigma=None):
    """Generate a 1D Gaussian kernel."""
    if sigma is None:
        sigma = radius / 2.0  # rule of thumb
    kernel = [math.exp(-(x**2) / (2 * sigma**2)) for x in range(-radius, radius+1)]
    s = sum(kernel)
    return [v/s for v in kernel]  # normalize

def gaussian_blur(image, radius=2):
    """Apply a Gaussian blur to a 2D RGB image using separable convolution."""
    height = len(image)
    width = len(image[0])
    kernel = gaussian_kernel(radius)
    k_len = len(kernel)

    # Horizontal pass
    temp = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            r_total = g_total = b_total = 0.0
            for k in range(k_len):
                dx = k - radius
                nx = min(max(x + dx, 0), width - 1)
                r, g, b = image[y][nx]
                weight = kernel[k]
                r_total += r * weight
                g_total += g * weight
                b_total += b * weight
            temp[y][x] = (r_total, g_total, b_total)

    # Vertical pass
    blurred = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            r_total = g_total = b_total = 0.0
            for k in range(k_len):
                dy = k - radius
                ny = min(max(y + dy, 0), height - 1)
                r, g, b = temp[ny][x]
                weight = kernel[k]
                r_total += r * weight
                g_total += g * weight
                b_total += b * weight
            blurred[y][x] = (int(r_total), int(g_total), int(b_total))

    return blurred

# ==========================================
#           IMAGE PROCESSING LOGIC
# ==========================================

@timing_decorator
def extract_pixels_pillow(image_path):
    try:
        img = Image.open(image_path)
        Console().print(f"[green]Image loaded successfully: {image_path}[/green]")
        print(f"Image format: {img.format}, Size: {img.size}, Mode: {img.mode}")

        width, height = img.size
        pixel_data = img.load()
        pixel_values = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]
        
        for y in range(0, height):
            for x in range(0, width):
                try:
                    pixel_values[y][x] = pixel_data[x, y]
                except Exception:
                    pass

        return pixel_values  
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def match(frame_one, frame_two, second_start_x, second_start_y, first_start_x, first_start_y):
    width = len(frame_one[0])
    height = len(frame_one)

    # Check boundaries including the block size
    if (first_start_x + MATCH_BLOCK_SIZE >= width or first_start_y + MATCH_BLOCK_SIZE >= height 
        or second_start_x + MATCH_BLOCK_SIZE >= width or second_start_y + MATCH_BLOCK_SIZE >= height
        or first_start_x < 0 or first_start_y < 0
        or second_start_x < 0 or second_start_y < 0):
        return [10000000, 0]
    
    pixel_cnt = 0
    match_cnt = 0
    
    for y in range(0, MATCH_BLOCK_SIZE + 1):
        for x in range(0, MATCH_BLOCK_SIZE + 1):
            pixel_cnt += 1
            
            # Calculate Manhattan distance for RGB
            dif = (abs(frame_one[y + first_start_y][x + first_start_x][0] - frame_two[y + second_start_y][x + second_start_x][0]) 
                 + abs(frame_one[y + first_start_y][x + first_start_x][1] - frame_two[y + second_start_y][x + second_start_x][1])
                 + abs(frame_one[y + first_start_y][x + first_start_x][2] - frame_two[y + second_start_y][x + second_start_x][2]))

            if abs(dif) < PIXEL_DIFF_THRESHOLD:
                match_cnt += 1
            
            if pixel_cnt - match_cnt > MAX_MISMATCH_TOLERANCE:
                return [10000000, 0]

    return [pixel_cnt, match_cnt]

@timing_decorator
def find_position_in_first_image(frame_one, frame_two, start_x, start_y):
    """
    Searches for the block defined by start_x/y in frame_two within frame_one.
    """
    min_val = 1_000_000_000
    yy, xx = -1, -1

    # Search range defined in config
    for y in range(start_y - SEARCH_RANGE_Y, start_y + SEARCH_RANGE_Y + 1):
        for x in range(start_x - SEARCH_RANGE_X, start_x + SEARCH_RANGE_X + 1):
            [i, j] = match(frame_one, frame_two, x, y, start_x, start_y)
            if min_val > i - j:
                min_val = i - j
                # Center offset adjustment
                yy, xx = y + (MATCH_BLOCK_SIZE // 2), x + (MATCH_BLOCK_SIZE // 2)
    
    print("[Min val, xx, yy] :", min_val, xx, yy)
    return xx, yy

@timing_decorator
def draw_unmatched_pixels(input_image_path, frame_one, first_center_x, first_center_y, frame_two, second_center_x, second_center_y):
    console = Console()
    try:
        img = Image.open(input_image_path)
        console.print(f"[cyan]Loading image for diff: {input_image_path}[/cyan]")
        
        width, height = img.size
        new_img = Image.new(img.mode, img.size)
        pixels_out = new_img.load()
        
        out_img = Image.new(img.mode, img.size)
        out_pixels_out = out_img.load()

        # Pre-calculate blur if needed (currently used for logic but not displayed directly)
        blurred_frame_one = gaussian_blur(frame_one, BLUR_RADIUS)

        console.print(f"[cyan]Applying modification...[/cyan]")
        for y in range(height):
            for x in range(width):
                # Map coordinates relative to the matched centers
                sx = (x + second_center_x - first_center_x)
                sy = (y + second_center_y - first_center_y)

                pixels_out[x, y] = frame_one[y][x]

                if 0 <= sx < width and 0 <= sy < height:
                    dif = (abs(frame_one[y][x][0] - frame_two[sy][sx][0])
                         + abs(frame_one[y][x][1] - frame_two[sy][sx][1])
                         + abs(frame_one[y][x][2] - frame_two[sy][sx][2]))
                    
                    if dif > 0:
                        # Draw black for difference
                        out_pixels_out[x, y] = (0, 0, 0) 
                    else:                    
                        out_pixels_out[x, y] = pixels_out[x, y]
                else:
                    # Out of bounds comparison
                    out_pixels_out[x, y] = pixels_out[x, y]

        out_img.show(title="Image Modified")
        return True
        
    except FileNotFoundError:
        console.print(f"[red]Error: Input image file not found at {input_image_path}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]An error occurred: {e}[/red]")
        return False

def draw_square_and_open(image_path, center_x, center_y):
    """Draws a square on the image at results coordinate."""
    try:
        img = Image.open(image_path)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        draw = ImageDraw.Draw(img)
        half_side = MATCH_BLOCK_SIZE // 2

        x1 = center_x - half_side
        y1 = center_y - half_side
        x2 = center_x + half_side
        y2 = center_y + half_side

        draw.rectangle(
            [x1, y1, x2, y2],
            outline=RESULT_SQUARE_COLOR,
            width=RESULT_SQUARE_WIDTH
        )

        img.show(title=f"Image with Square at ({center_x},{center_y})")
        print(f"Displayed image '{image_path}' with square at ({center_x}, {center_y}).")
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

# ==========================================
#           SUBPROCESS / GUI COMMS
# ==========================================

def get_coordinates_from_image(image_path_to_process):
    if not os.path.exists(image_path_to_process):
        print(f"Error: Image file not found at '{image_path_to_process}'")
        return None, None

    try:
        process = subprocess.Popen(
            [sys.executable, MARKER_SCRIPT_FILENAME, image_path_to_process],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        print(f"Launched marker script on '{image_path_to_process}'. Click the image.")
        
        while True:
            output_line = process.stdout.readline()
            if not output_line:
                break

            line_content = output_line.strip()
            print(f"[Marker Output]: {line_content}")

            if "WINDOW_CLOSED_MANUALLY" in line_content:
                print("Window closed.")
                break
            elif "NO_IMAGE_SELECTED" in line_content:
                break
            elif line_content.startswith("X:") and ",Y:" in line_content:
                try:
                    parts = line_content.split(',')
                    x_part = parts[0].split(':')[1]
                    y_part = parts[1].split(':')[1]
                    x_coord, y_coord = int(x_part), int(y_part)
                    print(f"RECEIVED: X={x_coord}, Y={y_coord}")
                    process.kill() # Close the GUI once we have coordinates
                    return x_coord, y_coord
                except Exception as e:
                    print(f"Error parsing coordinates: {e}")

        process.wait()
        return None, None

    except Exception as e:
        print(f"Subprocess error: {e}")
        return None, None

# ==========================================
#                   MAIN
# ==========================================

if __name__ == "__main__":
    # 1. Get coordinates from the first image via GUI
    x, y = get_coordinates_from_image(FRAME_1_PATH := IMAGE_1_PATH)
    
    if x is not None and y is not None:
        print(f"Processing around: {x}, {y}")
        
        # 2. Load pixel data
        frame_one = extract_pixels_pillow(IMAGE_1_PATH)
        frame_two = extract_pixels_pillow(IMAGE_2_PATH)

        if frame_one and frame_two:
            # 3. Find matching position in the second image
            # Adjustment: The algorithm subtracts half block size to search top-left corner
            half_block = MATCH_BLOCK_SIZE // 2
            mx, my = find_position_in_first_image(frame_one, frame_two, x - half_block, y - half_block)
            
            print(f"Match found at: {mx}, {my}")

            # 4. Visualize results
            draw_square_and_open(IMAGE_2_PATH, mx, my)
            draw_unmatched_pixels(IMAGE_1_PATH, frame_one, x, y, frame_two, mx, my)
    else:
        print("No coordinates received. Exiting.")