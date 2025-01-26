from bs4 import BeautifulSoup
import re

def clean_text(element):
    if isinstance(element, str):
        return element.strip()
    return ""

def select_image(input_string):
    if "emot-siren.gif" in input_string:
        return False
    # Extract the filename using regex (assuming format is 'Image: <filename>')
    match = re.search(r"\s*(\S+)", input_string)
    if match:
        filename = match.group(1)
        
        # Remove the file extension (e.g., '.png')
        base_filename = filename.rsplit('.', 1)[0]
        
        # Check if any character in the filename is alphabetic
        return any(char.isalpha() for char in base_filename)
    
    return False  # In case the input string doesn't match the expected format

def parse_nontrial_html(html_content):
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Prepare to write the parsed output to a file
    output_lines = []

    # Flag to determine if we are past the "Chapter" line
    started = False

    # Iterate through each element in the parsed HTML
    for element in soup.descendants:
        # Skip elements that don't contain useful text
        if isinstance(element, str):
            element_text = clean_text(element)
            
            if not started:
                # Check for the "Chapter" line to start processing
                if element_text.startswith("Chapter"):
                    started = True
                continue
            
            # Process text when we are past the chapter line
            if element_text:
                if element_text == "google_ad_section_end":
                    break
                output_lines.append(element_text)
            
        # If element is a tag and it's an image (<img>) tag
        if element.name == 'img':
            image_src = element.get('src')
            if image_src and select_image(image_src):
                output_lines.append(f"{image_src}")
                
    return '\n'.join(output_lines) + '\n'

def parse_trial_html(html_content):
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Prepare to write the parsed output to a file
    output_lines = []

    # Flag to determine if we are past the "Chapter" line
    started = False

    # Iterate through each element in the parsed HTML
    for element in soup.descendants:
        is_br = element.name == 'b'
        # Skip elements that don't contain useful text
        if is_br or isinstance(element, str):
            if isinstance(element, str):
                element_text = clean_text(element)
            if not started:
                # Check for the "Chapter" line to start processing
                if element_text.startswith("Trial"):
                    started = True
                continue
            
            # Process text when we are past the chapter line
            if element_text:
                if "Click here to watch this update's video." in element_text:
                    continue
                if element_text == "google_ad_section_end":
                    break
                if is_br:
                    element_text = "**"
                output_lines.append(element_text)
            
        # If element is a tag and it's an image (<img>) tag
        if element.name == 'img':
            image_src = element.get('src')
            if image_src and select_image(image_src):
                output_lines.append(f"{image_src}")
                
    return '\n'.join(output_lines) + '\n'

def parse_nontrial():
    for ch in range(1,7):
        for life in ["Daily-Life", "Deadly-Life"]:
            pt = 1
            while True:
                fname = f"../html/Chapter-{ch}_{life}_Part-{pt}.html"
                print(fname)
                out_fname = f"../text/Chapter-{ch}_{life}_Part-{pt}.txt"
                try:
                    with open(fname) as f, open(out_fname, 'w') as fw:
                        html_content = f.read()
                        parsed_text = parse_nontrial_html(html_content)
                        fw.write(parsed_text)
                except FileNotFoundError:
                    break
                pt += 1
            
def parse_trial():
    for ch in range(1,7):
        for life in ["Class-Trial"]:
            pt = 1
            while True:
                fname = f"../html/Chapter-{ch}_{life}_Part-{pt}.html"
                print(fname)
                out_fname = f"../text/Chapter-{ch}_{life}_Part-{pt}.txt"
                try:
                    with open(fname) as f, open(out_fname, 'w') as fw:
                        html_content = f.read()
                        parsed_text = parse_trial_html(html_content)
                        fw.write(parsed_text)
                except FileNotFoundError:
                    break
                pt += 1

parse_trial()