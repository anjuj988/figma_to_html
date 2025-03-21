from paddleocr import PPStructure, draw_structure_result, save_structure_res
import cv2
import matplotlib.pyplot as plt

# Initialize PPStructure with table detection
pp_structure = PPStructure()

# Path to your image
img_path = "/content/food-bill_10.png"

# Read the image
image = cv2.imread(img_path)
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Analyze the layout of the bill
layout_result = pp_structure(img_path)

# Save structured results
save_structure_res(layout_result, "./", img_name="bill_structure")

# Visualize the layout results
image_with_layout = draw_structure_result(image, layout_result, font_path="/content/Roboto-Regular.ttf")

# Display the processed image
plt.figure(figsize=(10, 10))
plt.imshow(image_with_layout)
plt.axis("off")
plt.show()

# Print structured results for debugging
print("Extracted Structured Data:", layout_result)
