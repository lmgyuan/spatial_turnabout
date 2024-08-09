import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs"

const OBJECT_RAW_DATA_ROOT_DIRECTORY = "./case_data/generated/objects_raw";  // Define your root directory
const OBJECT_FILES_NAMES = fs.readdirSync(OBJECT_RAW_DATA_ROOT_DIRECTORY).filter((fileName) => fileName.endsWith(".html"));

const OBJECTS_HTML_FILE_PATHS = OBJECT_FILES_NAMES.map((fileName) => path.join(OBJECT_RAW_DATA_ROOT_DIRECTORY, fileName));
const OUTPUT_DIRECTORY = "./case_data/generated/objects_parsed";

type ObjectData = {
    currentChapter: string;
    name: string;
    type: string;
    obtained: string;
    [key: `description${number}`]: string;
};

async function main() {
    consola.start("Parsing HTML file");

    for (let i = 0; i < OBJECTS_HTML_FILE_PATHS.length; i++) {
        let rawHtml: string;
        const HTML_FILE_PATH = OBJECTS_HTML_FILE_PATHS[i];
        if (HTML_FILE_PATH.split("/").pop() == "List_of_Evidence_in_Phoenix_Wright_Ace_Attorney.html") {
            console.log("Skipping List_of_Evidence_in_Phoenix_Wright_Ace_Attorney.html");
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
            path.join(OUTPUT_DIRECTORY, `${OBJECT_FILES_NAMES[i].split(".html")[0]}.json`),
            JSON.stringify(parsedData, null, 2)
        );
    }
}

function parseHTMLContent(contentWrapper: Element, document: Document) {
    let data = [];
    let childIndex = 0;
    let currentChapter = "";
    let chapterData = { chapter: "", evidences: [] };

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];
        if (child.tagName === "H2") {
            if (chapterData.chapter) {
                data.push(chapterData);
            }

            // split("[") is used to remove the "[]" text from the chapter name
            currentChapter = child.textContent.split("[")[0];
            console.log("child.querySelector: ", child.textContent);
            chapterData = { chapter: currentChapter, evidences: [] };
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
            chapterData.evidences.push(tableData);
        }
        ++childIndex;
    }
    if (chapterData.chapter) {
        data.push(chapterData);
    }
    return data;
}

function parseDescription(tableData: ObjectData): ObjectData {
    let description = tableData.description1;
    let descriptions = description.split("↳");
    descriptions.forEach((desc, index) => {
        tableData[`description${index + 1}`] = desc.trim();
    });
    return tableData;
}

function parseTable(table: Element, currentChapter: string) {
    const rows = table.querySelectorAll("td");
    let object: ObjectData = { currentChapter: currentChapter, name: "", type: "", obtained: "", description1: "" };
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (i === 0) {
            object.name = row.textContent.trim();
        } else if (i === 1) {
            object.type = row.textContent.split(":").slice(1).join(" ").trim();
        } else if (i === 2) {
            object.obtained = row.textContent.split(":").slice(1).join(" ").trim();
        } else {
            object.description1 = row.textContent.trim();
        }
    }
    return object;
}

main();
