import csv
import re
import sys

# Function to extract the first GitHub URL from the `array_agg` column in a CSV file
def extract_github_url(csv_file_path):
    github_urls = []

    # Set the maximum field size limit to the maximum possible integer size
    max_int = sys.maxsize
    while True:
        # Decrease the max_int value by factor of 10 
        # as long as the OverflowError occurs.
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = int(max_int/10)

    with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        
        for row in csv_reader:
            # Extract the array_agg field and remove the curly braces
            array_agg_content = row['array_agg'].strip('{}')

            # Use regex to find URLs containing 'github.com'
            urls = re.findall(r'https?://github\.com[\w/.\-]+', array_agg_content)
            
            # If we find any URLs, append the first one to our list
            if urls:
                github_urls.append(urls[0])  # Take the first match

    return github_urls

# Provide the correct path to your CSV file
csv_file_path = 'vul_patch_info_full_one_record_only.csv'
extracted_urls = extract_github_url(csv_file_path)
print(extracted_urls)
