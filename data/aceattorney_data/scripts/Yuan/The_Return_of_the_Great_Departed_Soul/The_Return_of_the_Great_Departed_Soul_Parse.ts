import * as path from "path";
import consola from "consola";
import {mkdir, readdir, readFile, writeFile} from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts";

// Load evidence data for The Great Ace Attorney
let FULL_EVIDENCES = JSON.parse(await readFile(path.join(CASE_DATA_ROOT_DIRECTORY, "objects_parsed", "List_of_Evidence_in_The_Great_Ace_Attorney_2_Resolve.json"), "utf-8"));
let CURR_CHAPTER_EVIDENCES;
FULL_EVIDENCES.forEach((e) => {
    if (e.chapter == "The Return of the Great Departed Soul") {
        CURR_CHAPTER_EVIDENCES = e.evidences;
    }
});
let HTML_FILE_PATHS = [];

// Load character data for The Great Ace Attorney
let FULL_CHARACTERS = JSON.parse(await readFile(path.join(CASE_DATA_ROOT_DIRECTORY, "characters_parsed", "List_of_Profiles_in_The_Great_Ace_Attorney_2_Resolve.json"), "utf-8"));
let CURR_CHAPTER_CHARACTERS;
FULL_CHARACTERS.forEach((e) => {
    if (e.chapter == "The Return of the Great Departed Soul") {
        CURR_CHAPTER_CHARACTERS = e.characters;
    }
});

// Get the Clouded Kokoro HTML files
try {
    const files = await readdir(path.join(CASE_DATA_ROOT_DIRECTORY, "raw"));
    HTML_FILE_PATHS = files
        .filter(file => file.includes("The_Return_of_the_Great_Departed_Soul") && file.endsWith(".html"))
        .map(file => path.join(CASE_DATA_ROOT_DIRECTORY, "raw", file));
} catch (e) {
    consola.fatal("Could not read the directory or filter HTML files.");
    consola.log(e);
}

const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed_full_context");

async function main() {
    consola.start("Parsing The Return of the Great Departed Soul HTML files");
    
    let accumulatedPreviousContext = "";

    for (let i = 0; i < HTML_FILE_PATHS.length; i++) {
        let rawHtml: string;
        const HTML_FILE_PATH = HTML_FILE_PATHS[i];
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
        
        const crossExaminations = parseHtmlContent(contentWrapper, document, CURR_CHAPTER_EVIDENCES);

        const parsedData = {
            previousContext: accumulatedPreviousContext,
            characters: CURR_CHAPTER_CHARACTERS,
            evidences: CURR_CHAPTER_EVIDENCES,
            turns: crossExaminations
        };

        accumulatedPreviousContext += parseContent(contentWrapper);

        consola.log("Writing parsed data to JSON file");
        if (!existsSync(OUTPUT_DIRECTORY)) {
            await mkdir(OUTPUT_DIRECTORY);
        }

        await writeFile(
            path.join(OUTPUT_DIRECTORY, `8-3-${i+1}_The_Return_of_the_Great_Departed_Soul.json`),
            JSON.stringify(parsedData, null, 2)
        );
    }
}

function parseHtmlContent(contentWrapper: Element, document: Document, evidence_objects) {
    const crossExaminations = [];
    let childIndex = 0;
    let newContext = "";

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];
        if (child && child.textContent) {
            newContext += child.textContent.trim();
        }

        if (child && child.tagName === "CENTER" && 
            child.textContent && 
            (child.textContent.trim().includes("Cross-Examination") || child.textContent.trim().includes("Cross Examination"))) {
            const crossExamination = parseCrossExamination(
                contentWrapper, 
                childIndex, 
                document, 
                newContext, 
                evidence_objects
            );
            crossExaminations.push(crossExamination);
            newContext = "";
        }

        ++childIndex;
    }

    return crossExaminations;
}

function parseCrossExamination(contentWrapper: Element, startIndex: number, document: Document, newContext: string, evidence_objects: any[]) {
    const testimonies = [];
    let childIndex = startIndex;
    let secondBarIndex = startIndex;

    while (secondBarIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[secondBarIndex] as HTMLElement;
        if (child && child.tagName === "HR") {
            ++secondBarIndex;
            break;
        }

        ++secondBarIndex;
    }

    for (; childIndex < contentWrapper.children.length; ++childIndex) {
        const child = contentWrapper.children[childIndex] as HTMLElement;
        if (child && child.tagName === "HR") break;

        if (child && child.tagName === "P" && child.querySelector("span[style*='color:green']") && child.textContent) {
            const textParts = child.textContent.split('\n');
            if (textParts.length >= 2) {
                const name = textParts[0].replace(":", "").trim();
                const comment = textParts[1].trim();
                const presentEvidence = getPresentEvidence(contentWrapper, childIndex, document, secondBarIndex);
                testimonies.push({ testimony: comment, person: name, present: presentEvidence });
            }
        }
    }

    const hasPresent = testimonies.some(t => t.present && t.present.length > 0);

    return {
        category: "cross_examination",
        newContext: newContext,
        testimonies,
        noPresent: !hasPresent
    };
}

function getPresentEvidence(contentWrapper: Element, index: number, document: Document, secondBarIndex: number) {
    let evidence = [];
    index++;
    if (index < contentWrapper.children.length) {
        let child = contentWrapper.children[index] as HTMLElement;

        while (child && child.tagName === "TABLE") {
            // Look for the title element with the navbox1title class
            const titleElement = child.querySelector("th.navbox1title");
            if (titleElement && titleElement.textContent) {
                // Extract the evidence name from the title
                const titleText = titleElement.textContent.trim();
                // Check if it contains "Present" to confirm it's a presentable evidence
                if (titleText.includes("Present")) {
                    // Extract the evidence name by removing "Present" from the title
                    const evidenceName = titleText.replace("Present", "").trim();
                    evidence.push(evidenceName);
                }
            }
            
            index++;
            if (index < contentWrapper.children.length) {
                child = contentWrapper.children[index] as HTMLElement;
            } else {
                break;
            }
        }
    }
    return evidence;
}

function parseContent(contentWrapper: Element): string {
    const textParts: string[] = [];
    
    // Process each child element
    for (const child of Array.from(contentWrapper.children)) {
        // Skip navigation elements and other non-content elements
        if (child.classList.contains('toc') || 
            child.tagName === 'TABLE' || 
            child.id === 'toc') {
            continue;
        }

        // Get text content and clean it
        const text = child.textContent?.trim();
        if (text && text.length > 0) {
            textParts.push(text);
        }
    }

    // Join all text parts with newlines
    return textParts.join("\n");
}

main();
