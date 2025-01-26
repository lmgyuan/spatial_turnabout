import requests
from bs4 import BeautifulSoup
import re

def parse_catalog():
    catalog = []
    current_chapter = ""
    current_stage = ""

    with open('../html/catalog.html', 'r') as file:
        for line in file:
            if line.startswith("<b><u>"):
                current_chapter = BeautifulSoup(line, 'html.parser').get_text().strip()
            elif line.startswith("<b>"):
                current_stage = BeautifulSoup(line, 'html.parser').get_text().strip()
            elif line.startswith("<a href"):
                match = re.search(r'href="([^"]+)"[^>]*>([^<]+)', line)
                url = match.group(1)  # "Update%2007/"
                current_part = match.group(2)  # "Part 1"
                catalog.append([url, current_chapter, current_stage, current_part])

    #print(catalog)
    return catalog

def crawl_website(url):
    # Send a GET request to the website
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        print(f"Successfully fetched content from {url}")
        
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Get the raw HTML as a string
        html_content = soup.prettify()  # prettify to format the HTML
        return html_content
    else:
        print(f"Failed to retrieve content from {url} (Status code: {response.status_code})")
        return None

if __name__ == "__main__":
    catalog = parse_catalog()
    for url, current_chapter, current_stage, current_part in catalog:
        full_url = f"https://lparchive.org/Danganronpa-Trigger-Happy-Havoc/{url}"
        html = crawl_website(full_url)
        #print(html)
        if html:
            # Optionally, save the HTML to a file
            out_fname = current_chapter.replace(" ", "-") + "_" + current_stage.replace(" ", "-") + "_" + current_part.replace(" ", "-")
            print(out_fname)
            with open(f'../html/{out_fname}.html', "w", encoding="utf-8") as file:
                file.write(html)
            #print(f"HTML content saved to {out_fname}")