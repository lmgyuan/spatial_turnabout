import * as path from "path";
import consola from "consola";
import {mkdir, readdir, readFile, writeFile} from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts";

// Load evidence data for Apollo Justice
let FULL_EVIDENCES = JSON.parse(await readFile(path.join(CASE_DATA_ROOT_DIRECTORY, "objects_parsed", "List_of_Evidence_in_Apollo_Justice_Ace_Attorney.json"), "utf-8"));
let CURR_CHAPTER_EVIDENCES;
FULL_EVIDENCES.forEach((e, index) => {
    if (e.chapter == "Turnabout Succession") {
        CURR_CHAPTER_EVIDENCES = e.evidences;
    }
})
let HTML_FILE_PATHS = [];

// Load character data for Apollo Justice
let FULL_CHARACTERS = JSON.parse(await readFile(path.join(CASE_DATA_ROOT_DIRECTORY, "characters_parsed", "List_of_Profiles_in_Apollo_Justice_Ace_Attorney.json"), "utf-8"));
let CURR_CHAPTER_CHARACTERS;
FULL_CHARACTERS.forEach((e, index) => {
    if (e.chapter == "Turnabout Succession") {
        CURR_CHAPTER_CHARACTERS = e.characters;
    }
})

// Get the HTML files
try {
    const files = await readdir(path.join(CASE_DATA_ROOT_DIRECTORY, "raw"));
    HTML_FILE_PATHS = files
        .filter(file => file.startsWith("Turnabout_Succession") && file.endsWith(".html"))
        .map(file => path.join(CASE_DATA_ROOT_DIRECTORY, "raw", file));
} catch (e) {
    consola.fatal("Could not read the directory or filter HTML files.");
    consola.log(e);
}

// Rest of the code is identical to Turnabout_Trump_Parse.ts except for the output filename 

const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed_full_context");

async function main() {
    consola.start("Parsing Turnabout Succession HTML file");
    
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

        // // For files after the first one, include all content
        // if (i > 0) {
        //     for (let j = 0; j < i; j++) {
                
        //     }
        //     // Process cross examinations and write file
        //     const initialEvidences = findInitialListOfEvidence(contentWrapper, CURR_CHAPTER_EVIDENCES);
        //     const crossExaminations = parseHtmlContent(contentWrapper, document, initialEvidences);
            
        //     const parsedData = {
        //         previousContext: accumulatedPreviousContext,
        //         characters: CURR_CHAPTER_CHARACTERS,
        //         evidences: initialEvidences,
        //         crossExaminations
        //     };
        //     consola.log("Writing parsed data to JSON file");
        //     if (!existsSync(OUTPUT_DIRECTORY)) {
        //         await mkdir(OUTPUT_DIRECTORY);
        //     }

        //     await writeFile(
        //         path.join(OUTPUT_DIRECTORY, `4-1-${i+1}_Turnabout_Trump_Parsed.json`),
        //         JSON.stringify(parsedData, null, 2)
        //     );
        //     continue;
        // }

        // For first file, only include content before first cross examination
        // let beforeFirstCrossExam = "";
        // for (const child of Array.from(contentWrapper.children)) {
        //     if (child.tagName === "CENTER" && 
        //         child.querySelector("span[style*='color:red']") && 
        //         child.textContent.trim() === "Cross Examination") {
        //         break;
        //     }
        //     beforeFirstCrossExam += child.textContent.trim() + "\n";
        // }
        
        // accumulatedPreviousContext = beforeFirstCrossExam;
        
        const initialEvidences = findInitialListOfEvidence(contentWrapper, CURR_CHAPTER_EVIDENCES);
        const crossExaminations = parseHtmlContent(contentWrapper, document, initialEvidences);

        const parsedData = {
            previousContext: accumulatedPreviousContext,
            characters: CURR_CHAPTER_CHARACTERS,
            evidences: initialEvidences,
            crossExaminations
        };

        accumulatedPreviousContext += parseContent(contentWrapper);

        consola.log("Writing parsed data to JSON file");
        if (!existsSync(OUTPUT_DIRECTORY)) {
            await mkdir(OUTPUT_DIRECTORY);
        }

        await writeFile(
            path.join(OUTPUT_DIRECTORY, `4-3-${i+1}_Turnabout_Succession_Parsed.json`),
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
        newContext += child.textContent.trim();

        if (child.tagName === "CENTER" && 
            child.querySelector("span[style*='color:red']") && 
            child.textContent.trim() === "Cross Examination") {
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

        if (child.tagName === "P" && child.querySelector("span[style*='color:#0070C0']")) {
            if (child.textContent.toLowerCase().includes(" added to the court record")) {
                addEvidenceToCourtRecord(child.textContent.toLowerCase(), evidence_objects);
            }
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
        if (child.tagName === "HR") {
            ++secondBarIndex;
            break;
        }

        if (child.tagName === "P" && child.querySelector("span[style*='color:#0070C0']")) {
            if (child.textContent.toLowerCase().includes(" added to the court record")) {
                addEvidenceToCourtRecord(child.textContent.toLowerCase(), evidence_objects);
            }
        }

        ++secondBarIndex;
    }

    for (; childIndex < contentWrapper.children.length; ++childIndex) {
        const child = contentWrapper.children[childIndex] as HTMLElement;
        if (child.tagName === "HR") break;

        if (child.tagName === "P" && child.querySelector("span[style*='color:green']")) {
            const name = child.textContent.split('\n')[0].replace(":", "").trim();
            const comment = child.textContent.split('\n')[1].trim()
            const presentEvidence = getPresentEvidence(contentWrapper, childIndex, document, secondBarIndex);
            testimonies.push({ testimony: comment, person: name, present: presentEvidence });
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
    let child = contentWrapper.children[index] as HTMLElement;

    while (child.tagName === "TABLE") {
        child = contentWrapper.children[index] as HTMLElement;
        const boxText = child.textContent.trim();
        if (boxText.includes("Present ")) {
            const texts = boxText.split("\n");
            for (let i = 0; i < texts.length; i++) {
                if (texts[i].includes("Present ")) {
                    evidence.push(texts[i].replace("Present ", "").trim());
                }
                break;
            }
        }
        index++;
    }
    return evidence;
}

function findInitialListOfEvidence(contentWrapper: Element, initialEvidences: any[]) {
    let childIndex = 0;
    let evidences = [...initialEvidences]

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];
        if (child.tagName === "P" && child.querySelector("span[style*='color:#0070C0']")) {
            if (child.textContent.toLowerCase().includes("added to the court record")) {
                const objectName = child.textContent.split("added to the court record")[0].trim();
                evidences.forEach((e, index) => {
                    if (e.name.trim().toLowerCase() === objectName.toLowerCase()) {
                        evidences.splice(index, 1);
                    }
                });
            }
        }
        ++childIndex;
    }

    return evidences;
}

function addEvidenceToCourtRecord(childTextContent: string, evidence_objects: any[]) {
    if (childTextContent.toLowerCase().includes("added to the court record")) {
        const objectName = childTextContent.split("added to the Court Record")[0].trim();
        CURR_CHAPTER_EVIDENCES.forEach((e, index) => {
            if (e.name.trim().toLowerCase() === objectName.toLowerCase()) {
                evidence_objects.push(e);
            }
        })
    };
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