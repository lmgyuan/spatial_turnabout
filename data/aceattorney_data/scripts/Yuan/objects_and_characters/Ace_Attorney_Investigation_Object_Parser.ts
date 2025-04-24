import * as path from "path";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import fs from "fs";
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts"; // Assuming this path is correct

// --- Configuration ---
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "objects_parsed"); // Output directory for parsed objects
const OBJECT_RAW_DATA_ROOT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "objects_raw"); // Directory containing raw HTML files for objects/evidence

// Filter specifically for Ace Attorney Investigations evidence/object files
const OBJECT_HTML_FILE_NAMES = fs.readdirSync(OBJECT_RAW_DATA_ROOT_DIRECTORY).filter((fileName) =>
    fileName.startsWith("List_of_Evidence_in_Ace_Attorney_Investigations") && fileName.endsWith(".html")
);
const OBJECT_HTML_FILE_PATHS = OBJECT_HTML_FILE_NAMES.map((fileName) => path.join(OBJECT_RAW_DATA_ROOT_DIRECTORY, fileName));

// Style string used to identify evidence tables (seems same as character tables in Investigations)
const EVIDENCE_TABLE_STYLE = 'color:#000;border:3px solid #000;padding:2px;background:#8B8B93;border-radius: 10px; -moz-border-radius: 10px; -webkit-border-radius: 10px; -khtml-border-radius: 10px; -icab-border-radius: 10px; -o-border-radius: 10px';

// --- Type Definition (Based on Object_Parser.ts, adjusted for observed data) ---
type ObjectData = {
    currentChapter: string;
    name: string;
    // type?: string; // Not obviously present in the AAI HTML structure
    // obtained?: string; // Not obviously present in the AAI HTML structure
    [key: `description${number}`]: string | undefined; // Allow undefined for cleaned descriptions
};

// --- Main Function ---
async function main() {
    consola.start("Parsing Ace Attorney Investigations Evidence/Object HTML files");

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


    if (OBJECT_HTML_FILE_PATHS.length === 0) {
        consola.warn(`No Ace Attorney Investigations evidence HTML files found in ${OBJECT_RAW_DATA_ROOT_DIRECTORY}`);
        return;
    }

    for (let i = 0; i < OBJECT_HTML_FILE_PATHS.length; i++) {
        const HTML_FILE_PATH = OBJECT_HTML_FILE_PATHS[i];
        const currentFileName = OBJECT_HTML_FILE_NAMES[i];
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
        const contentWrapper = document.querySelector(".mw-parser-output");
        if (!contentWrapper) {
            consola.error(`Could not find the content wrapper element (.mw-parser-output) in ${currentFileName}`);
            continue; // Skip to the next file if content wrapper is missing
        }

        const parsedData = parseHTMLContent(contentWrapper, document);

        if (parsedData.length === 0) {
             consola.warn(`No evidence data parsed from ${currentFileName}. Check H2 tags and table styles.`);
             continue; // Skip writing if no data was parsed
        }

        consola.log(`Parsed ${parsedData.reduce((sum, chap) => sum + chap.evidences.length, 0)} evidences from ${currentFileName}. Writing to JSON file...`);
        const outputJsonFileName = `${currentFileName.split(".html")[0]}.json`;
        const outputJsonPath = path.join(OUTPUT_DIRECTORY, outputJsonFileName);

        try {
            await writeFile(outputJsonPath, JSON.stringify(parsedData, null, 2));
            consola.success(`Successfully wrote parsed data to ${outputJsonPath}`);
        } catch (e) {
            consola.error(`Failed to write JSON file ${outputJsonPath}`);
            consola.log(e);
        }
    }
    consola.success("Finished processing all Ace Attorney Investigations evidence files.");
}

// --- HTML Parsing Logic ---
function parseHTMLContent(contentWrapper: Element, document: Document): Array<{ chapter: string; evidences: ObjectData[] }> {
    let data: Array<{ chapter: string; evidences: ObjectData[] }> = [];
    let childIndex = 0;
    let currentChapter = "";
    let chapterData: { chapter: string; evidences: ObjectData[] } = { chapter: "", evidences: [] };

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];

        if (child.tagName === "H2") {
            // Save previous chapter's data if it exists and has evidence
            if (chapterData.chapter && chapterData.evidences.length > 0) {
                data.push(chapterData);
            }

            // Extract chapter name
            currentChapter = child.querySelector('.mw-headline')?.textContent?.trim() || child.textContent?.split("[")[0].trim() || "Unknown Chapter";
            currentChapter = currentChapter.replace(/[\u00A0\s]+$/, '').trim(); // Clean trailing spaces/nbsp
            chapterData = { chapter: currentChapter, evidences: [] };

        } else if (child.tagName === "TABLE" && child.getAttribute('style') === EVIDENCE_TABLE_STYLE) {
            // Check if we are inside a chapter section
            if (!chapterData.chapter) {
                consola.warn("Found evidence table outside of an H2 chapter section. Assigning to 'Unknown Chapter'.");
                chapterData.chapter = "Unknown Chapter";
            }
            try {
                // consola.log("Processing evidence table:", {
                //     tagName: child.tagName,
                //     style: child.getAttribute('style'),
                //     textContent: child.textContent
                // }, "\n");

                // Use the specific parseTable function for AAI evidence structure
                let tableData = parseTable(child, chapterData.chapter);

                // Check if description needs splitting
                if (tableData.description1 && typeof tableData.description1 === 'string' && tableData.description1.includes("↳")) {
                    tableData = parseDescription(tableData);
                }

                if (tableData.name) { // Only add if a name was successfully parsed
                    chapterData.evidences.push(tableData);
                } else {
                    // Warning already logged in parseTable if name extraction failed
                }
            } catch (parseError) {
                consola.error(`Error parsing evidence table in chapter "${chapterData.chapter}":`, parseError);
            }
        }
        childIndex++;
    }

    // Add the last chapter's data if it exists and has evidence
    if (chapterData.chapter && chapterData.evidences.length > 0) {
        data.push(chapterData);
    } else if (chapterData.chapter) {
         // consola.debug(`No evidence found for chapter: ${chapterData.chapter}`);
    }

    return data;
}

