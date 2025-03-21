import pandas as pd

def compare_csv(file1, file2, output_file):
    # Load CSV files
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    compare_columns = ["Bill_Number", "Date", "Bill_Amount", "Time", "Bill_Category"]

    # Merge data on filename to compare row by row
    merged_df = df1.merge(df2, on="filename", suffixes=("_file1", "_file2"), how="outer")

    # Find mismatches in specified columns
    diff_rows = []
    for _, row in merged_df.iterrows():
        mismatches = {}
        for col in compare_columns:
            col1 = f"{col}_file1"
            col2 = f"{col}_file2"
            if row[col1] != row[col2]:  # Check if values differ
                mismatches[col] = (row[col1], row[col2])
        
        if mismatches:
            diff_rows.append({"filename": row["filename"], "differences": mismatches})

    # Save differences to a new CSV file
    diff_df = pd.DataFrame(diff_rows)
    diff_df.to_csv(output_file, index=False)
    
    print(f"Comparison complete! Differences saved to {output_file}")

file1 = "./output_results_new.csv"  
file2 = "./correct_results_new.csv"  
output_file = "differences_new.csv"

compare_csv(file1, file2, output_file)
