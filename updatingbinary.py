# # Define the path to your image file
# image_path = "internet-bill_8.png"
# output_image_path = "up_internet-bill_8.png"

# # Read the image file in binary mode
# with open(image_path, "rb") as image_file:
#     image_data = image_file.read()

# # Define the characters \r\n\r\n (CRLF + CRLF)
# newline_bytes = b"\r\n\r\n"

# # Prepend the newline bytes to the image data
# updated_image_data = newline_bytes + image_data

# # Write the updated binary data to a new image file
# with open(output_image_path, "wb") as updated_image_file:
#     updated_image_file.write(updated_image_data)

# print(f"Updated image saved as {output_image_path}")


import os

# Define the folder containing images
input_folder = "./images"
output_folder = "./updated_bills"

# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Define the characters \r\n\r\n (CRLF + CRLF)
newline_bytes = b"\r\n\r\n"

# Loop through all files in the input folder
for filename in os.listdir(input_folder):
    input_path = os.path.join(input_folder, filename)

    # Ensure it's a file and likely an image
    if os.path.isfile(input_path) and filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
        output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_updated{os.path.splitext(filename)[1]}")
        
        # Read the image file in binary mode
        with open(input_path, "rb") as image_file:
            image_data = image_file.read()

        # Prepend the newline bytes to the image data
        updated_image_data = newline_bytes + image_data

        # Write the updated binary data to a new image file
        with open(output_path, "wb") as updated_image_file:
            updated_image_file.write(updated_image_data)

        print(f"Updated image saved as {output_path}")

print("Processing complete.")

