import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs";

const OUTPUT_DIRECTORY = "./case_data/generated/characters_parsed/";
const CHARACTERS_HTML_FILE_DIRECTORY = "./case_data/generated/raw/";
const CHARACTERS_HTML_FILE_NAMES = fs.readdirSync(CHARACTERS_HTML_FILE_DIRECTORY).filter((fileName) => fileName.startsWith("List_of_Profiles_in"));
const CHARACTERS_HTML_FILE_PATHS = CHARACTERS_HTML_FILE_NAMES.map((fileName) => path.join(CHARACTERS_HTML_FILE_DIRECTORY, fileName));

mkdir(OUTPUT_DIRECTORY).catch((e) => {
    if (e.code !== "EEXIST") {
        consola.fatal("Could not create output directory");
        consola.log(e);
        process.exit(1);
    }
})

type CharacterData = {
    currentChapter: string;
    name: string;
    age: string;
    [key: `description${number}`]: string;
    gender: string;
};


async function main() {
    consola.start("Parsing HTML file");

    for (let i = 0; i < CHARACTERS_HTML_FILE_PATHS.length; i++) {
        let rawHtml: string;
        const HTML_FILE_PATH = CHARACTERS_HTML_FILE_PATHS[i];
        if (path.join(CHARACTERS_HTML_FILE_DIRECTORY, "List_of_Profiles_in_Phoenix_Wright_Ace_Attorney.html") === HTML_FILE_PATH) {
            console.log("Skipping List_of_Profiles_in_Phoenix_Wright_Ace_Attorney.html");
            continue;
        }

        try {
            rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
            console.log("Raw HTML content read successfully.");
        } catch (e) {
            consola.fatal(`Could not read file at ${HTML_FILE_PATH}`);
            consola.log(e);
            return;
        }

        let dom: JSDOM;
        try {
            dom = new JSDOM(rawHtml);
            console.log("JSDOM instance created successfully.");
        } catch (e) {
            consola.fatal("Malformed HTML content");
            consola.log(e);
            return;
        }

        const document = dom.window.document;
        const contentWrapper = document.querySelector(".mw-parser-output");
        if (!contentWrapper) {
            consola.fatal("Could not find the content wrapper element");
            return;
        }

        const parsedData = parseHTMLContent(contentWrapper, document);
        consola.log("Writing parsed data to JSON file");
        if (!fs.existsSync(OUTPUT_DIRECTORY)) {
            await mkdir(OUTPUT_DIRECTORY);
        }

        await writeFile(
            path.join(OUTPUT_DIRECTORY, `${CHARACTERS_HTML_FILE_NAMES[i].split(".html")[0]}.json`),
            JSON.stringify(parsedData, null, 2)
        );
    }
}

function parseHTMLContent(contentWrapper: Element, document: Document) {
    let data = [];
    let childIndex = 0;
    let currentChapter = "";
    let chapterData = { chapter: "", characters: [] };

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];
        if (child.tagName === "H2") {
            if (chapterData.chapter) {
                data.push(chapterData);
            }

            // split by [ to remove the [] at the end of the chapter name
            currentChapter = child.textContent.split("[")[0].trim();
            // handle a special character. If the chapter name includes a special character, replace it with a space
            // Found it when parsing the List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_Justice_For_All.html
            if (currentChapter.includes(" ")) {
                currentChapter = currentChapter.replace(" ", " ");
            }
            chapterData = { chapter: currentChapter, characters: [] };
        } else if (
            child.getAttribute('style') === 'color:#000;' +
            'border:3px solid #000;' +
            'padding:2px;background:#867545;' +
            'border-radius: 10px; ' +
            '-moz-border-radius: 10px; ' +
            '-webkit-border-radius: 10px; ' +
            '-khtml-border-radius: 10px; ' +
            '-icab-border-radius: 10px; ' +
            '-o-border-radius: 10px') {
            let tableData = parseTable(child, currentChapter);
            if (tableData.description1.includes("↳")) {
                tableData = parseDescription(tableData);
            }
            chapterData.characters.push(tableData);
        }
        ++childIndex;
    }
    if (chapterData.chapter) {
        data.push(chapterData);
    }
    return data;
}

function parseDescription(tableData: CharacterData): CharacterData {
    let description = tableData.description1;
    let descriptions = description.split("↳");
    descriptions.forEach((desc, index) => {
        tableData[`description${index + 1}`] = desc.trim();
    });
    return tableData;
}

function parseTable(table: Element, currentChapter: string) {
    const rows = table.querySelectorAll("td");
    let object: CharacterData = { currentChapter: currentChapter, name: "", age: "", gender: "", description1: "" };
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (i === 0) {
            object.name = row.textContent.trim();
        } else if (i === 1) {
            object.age = row.textContent.split(":").slice(1).join(" ").trim();
        } else if (i === 2) {
            object.gender = row.textContent.split(":").slice(1).join(" ").trim();
        } else {
            object.description1 = row.textContent.trim();
        }
    }
    return object;
}

main();
