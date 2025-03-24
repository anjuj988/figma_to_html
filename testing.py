from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
import io
from .utils.storage import MinioStorage
import mimetypes
# from pdf2image import convert_from_bytes


class OCRService:
    def __init__(self):
        # Common OCR configuration parameters
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

        # Initialize PaddleOCR for general use
        self.ocr = PaddleOCR(**self.ocr_config)

        # Initialize PaddleOCR specifically for PDFs with cls disabled
        pdf_config = self.ocr_config.copy()
        pdf_config['cls'] = False  # Disable classification for PDFs
        self.ocr_pdf = PaddleOCR(**pdf_config)

        
    
    def process_extract_text(self, text):
        # Process the extracted text here
        def avg_y(block):
            return np.mean([block[0][1], block[1][1], block[2][1], block[3][1]])

        # Function to get the average x-coordinate of a block
        def avg_x(block):
            return np.mean([block[0][0], block[1][0], block[2][0], block[3][0]])

        ocr_results = text[0]

        # Sort by average Y-coordinate (line-wise sorting)
        ocr_results.sort(key=lambda x: avg_y(x[0]))

        # Group lines by a threshold to handle small variations in Y
        lines = []
        current_line = []
        threshold = 15  # Adjust this based on text size and resolution

        for i, block in enumerate(ocr_results):
            if not current_line:
                current_line.append(block)
            else:
                # Check if the current block is in the same line as the previous one
                if abs(avg_y(block[0]) - avg_y(current_line[-1][0])) < threshold:
                    current_line.append(block)
                else:
                    # Sort the current line by X-coordinate and add to lines
                    current_line.sort(key=lambda x: avg_x(x[0]))
                    lines.append(current_line)
                    current_line = [block]

        # Append the last line
        if current_line:
            current_line.sort(key=lambda x: avg_x(x[0]))
            lines.append(current_line)

        # Reconstruct the paragraph
        paragraph = []
        for line in lines:
            paragraph.append(" ".join([block[1][0] for block in line]))

        # Join lines to form the full paragraph
        paragraph_text = "\n".join(paragraph)
        return paragraph_text

    async def extract_text(self, file):
        # Read the uploaded file
        contents = await file.read()
        # temp fix for appforms
        contents = contents[4:]
        minio_storage = MinioStorage()
        
        # Store file with proper content type
        minio_storage.store_file(
            file_name=file.filename,
            data=contents,
            content_type=file.content_type,
            bucket_name=minio_storage.bucket_name
        )
 #121122
        mime_type, _ = mimetypes.guess_type(file.filename)
        # Process based on file type
        if file.content_type.startswith('image/') or mime_type.startswith('image/'):
            image = Image.open(io.BytesIO(contents))
            image_array = np.array(image)
            result = self.ocr.ocr(image_array)
            extracted_text = self.process_extract_text(result)

        elif file.content_type.startswith('application/pdf') or mime_type.startswith('application/pdf'):
            result = self.ocr_pdf.ocr(contents)
            extracted_text = self.process_extract_text(result)
            
        else:
            raise ValueError("Unsupported file type. Only images and PDFs are supported.")
        
        return extracted_text    
            
        # elif file.content_type.startswith('application/pdf') or mime_type.startswith('application/pdf'):
        #         images = convert_from_bytes(contents)
        #         extracted_text = ""
        #         for image in images:
        #             image_array = np.array(image)
        #             result = self.ocr.ocr(image_array)
        #             extracted_text += self.process_extract_text(result) + "\n"
            
        # else:
        #         raise ValueError("Unsupported file type. Only images and PDFs are supported.")
            
        # return extracted_text