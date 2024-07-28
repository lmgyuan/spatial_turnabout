import * as path from "path";
import consola from "consola";
import {mkdir, readdir, readFile, writeFile} from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";

// @ts-ignore
let FULL_EVIDENCES = JSON.parse(await readFile("./case_data/scripts/generated/objects_parsed/Turnabout_Attorney_1_List_of_Evidence.json", "utf-8"));
let CURR_CHAPTER_EVIDENCES;
FULL_EVIDENCES.forEach((e, index) => {
    if (e.chapter == "Turnabout Samurai") {
        CURR_CHAPTER_EVIDENCES = e.evidences;
    }
})
const CASE_DATA_ROOT_DIRECTORY = "./case_data/scripts/generated";  // Define your root directory

// dynamically include all the Turnabout Samurai html files in the raw directory
let HTML_FILE_PATHS = [];
try {
    // @ts-ignore
    const files = await readdir(path.join(CASE_DATA_ROOT_DIRECTORY, "raw"));
    HTML_FILE_PATHS = files
        .filter(file => file.startsWith("Turnabout_Samurai") && file.endsWith(".html"))
        .map(file => path.join(CASE_DATA_ROOT_DIRECTORY, "raw", file));
} catch (e) {
    consola.fatal("Could not read the directory or filter HTML files.");
    consola.log(e);
}

const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed");


async function main() {
    consola.start("Parsing HTML file");

    let context = "";
    let newContext = "";

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
        console.log("Document object: ", document);

        const contentWrapper = document.querySelector(".mw-parser-output");
        if (!contentWrapper) {
            consola.fatal("Could not find the content wrapper element");
            return;
        }

        const initialEvidences = findInitialListOfEvidence(contentWrapper, CURR_CHAPTER_EVIDENCES);

        let parsedData = parseHtmlContent(contentWrapper, document, context, initialEvidences, newContext);
        parsedData = parsedDataHandling(parsedData);

        consola.log("Writing parsed data to JSON file");
        if (!existsSync(OUTPUT_DIRECTORY)) {
            await mkdir(OUTPUT_DIRECTORY);
        }

        await writeFile(
            path.join(OUTPUT_DIRECTORY, `Turnabout_Samurai_Parsed${i+1}.json`),
            JSON.stringify(parsedData, null, 2)
        );
    }
}


function parsedDataHandling(parsedData: any) {
    // flag cross examinations that do not require players to present anything
    if (!parsedData) {
        return parsedData
    }

    // check if the cross examination has any present evidence
    // if it does, set the no_present flag to false
    // otherwise, set it to true
    parsedData.forEach((data, index) => {
        data['no_present'] = true;

        for (let i = 0; i < data.testimonies.length; i++) {
            if (data.testimonies[i].present.length > 0) {
                data['no_present'] = false;
                break;
            }
        }
    })

    return parsedData
}

function parseHtmlContent(contentWrapper: Element, document: Document, context, evidence_objects, newContext: string) {
    const data = [];
    let childIndex = 0;

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];

        context += child.textContent.trim();
        newContext += child.textContent.trim();

        if (child.tagName === "CENTER" && child.querySelector("span[style*='color:red']") && child.textContent.trim() === "Cross Examination") {
            const crossExamination = parseCrossExamination(contentWrapper, childIndex, document, context, evidence_objects, newContext);
            data.push(crossExamination);
            newContext = "";
        }

        if (child.tagName === "P" && child.querySelector("span[style*='color:#0070C0']")) {
            if (child.textContent.toLowerCase().includes(" added to the court record")) {
                addEvidenceToCourtRecord(child.textContent.toLowerCase(), evidence_objects);
            }
        }

        ++childIndex;
    }

    return data;
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
                        evidences.splice(index, 1); // Delete the item from the array
                    }
                });
            }
        }
        ++childIndex;
    }

    return evidences; // Return the modified array if needed
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

