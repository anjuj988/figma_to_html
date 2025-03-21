from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
import io
import mimetypes
from .utils.storage import MinioStorage
from pdf2image import convert_from_bytes

class OCRService:
    def __init__(self):
        # OCR Configuration
        self.ocr_config = {
            'use_gpu': False,
            'use_angle_cls': True,
            'lang': 'en',
            'det_db_thresh': 0.3,
            'det_db_box_thresh': 0.6,
            'det_db_unclip_ratio': 1.5,
            'rec_image_inverse': True,
            'rec_image_shape': '3, 48, 320',
            'rec_batch_num': 6,
            'max_text_length': 25,
            'use_space_char': True,
            'drop_score': 0.5,
            'cls_batch_num': 6,
            'cls_thresh': 0.9,
            'det_limit_side_len': 960,
            'det_limit_type': 'max',
            'rec_algorithm': 'SVTR_LCNet',
            'det_algorithm': 'DB',
        }

        # Initialize PaddleOCR for general and PDF-specific processing
        self.ocr = PaddleOCR(**self.ocr_config)

        pdf_config = self.ocr_config.copy()
        pdf_config['cls'] = False  # Disable classification for PDFs
        self.ocr_pdf = PaddleOCR(**pdf_config)

    def extract_text_data(self, results):
        """Extract text and spatial information from OCR results."""
        text_data = []
        for res in results:
            for line in res:
                bbox, text_info = line
                text, confidence = text_info

                # Extract coordinates
                x1, y1 = bbox[0]
                x2, y2 = bbox[1]
                x3, y3 = bbox[2]
                x4, y4 = bbox[3]

                width = max(abs(x2 - x1), abs(x3 - x4))
                height = max(abs(y3 - y1), abs(y4 - y2))

                center_y = (y1 + y2 + y3 + y4) / 4
                top_y = min(y1, y2)
                bottom_y = max(y3, y4)

                if confidence > 0.6:
                    text_data.append({
                        "text": text,
                        "x": x1,
                        "y": center_y,
                        "top_y": top_y,
                        "bottom_y": bottom_y,
                        "confidence": confidence,
                        "width": width,
                        "height": height,
                        "bbox": bbox
                    })
        return text_data

    def calculate_adaptive_y_threshold(self, text_data):
        """Calculate dynamic threshold for vertical line grouping."""
        if len(text_data) < 2:
            return 10

        y_values = [item["y"] for item in text_data]
        heights = [item["height"] for item in text_data if "height" in item]

        y_differences = [y_values[i+1] - y_values[i] for i in range(len(y_values) - 1) if y_values[i+1] - y_values[i] > 0]

        threshold = np.percentile(y_differences, 25) if y_differences else 10
        avg_height = np.mean(heights) if heights else 10
        return max(3, min(threshold, avg_height * 0.5, 15))

    def group_text_by_lines_improved(self, text_data):
        """Improved method to group text into structured lines."""
        if not text_data:
            return []

        text_data.sort(key=lambda item: item["y"])
        y_threshold = self.calculate_adaptive_y_threshold(text_data)

        grouped_lines = []
        current_line = [text_data[0]]

        for i in range(1, len(text_data)):
            current_item = text_data[i]
            prev_item = text_data[i-1]

            y_distance = abs(current_item["y"] - prev_item["y"])
            overlap = min(prev_item["bottom_y"], current_item["bottom_y"]) - max(prev_item["top_y"], current_item["top_y"])
            overlap_ratio = overlap / min(current_item["height"], prev_item["height"]) if min(current_item["height"], prev_item["height"]) > 0 else 0

            if y_distance <= y_threshold or overlap_ratio > 0.3:
                current_line.append(current_item)
            else:
                current_line.sort(key=lambda item: item["x"])
                grouped_lines.append(current_line)
                current_line = [current_item]

        if current_line:
            current_line.sort(key=lambda item: item["x"])
            grouped_lines.append(current_line)

        return grouped_lines

    def calculate_dynamic_widths(self, text_data):
        """Calculate average character and space width for structured formatting."""
        char_widths = [item["width"] / len(item["text"]) for item in text_data if len(item["text"]) > 1]

        if not char_widths:
            return 6, 6

        avg_char_width = np.median(char_widths)
        space_width = avg_char_width * 0.9
        return avg_char_width, space_width

    def render_text_with_dynamic_spacing(self, text_elements, char_width, space_width):
        """Format structured text with correct spacing."""
        rendered_text = ""
        prev_x = None
        prev_width = 0

        for element in text_elements:
            text = element["text"]
            x = element["x"]
            width = element.get("width", len(text) * char_width)

            if prev_x is not None:
                gap = x - (prev_x + prev_width)
                space_count = max(1, round(gap / space_width)) if gap > 0 else 1
                rendered_text += " " * space_count
            else:
                rendered_text += " " * max(0, round(x / space_width))

            rendered_text += text
            prev_x = x
            prev_width = width

        return rendered_text
    

    async def extract_text(self, file):
        """Main OCR function for processing image or PDF files."""
        contents = await file.read()
        contents = contents[4:]
        minio_storage = MinioStorage()
        minio_storage.store_file(file.filename, contents, file.content_type, minio_storage.bucket_name)

        mime_type, _ = mimetypes.guess_type(file.filename)

        if file.content_type.startswith('image/') or mime_type.startswith('image/'):
            image = Image.open(io.BytesIO(contents))
            image_array = np.array(image)
            result = self.ocr.ocr(image_array)

        # elif file.content_type.startswith('application/pdf') or mime_type.startswith('application/pdf'):
        #     result = self.ocr_pdf.ocr(contents)

        elif file.content_type.startswith('application/pdf') or mime_type.startswith('application/pdf'):
                images = convert_from_bytes(contents)
                extracted_text = ""
                for image in images:
                    image_array = np.array(image)
                    result = self.ocr.ocr(image_array)
                    extracted_text += self.process_extract_text(result) + "\n"
 

        else:
            raise ValueError("Unsupported file type. Only images and PDFs are supported.")

        text_data = self.extract_text_data(result)
        grouped_lines = self.group_text_by_lines_improved(text_data)
        char_width, space_width = self.calculate_dynamic_widths(text_data)

        extracted_text = "\n".join(self.render_text_with_dynamic_spacing(line, char_width, space_width) for line in grouped_lines)

        return extracted_text
