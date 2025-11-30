import csv
import re

def load_replacements(replace_file="02_replace.csv"):
    """
    Load replacement rules from CSV file.
    
    Args:
        replace_file (str): Path to the replacement CSV file
        
    Returns:
        dict: Dictionary mapping original names to replacement names
    """
    replacements = {}
    try:
        with open(replace_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    original = row[0].strip()
                    replacement = row[1].strip()
                    replacements[original] = replacement
        print(f"Loaded {len(replacements)} replacement rules from {replace_file}")
    except FileNotFoundError:
        print(f"Warning: Replacement file {replace_file} not found. No replacements will be applied.")
    except Exception as e:
        print(f"Error loading replacement file: {e}")
    
    return replacements

def parse_markdown_to_csv(input_file="01_output.md", output_file="02_output.csv"):
    """
    Parse the markdown file to extract headers and their associated content.
    
    Args:
        input_file (str): Path to the input markdown file
        output_file (str): Path to the output CSV file
    """
    csv_data = []
    
    # Load replacement rules
    replacements = load_replacements()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into lines
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this is a header (starts with ##)
        if line.startswith('##'):
            # Extract the name (text after ##)
            name = line[2:].strip()
            
            # Apply replacement if available
            if name in replacements:
                name = replacements[name]
            else:
                # Also check if the "firstlast" version matches any replacement key
                name_parts = name.split(',')
                if len(name_parts) >= 2:
                    firstlast_name = f"{name_parts[1].strip()} {name_parts[0].strip()}"
                    if firstlast_name in replacements:
                        name = replacements[firstlast_name]
            
            # Look for the page number in HTML comments before this header
            page_num = None
            j = i - 1
            while j >= 0:
                comment_match = re.search(r'<!-- Page (\d+):', lines[j])
                if comment_match:
                    page_num = int(comment_match.group(1))
                    break
                j -= 1
            
            # Collect aka content (lines after the header until empty line or next header)
            aka_lines = []
            i += 1
            
            # Check if the next line is empty - if so, this entry has no content
            if i < len(lines) and lines[i].strip() == '':
                # Header followed immediately by empty line - no content
                pass
            else:
                # Skip any empty lines immediately after header
                while i < len(lines) and lines[i].strip() == '':
                    i += 1
                
                # Collect content until we hit an empty line or next header
                while i < len(lines):
                    current_line = lines[i].strip()
                    
                    # Stop if we hit an empty line
                    if current_line == '':
                        break
                    
                    # Stop if we hit another header
                    if current_line.startswith('##'):
                        i -= 1  # Back up one line so the next iteration can process this header
                        break
                    
                    # Add this line to aka content
                    aka_lines.append(current_line)
                    i += 1
            
            # Join aka lines with semicolons and clean up
            aka = '; '.join(aka_lines).strip()

            # Check if first non-empty line after header and aka starts with a date (dd.mm.yyyy format)
            dob = None
            j = i
            while j < len(lines):
                current_line = lines[j].strip()
                if current_line != '':
                    # Check if this first non-empty line starts with a date
                    date_match = re.match(r'^(\d{1,2}\.\d{1,2}\.\d{4})', current_line)
                    if date_match:
                        dob = date_match.group(1)   
                    break  # Only check the first non-empty line
                j += 1
            
            # Now collect all content for counting (from header to next header)
            # Reset to line after header
            count_i = i - len(aka_lines) if aka_lines else i
            if count_i < len(lines) and lines[count_i].strip() == '':
                count_i += 1  # Skip empty line after header
            
            # Count all non-empty lines until next header and calculate total chars
            count = 0
            total_chars = 0
            page_end = page_num if page_num else None  # Initialize with page_start
            while count_i < len(lines):
                current_line = lines[count_i].strip()
                
                # Stop if we hit another header
                if current_line.startswith('##'):
                    break
                
                # Check for page comments and update page_end
                comment_match = re.search(r'<!-- Page (\d+):', current_line)
                if comment_match:
                    page_end = int(comment_match.group(1))
                
                # Count non-empty lines and their characters
                if current_line != '':
                    count += 1
                    total_chars += len(current_line)
                
                count_i += 1
            
            # Check if aka starts with "ks."
            ks_value = 1 if aka.lower().startswith('ks.') else 0
            
            # Create firstlast by splitting name by comma and reversing
            name_parts = name.split(',')
            if len(name_parts) >= 2:
                firstlast = f"{name_parts[1].strip()} {name_parts[0].strip()}"
            else:
                firstlast = name  # If no comma, keep original name
            
            # Add to CSV data
            csv_data.append({
                'name': name,
                'aka': aka,
                'page_start': page_num if page_num else '',
                'page_end': page_end if page_end else '',
                'row_count': count,
                'chars_count': total_chars,
                'ks.': ks_value,
                'firstlast': firstlast,
                'dob': dob if dob else ''
            })
        
        i += 1
    
    # Write CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if csv_data:
            writer = csv.DictWriter(f, fieldnames=['name', 'aka', 'page_start', 'page_end', 'row_count', 'chars_count', 'ks.', 'firstlast', 'dob'])
            writer.writeheader()
            writer.writerows(csv_data)
    
    print(f"CSV file created: {output_file}")
    print(f"Total entries: {len(csv_data)}")
    
    # Count rows without ks. value 1
    rows_without_ks = sum(1 for entry in csv_data if entry['ks.'] != 1)
    print(f"Rows without ks. value 1: {rows_without_ks}")
    
    # Print first entry as preview
    if csv_data:
        print("\nFirst entry:")
        entry = csv_data[0]
        print(f"Name: '{entry['name']}'")
        print(f"AKA: '{entry['aka']}'")
        print(f"Page start: {entry['page_start']}")
        print(f"Page end: {entry['page_end']}")
        print(f"Row count: {entry['row_count']}")
        print(f"Chars count: {entry['chars_count']}")
        print(f"ks.: {entry['ks.']}")
        print(f"firstlast: '{entry['firstlast']}'")
        print(f"dob: '{entry['dob']}'")
        print()

def main():
    parse_markdown_to_csv()

if __name__ == "__main__":
    main()
