import os
import time
import requests
import csv
import mimetypes

def process_images(folder_path, output_csv):
    api_url = "https://expenseprocessing.unysite.com/process-ocr"
    params = {"configuration": "process-bill"}
    headers = {"Accept": "application/json"}  # DO NOT set 'Content-Type' manually

    # Read existing CSV and store processed filenames
    processed_files = set()
    if os.path.exists(output_csv):
        with open(output_csv, mode="r", newline="") as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header
            for row in reader:
                if row:
                    processed_files.add(row[0])  # First column is filename

    images = [f for f in os.listdir(folder_path) if f.lower().endswith(('png', 'jpg', 'jpeg'))]

    # Open CSV in append mode
    with open(output_csv, mode="a", newline="") as file:
        writer = csv.writer(file)

        # Write header if file is empty
        if os.stat(output_csv).st_size == 0:
            writer.writerow(["filename", "Bill_Number", "Date", "Bill_Amount", "Time", "Bill_Category", "processing_time", "status"])

        for image in images:
            if image in processed_files:
                print(f"Skipping {image}, already processed.")
                continue  # Skip if already in CSV
            
            file_path = os.path.join(folder_path, image)
            if not os.path.isfile(file_path):
                print(f"File not found: {image}")
                writer.writerow([image, "File Not Found", "File Not Found", "File Not Found", "File Not Found", "File Not Found", "failed"])
                continue
            
            # Get the correct MIME type dynamically (Keeping your original logic)
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = "application/octet-stream"  # Fallback if unknown type

            try:
                with open(file_path, "rb") as f:
                    files = {"file": (image, f, mime_type)}
                    
                    print(f"Uploading {image} ({mime_type})...")
                    response = requests.post(api_url, params=params, headers=headers, files=files, verify=False)
                    
                    if response.status_code == 200:
                        data = response.json()
                        response_data = data.get("response", {})
                        writer.writerow([
                            image,
                            response_data.get("Bill_Number", "Not Available"),
                            response_data.get("Date", "Not Available"),
                            response_data.get("Bill_Amount", "Not Available"),
                            response_data.get("Time", "Not Available"),
                            response_data.get("Bill_Category", "Not Available"),
                            data.get("processing_time", "N/A"),
                            data.get("status", "failed")
                        ])
                        print(f"Response received for {image}, processing complete.")
                    else:
                        print(f"Error processing {image}. Status code: {response.status_code}, Response: {response.text}")
                        writer.writerow([image, "Error", "Error", "Error", "Error", "Error", "failed"])
                    
            except Exception as e:
                print(f"An error occurred while processing {image}: {e}")
                writer.writerow([image, "Error", "Error", "Error", "Error", "Error", "failed"])
            
            print(f"Waiting for 5 seconds before processing the next file...")
            time.sleep(5)

    print(f"Processing complete. Results saved to {output_csv}")

folder_path = "./updated_bills"
output_csv = "output_results6.csv"
process_images(folder_path, output_csv)