function parseCrossExamination(contentWrapper: Element, startIndex: number, document: Document, context: string, evidence_objects: any[], newContext: string) {
    const testimonies = [];
    let childIndex = startIndex;
    let secondBarIndex = startIndex;

    // Skip the cross-examination text and move to testimonies
    while (secondBarIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[secondBarIndex] as HTMLElement;
        if (child.tagName === "HR") {
            ++secondBarIndex; // Move past the <hr> tag
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

    return {
        category: "cross_examination",
        context: context,
        newContext: newContext,
        court_record: { evidence_objects },
        testimonies,
    };
}

function getPresentEvidence(contentWrapper: Element, index: number, document: Document, secondBarIndex: number) {
    let evidence = [];
    index++;
    let child = contentWrapper.children[index] as HTMLElement;

    while (child.tagName === "TABLE") {
        child = contentWrapper.children[index] as HTMLElement;
        /* TODO:
            Look at the relevant html codes about the evidence and extract the evidence name
            Also think about how to extract the present evidence response. It's a number of children down the html page.
         */
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

main();


// import * as path from "path";
// import consola from "consola";
// import { mkdir, readFile, writeFile } from "fs/promises";
// import { JSDOM } from "jsdom";
// import { existsSync } from "fs";
//
// const CASE_DATA_ROOT_DIRECTORY = "./case_data/scripts/generated";  // Define your root directory
// const HTML_FILE_PATHS = [];
// for (let i = 1; i <= 4; i++) {
//     HTML_FILE_PATHS.push(path.join(CASE_DATA_ROOT_DIRECTORY, `raw/Turnabout_Samurai_-_Transcript_-_Part_${i}.html`));
// }
// const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed");
//
//
// async function main() {
//     consola.start("Parsing HTML file");
//
//     let context = "";
//     const objects = [];
//
//     for (let i = 0; i < HTML_FILE_PATHS.length; i++) {
//         let rawHtml: string;
//         const HTML_FILE_PATH = HTML_FILE_PATHS[i];
//         try {
//             rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
//             console.log("Raw HTML content read successfully.");
//         } catch (e) {
//             consola.fatal(`Could not read file at ${HTML_FILE_PATH}`);
//             consola.log(e);
//             return;
//         }
//
//         let dom: JSDOM;
//         try {
//             dom = new JSDOM(rawHtml);
//             console.log("JSDOM instance created successfully.");
//         } catch (e) {
//             consola.fatal("Malformed HTML content");
//             consola.log(e);
//             return;
//         }
//
//         const document = dom.window.document;
//         console.log("Document object: ", document);
//
//         const contentWrapper = document.querySelector(".mw-parser-output");
//         if (!contentWrapper) {
//             consola.fatal("Could not find the content wrapper element");
//             return;
//         }
//
//         const parsedData = parseHtmlContent(contentWrapper, document, context, objects);
//         consola.log("Writing parsed data to JSON file");
//         if (parsedData) {
//             console.log("Parsed data succeeded");
//         } else {
//             console.log("Parsed data failed");
//         }
//         if (!existsSync(OUTPUT_DIRECTORY)) {
//             await mkdir(OUTPUT_DIRECTORY);
//         }
//
//         await writeFile(
//             path.join(OUTPUT_DIRECTORY, `Turnabout_Samurai_Parsed${i+1}.json`),
//             JSON.stringify(parsedData, null, 2)
//         );
//     }
// }
//
// function parseHtmlContent(contentWrapper: Element, document: Document, context, objects) {
//     const data = [];
//     let childIndex = 0;
//
//     while (childIndex < contentWrapper.children.length) {
//         const child = contentWrapper.children[childIndex];
//
//         if (child.tagName === "CENTER" && child.querySelector("span[style*='color:red']") && child.textContent.trim() === "Cross Examination") {
//             const crossExamination = parseCrossExamination(contentWrapper, childIndex, document, context, objects);
//             data.push(crossExamination);
//         }
//
//         if (child.tagName === "P" && child.querySelector("span[style*='color:#0070C0']")) {
//             if (child.textContent.toLowerCase().includes("added to the court record")) {
//                 const objectName = child.textContent.split("added to the Court Record")[0];
//                 objects.push({ name: objectName, description: "TODO" });
//             }
//         }
//         context += child.textContent.trim();
//
//         ++childIndex;
//     }
//
//     return data;
// }
//
// function parseCrossExamination(contentWrapper: Element, startIndex: number, document: Document, context: string, objects: any[]) {
//     const testimonies = [];
//     let childIndex = startIndex;
//     let secondBarIndex = startIndex;
//
//     // Skip the cross-examination text and move to testimonies
//     while (secondBarIndex < contentWrapper.children.length) {
//         const child = contentWrapper.children[secondBarIndex] as HTMLElement;
//         if (child.tagName === "HR") {
//             ++secondBarIndex; // Move past the <hr> tag
//             break;
//         }
//         context += child.textContent.trim();
//
//         if (child.tagName === "P" && child.querySelector("span[style*='color:#0070C0']")) {
//             if (child.textContent.toLowerCase().includes("added to the court record")) {
//                 const objectName = child.textContent.split("added to the Court Record")[0];
//                 objects.push({ name: objectName, description: "TODO" });
//             }
//         }
//
//         ++secondBarIndex;
//     }
//
//     for (; childIndex < contentWrapper.children.length; ++childIndex) {
//         const child = contentWrapper.children[childIndex] as HTMLElement;
//         if (child.tagName === "HR") break;
//
//         if (child.tagName === "P" && child.querySelector("span[style*='color:green']")) {
//             const name = child.textContent.split('\n')[0].replace(":", "").trim();
//             const comment = child.textContent.split('\n')[1].trim()
//             const presentEvidence = getPresentEvidence(contentWrapper, childIndex, document, secondBarIndex);
//             testimonies.push({ testimony: comment, person: name, present: presentEvidence });
//         }
//     }
//
//     return {
//         category: "cross_examination",
//         context: context,
//         court_record: { objects },
//         testimonies,
//     };
// }
//
// function getPresentEvidence(contentWrapper: Element, index: number, document: Document, secondBarIndex: number) {
//     let evidence = [];
//     index++;
//     let child = contentWrapper.children[index] as HTMLElement;
//
//     while (child.tagName === "TABLE") {
//         child = contentWrapper.children[index] as HTMLElement;
//         /* TODO:
//             Look at the relevant html codes about the evidence and extract the evidence name
//             Also think about how to extract the present evidence response. It's a number of children down the html page.
//          */
//         const boxText = child.textContent.trim();
//         if (boxText.includes("Present ")) {
//             const texts = boxText.split("\n");
//             for (let i = 0; i < texts.length; i++) {
//                 if (texts[i].includes("Present ")) {
//                     evidence.push(texts[i].replace("Present ", "").trim());
//                 }
//                 break;
//             }
//         }
//
//         index++;
//     }
//     return evidence;
// }
//
// main();
