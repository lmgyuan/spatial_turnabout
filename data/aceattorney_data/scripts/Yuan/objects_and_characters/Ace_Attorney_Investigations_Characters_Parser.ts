import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs";
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts"; // Assuming this path is correct

// --- Configuration ---
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "characters_parsed");
const CHARACTERS_HTML_FILE_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "raw");
// Filter specifically for Ace Attorney Investigations profile files
const CHARACTERS_HTML_FILE_NAMES = fs.readdirSync(CHARACTERS_HTML_FILE_DIRECTORY).filter((fileName) =>
    fileName.startsWith("List_of_Profiles_in_Ace_Attorney_Investigations")
);
const CHARACTERS_HTML_FILE_PATHS = CHARACTERS_HTML_FILE_NAMES.map((fileName) => path.join(CHARACTERS_HTML_FILE_DIRECTORY, fileName));

// Style string used to identify character profile tables in Ace Attorney Investigations HTML
const CHARACTER_TABLE_STYLE = 'color:#000;border:3px solid #000;padding:2px;background:#8B8B93;border-radius: 10px; -moz-border-radius: 10px; -webkit-border-radius: 10px; -khtml-border-radius: 10px; -icab-border-radius: 10px; -o-border-radius: 10px';

// --- Type Definition ---
type CharacterData = {
    currentChapter: string;
    name: string;
    age?: string; // Optional fields based on cleanup logic
    gender?: string; // Optional fields based on cleanup logic
    [key: `description${number}`]: string | undefined; // Allow undefined for cleaned descriptions
};

// --- Main Function ---
async function main() {
    consola.start("Parsing Ace Attorney Investigations Character HTML files");

    // Ensure output directory exists (moved inside main)
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
            // Removed success log here for brevity per file
        } catch (e) {
            consola.error(`Could not read file at ${HTML_FILE_PATH}`);
            consola.log(e);
            continue; // Skip to the next file on read error
        }

        let dom: JSDOM;
        try {
            dom = new JSDOM(rawHtml);
            // Removed success log here for brevity per file
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
        const outputJsonFileName = `${currentFileName.split(".html")[0]}.json`;
        const outputJsonPath = path.join(OUTPUT_DIRECTORY, outputJsonFileName);

        try {
            // Use JSON.stringify with null, 2 for pretty printing
            await writeFile(outputJsonPath, JSON.stringify(parsedData, null, 2));
            consola.success(`Successfully wrote parsed data to ${outputJsonPath}`);
        } catch (e) {
            consola.error(`Failed to write JSON file ${outputJsonPath}`);
            consola.log(e);
        }
    }
    consola.success("Finished processing all Ace Attorney Investigations files.");
}

