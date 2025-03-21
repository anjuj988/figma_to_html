from paddleocr import PaddleOCR
import numpy as np

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang="en")

def extract_text(image_path):
    results = ocr.ocr(image_path, cls=True)

    extracted_lines = []
    for page in results:
        for line in page:
            (coordinates, (text, confidence)) = line
            x1, y1 = coordinates[0]  # Top-left corner of the bounding box
            extracted_lines.append((x1, y1, text))

    # Sort text based on Y (row-wise) first, then X (left to right)
    extracted_lines.sort(key=lambda item: (item[1], item[0]))

    structured_text = ""
    prev_y = None

    for x, y, text in extracted_lines:
        # If the Y-position is significantly different, start a new line
        if prev_y is not None and abs(y - prev_y) > 10:
            structured_text += "\n"
        
        structured_text += text + " "  # Add text with spacing
        prev_y = y  # Update last Y position
    
    return structured_text

# Example Usage
image_path = "./images/food-bill_10.png"  # Change to your document image path
output_text = extract_text(image_path)

print(output_text)

# Save to a text file if needed
with open("extracted_text.txt", "w", encoding="utf-8") as f:
    f.write(output_text)



#2/28/2025-morning

import numpy as np

def calculate_adaptive_y_threshold(text_data):
    """
    Calculates an adaptive Y-axis threshold based on median Y differences.

    Args:
        text_data: List of text elements with 'y' values.

    Returns:
        Adaptive Y-threshold for grouping.
    """
    y_values = sorted(set(item["y"] for item in text_data))
    y_differences = [j - i for i, j in zip(y_values[:-1], y_values[1:])]

    if not y_differences:
        return 10  # Default if only one line exists

    return max(5, np.median(y_differences))  # Use median Y-gap, min 5


def group_text_by_lines(results):
    """
    Groups detected text into lines based on Y-coordinates.
    Uses an adaptive Y-threshold for accurate grouping.

    Args:
        results: PaddleOCR output (list of detected text with bounding boxes)

    Returns:
        List of grouped text lines, sorted in reading order.
    """
    text_data = []
    
    # Extract text, confidence, and bounding box info
    for res in results:
        for line in res:
            bbox, text_data_info = line
            text, confidence = text_data_info
            x1, y1 = bbox[0]  # Top-left coordinate
            x2, y2 = bbox[1]
            x3, y3 = bbox[2]
            x4, y4 = bbox[3]
            avg_y = np.mean([y1, y2, y3, y4])  # Average Y for line grouping

            # Only keep high-confidence results
            if confidence > 0.95:  
                text_data.append({"text": text, "x": x1, "y": avg_y, "confidence": confidence})

    # Sort detected text by rounded Y first, then by X
    text_data.sort(key=lambda item: (round(item["y"]), item["x"]))

    # Compute adaptive Y-threshold based on content
    y_threshold = calculate_adaptive_y_threshold(text_data)

    # Group texts into lines based on adaptive Y-threshold
    grouped_lines = []
    current_line = []
    last_y = None

    for item in text_data:
        if last_y is None or abs(item["y"] - last_y) <= y_threshold:
            current_line.append(item)
        else:
            grouped_lines.append(current_line)  # Save previous line
            current_line = [item]  # Start new line
        last_y = item["y"]

    if current_line:
        grouped_lines.append(current_line)

    return grouped_lines


def print_text_layout(results, spacing="  "):
    """
    Prints extracted text while ensuring inline flow without stretching across the page.

    Args:
        results: PaddleOCR output (list of detected text with bounding boxes)
        spacing: Custom spacing to maintain inline formatting.
    """
    grouped_lines = group_text_by_lines(results)

    print("\n Extracted Text \n")
    
    for line in grouped_lines:
        # Sort each line by X-coordinates to maintain left-to-right order
        line.sort(key=lambda item: item["x"])
        
        # Join words using the specified spacing
        formatted_text = spacing.join([word["text"] for word in line])
        print(formatted_text)


# Example Usage: Process and Print for a Given Image
folder_path = "/content/drive/MyDrive/ocr/2 images" 
sample_image = os.path.join(folder_path, os.listdir(folder_path)[0])  # Pick first image
results = ocr.ocr(sample_image, cls=True)  # Perform OCR

print_text_layout(results, spacing="  ")  # Adjust spacing as needed



#2/28/2025

import numpy as np
from paddleocr import PaddleOCR
import os

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def calculate_adaptive_y_threshold(text_data):
    
    y_values = sorted(set(item["y"] for item in text_data))
    y_differences = [j - i for i, j in zip(y_values[:-1], y_values[1:])]

    if not y_differences:
        return 10  # Default if only one line exists

    return max(5, np.median(y_differences))  # Use median Y-gap, min 5


def group_text_by_lines(results):
    
    text_data = []
    
    # Extract text, confidence, and bounding box info
    for res in results:
        for line in res:
            bbox, text_data_info = line
            text, confidence = text_data_info
            x1, y1 = bbox[0]  # Top-left coordinate
            x2, y2 = bbox[1]
            x3, y3 = bbox[2]
            x4, y4 = bbox[3]
            avg_y = np.mean([y1, y2, y3, y4])  # Average Y for line grouping

            # Only keep high-confidence results
            if confidence > 0.85:  
                text_data.append({"text": text, "x": x1, "y": avg_y, "confidence": confidence})

    # Sort detected text by rounded Y first, then by X
    text_data.sort(key=lambda item: (round(item["y"]), item["x"]))

    # Compute adaptive Y-threshold based on content
    y_threshold = calculate_adaptive_y_threshold(text_data)

    # Group texts into lines based on adaptive Y-threshold
    grouped_lines = []
    current_line = []
    last_y = None

    for item in text_data:
        if last_y is None or abs(item["y"] - last_y) <= y_threshold:
            current_line.append(item)
        else:
            grouped_lines.append(current_line)  # Save previous line
            current_line = [item]  # Start new line
        last_y = item["y"]

    if current_line:
        grouped_lines.append(current_line)

    return grouped_lines


def render_text_with_static_spacing(text_elements, char_width, space_width):
    rendered_text = ""
    prev_x = 8
    
    for element in text_elements:
        text = element["text"]
        x = element["x"]
        
        if prev_x is not None:
            # Calculate the number of spaces needed
            space_count = int((x - prev_x) / space_width)
            rendered_text += " " * space_count
        
        rendered_text += text
        prev_x = x + len(text) * char_width  
        
    return rendered_text


def print_text_layout(results, char_width=6, space_width=6):
    grouped_lines = group_text_by_lines(results)

    print("\n Extracted Text with Adjusted Spacing \n")
    
    for line in grouped_lines:
        # Sort each line by X-coordinates to maintain left-to-right order
        line.sort(key=lambda item: item["x"])
        
        # Apply the rendering function to add spaces between words based on their positions
        rendered_text = render_text_with_static_spacing(line, char_width, space_width)
        print(rendered_text)




folder_path = "/content/drive/MyDrive/ocr/2 images" 
sample_image = os.path.join(folder_path, os.listdir(folder_path)[3])  # Pick first image
results = ocr.ocr(sample_image, cls=True)  # Perform OCR

print_text_layout(results)  

