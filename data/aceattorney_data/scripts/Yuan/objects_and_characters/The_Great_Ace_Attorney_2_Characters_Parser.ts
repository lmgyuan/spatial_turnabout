import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs";
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts";

const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "characters_parsed");
const CHARACTERS_HTML_FILE_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "raw");
const CHARACTERS_HTML_FILE_NAMES = fs.readdirSync(CHARACTERS_HTML_FILE_DIRECTORY).filter((fileName) => 
    fileName.startsWith("List_of_Profiles_in") && fileName.includes("Great_Ace_Attorney_2"));
const CHARACTERS_HTML_FILE_PATHS = CHARACTERS_HTML_FILE_NAMES.map((fileName) => path.join(CHARACTERS_HTML_FILE_DIRECTORY, fileName));

// Check if we found any matching files
if (CHARACTERS_HTML_FILE_NAMES.length === 0) {
    consola.warn("No Great Ace Attorney 2 character files found!");
}

mkdir(OUTPUT_DIRECTORY).catch((e) => {
    if (e.code !== "EEXIST") {
        consola.fatal("Error creating output directory");
        consola.log(e);
    }
});

type CharacterData = {
    currentChapter: string;
    name: string;
    age: string;
    gender?: string;
    description1: string;
};

async function main() {
    consola.start("Parsing HTML files for Great Ace Attorney 2 character profiles");

    for (let i = 0; i < CHARACTERS_HTML_FILE_PATHS.length; i++) {
        const HTML_FILE_PATH = CHARACTERS_HTML_FILE_PATHS[i];
        let rawHtml;
        
        try {
            rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
            console.log(`Raw HTML content read successfully from ${HTML_FILE_PATH}`);
        } catch (e) {
            consola.fatal(`Could not read file at ${HTML_FILE_PATH}`);
            consola.log(e);
            return;
        }

        if (!rawHtml || rawHtml.trim() === "") {
            consola.warn(`File at ${HTML_FILE_PATH} is empty. Skipping...`);
            continue;
        }

        let dom;
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
        const contentDiv = document.querySelector("div.mw-parser-output");
        const children = contentDiv ? contentDiv.children : document.body.children;
        
        if (!children || children.length === 0) {
            consola.warn("Document body has no children. Nothing to parse.");
            return [];
        }
        
        console.log(`Found ${children.length} child elements to parse`);
        
        let chapterData = {chapter: "", characters: []};
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
                console.log(`Found heading: "${headlineText}"`);
                
                if (chapterData.chapter && chapterData.chapter.trim() !== "") {
                    console.log(`Pushing chapter: "${chapterData.chapter}" with ${chapterData.characters.length} characters`);
                    data.push(chapterData);
                }
                
                // Split by [ to remove the [] at the end of the chapter name if present
                currentChapter = headlineText.split("[")[0].trim();
                // Handle special characters if needed
                if (currentChapter.includes(" ")) {
                    currentChapter = currentChapter.replace(" ", " ");
                }
                
                chapterData = {chapter: currentChapter, characters: []};
            } 
            // Table detection
            else if (child.tagName === "TABLE") {
                // Check for profile tables - they typically have specific structure
                const rows = child.querySelectorAll("tr");
                if (rows.length >= 2) {
                    console.log(`Found potential character profile table with ${rows.length} rows`);
                    let tableData = parseDescription(parseProfile(child, currentChapter));
                    
                    if (tableData && tableData.name) {
                        console.log(`Found character: ${tableData.name}`);
                        chapterData.characters.push(tableData);
                        tablesFound++;
                    }
                }
            }
            
            ++childIndex;
        }
        
        if (chapterData.chapter && chapterData.chapter.trim() !== "") {
            console.log(`Pushing final chapter: "${chapterData.chapter}" with ${chapterData.characters.length} characters`);
            data.push(chapterData);
        }
        
        console.log(`Total character profiles found: ${tablesFound}`);
        return data;
    } catch (e) {
        consola.fatal("Error parsing HTML content");
        consola.log(e);
        return [];
    }
}

function parseDescription(tableData: CharacterData): CharacterData {
    return tableData;
}

function parseProfile(table: Element, currentChapter: string) {
    const rows = table.querySelectorAll("td");
    let object: CharacterData = { currentChapter: currentChapter, name: "", age: "", description1: "" };
    
    if (!rows || rows.length === 0) {
        return object;
    }
    
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (!row) continue;
        
        if (i === 0) {
            object.name = row.textContent?.trim() || "";
        } else if (i === 1) {
            // Try to extract age from text like "Age: 23"
            const ageText = row.textContent?.trim() || "";
            const ageParts = ageText.split(":");
            object.age = ageParts.length > 1 ? ageParts.slice(1).join(" ").trim() : ageText;
        } else {
            object.description1 = row.textContent?.trim() || "";
        }
    }
    return object;
}

main();
