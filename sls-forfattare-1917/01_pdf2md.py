import pdfplumber
import csv

path = "material/Suomen kirjailijat 1917-1944.pdf"
pages = "13-574"
skip_pages = "273-306, 387-394"
page_limit = -1

def parse_skip_pages(skip_pages_str):
    """Parse skip_pages string into a list of page ranges to skip"""
    if not skip_pages_str.strip():
        return []
    
    skip_ranges = []
    for range_str in skip_pages_str.split(','):
        range_str = range_str.strip()
        if '-' in range_str:
            start, end = map(int, range_str.split('-'))
            skip_ranges.append((start, end))
        else:
            # Single page
            skip_ranges.append((int(range_str), int(range_str)))
    
    return skip_ranges

def is_page_skipped(page_num, skip_ranges):
    """Check if a page should be skipped"""
    for start, end in skip_ranges:
        if start <= page_num <= end:
            return True
    return False

def load_exclusion_patterns():
    """Load patterns from 01_not_header.txt that should not be treated as headers"""
    try:
        with open("01_not_header.txt", 'r', encoding='utf-8') as f:
            patterns = [line.strip() for line in f.readlines() if line.strip()]
        return patterns
    except FileNotFoundError:
        print("Warning: 01_not_header.txt not found. No exclusion patterns will be applied.")
        return []

def load_inclusion_patterns():
    """Load patterns from 01_is_header.txt that should be treated as headers"""
    try:
        with open("01_is_header.txt", 'r', encoding='utf-8') as f:
            patterns = [line.strip() for line in f.readlines() if line.strip()]
        return patterns
    except FileNotFoundError:
        print("Warning: 01_is_header.txt not found. No inclusion patterns will be applied.")
        return []

