#!/usr/bin/env python3
"""
Script to add Wikidata information to the CSV file.
Reads 02_output.csv, searches Wikidata for each name, and adds results.
"""

import csv
import requests
import time
import sys
import json
import argparse
from urllib.parse import quote

def search_wikidata_by_name(name):
    """
    Search Wikidata for a person by name and return Q-code, Finnish label, and birth date.
    If initial search fails and name has more than two words, tries again with first and last word only.
    
    Args:
        name (str): The name to search for
    
    Returns:
        dict: {'qcode': str, 'wd_fi': str, 'wd_dob': str} or None if not found
    """
    def perform_search(search_name):
        """Helper function to perform the actual Wikidata search"""
        try:
            # Wikidata SPARQL query to search for people by name
            query = f"""
            SELECT ?person ?personLabel ?birthDate WHERE {{
              ?person wdt:P31 wd:Q5 .  # Instance of human
              ?person ?label "{search_name}"@fi .
              OPTIONAL {{ ?person wdt:P569 ?birthDate . }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fi,en" . }}
            }}
            LIMIT 1
            """
            
            # Wikidata SPARQL endpoint
            url = "https://query.wikidata.org/sparql"
            
            headers = {
                'User-Agent': 'Wikidata-Searcher/1.0 (projektfredrika.fi)',
                'Accept': 'application/sparql-results+json'
            }
            
            params = {
                'query': query,
                'format': 'json'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract results
            bindings = data.get('results', {}).get('bindings', [])
            
            if bindings:
                binding = bindings[0]
                qcode = binding.get('person', {}).get('value', '').split('/')[-1]
                finnish_label = binding.get('personLabel', {}).get('value', '')
                birth_date = binding.get('birthDate', {}).get('value', '')
                
                return {
                    'qcode': qcode,
                    'wd_fi': finnish_label,
                    'wd_dob': birth_date
                }
            
            return None
            
        except Exception as e:
            print(f"Error searching Wikidata for '{search_name}': {str(e)}")
            return None
    
    # First attempt with the full name
    result = perform_search(name)
    if result:
        return result
    
    name_words = name.strip().split()
    
    # Second attempt: if name has more than two words, try with first and last word only
    if len(name_words) > 2:
        # Remove the second word (middle name) and keep first and last
        fallback_name = f"{name_words[0]} {name_words[-1]}"
        print(f"  No result for '{name}', trying fallback search with '{fallback_name}'...")
        result = perform_search(fallback_name)
        if result:
            return result
    
    # Third attempt: try with just the last name
    if len(name_words) > 1:
        last_name_only = name_words[-1]
        print(f"  No result for '{name}', trying fallback search with last name only '{last_name_only}'...")
        result = perform_search(last_name_only)
        if result:
            return result
    
    return None


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Add Wikidata information to CSV file')
    parser.add_argument('--start-row', type=int, default=1, 
                       help='Row number to start processing from (1-based, default: 1)')
    parser.add_argument('--input', default='02_output.csv',
                       help='Input CSV file (default: 02_output.csv)')
    parser.add_argument('--output', default='03_output.csv',
                       help='Output CSV file (default: 03_output.csv)')
    
    args = parser.parse_args()
    
    input_file = args.input
    output_file = args.output
    start_row = args.start_row
    
    print(f"Loading data from {input_file}...")
    print(f"Starting from row {start_row}")
    
    # Read the CSV file
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
    except FileNotFoundError:
        print(f"Error: {input_file} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        sys.exit(1)
    
    print(f"Loaded {len(rows)} rows from {input_file}")
    
    # Validate start_row against total rows
    if start_row < 1 or start_row > len(rows):
        print(f"Error: start-row must be between 1 and {len(rows)}")
        sys.exit(1)
    
    # Slice rows starting from start_row (convert to 0-based index)
    rows_to_process = rows[start_row - 1:]
    print(f"Starting from row {start_row} of {len(rows)} total rows")
    print(f"Processing {len(rows_to_process)} rows")
    
    # First pass: filter out rows with ks. = 1
    eligible_rows = []
    skipped_count = 0
    
    for i, row in enumerate(rows_to_process):
        original_index = start_row - 1 + i  # Original position in full CSV
        ks_value = row.get('ks.', '')
        
        # Skip rows where ks. = 1
        if ks_value == '1':
            print(f"Row {original_index+1}: Skipping '{row.get('firstlast', '')}' (ks. = 1)")
            skipped_count += 1
            continue
        
        name = row.get('firstlast', '')
        if not name:
            continue
            
        eligible_rows.append((original_index, row))  # Store original row index and row data
    
    print(f"Found {len(eligible_rows)} eligible rows after filtering out ks. = 1")
    
    if len(eligible_rows) == 0:
        print("No eligible rows to process")
        sys.exit(0)
    
    # Second pass: process eligible rows
    filtered_rows = []
    processed_count = 0
    
    for eligible_index, (original_index, row) in enumerate(eligible_rows):
        name = row.get('firstlast', '')
        print(f"Row {original_index+1} (eligible #{eligible_index+1}): Searching Wikidata for '{name}'...")
        
        # Search Wikidata
        result = search_wikidata_by_name(name)
        
        if result:
            print(f"  Found: {result['qcode']} - {result['wd_fi']}")
            row['wd'] = result['qcode']
            row['wd_fi'] = result['wd_fi']
            row['wd_dob'] = result['wd_dob']
        else:
            print(f"  No Wikidata entry found")
            row['wd'] = ''
            row['wd_fi'] = ''
            row['wd_dob'] = ''
        
        filtered_rows.append(row)
        processed_count += 1
        
        # Be nice to the API - add a small delay
        time.sleep(0.5)
    
    print(f"\nProcessed {processed_count} rows from row {start_row} onwards")
    print(f"Skipped {skipped_count} rows with ks. = 1")
    
    # Write the filtered CSV with new columns
    if filtered_rows:
        # Get fieldnames from the first row and add new columns
        fieldnames = list(filtered_rows[0].keys())
        
        try:
            with open(output_file, 'w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(filtered_rows)
            
            print(f"Results saved to {output_file}")
            print(f"Total rows in output: {len(filtered_rows)}")
            
        except Exception as e:
            print(f"Error writing {output_file}: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()