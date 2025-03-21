import pandas as pd
import jiwer

# Function to calculate WER for a single field
def calculate_wer(ground_truth, ocr_text):
    transformation = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.Strip(),
        jiwer.RemoveMultipleSpaces()
    ])

    # Convert to string and handle None values
    ground_truth = str(ground_truth) if pd.notna(ground_truth) else ""
    ocr_text = str(ocr_text) if pd.notna(ocr_text) else ""

    # Ensure strings are not empty after transformation
    transformed_ground_truth = transformation(ground_truth)
    transformed_ocr_text = transformation(ocr_text)

    if not transformed_ground_truth or not transformed_ocr_text:
        return 1.0  # If one of the fields is empty, consider it 100% error

    return jiwer.wer(transformed_ground_truth, transformed_ocr_text)

# Define the fields to compare
fields_to_compare = ["Bill_Number", "Date", "Bill_Amount", "Time", "Bill_Category"]

# Load OCR extracted text and ground truth CSVs
try:
    ocr_df = pd.read_csv("output_results_new.csv")  # OCR extracted data
    ground_truth_df = pd.read_csv("correct_results_new.csv")  # Correct results
except FileNotFoundError as e:
    print(f"Error: {e}")
    exit(1)

# Ensure both files have required fields
for field in fields_to_compare:
    if field not in ocr_df.columns or field not in ground_truth_df.columns:
        raise ValueError(f"Missing field '{field}' in one of the CSV files.")

# Calculate WER for each field
wer_results = {}
for field in fields_to_compare:
    wer_per_record = []
    
    for i in range(len(ocr_df)):
        try:
            wer_value = calculate_wer(ground_truth_df.iloc[i][field], ocr_df.iloc[i][field])
            wer_per_record.append(wer_value)
        except Exception as e:
            print(f"Error processing record {i} for field '{field}': {e}")
            wer_per_record.append(1.0)  # Assume worst-case error for that record

    avg_wer = sum(wer_per_record) / len(wer_per_record) if wer_per_record else 0.0  # Avoid division by zero
    wer_results[field] = avg_wer

# Print results
print("\nWord Error Rate (WER) for selected fields:")
for field, wer in wer_results.items():
    print(f"{field}: {wer:.2%}")

# Save results to a CSV
pd.DataFrame(wer_results.items(), columns=["Field", "WER"]).to_csv("wer_results.csv", index=False)
print("\nWER results saved to 'wer_results.csv'.")