// --- HTML Parsing Logic (Structure from Characters_Parser.ts, specifics from Investigations) ---
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
            } else if (chapterData.chapter) {
                // Optional: Log chapters with no characters found
                // consola.debug(`No characters found for chapter: ${chapterData.chapter}`);
            }

            // Extract chapter name using Investigations logic (prefer .mw-headline)
            currentChapter = child.querySelector('.mw-headline')?.textContent?.trim() || child.textContent?.split("[")[0].trim() || "Unknown Chapter";
            // Handle potential special non-breaking space characters and trim trailing whitespace
            currentChapter = currentChapter.replace(/[\u00A0\s]+$/, '').trim();
            chapterData = { chapter: currentChapter, characters: [] };
            // consola.debug(`Found chapter: ${currentChapter}`); // Optional debug log

        } else if (child.tagName === "TABLE" && child.getAttribute('style') === CHARACTER_TABLE_STYLE) {
            // Check if we are inside a chapter section (or assign to default)
            if (!chapterData.chapter) {
                consola.warn("Found character table outside of an H2 chapter section. Assigning to 'Unknown Chapter'.");
                chapterData.chapter = "Unknown Chapter";
            }
            try {
                // Use the detailed parseTable function specific to Investigations structure
                let tableData = parseTable(child, chapterData.chapter);

                // Check if description needs splitting *after* parsing the table
                if (tableData.description1 && typeof tableData.description1 === 'string' && tableData.description1.includes("↳")) {
                    tableData = parseDescription(tableData);
                }

                if (tableData.name) { // Only add if a name was successfully parsed
                    chapterData.characters.push(tableData);
                    // consola.debug(`Parsed character: ${tableData.name} for chapter ${chapterData.chapter}`); // Optional debug log
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
    } else if (chapterData.chapter) {
         // Optional: Log the last chapter if it had no characters
         // consola.debug(`No characters found for the last chapter: ${chapterData.chapter}`);
    }

    return data;
}

// --- Description Parsing (Handles multi-part descriptions using "↳") ---
function parseDescription(tableData: CharacterData): CharacterData {
    // Assumes description1 holds the combined string initially
    let description = tableData.description1 || "";
    let descriptions = description.split("↳");

    // Important: Clear the original combined description *before* adding numbered ones
    // Use delete or set to undefined based on preference. Undefined might be safer for type consistency.
    tableData.description1 = undefined;
    // delete tableData.description1; // Alternative

    descriptions.forEach((desc, index) => {
        // Assign to description1, description2, etc.
        tableData[`description${index + 1}`] = desc.trim();
    });
    return tableData;
}

// --- Table Parsing (More flexible logic) ---
// This function attempts to find name and details cells based on content patterns
function parseTable(table: Element, currentChapter: string): CharacterData {
    // Initialize with default values
    let object: CharacterData = { currentChapter: currentChapter, name: "", age: undefined, gender: undefined, description1: undefined };

    // Find the first table body and its direct rows
    const tbody = table.querySelector("tbody");
    if (!tbody) {
        consola.warn(`Could not find <tbody> in a table for chapter "${currentChapter}".`);
        return object;
    }
    // Get direct children rows of the tbody
    const rows = Array.from(tbody.children).filter(el => el.tagName === 'TR');
    if (rows.length === 0) {
        consola.warn(`Could not find any <tr> elements within <tbody> for a table in chapter "${currentChapter}".`);
        return object;
    }

    // Assume the primary data is in the first row
    const firstRow = rows[0];
    const cells = Array.from(firstRow.children).filter(el => el.tagName === 'TD');

    if (cells.length === 0) {
        consola.warn(`Could not find any <td> elements within the first <tr> for a table in chapter "${currentChapter}".`);
        return object;
    }

    let nameCell: Element | null = null;
    let detailsCell: Element | null = null;

    // Attempt to identify name cell (often the first one, might have <b>)
    if (cells.length > 0) {
        const potentialNameCell = cells[0];
        // Check if it has significant text content or a bold tag inside
        const boldTag = potentialNameCell.querySelector('b');
        const textContent = (boldTag?.textContent || potentialNameCell.textContent)?.trim();
        if (textContent && textContent.length > 1) { // Require more than 1 char to be likely name
             nameCell = potentialNameCell;
             object.name = textContent.replace(/\s+/g, ' ').trim();
             consola.debug(`Identified potential name cell (1st TD): "${object.name}"`);
        }
    }

    // Attempt to identify details cell (look for Age:, Gender:, or <br>)
    // Start searching from the second cell onwards if the first was identified as name, otherwise check all
    const searchStartIndex = nameCell ? 1 : 0;
    for (let i = searchStartIndex; i < cells.length; i++) {
        const cell = cells[i];
        const cellHtml = cell.innerHTML;
        // Check for keywords or multiple line breaks as indicators
        if (cellHtml.includes("Age:") || cellHtml.includes("Gender:") || (cellHtml.match(/<br\s*\/?>/gi)?.length ?? 0) > 0) {
            detailsCell = cell;
            consola.debug(`Identified potential details cell (TD index ${i})`);
            break; // Assume the first cell matching criteria is the details cell
        }
    }

    // Log warnings if cells weren't identified
    if (!nameCell) {
        consola.warn(`Could not reliably identify the name cell for a table in chapter "${currentChapter}".`);
        // Attempt fallback: maybe name is in 2nd row's first cell? (Less common)
        if (rows.length > 1) {
            const secondRowCells = Array.from(rows[1].children).filter(el => el.tagName === 'TD');
            if (secondRowCells.length > 0) {
                 const fallbackName = secondRowCells[0].textContent?.replace(/\s+/g, ' ').trim();
                 if (fallbackName && fallbackName.length > 1) {
                     object.name = fallbackName;
                     consola.debug(`Fallback: Found potential name in second row, first cell: "${object.name}"`);
                 }
            }
        }
    }
     if (!detailsCell) {
        // Use object.name in the warning if it was found
        consola.warn(`Could not reliably identify the details cell for character "${object.name || 'Unknown'}" in chapter "${currentChapter}".`);
    }


    // --- Process Details Cell (if found) ---
    if (detailsCell) {
        const detailsHtml = detailsCell.innerHTML;
        // Split by <br> tag, case-insensitive, allowing for self-closing or not
        const lines = detailsHtml.split(/<br\s*\/?>/i);
        let descriptionParts: string[] = [];

        lines.forEach(lineHtml => {
            // Trim HTML whitespace before parsing to avoid empty strings from just whitespace
            const trimmedLineHtml = lineHtml.trim();
            if (!trimmedLineHtml) return; // Skip empty lines resulting from split

            // Use JSDOM to parse the line fragment and get text content, stripping potential HTML tags
            const lineDom = new JSDOM(`<div>${trimmedLineHtml}</div>`);
            // Get text content and trim resulting whitespace
            let lineText = lineDom.window.document.body.textContent?.trim() || "";

            // Remove potential trailing "[edit]" link text more robustly
            lineText = lineText.replace(/\[edit\]$/i, '').trim();

            // Skip if the line becomes empty after trimming and removing [edit]
            if (!lineText) return;

            // Check for known prefixes
            if (lineText.startsWith("Age:")) {
                // Ensure age is captured even if description logic changes
                object.age = lineText.substring(4).trim();
            } else if (lineText.startsWith("Gender:")) {
                 // Ensure gender is captured even if description logic changes
                object.gender = lineText.substring(7).trim();
            } else {
                // If it's not Age or Gender, and it's not empty, consider it part of the description
                descriptionParts.push(lineText);
            }
        });

        // Join the collected description parts into description1, only if any parts were found
        if (descriptionParts.length > 0) {
             // Join with a single space, and trim final result
            object.description1 = descriptionParts.join(" ").trim();
        } else {
            // Ensure description1 is explicitly undefined if no parts were collected
            object.description1 = undefined;
        }
    }
    // --- End Process Details Cell ---


    // Final check: if no name was found at all, this probably wasn't a valid character table
    if (!object.name) {
        consola.warn(`Failed to extract a name from a table matching the style in chapter "${currentChapter}". Skipping this table.`);
        return { currentChapter: currentChapter, name: "" }; // Return minimal object indicating failure to parse name
    }

    // Clean up empty fields
    if (!object.age) object.age = undefined;
    if (!object.gender) object.gender = undefined;
    if (!object.description1) object.description1 = undefined;

    return object;
}

// --- Script Execution ---
main().catch(error => {
    consola.fatal("Unhandled error during script execution:");
    consola.error(error);
    process.exit(1);
});
