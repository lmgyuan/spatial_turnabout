import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs";
import { CASE_DATA_ROOT_DIRECTORY } from "../../../legacy/utils.ts";

// --- Configuration ---
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "characters_parsed");
const CHARACTERS_HTML_FILE_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "raw");

// Get all profile HTML files for both AAI and AAI2
const CHARACTERS_HTML_FILE_NAMES = fs.readdirSync(CHARACTERS_HTML_FILE_DIRECTORY).filter((fileName) => {
    return (
        (fileName.startsWith("List_of_Profiles_in_Ace_Attorney_Investigations") ||
         fileName.includes("Prosecutor%27s_Gambit")) && 
        fileName.endsWith(".html")
    );
});

const CHARACTERS_HTML_FILE_PATHS = CHARACTERS_HTML_FILE_NAMES.map((fileName) => 
    path.join(CHARACTERS_HTML_FILE_DIRECTORY, fileName)
);

// Style string used to identify character profile tables in Ace Attorney Investigations HTML
const CHARACTER_TABLE_STYLE = 'color:#000;border:3px solid #000;padding:2px;background:#8B8B93;border-radius: 10px; -moz-border-radius: 10px; -webkit-border-radius: 10px; -khtml-border-radius: 10px; -icab-border-radius: 10px; -o-border-radius: 10px';

// --- Type Definition ---
type CharacterData = {
    currentChapter: string;
    name: string;
    age?: string;
    gender?: string;
    [key: `description${number}`]: string | undefined;
};

// --- Main Function ---
async function main() {
    consola.start("Parsing Ace Attorney Investigations Character HTML files");

    // Ensure output directory exists
    try {
        await mkdir(OUTPUT_DIRECTORY, { recursive: true });
        consola.success(`Ensured output directory exists: ${OUTPUT_DIRECTORY}`);
    } catch (e: any) {
        if (e.code !== "EEXIST") {
            consola.fatal("Could not create output directory");
            consola.error(e);
            process.exit(1);
        }
    }

    if (CHARACTERS_HTML_FILE_PATHS.length === 0) {
        consola.warn(`No Ace Attorney Investigations profile HTML files found in ${CHARACTERS_HTML_FILE_DIRECTORY}`);
        return;
    }

    for (let i = 0; i < CHARACTERS_HTML_FILE_PATHS.length; i++) {
        const HTML_FILE_PATH = CHARACTERS_HTML_FILE_PATHS[i];
        const currentFileName = CHARACTERS_HTML_FILE_NAMES[i];
        consola.info(`Processing file: ${currentFileName}`);

        let rawHtml: string;
        try {
            rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
        } catch (e) {
            consola.error(`Could not read file at ${HTML_FILE_PATH}`);
            consola.log(e);
            continue; // Skip to the next file on read error
        }

        let dom: JSDOM;
        try {
            dom = new JSDOM(rawHtml);
        } catch (e) {
            consola.error(`Malformed HTML content in ${currentFileName}`);
            consola.log(e);
            continue; // Skip to the next file on parse error
        }

        const document = dom.window.document;
        // Standard content wrapper class for MediaWiki sites
        const contentWrapper = document.querySelector(".mw-parser-output");
        if (!contentWrapper) {
            consola.error(`Could not find the content wrapper element (.mw-parser-output) in ${currentFileName}`);
            continue; // Skip to the next file if content wrapper is missing
        }

        const parsedData = parseHTMLContent(contentWrapper, document);

        if (parsedData.length === 0) {
            consola.warn(`No character data parsed from ${currentFileName}. Check H2 tags and table styles.`);
            continue; // Skip writing if no data was parsed
        }

        consola.log(`Parsed ${parsedData.reduce((sum, chap) => sum + chap.characters.length, 0)} characters from ${currentFileName}. Writing to JSON file...`);

        // Determine game name for the output filename
        let gameName: string;
        if (currentFileName.includes("Prosecutor%27s_Gambit") || currentFileName.includes("Prosecutor's_Gambit")) {
            gameName = "List_of_Profiles_in_Ace_Attorney_Investigations_2_Prosecutor's_Gambit";
        } else {
            gameName = "List_of_Profiles_in_Ace_Attorney_Investigations_Miles_Edgeworth";
        }

        // Generate output path
        const outputFilePath = path.join(OUTPUT_DIRECTORY, `${gameName}.json`);

        try {
            await writeFile(outputFilePath, JSON.stringify(parsedData, null, 2));
            consola.success(`Successfully wrote character data to ${outputFilePath}`);
        } catch (e) {
            consola.error(`Could not write character data to ${outputFilePath}`);
            consola.log(e);
        }
    }

    consola.success("Character parsing completed!");
}

