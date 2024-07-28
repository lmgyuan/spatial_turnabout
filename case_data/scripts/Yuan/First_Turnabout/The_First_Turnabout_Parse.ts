import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile, readdir } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";

// @ts-ignore
let FULL_EVIDENCES = JSON.parse(await readFile("./case_data/scripts/generated/objects_parsed/Turnabout_Attorney_1_List_of_Evidence.json", "utf-8"));
let CURR_CHAPTER_EVIDENCES;
FULL_EVIDENCES.forEach((e, index) => {
    if (e.chapter == "The First Turnabout") {
        CURR_CHAPTER_EVIDENCES = e.evidences;
    }
})

// @ts-ignore
let FULL_CHARACTERS = JSON.parse(await readFile("./case_data/scripts/generated/characters_parsed/Turnabout_Attorney_1_List_of_Characters.json", "utf-8"));
let CURR_CHAPTER_CHARACTERS;
FULL_CHARACTERS.forEach((e, index) => {
    if (e.chapter.trim() == "The First Turnabout") {
        CURR_CHAPTER_CHARACTERS = e.characters;
    }
})

const CASE_DATA_ROOT_DIRECTORY = "./case_data/scripts/generated";  // Define your root directory
let HTML_FILE_PATHS = [];
// for (let i = 1; i <= 4; i++) {
//     HTML_FILE_PATHS.push(path.join(CASE_DATA_ROOT_DIRECTORY, `raw/The_First_Turnabout-_Transcript_-_Part_${i}.html`));
// }
try {
    // @ts-ignore
    const files = await readdir(path.join(CASE_DATA_ROOT_DIRECTORY, "raw"));
    HTML_FILE_PATHS = files
        .filter(file => file.startsWith("The_First_Turnabout") && file.endsWith(".html"))
        .map(file => path.join(CASE_DATA_ROOT_DIRECTORY, "raw", file));
} catch (e) {
    consola.fatal("Could not read the directory or filter HTML files.");
    consola.log(e);
}
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed");


async function main() {
    consola.start("Parsing HTML file");

    let context = "";

    // define the new context outside the loop so it can handle edge cases where
    // the new context before a cross examination is across two html files.
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
            path.join(OUTPUT_DIRECTORY, `The_First_Turnabout${i+1}.json`),
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

        // add the current context to the overraching context variable and newContext variable
        context += child.textContent.trim();
        newContext += child.textContent.trim();

        if (child.tagName === "CENTER" && child.querySelector("span[style*='color:red']") && child.textContent.trim() === "Cross Examination") {
            const crossExamination = parseCrossExamination(contentWrapper, childIndex, document, context, evidence_objects, newContext);
            console.log("Cross Examination: ", crossExamination);
            data.push(crossExamination);
            newContext = "";
        }

        if (child.tagName === "P" && child.querySelector("span[style*='color:#0070C0']")) {
            if (child.textContent.toLowerCase().includes(" added to the court record")) {
                console.log("Adding evidence to court record: ", child.textContent.toLowerCase());
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
                const objectName = child.textContent.split("added to the Court Record")[0].trim();
                evidences.forEach((e, index) => {
                    if (e.name.trim().toLowerCase() === objectName.toLowerCase()) {
                        console.log("Deleting ", e.name);
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
        const objectName = childTextContent.split("added to the court record")[0].trim();
        console.log("objectName: ", objectName);
        CURR_CHAPTER_EVIDENCES.forEach((e, index) => {
            if (e.name.trim().toLowerCase() === objectName.toLowerCase()) {
                console.log("Found ", e.name);
                evidence_objects.push(e);
            }
        })
    };
}

function parseCrossExamination(contentWrapper: Element, startIndex: number, document: Document, context: string, evidence_objects: any[], newContext: string) {
    const testimonies = [];
    let childIndex = startIndex;
    let secondBarIndex = startIndex;

    // Skip first bar before the actual cross exmination text and move to testimonies
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
        // cross examinations are separeted by a bar, so break the loop when you find it
        if (child.tagName === "HR") break;

        if (child.tagName === "P" && child.querySelector("span[style*='color:green']")) {
            const name = child.textContent.split('\n')[0].replace(":", "").trim();
            const comment = child.textContent.split('\n')[1].trim()
            const presentEvidence = getPresentEvidence(contentWrapper, childIndex, document, secondBarIndex, context);
            testimonies.push({ testimony: comment, person: name, present: presentEvidence });
        }
    }


    return {
        category: "cross_examination",
        context: context,
        new_context: newContext,
        characters: CURR_CHAPTER_CHARACTERS,
        court_record: { evidence_objects },
        testimonies,
    };
}

function getPresentEvidence(contentWrapper: Element, index: number, document: Document, secondBarIndex: number, context: string) {
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
// const HTML_FILE_PATH = path.join(CASE_DATA_ROOT_DIRECTORY, "raw/1-1.html");
// const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed");
//
// async function main() {
//     consola.start("Parsing HTML file");
//
//     let rawHtml: string;
//     try {
//         rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
//         console.log("Raw HTML content read successfully.");
//     } catch (e) {
//         consola.fatal(`Could not read file at ${HTML_FILE_PATH}`);
//         consola.log(e);
//         return;
//     }
//
//     let dom: JSDOM;
//     try {
//         dom = new JSDOM(rawHtml);
//         console.log("JSDOM instance created successfully.");
//     } catch (e) {
//         consola.fatal("Malformed HTML content");
//         consola.log(e);
//         return;
//     }
//
//     const document = dom.window.document;
//     console.log("Document object: ", document);
//
//     const contentWrapper = document.querySelector(".mw-parser-output");
//     if (!contentWrapper) {
//         consola.fatal("Could not find the content wrapper element");
//         return;
//     }
//
//     const parsedData = parseHtmlContent(contentWrapper, document);
//     consola.log("Writing parsed data to JSON file");
//     if (!existsSync(OUTPUT_DIRECTORY)) {
//         await mkdir(OUTPUT_DIRECTORY);
//     }
//
//     await writeFile(
//         path.join(OUTPUT_DIRECTORY, "parsed_data.json"),
//         JSON.stringify(parsedData, null, 2)
//     );
// }
//
// function parseHtmlContent(contentWrapper: Element, document: Document) {
//     const data = [];
//     let childIndex = 0;
//     let context = "";
//     const objects = [];
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
// //
// // function getTextContentFromElement(el: Element, document: Document): string {
// //     el.querySelectorAll("br").forEach((br) => {
// //         const newLine = document.createElement("span");
// //         newLine.textContent = "\n";
// //         br.replaceWith(newLine);
// //     });
// //     return el.textContent.trim();
// // }
//
// main();