def load_replacement_map():
    """Load replacement mappings from 01_replace.csv"""
    replacement_map = {}
    try:
        with open("01_replace.csv", 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            for row in reader:
                if len(row) >= 2:
                    original = row[0].strip()
                    replacement = row[1].strip()
                    if original and replacement:
                        replacement_map[original] = replacement
        print(f"Loaded {len(replacement_map)} replacement mappings.")
        return replacement_map
    except FileNotFoundError:
        print("Warning: 01_replace.csv not found. No text replacements will be applied.")
        return {}

def extract_pdf_text(pdf_path, pages_range, page_limit, skip_pages_str):
    # Load replacement map early
    replacement_map = load_replacement_map()
    
    # Parse the pages range
    start_page, end_page = map(int, pages_range.split('-'))
    
    # Apply page limit if specified
    if page_limit > 0:
        end_page = min(start_page + page_limit - 1, end_page)
    
    # Parse skip pages
    skip_ranges = parse_skip_pages(skip_pages_str)
    
    # Open the PDF file
    with pdfplumber.open(pdf_path) as pdf:
        pdf_total_pages = len(pdf.pages)
        
        debug_output = ""
        clean_output = ""
        
        # Track continuous page numbering for HTML comments
        # This counts only the processed pages, skipping "extra" unnumbered pages
        continuous_page_num = start_page
        
        # Extract text from specified pages
        for page_num in range(start_page - 1, min(end_page, pdf_total_pages)):
            actual_page_num = page_num + 1  # Convert to 1-based numbering
            
            # Skip this page if it's in the skip list (extra pages without numbers)
            if is_page_skipped(actual_page_num, skip_ranges):
                print(f"Skipping extra page {actual_page_num} (no page number)...")
                continue
            
            print(f"Processing page {actual_page_num} (numbered as {continuous_page_num})...")
            page = pdf.pages[page_num]
            
            # Get page dimensions
            page_width = page.width
            page_height = page.height
            
            # Define layout zones
            header_height = page_height * 0.047  # Top 4.7% is header
            
            # Process text by layout zones using continuous page numbering
            # (skipping unnumbered extra pages)
            debug_text, clean_text = process_page_layout(page, page_width, page_height, header_height, continuous_page_num, replacement_map)
            debug_output += debug_text
            clean_output += clean_text
            
            # Increment continuous page number only for processed pages
            continuous_page_num += 1
        
        # Write debug output
        with open("01_output_debug.txt", 'w', encoding='utf-8') as f:
            f.write(debug_output)
        
        # Write clean output
        with open("01_output.md", 'w', encoding='utf-8') as f:
            f.write(clean_output)
        
        print("Debug output saved to 01_output_debug.txt")
        print("Clean output saved to 01_output.md")

def process_page_layout(page, page_width, page_height, header_height, page_num, replacement_map):
    # Extract all text objects with their positions
    words = page.extract_words()
    
    # Separate header and content
    header_words = [w for w in words if w['top'] < header_height]
    content_words = [w for w in words if w['top'] >= header_height]
    
    debug_result = ""
    clean_result = ""
    
    # Process header
    if header_words:
        header_text = " ".join([w['text'] for w in sorted(header_words, key=lambda x: x['x0'])])
        debug_result += "HEADER:\n"
        debug_result += header_text + "\n\n"
        clean_result += f"<!-- Page {page_num}: {header_text} -->\n\n"
    
    # Process content in two columns
    if content_words:
        # Split into left and right columns
        mid_x = page_width / 2
        left_column = [w for w in content_words if w['x0'] < mid_x]
        right_column = [w for w in content_words if w['x0'] >= mid_x]
        
        # Sort each column by top position, then by left position
        left_column.sort(key=lambda x: (x['top'], x['x0']))
        right_column.sort(key=lambda x: (x['top'], x['x0']))
        
        # Process columns
        left_debug, left_clean = process_column(left_column, replacement_map)
        right_debug, right_clean = process_column(right_column, replacement_map)
        
        # Add column content
        if left_debug.strip():
            debug_result += "LEFT COLUMN:\n"
            debug_result += left_debug + "\n"
            clean_result += left_clean + "\n"
        if right_debug.strip():
            debug_result += "RIGHT COLUMN:\n"
            debug_result += right_debug + "\n"
            clean_result += right_clean + "\n"
    
    return debug_result, clean_result

def is_excluded_header(line_text, exclusion_patterns):
    """Check if a line should be excluded from being treated as a header"""
    for pattern in exclusion_patterns:
        if line_text.startswith(pattern):
            return True
    return False

def is_included_header(line_text, inclusion_patterns):
    """Check if a line should be treated as a header based on inclusion patterns"""
    for pattern in inclusion_patterns:
        if line_text == pattern:
            return True
    return False

def is_probable_header(text):
    """
    Check if text is likely a header based on capitalization patterns.
    Returns True if:
    - First character is uppercase, OR
    - Text starts with lowercase followed by apostrophe and capital letter (e.g., "d’Ornot")
    - Text starts with "de " or "van " followed by a capital letter (e.g., "de Vries", "van Gogh")
    """
    if not text:
        return False
    
    # First character is uppercase
    if text[0].isupper():
        return True
    
    # Check for lowercase + apostrophe + capital pattern (e.g., "d’Ornot")
    if len(text) >= 3:
        if text[0].islower() and text[1] == "’" and text[2].isupper():
            return True
    
    # Check for "de " followed by capital letter (e.g., "de Vries")
    if text.startswith("de ") and len(text) >= 4:
        if text[3].isupper():
            return True
    
    # Check for "van " followed by capital letter (e.g., "van Gogh")
    if text.startswith("van ") and len(text) >= 5:
        if text[4].isupper():
            return True
    
    return False

def process_column(column_words, replacement_map):
    if not column_words:
        return "", ""
    
    # Load exclusion patterns
    exclusion_patterns = load_exclusion_patterns()
    
    # Load inclusion patterns
    inclusion_patterns = load_inclusion_patterns()
    
    debug_result = ""
    clean_result = ""
    current_line = []
    current_line_height = None
    previous_line_height = None
    
    for word in column_words:
        line_height = word.get('top', 0)
        
        # Check if we're starting a new line (significant vertical movement)
        if current_line_height and abs(line_height - current_line_height) > 5:
            # Process the current line
            if current_line:
                # Sort words within the line by horizontal position
                current_line.sort(key=lambda x: x['x0'])
                line_text = " ".join([w['text'] for w in current_line])
                
                # Apply replacement if the line exists in replacement_map
                if line_text in replacement_map:
                    line_text = replacement_map[line_text]
                avg_height = sum(w.get('height', 0) for w in current_line) / len(current_line)
                first_word_x = current_line[0]['x0'] if current_line else 0
                
                # Calculate distance from previous row
                if previous_line_height is not None:
                    distance = current_line_height - previous_line_height
                    # Add empty row if distance >= 12.5
                    if distance >= 12.5:
                        debug_result += "\n"
                        clean_result += "\n"
                    
                    # Check if this is a header
                    # First check if line matches inclusion patterns
                    if is_included_header(line_text, inclusion_patterns):
                        is_header = True
                    else:
                        # A line is a header if it has large height, sufficient distance, contains no numbers, starts with capital letter, is not excluded, and is longer than 1 character
                        is_header = (avg_height > 8.5 and distance > 24 and 
                                   not any(char.isdigit() for char in line_text) and 
                                   is_probable_header(line_text) and
                                   len(line_text.strip()) > 1 and
                                   not is_excluded_header(line_text, exclusion_patterns))
                    if is_header:
                        debug_result += f"[height: {avg_height:.1f}px, distance: {distance:.1f}px, x: {first_word_x:.1f}px] ## {line_text}\n"
                        clean_result += f"## {line_text}\n"
                    else:
                        debug_result += f"[height: {avg_height:.1f}px, distance: {distance:.1f}px, x: {first_word_x:.1f}px] {line_text}\n"
                        clean_result += f"{line_text}\n"
                else:
                    # First row - check if header based on height only, no numbers, starts with capital letter, is not excluded, and is longer than 1 character
                    # First check if line matches inclusion patterns
                    if is_included_header(line_text, inclusion_patterns):
                        is_header = True
                    else:
                        is_header = (avg_height > 8.5 and 
                                   not any(char.isdigit() for char in line_text) and 
                                   is_probable_header(line_text) and
                                   len(line_text.strip()) > 1 and
                                   not is_excluded_header(line_text, exclusion_patterns))
                    if is_header:
                        debug_result += f"[height: {avg_height:.1f}px, distance: N/A, x: {first_word_x:.1f}px] ## {line_text}\n"
                        clean_result += f"## {line_text}\n"
                    else:
                        debug_result += f"[height: {avg_height:.1f}px, distance: N/A, x: {first_word_x:.1f}px] {line_text}\n"
                        clean_result += f"{line_text}\n"
                
                previous_line_height = current_line_height
            
            # Start new line
            current_line = [word]
            current_line_height = line_height
        else:
            # Continue current line
            current_line.append(word)
            current_line_height = line_height
    
    # Process the last line
    if current_line:
        # Sort words within the line by horizontal position
        current_line.sort(key=lambda x: x['x0'])
        line_text = " ".join([w['text'] for w in current_line])
        
        # Apply replacement if the line exists in replacement_map
        if line_text in replacement_map:
            line_text = replacement_map[line_text]
        
        avg_height = sum(w.get('height', 0) for w in current_line) / len(current_line)
        first_word_x = current_line[0]['x0'] if current_line else 0
        
        if previous_line_height is not None:
            distance = current_line_height - previous_line_height
            # Add empty row if distance >= 12.5
            if distance >= 12.5:
                debug_result += "\n"
                clean_result += "\n"
            
            # Check if this is a header
            # First check if line matches inclusion patterns
            if is_included_header(line_text, inclusion_patterns):
                is_header = True
            else:
                # A line is a header if it has large height, sufficient distance, contains no numbers, starts with capital letter, is not excluded, and is longer than 1 character
                is_header = (avg_height > 8.5 and distance > 24 and 
                           not any(char.isdigit() for char in line_text) and 
                           is_probable_header(line_text) and
                           len(line_text.strip()) > 1 and
                           not is_excluded_header(line_text, exclusion_patterns))
            if is_header:
                debug_result += f"[height: {avg_height:.1f}px, distance: {distance:.1f}px, x: {first_word_x:.1f}px] ## {line_text}\n"
                clean_result += f"## {line_text}\n"
            else:
                debug_result += f"[height: {avg_height:.1f}px, distance: {distance:.1f}px, x: {first_word_x:.1f}px] {line_text}\n"
                clean_result += f"{line_text}\n"
        else:
            # First row - check if header based on height only, no numbers, starts with capital letter, is not excluded, and is longer than 1 character
            # First check if line matches inclusion patterns
            if is_included_header(line_text, inclusion_patterns):
                is_header = True
            else:
                is_header = (avg_height > 8.5 and 
                           not any(char.isdigit() for char in line_text) and 
                           is_probable_header(line_text) and
                           len(line_text.strip()) > 1 and
                           not is_excluded_header(line_text, exclusion_patterns))
            if is_header:
                debug_result += f"[height: {avg_height:.1f}px, distance: N/A, x: {first_word_x:.1f}px] ## {line_text}\n"
                clean_result += f"## {line_text}\n"
            else:
                debug_result += f"[height: {avg_height:.1f}px, distance: N/A, x: {first_word_x:.1f}px] {line_text}\n"
                clean_result += f"{line_text}\n"
    
    return debug_result, clean_result

def main():
    extract_pdf_text(path, pages, page_limit, skip_pages)

if __name__ == "__main__":
    main()
