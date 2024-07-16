import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";

const CASE_DATA_ROOT_DIRECTORY = "./case_data";  // Define your root directory
const HTML_FILE_PATH = path.join(CASE_DATA_ROOT_DIRECTORY, "raw/1-1.html");
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed");

async function main() {
    consola.start("Parsing HTML file");

    let rawHtml: string;
    try {
        rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
    } catch (e) {
        consola.fatal(`Could not read file at ${HTML_FILE_PATH}`);
        consola.log(e);
        return;
    }

    let dom: JSDOM;
    try {
        dom = new JSDOM(rawHtml);
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

    const parsedData = parseHtmlContent(contentWrapper, document);
    consola.log("Writing parsed data to JSON file");
    if (!existsSync(OUTPUT_DIRECTORY)) {
        await mkdir(OUTPUT_DIRECTORY);
    }

    await writeFile(
        path.join(OUTPUT_DIRECTORY, "parsed_data.json"),
        JSON.stringify(parsedData, null, 2)
    );

    consola.success("HTML parsing completed");
}

function parseHtmlContent(contentWrapper: Element, document: Document) {
    const data = {};
    let contextBuffer: string[] = [];
    let childIndex = 0;

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];

        if (child.tagName === "TH" && child.textContent.includes("Present")) {
            const context = contextBuffer.join("\n").trim();
            const crossExamination = parseCrossExamination(contentWrapper, childIndex, document);

            data[childIndex] = {
                context,
                category: "cross_examination",
                ...crossExamination,
            };
            contextBuffer = [];
            childIndex += crossExamination.testimonies.length + 1;
        } else {
            contextBuffer.push(getTextContentFromElement(child));
            ++childIndex;
        }
    }

    return data;
}

function parseCrossExamination(contentWrapper: Element, startIndex: number, document: Document) {
    const testimonies = [];
    let buffer = [];
    const courtRecord = { objects: [], people: [] };
    let childIndex = startIndex;

    // Find the first <hr> before cross examination
    while (childIndex < contentWrapper.children.length) {
        if (contentWrapper.children[childIndex].tagName === "HR") break;
        ++childIndex;
    }

    // Skip cross examination text and move to testimonies
    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex] as HTMLElement;
        if (child.tagName === "HR") break;
        if (child.tagName === "SPAN" && child.style.color === "red" && child.textContent.trim() === "Cross Examination") {
            childIndex += 2;
            break;
        }
        ++childIndex;
    }

    for (; childIndex < contentWrapper.children.length; ++childIndex) {
        const child = contentWrapper.children[childIndex] as HTMLElement;
        if (child.tagName === "HR") break;

        if (child.tagName === "P" && child.querySelector("span[style*='color:red']")) {
            // Add to court record
            const object = getTextContentFromElement(child);
            courtRecord.objects.push({ name: object, description: "TODO" });  // Add appropriate description
        } else if (child.tagName === "P" && child.querySelector("span[style*='color:green']")) {
            const name = child.querySelector("span[style*='color:green']").textContent.split(':')[0].trim();
            const comment = child.querySelector("span[style*='color:green']").textContent.split(':')[1].trim();
            const pressResponse = getPressResponse(contentWrapper, childIndex, document);
            testimonies.push({ testimony: comment, person: name, press_response: pressResponse });
        } else {
            buffer.push(getTextContentFromElement(child));
        }
    }

    return {
        court_record: courtRecord,
        testimonies,
    };
}

function getPressResponse(contentWrapper: Element, index: number, document: Document) {
    let response = "";
    while (++index < contentWrapper.children.length) {
        const child = contentWrapper.children[index] as HTMLElement;
        if (child.tagName === "P" && child.querySelector("span[style*='color:blue']")) {
            response = getTextContentFromElement(child);
            break;
        }
    }
    return response;
}

function getTextContentFromElement(el: Element): string {
    el.querySelectorAll("br").forEach((br) => {
        const newLine = document.createElement("span");
        newLine.textContent = "\n";
        br.replaceWith(newLine);
    });
    return el.textContent.trim();
}

main();
