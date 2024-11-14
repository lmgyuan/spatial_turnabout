from bs4 import BeautifulSoup
import re

def clean_text(element):
    if isinstance(element, str):
        return element.strip()
    return ""

def parse_html(html_content):
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
                output_lines.append(element_text)
            
        # If element is a tag and it's an image (<img>) tag
        if element.name == 'img':
            image_src = element.get('src')
            if image_src:
                output_lines.append(f"Image: {image_src}")
                
    # Write the output to a file
    with open("output.txt", "w", encoding="utf-8") as f:
        for line in output_lines:
            f.write(line + "\n")

    print("HTML content has been parsed and written to 'output.txt'")

with open("../html/Chapter-1_Daily-Life_Part-7.html") as f:
    html_content = f.read()
    parse_html(html_content)