// --- HTML Parsing Logic ---
function parseHTMLContent(contentWrapper: Element, document: Document): Array<{ chapter: string; characters: CharacterData[] }> {
    let data: Array<{ chapter: string; characters: CharacterData[] }> = [];
    let childIndex = 0;
    let currentChapter = "";
    // Initialize with empty chapter to handle cases where the first element isn't H2
    let chapterData: { chapter: string; characters: CharacterData[] } = { chapter: "", characters: [] };

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];

        if (child.tagName === "H2") {
            // Save previous chapter's data if it exists and has characters
            if (chapterData.chapter && chapterData.characters.length > 0) {
                data.push(chapterData);
            }

            // Extract chapter name (prefer .mw-headline)
            currentChapter = child.querySelector('.mw-headline')?.textContent?.trim() || child.textContent?.split("[")[0].trim() || "Unknown Chapter";
            // Handle potential special non-breaking space characters and trim trailing whitespace
            currentChapter = currentChapter.replace(/[\u00A0\s]+$/, '').trim();
            chapterData = { chapter: currentChapter, characters: [] };
            consola.debug(`Found chapter: ${currentChapter}`);

        } else if (child.tagName === "TABLE" && 
                  (child.getAttribute('style') === CHARACTER_TABLE_STYLE || 
                   child.outerHTML.includes('ProfileAAI'))) { // Added check for ProfileAAI template
            // Check if we are inside a chapter section (or assign to default)
            if (!chapterData.chapter) {
                consola.warn("Found character table outside of an H2 chapter section. Assigning to 'Unknown Chapter'.");
                chapterData.chapter = "Unknown Chapter";
            }

            try {
                const tableData = parseTable(child, chapterData.chapter);
                // Process multi-part descriptions (must run before adding to collection)
                const processedData = parseDescription(tableData);
                
                if (processedData.name) { // Only add if a name was successfully parsed
                    chapterData.characters.push(processedData);
                    consola.debug(`Parsed character: ${processedData.name} for chapter ${chapterData.chapter}`);
                } else {
                    consola.warn(`Parsed a table in chapter "${chapterData.chapter}" but could not extract character name.`);
                }
            } catch (parseError) {
                consola.error(`Error parsing character table in chapter "${chapterData.chapter}":`, parseError);
            }
        }
        childIndex++;
    }

    // Add the last chapter's data if it exists and has characters
    if (chapterData.chapter && chapterData.characters.length > 0) {
        data.push(chapterData);
    }

    return data;
}

// --- Description Parsing (Handles multi-part descriptions using "↳") ---
function parseDescription(tableData: CharacterData): CharacterData {
    // Make a copy to avoid modifying the original object directly
    const processedData = { ...tableData };
    
    // Process description1 if it exists
    if (processedData.description1) {
        const description = processedData.description1;
        
        // Check if description contains the special arrow character for multi-part descriptions
        if (description.includes("↳")) {
            // Split by arrow character
            const parts = description.split("↳");
            
            // Remove the original combined description
            delete processedData.description1;
            
            // Add each part as a separate description field
            parts.forEach((part, index) => {
                const trimmedPart = part.trim();
                if (trimmedPart) {
                    processedData[`description${index + 1}`] = trimmedPart;
                }
            });
        }
    }
    
    return processedData;
}

