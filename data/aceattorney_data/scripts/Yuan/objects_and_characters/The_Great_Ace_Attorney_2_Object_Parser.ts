import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs"
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts";


const OBJECT_RAW_DATA_ROOT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "objects_raw");
const OBJECT_FILES_NAMES = fs.readdirSync(OBJECT_RAW_DATA_ROOT_DIRECTORY).filter((fileName) => fileName.endsWith(".html") && fileName.includes("Great_Ace_Attorney_2"));

// Check if we found any matching files
if (OBJECT_FILES_NAMES.length === 0) {
    consola.warn("No Great Ace Attorney 2 object files found!");
}

const OBJECTS_HTML_FILE_PATHS = OBJECT_FILES_NAMES.map((fileName) => path.join(OBJECT_RAW_DATA_ROOT_DIRECTORY, fileName));
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "objects_parsed");

// The exact table style to match - but also allow partial matches
const TABLE_STYLE = "color:#000;border:3px solid #6b5e30;padding:2px;background:#dfd8bb;border-radius: 10px; -moz-border-radius: 10px; -webkit-border-radius: 10px; -khtml-border-radius: 10px; -icab-border-radius: 10px; -o-border-radius: 10px";

type ObjectData = {
    currentChapter: string;
    name: string;
    type: string;
    obtained: string;
    [key: `description${number}`]: string;
};

async function main() {
    consola.start("Parsing HTML file for Great Ace Attorney 2 objects");

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

        if (!rawHtml || rawHtml.trim() === "") {
            consola.warn(`File at ${HTML_FILE_PATH} is empty. Skipping...`);
            continue;
        }

        let dom: JSDOM;
        try {
            dom = new JSDOM(rawHtml);
            console.log("JSDOM instance created successfully.");
        } catch (e) {
            consola.fatal("Error creating JSDOM instance");
            consola.log(e);
            return;
        }

        // Log DOM structure for debugging
        console.log("Analyzing HTML structure...");
        const headings = dom.window.document.querySelectorAll("h2");
        console.log(`Found ${headings.length} h2 elements`);
        
        const tables = dom.window.document.querySelectorAll("table");
        console.log(`Found ${tables.length} table elements`);
        
        if (tables.length > 0) {
            // Log the style of the first few tables to debug
            for (let t = 0; t < Math.min(3, tables.length); t++) {
                console.log(`Table ${t} style:`, tables[t].getAttribute('style'));
            }
        }

        const parsedData = parseHtml(dom);
        console.log("HTML successfully parsed.");
        
        if (!parsedData || parsedData.length === 0) {
            consola.warn(`No data parsed from ${HTML_FILE_PATH}. Skipping file.`);
            continue;
        }

        const outputFileName = HTML_FILE_PATH.split("/").pop()?.replace(".html", ".json");
        if (!outputFileName) {
            consola.warn(`Could not determine output filename for ${HTML_FILE_PATH}. Skipping file.`);
            continue;
        }
        
        const outputPath = path.join(OUTPUT_DIRECTORY, outputFileName);

        await mkdir(OUTPUT_DIRECTORY, {recursive: true});
        await writeFile(outputPath, JSON.stringify(parsedData, null, 2));
        console.log(`Parsed data written to ${outputPath}`);
    }

    consola.success("HTML parsing and data writing successful");
}

function parseHtml(dom: JSDOM) {
    try {
        let data = [];
        const document = dom.window.document;
        
        // Try different approaches to find content
        // 1. Check if content is in div.mw-parser-output
        const contentDiv = document.querySelector("div.mw-parser-output");
        const children = contentDiv ? contentDiv.children : document.body.children;
        
        if (!children || children.length === 0) {
            consola.warn("Document body has no children. Nothing to parse.");
            return [];
        }
        
        console.log(`Found ${children.length} child elements to parse`);
        
        let chapterData = {chapter: "", evidences: []};
        let currentChapter = "";
        let childIndex = 0;
        let tablesFound = 0;
        
        while (childIndex < children.length) {
            let child = children[childIndex];
            
            if (!child) {
                childIndex++;
                continue;
            }
            
            // More flexible heading detection
            if ((child.tagName === "H2" || child.tagName === "H3") && 
                (child.classList.contains("mw-headline") || child.querySelector(".mw-headline"))) {
                
                const headlineText = child.textContent?.trim() || 
                                    child.querySelector(".mw-headline")?.textContent?.trim() || "";
                headlineText = headlineText.replace("[]", "");
                console.log(`Found heading: "${headlineText}"`);
                
                if (chapterData.chapter && chapterData.chapter.trim() !== "") {
                    console.log(`Pushing chapter: "${chapterData.chapter}" with ${chapterData.evidences.length} evidences`);
                    data.push(chapterData);
                }
                
                currentChapter = headlineText;
                chapterData = {chapter: currentChapter, evidences: []};
            } 
            // More flexible table detection - either exact match or contains key parts
            else if (child.tagName === "TABLE") {
                const style = child.getAttribute('style') || "";
                
                // Check either exact match or if it contains key style elements
                if (style === TABLE_STYLE || 
                    (style.includes("border:3px solid #6b5e30") && 
                     style.includes("background:#dfd8bb"))) {
                    
                    console.log(`Found matching table in chapter: "${currentChapter}"`);
                    tablesFound++;
                    
                    let tableData = parseTable(child, currentChapter);
                    console.log(`Parsed table data: ${tableData.name}`);
                    
                    if (tableData && tableData.description1 && tableData.description1.includes("↳")) {
                        tableData = parseDescription(tableData);
                    }
                    
                    chapterData.evidences.push(tableData);
                } else {
                    // Try to find tables that might have different styles but correct structure
                    const rows = child.querySelectorAll("td");
                    if (rows.length >= 2) {
                        console.log(`Found potential evidence table with ${rows.length} cells`);
                        let tableData = parseTable(child, currentChapter);
                        if (tableData.name && tableData.description1) {
                            console.log(`Found alternative evidence: ${tableData.name}`);
                            chapterData.evidences.push(tableData);
                            tablesFound++;
                        }
                    }
                }
            }
            ++childIndex;
        }
        
        if (chapterData.chapter && chapterData.chapter.trim() !== "") {
            console.log(`Pushing final chapter: "${chapterData.chapter}" with ${chapterData.evidences.length} evidences`);
            data.push(chapterData);
        }
        
        console.log(`Total tables/evidence items found: ${tablesFound}`);
        return data;
    } catch (e) {
        consola.fatal("Error parsing HTML content");
        consola.log(e);
        return [];
    }
}

function parseDescription(tableData: ObjectData): ObjectData {
    if (!tableData.description1) {
        return tableData;
    }
    
    let description = tableData.description1;
    let descriptions = description.split("↳");
    
    if (!descriptions || descriptions.length === 0) {
        return tableData;
    }
    
    descriptions.forEach((desc, index) => {
        if (desc) {
            tableData[`description${index + 1}`] = desc.trim();
        }
    });
    return tableData;
}

function parseTable(table: Element, currentChapter: string) {
    if (!table) {
        return { currentChapter, name: "", type: "", obtained: "", description1: "" };
    }
    
    const rows = table.querySelectorAll("td");
    let object: ObjectData = { currentChapter, name: "", type: "", obtained: "", description1: "" };
    
    if (!rows || rows.length === 0) {
        return object;
    }
    
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (!row) continue;
        
        if (i === 0) {
            object.name = row.textContent?.trim() || "";
        } else {
            object.description1 = row.textContent?.trim() || "";
        }
    }
    return object;
}

main();
