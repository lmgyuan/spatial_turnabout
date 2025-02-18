import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs"
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts";


const OBJECT_RAW_DATA_ROOT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "objects_raw");  // Define your root directory
const OBJECT_FILES_NAMES = fs.readdirSync(OBJECT_RAW_DATA_ROOT_DIRECTORY).filter((fileName) => fileName.endsWith(".html"));

const OBJECTS_HTML_FILE_PATHS = OBJECT_FILES_NAMES.map((fileName) => path.join(OBJECT_RAW_DATA_ROOT_DIRECTORY, fileName));
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "objects_parsed");

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
        // if (HTML_FILE_PATH.split("/").pop() == "List_of_Evidence_in_Phoenix_Wright_Ace_Attorney.html") {
        //     console.log("Skipping List_of_Evidence_in_Phoenix_Wright_Ace_Attorney.html");
        //     continue;
        // }
        // if (HTML_FILE_PATH.split("/").pop() == "List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.html") {
        //     console.log("Skipping List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.html");
        //     continue;
        // }
        if (HTML_FILE_PATH.split("/").pop() != 
        "List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.html") {
            continue;
        }

        console.log("Parsing Dual Destinies List of Evidence");
        
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
        consola.log(`Finished parsing ${OBJECT_FILES_NAMES[i]}`);
    }
}

function parseHTMLContent(contentWrapper: Element, document: Document) {
    const data: Array<{chapter: string, evidences: Array<ObjectData>}> = [];
    let childIndex = 0;
    let currentChapter = "";
    let chapterData = { chapter: "", evidences: [] };

    try {
        while (childIndex < contentWrapper.children.length) {
            const child = contentWrapper.children[childIndex];
            if (child.tagName === "H2") {
                if (chapterData.chapter) {
                    data.push(chapterData);
                }
    
                currentChapter = child.textContent?.split("[")[0].trim() || "";
                console.log("Processing chapter: ", currentChapter);
                chapterData = { chapter: currentChapter, evidences: [] };
            } else if (
                child.tagName === "TABLE" && 
                child.getAttribute('width') === "100%" &&
                child.getAttribute('style')?.includes('background:#D7D7D7')
            ) {
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
    } catch (e) {
        consola.fatal("Error parsing HTML content");
        consola.log(e);
        return [];
    }
}

function parseDescription(tableData: ObjectData): ObjectData {
    let description = tableData.description1;
    let descriptions = description.split("↳");
    descriptions.forEach((desc, index) => {
        tableData[`description${index + 1}`] = desc.trim();
    });
    return tableData;
}

function parseTable(table: Element, currentChapter: string): ObjectData {
    const rows = table.querySelectorAll("td");

    const object: ObjectData = { 
        currentChapter: currentChapter, 
        name: rows[0]?.textContent?.trim() || "",
        description1: rows[1]?.textContent?.trim() || ""
    };

    return object;
}

main();