// --- Table Parsing ---
function parseTable(table: Element, currentChapter: string): CharacterData {
    const object: CharacterData = {
        currentChapter,
        name: ""
    };

    // Get all table rows
    const rows = Array.from(table.querySelectorAll("tr"));
    if (rows.length === 0) {
        consola.warn(`No rows found in character table in chapter "${currentChapter}".`);
        return object;
    }

    // Check if this is a ProfileAAI template table (specific to the Wiki format)
    const isProfileTemplate = table.outerHTML.includes('ProfileAAI');
    
    if (isProfileTemplate) {
        // Special handling for ProfileAAI template tables
        // These usually have a different structure with name in first row and details in second row
        
        // Get the name from the first row (first cell)
        if (rows[0]) {
            const firstCell = rows[0].querySelector('td');
            if (firstCell && firstCell.textContent) {
                // Clean up name by removing potential "[edit]" links
                object.name = firstCell.textContent.replace(/\[edit\]/g, '').trim();
            }
        }
        
        // Get the age from the second row (first cell)
        if (rows[1]) {
            const ageCell = rows[1].querySelector('td');
            if (ageCell && ageCell.textContent) {
                let ageText = ageCell.textContent.trim();
                ageText = ageText.replace("•", "").trim();
                ageText = ageText.replace("Age:", "").trim();
                object.age = ageText;
            }
        }

        // Get the gender from the second row (second cell)
        if (rows[2]) {
            const genderCell = rows[2].querySelector('td');
            if (genderCell && genderCell.textContent) {
                let genderText = genderCell.textContent.trim();
                genderText = genderText.replace("•", "").trim();
                genderText = genderText.replace("Gender:", "").trim();
                object.gender = genderText;
            }
        }

        // Get the description from the second row (third cell)
        if (rows[3]) {
            const descriptionCell = rows[3].querySelector('td');
            if (descriptionCell && descriptionCell.textContent) {
                const descriptionParts = descriptionCell.textContent.trim().split("↳");
                for (let i = 0; i < descriptionParts.length; i++) {
                    const trimmedPart = descriptionParts[i].trim();
                    if (trimmedPart) {
                        object[`description${i + 1}`] = trimmedPart;
                    }
                }
            }
        }
        
        return object;
    }
    
    // Standard table handling for non-template tables
    // Locate cells containing name and details
    let nameCell: Element | null = null;
    let detailsCell: Element | null = null;

    // Try to locate name cell (usually first cell of first row)
    if (rows[0]) {
        const firstRowCells = Array.from(rows[0].children).filter(el => el.tagName === 'TD');
        if (firstRowCells.length > 0) {
            nameCell = firstRowCells[0];
            
            // Extract character name - Look for a header tag first
            const nameHeader = nameCell.querySelector('b') || nameCell.querySelector('strong');
            if (nameHeader && nameHeader.textContent) {
                object.name = nameHeader.textContent.trim();
            } 
            // If no header, use the cell's text content
            else if (nameCell.textContent) {
                object.name = nameCell.textContent.trim();
            }
        }
    }

    if (rows[1]) {
        const ageCell = rows[1].querySelector('td');
        if (ageCell && ageCell.textContent) {
            let ageText = ageCell.textContent.trim();
            ageText = ageText.replace("•", "").trim();
            ageText = ageText.replace("Age:", "").trim();
            object.age = ageText;
        }
    }

    if (rows[2]) {
        const genderCell = rows[2].querySelector('td');
        if (genderCell && genderCell.textContent) {
            let genderText = genderCell.textContent.trim();
            genderText = genderText.replace("•", "").trim();
            genderText = genderText.replace("Gender:", "").trim();
            object.gender = genderText;
        }
    }

    if (rows[3]) {
        const descriptionCell = rows[3].querySelector('td');
        if (descriptionCell && descriptionCell.textContent) {
            const descriptionParts = descriptionCell.textContent.trim().split("↳");
            for (let i = 0; i < descriptionParts.length; i++) {
                const trimmedPart = descriptionParts[i].trim();
                if (trimmedPart) {
                    object[`description${i + 1}`] = trimmedPart;
                }
            }
        }
    }
            
    return object;
}

// Helper function to process details cell content
function processDetailsCell(detailsCell: Element, object: CharacterData): void {
    const detailsHtml = detailsCell.innerHTML;
    
    // Split by <br> tag, case-insensitive, allowing for self-closing or not
    const lines = detailsHtml.split(/<br\s*\/?>/i);
    let descriptionParts: string[] = [];
    let hasAgeOrGender = false;

    lines.forEach(lineHtml => {
        // Trim HTML whitespace before parsing
        const trimmedLineHtml = lineHtml.trim();
        if (!trimmedLineHtml) return; // Skip empty lines

        // Use JSDOM to parse the line fragment and get text content
        const lineDom = new JSDOM(`<div>${trimmedLineHtml}</div>`);
        let lineText = lineDom.window.document.body.textContent?.trim() || "";

        // Remove potential "[edit]" link text
        lineText = lineText.replace(/\[edit\]/gi, '').trim();
        if (!lineText) return;

        // Check for known prefixes with more robust handling
        const lowerLineText = lineText.toLowerCase();
        
        if (lowerLineText.startsWith("age:")) {
            object.age = lineText.substring(lineText.indexOf(':') + 1).trim();
            hasAgeOrGender = true;
        } 
        else if (lowerLineText.startsWith("gender:")) {
            object.gender = lineText.substring(lineText.indexOf(':') + 1).trim();
            hasAgeOrGender = true;
        } 
        else {
            // If it's not Age or Gender, consider it part of the description
            descriptionParts.push(lineText);
        }
    });

    // Join the collected description parts into description1
    if (descriptionParts.length > 0) {
        const joinedDescription = descriptionParts.join(" ").trim();
        
        // If no Age or Gender was found, check if description actually contains them
        if (!hasAgeOrGender && joinedDescription.includes("Age:") && joinedDescription.includes("Gender:")) {
            // Try to extract Age and Gender from the combined description
            const agePart = joinedDescription.match(/Age:\s*([^,;]+)/i);
            if (agePart && agePart[1]) {
                object.age = agePart[1].trim();
            }
            
            const genderPart = joinedDescription.match(/Gender:\s*([^,;]+)/i);
            if (genderPart && genderPart[1]) {
                object.gender = genderPart[1].trim();
            }
            
            // Create a clean description without the Age/Gender parts
            const cleanDescription = joinedDescription
                .replace(/Age:\s*[^,;]+[,;]?\s*/i, '')
                .replace(/Gender:\s*[^,;]+[,;]?\s*/i, '')
                .trim();
                
            if (cleanDescription) {
                object.description1 = cleanDescription;
            }
        } else {
            // If Age/Gender were already handled separately or not present
            object.description1 = joinedDescription;
        }
    }
}

// Run the main function
main().catch(error => {
    consola.fatal("Unhandled error during script execution:");
    consola.error(error);
    process.exit(1);
});
