import pandas as pd
from datetime import datetime

# Read the CSV file
df = pd.read_csv('correct_results.csv')

# Function to convert date to mm/dd/yyyy format
def convert_date(date):
    try:
        # Convert the date string to a datetime object
        date_obj = datetime.strptime(str(date), '%m/%d/%Y')  # Assuming the initial format is mm/dd/yyyy
        # Return the formatted date with leading zeros where necessary
        return date_obj.strftime('%m/%d/%Y')
    except ValueError:
        # If the date is already in the correct format or can't be converted, return it as it is
        return date

# Apply the function to the 'Date' column
df['Date'] = df['Date'].apply(convert_date)

# Save the updated dataframe back to a new CSV file
df.to_csv('updated_file.csv', index=False)

print("CSV file updated successfully!")
