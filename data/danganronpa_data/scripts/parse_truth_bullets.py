from bs4 import BeautifulSoup
import json

chapter_bullets = {}

current_bullet_desc = ["",""]
current_chapter = ""
look_for_description = False
with open("../html/_truth_bullets.html") as f:
    for line in f.readlines():
        if line.startswith('<h2><span class="mw-headline"'):
            soup = BeautifulSoup(line, 'html.parser')
            chapter = soup.find('span', class_='mw-headline').get_text()
            current_chapter = chapter
            chapter_bullets[current_chapter] = []
        if line.startswith('<th colspan="2" style="font-size:115%">'):
            current_bullet_desc[0] = line.removeprefix('<th colspan="2" style="font-size:115%">').split('(')[0].strip()
            look_for_description = True
        if look_for_description and not line.startswith('<td><a href') and line.startswith('<td>'):
            if not line.endswith("</td>"):
                line = line + "</td>"
            soup = BeautifulSoup(line, 'html.parser')
            current_bullet_desc[1] = soup.get_text().strip()
            chapter_bullets[current_chapter].append({"name": current_bullet_desc[0], "description": current_bullet_desc[1]})
            look_for_description = False
            #print(chapter_bullets)

with open("../json/_truth_bullets.json", "w") as json_file:
    json.dump(chapter_bullets, json_file, indent=4)