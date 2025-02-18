import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs";
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts";

const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "characters_parsed");
const CHARACTERS_HTML_FILE_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "raw");
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
};

async function main() {
    consola.start("Parsing HTML file");

    for (let i = 0; i < CHARACTERS_HTML_FILE_PATHS.length; i++) {
        let rawHtml: string;
        const HTML_FILE_PATH = CHARACTERS_HTML_FILE_PATHS[i];
        
        if (HTML_FILE_PATH.split("/").pop() !== 
        "List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.html" &&
        HTML_FILE_PATH.split("/").pop() !== 
        "List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.html"
        ) {
            continue;
        }

        console.log("Parsing List of Profiles for Dual Destinies or Spirit of Justice");

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
    const data: Array<{chapter: string, characters: Array<CharacterData>}> = [];
    let childIndex = 0;
    let currentChapter = "";
    let chapterData = { chapter: "", characters: [] };

    try {
        while (childIndex < contentWrapper.children.length) {
            const child = contentWrapper.children[childIndex];
            if (child.tagName === "H2") {
                if (chapterData.chapter) {
                    data.push(chapterData);
                }
    
                currentChapter = child.textContent?.split("[")[0].trim() || "";
                console.log("Processing chapter: ", currentChapter);
                chapterData = { chapter: currentChapter, characters: [] };
            } else if (
                child.tagName === "TABLE" && 
                child.getAttribute('width') === "100%" &&
                child.getAttribute('style')?.includes('background:#D7D7D7')
            ) {
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
    } catch (e) {
        consola.fatal("Error parsing HTML content");
        consola.log(e);
        return [];
    }
}

function parseDescription(tableData: CharacterData): CharacterData {
    let description = tableData.description1;
    let descriptions = description.split("↳");
    descriptions.forEach((desc, index) => {
        tableData[`description${index + 1}`] = desc.trim();
    });
    return tableData;
}

function parseTable(table: Element, currentChapter: string): CharacterData {
    const rows = table.querySelectorAll("td");
    const object: CharacterData = { 
        currentChapter: currentChapter,
        name: rows[0]?.textContent?.trim() || "",
        age: rows[1]?.textContent?.trim() || "",
        description1: rows[2]?.textContent?.trim() || ""
    };

    return object;
}

main();