// --- Table Parsing (More Flexible Row Scanning) ---
// Scans rows to find Name and Description based on content, not fixed position.
function parseTable(table: Element, currentChapter: string): ObjectData {
    let object: ObjectData = { currentChapter: currentChapter, name: "", description1: undefined };
    let nameFound = false;
    let descriptionText = ""; // Store potential description text

    const tbody = table.querySelector("tbody");
    if (!tbody) {
        consola.warn(`[${currentChapter}] Could not find <tbody> in an evidence table.`);
        return object;
    }

    const rows = Array.from(tbody.children).filter(el => el.tagName === 'TR');
    if (rows.length === 0) {
        consola.warn(`[${currentChapter}] No <tr> elements found in table body.`);
        return object;
    }

    // Iterate through rows to find name and description
    for (const row of rows) {
        const cells = Array.from(row.children).filter(el => el.tagName === 'TD'); // Get TD cells in the current row

        // --- Attempt to find Name (usually in first row with a TD) ---
        if (!nameFound && cells.length > 0) {
            const nameCell = cells[0]; // Often the first TD after a TH
            // Check specifically for a <b> tag within this TD
            const boldTag = nameCell.querySelector('b');
            let potentialName = boldTag?.textContent?.trim();

            if (potentialName) {
                object.name = potentialName.replace(/\s+/g, ' ').trim();
                nameFound = true;
                consola.debug(`[${currentChapter}] Found Name (bold): "${object.name}"`);
                continue; // Move to next row once name is found this way
            }
            // Fallback: If no bold tag, check if the first TD's text looks like a name
            // This is less reliable, might need adjustment
            potentialName = nameCell.textContent?.trim();
            // Heuristic: Check if it's likely a name (not starting with '•' or long text)
            if (potentialName && !potentialName.startsWith('•') && potentialName.length < 80) {
                 object.name = potentialName.replace(/\s+/g, ' ').trim();
                 nameFound = true;
                 consola.debug(`[${currentChapter}] Found Name (fallback TD text): "${object.name}"`);
                 continue; // Move to next row
            }
        }

        // --- Attempt to find Description ---
        // Look for a TD cell that doesn't contain the Type/Obtained info
        if (cells.length > 0) {
            const potentialDescCell = cells[0]; // Often the only TD in description rows
            const cellText = potentialDescCell.textContent?.trim() || "";

            // Check if it's NOT the Type/Obtained row and IS NOT empty
            if (!cellText.startsWith('• Type:') && !cellText.startsWith('• Obtained:') && cellText.length > 0) {
                // Use innerHTML to capture links etc. correctly
                const descDom = new JSDOM(`<div>${potentialDescCell.innerHTML}</div>`);
                let currentDescText = descDom.window.document.body.textContent || "";
                currentDescText = currentDescText.replace(/\[edit\]$/i, '').replace(/\s+/g, ' ').trim();

                if (currentDescText) {
                    // Append if description is split across multiple valid rows (unlikely but possible)
                    // More likely, the *last* row matching this condition is the main description.
                    descriptionText = currentDescText; // Overwrite with the latest potential description found
                    consola.debug(`[${currentChapter}] Found Potential Description Text: "${descriptionText}"`);
                }
            } else if (cellText.startsWith('• Type:') || cellText.startsWith('• Obtained:')) {
                 consola.debug(`[${currentChapter}] Skipping Type/Obtained row for "${object.name || 'Unknown'}"`);
            }
        }
    } // End row loop

    // Assign the final found description text
    if (descriptionText) {
        object.description1 = descriptionText;
        consola.debug(`[${currentChapter}] Final Description for "${object.name || 'Unknown'}": "${object.description1}"`);
    } else if (nameFound) {
        // Only warn if name was found but description wasn't
        consola.warn(`[${currentChapter}] Could not find description row for "${object.name}".`);
        object.description1 = undefined;
    }

    // Final check: If no name was extracted after checking all rows, consider it a failure
    if (!object.name) {
        consola.warn(`[${currentChapter}] Failed to extract a name from evidence table after scanning rows. Skipping.`);
        return { currentChapter: currentChapter, name: "" };
    }

    // Apply multi-description parsing if needed
    if (object.description1 && typeof object.description1 === 'string' && object.description1.includes("↳")) {
        object = parseDescription(object);
    }

    return object;
}

// --- Description Parsing (Handles multi-part descriptions using "↳") ---
function parseDescription(tableData: ObjectData): ObjectData {
    let description = tableData.description1 || "";
    // Create a copy to avoid modifying the original object directly during iteration if needed later
    const newData: ObjectData = { ...tableData, description1: undefined }; // Clear original combined description
    let descriptions = description.split("↳");

    descriptions.forEach((desc, index) => {
        const key = `description${index + 1}` as keyof ObjectData;
        const trimmedDesc = desc.trim();
        if (trimmedDesc) { // Only add non-empty descriptions
             newData[key] = trimmedDesc;
        }
    });
    return newData;
}

// --- Script Execution ---
main().catch(error => {
    consola.fatal("Unhandled error during script execution:");
    consola.error(error);
    process.exit(1);
});
