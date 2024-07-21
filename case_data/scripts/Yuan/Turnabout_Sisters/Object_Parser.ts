import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";

const CASE_DATA_ROOT_DIRECTORY = "./case_data/scripts/generated/objects_raw";  // Define your root directory
const OBJECT_FILES_NAMES = [
    "List_of_Evidence_in_Phoenix_Wright:_Ace_Attorney.html"
];
const OBJECTS_HTML_FILE_PATHS = OBJECT_FILES_NAMES.map((fileName) => path.join(CASE_DATA_ROOT_DIRECTORY, fileName));
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

    let context = "";
    const objects = [];

    for (let i = 0; i < OBJECTS_HTML_FILE_PATHS.length; i++) {
        let rawHtml: string;
        const HTML_FILE_PATH = OBJECTS_HTML_FILE_PATHS[i];
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
        console.log("Document object: ", document.documentElement);
        const contentWrapper = document.querySelector(".mw-parser-output");
        console.log("contentWrapper: ", contentWrapper);
        if (!contentWrapper) {
            consola.fatal("Could not find the content wrapper element");
            return;
        }

        const parsedData = parseHTMLContent(contentWrapper, document);
        consola.log("Writing parsed data to JSON file");
        if (!existsSync(OUTPUT_DIRECTORY)) {
            await mkdir(OUTPUT_DIRECTORY);
        }

        await writeFile(
            path.join(OUTPUT_DIRECTORY, `Turnabout_Sisters_Parsed${i+1}.json`),
            JSON.stringify(parsedData, null, 2)
        );
    }
}

function parseHTMLContent(contentWrapper: Element, document: Document) {
    let data = [];
    let childIndex = 0;
    let currentChapter = "";

    while(childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];
        if (child.tagName === "H2") {
            currentChapter = child.querySelector("span").textContent.trim();
            data.push({ chapter: currentChapter, content: "" });
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
            if (tableData.description1.includes("↳")){
                tableData = parseDescription(tableData);
            }
            data.push(tableData)
        }
        ++childIndex;
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
    let object:ObjectData = {currentChapter: currentChapter, name: "", type: "", obtained: "", description1: ""};
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (i === 0) {
            object.name = row.textContent.trim();
        } else if (i === 1) {
            object.type = row.textContent.split(":").slice(1).join(" ").trim();
        } else if (i === 2) {
            object.obtained = row.textContent.split(":").slice(1).join(" ").trim();
        }
        else {
            object.description1 = row.textContent.trim();
        }
    }
    // console.log("table object: ", object)
    return object;
}
//
// function parseObjectTables(tables: NodeListOf<Element>) {
//     let data = []
//     for (let i = 0; i < tables.length; i ++) {
//         data.push(parseTable(tables[i]));
//     }
//     console.log(data)
//     return data
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
// function getTextContentFromElement(el: Element, document: Document): string {
//     el.querySelectorAll("br").forEach((br) => {
//         const newLine = document.createElement("span");
//         newLine.textContent = "\n";
//         br.replaceWith(newLine);
//     });
//     return el.textContent.trim();
// }

main();

