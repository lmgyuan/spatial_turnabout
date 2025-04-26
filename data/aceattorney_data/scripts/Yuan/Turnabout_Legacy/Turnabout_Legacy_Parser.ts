import * as path from "path";
import consola from "consola";
import { mkdir, readdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";
import { CASE_DATA_ROOT_DIRECTORY } from "../../legacy/utils.ts";

// --- Configuration ---
const CHAPTER_NAME = "Turnabout Legacy";
const GAME_EVIDENCE_FILE = "List_of_Evidence_in_Ace_Attorney_Investigations_2_Prosecutor%27s_Gambit.json";
const GAME_CHARACTER_FILE = "List_of_Profiles_in_Ace_Attorney_Investigations_2_Prosecutor%27s_Gambit.json";
const HTML_FILENAME_IDENTIFIER = "Turnabout_Legacy"; // Used to filter raw HTML files
const OUTPUT_FILENAME_PREFIX = "10-3"; // Prefix for output JSON files (e.g., 9-2-1, 9-2-2)

// --- Load Evidence Data ---
let CURR_CHAPTER_EVIDENCES = [];
try {
    const evidenceFilePath = path.join(CASE_DATA_ROOT_DIRECTORY, "objects_parsed", GAME_EVIDENCE_FILE);
    const fullEvidenceData = JSON.parse(await readFile(evidenceFilePath, "utf-8"));
    const chapterEvidence = fullEvidenceData.find(e => e.chapter === CHAPTER_NAME);
    if (chapterEvidence) {
        CURR_CHAPTER_EVIDENCES = chapterEvidence.evidences;
        consola.success(`Loaded ${CURR_CHAPTER_EVIDENCES.length} evidences for chapter: ${CHAPTER_NAME}`);
    } else {
        consola.warn(`Could not find evidence for chapter "${CHAPTER_NAME}" in ${GAME_EVIDENCE_FILE}`);
    }
} catch (e) {
    consola.error(`Failed to load or parse evidence file ${GAME_EVIDENCE_FILE}`);
    consola.log(e);
}

// --- Load Character Data ---
let CURR_CHAPTER_CHARACTERS = [];
try {
    const characterFilePath = path.join(CASE_DATA_ROOT_DIRECTORY, "characters_parsed", GAME_CHARACTER_FILE);
    const fullCharacterData = JSON.parse(await readFile(characterFilePath, "utf-8"));
    const chapterCharacters = fullCharacterData.find(e => e.chapter === CHAPTER_NAME);
    if (chapterCharacters) {
        CURR_CHAPTER_CHARACTERS = chapterCharacters.characters;
        consola.success(`Loaded ${CURR_CHAPTER_CHARACTERS.length} characters for chapter: ${CHAPTER_NAME}`);
    } else {
        consola.warn(`Could not find characters for chapter "${CHAPTER_NAME}" in ${GAME_CHARACTER_FILE}`);
    }
} catch (e) {
    consola.error(`Failed to load or parse character file ${GAME_CHARACTER_FILE}`);
    consola.log(e);
}


// --- Get Raw HTML File Paths ---
let HTML_FILE_PATHS = [];
const rawHtmlDir = path.join(CASE_DATA_ROOT_DIRECTORY, "raw");
try {
    const files = await readdir(rawHtmlDir);
    HTML_FILE_PATHS = files
        .filter(file => file.includes(HTML_FILENAME_IDENTIFIER) && file.endsWith(".html"))
        .map(file => path.join(rawHtmlDir, file))
        .sort(); // Sort files to process them in order
    if (HTML_FILE_PATHS.length === 0) {
        consola.warn(`No HTML files found containing "${HTML_FILENAME_IDENTIFIER}" in ${rawHtmlDir}`);
    } else {
        consola.info(`Found ${HTML_FILE_PATHS.length} HTML files for ${CHAPTER_NAME}`);
    }
} catch (e) {
    consola.fatal(`Could not read the directory: ${rawHtmlDir}`);
    consola.log(e);
    process.exit(1); // Exit if we can't read the raw files directory
}

// --- Output Directory ---
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed_full_context");

// --- Main Parsing Function ---
async function main() {
    consola.start(`Parsing ${CHAPTER_NAME} HTML files`);

    let accumulatedPreviousContext = "";

    if (HTML_FILE_PATHS.length === 0) {
        consola.error("No HTML files to process. Exiting.");
        return;
    }

    for (let i = 0; i < HTML_FILE_PATHS.length; i++) {
        const HTML_FILE_PATH = HTML_FILE_PATHS[i];
        const currentFileName = path.basename(HTML_FILE_PATH);
        consola.info(`Processing file ${i + 1}/${HTML_FILE_PATHS.length}: ${currentFileName}`);

        let rawHtml: string;
        try {
            rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
        } catch (e) {
            consola.error(`Could not read file: ${currentFileName}`);
            consola.log(e);
            continue; // Skip to next file
        }

        let dom: JSDOM;
        try {
            dom = new JSDOM(rawHtml);
        } catch (e) {
            consola.error(`Malformed HTML content in: ${currentFileName}`);
            consola.log(e);
            continue; // Skip to next file
        }

        const document = dom.window.document;
        const contentWrapper = document.querySelector(".mw-parser-output");
        if (!contentWrapper) {
            consola.error(`Could not find content wrapper (.mw-parser-output) in: ${currentFileName}`);
            continue; // Skip to next file
        }

        // --- Parse Rebuttals ---
        // Pass current chapter's evidence to the parsing function
        const rebuttals = parseHtmlContent(contentWrapper, document, CURR_CHAPTER_EVIDENCES);
        consola.info(`Found ${rebuttals.length} rebuttal sections.`);

        // --- Prepare Output Data ---
        const parsedData = {
            previousContext: accumulatedPreviousContext,
            characters: CURR_CHAPTER_CHARACTERS,
            evidences: CURR_CHAPTER_EVIDENCES,
            turns: rebuttals
        };

        // --- Accumulate Context ---
        // Use parseContent to get text from the current file for the *next* file's context
        accumulatedPreviousContext += parseContent(contentWrapper) + "\n\n"; // Add separator

        // --- Write Output ---
        consola.log("Writing parsed data to JSON file");
        if (!existsSync(OUTPUT_DIRECTORY)) {
            try {
                await mkdir(OUTPUT_DIRECTORY, { recursive: true });
                consola.success(`Created output directory: ${OUTPUT_DIRECTORY}`);
            } catch (e) {
                 consola.error(`Failed to create output directory: ${OUTPUT_DIRECTORY}`);
                 consola.log(e);
                 continue; // Skip writing if directory creation failed
            }
        }

        const outputFileName = `${OUTPUT_FILENAME_PREFIX}-${i + 1}_${HTML_FILENAME_IDENTIFIER}.json`;
        const outputFilePath = path.join(OUTPUT_DIRECTORY, outputFileName);

        try {
            await writeFile(outputFilePath, JSON.stringify(parsedData, null, 2), "utf-8");
            consola.success(`Written output to: ${outputFilePath}`);
        } catch (e) {
            consola.error(`Failed to write output file: ${outputFilePath}`);
            consola.log(e);
        }
    }

    consola.success(`Finished processing all ${HTML_FILE_PATHS.length} files for ${CHAPTER_NAME}`);
}

// --- HTML Parsing Functions ---
function parseHtmlContent(contentWrapper: Element, document: Document, evidence_objects: any[]): any[] {
    const rebuttals = [];
    let currentContextBlock = ""; // Store text encountered before the next rebuttal

    // Iterate through all children of the content wrapper
    for (let i = 0; i < contentWrapper.children.length; i++) {
        const child = contentWrapper.children[i] as HTMLElement;

        // Look for the <p> tag styled with a background color (rebuttal header)
        // In AAI games, the rebuttal headers seem to be <CENTER> tags with red text
        if (child && child.tagName === "CENTER" && 
           (child.querySelector("span[style*='color:red']") || 
           child.querySelector("span[style*='color:#FF0000']")) &&
           child.textContent &&
           child.textContent.toLocaleLowerCase().trim().includes("rebuttal")) {
            
            // Parse the section following this header as a rebuttal
            const rebuttal = parseRebuttal(
                contentWrapper,
                i, // Current index (header)
                document,
                currentContextBlock, // Pass accumulated context
                evidence_objects
            );
            rebuttals.push(rebuttal);
            currentContextBlock = ""; // Reset context for the next block
        } else if (child && child.textContent) {
            // Accumulate text content if it's not a rebuttal header
            // Skip certain elements that don't contribute to the narrative
            if (child.tagName !== 'NAVBOX' && 
                !child.classList.contains('toc') && 
                child.id !== 'toc') {
                
                const text = child.textContent.trim();
                if (text.length > 0) {
                    currentContextBlock += text + "\n";
                }
            }
        }
    }

    return rebuttals;
}

// Parses a single rebuttal section identified by its header element index
function parseRebuttal(contentWrapper: Element, headerIndex: number, document: Document, contextBeforeSection: string, evidence_objects: any[]) {
    const testimonies = [];
    let currentIndex = headerIndex + 1; // Start looking *after* the header
    let endOfSectionIndex = -1;
    let rebuttalSectionText = ""; // Accumulate text *within* this section, EXCLUDING testimonies/present tables

    // 1. Find the end of the rebuttal section (next H2 or HR)
    let scanIndex = currentIndex;
    while (scanIndex < contentWrapper.children.length) {
        const scanChild = contentWrapper.children[scanIndex];
        if (scanChild.tagName === "H2" || scanChild.tagName === "HR") {
            endOfSectionIndex = scanIndex;
            break;
        }
        scanIndex++;
    }
    if (endOfSectionIndex === -1) {
        endOfSectionIndex = contentWrapper.children.length;
    }
    consola.debug(`Rebuttal section identified: headerIndex=${headerIndex}, endIndex=${endOfSectionIndex}`);

    // 2. Iterate within the identified section
    currentIndex = headerIndex + 1; // Reset current index
    while (currentIndex < endOfSectionIndex) {
        const child = contentWrapper.children[currentIndex] as HTMLElement;
        let isTestimony = false;
        let isPresentTable = false;

        // Check if it's a testimony paragraph
        if (child && child.tagName === "P" && child.querySelector("span[style*='color:green']") && child.textContent) {
            isTestimony = true;
            const textParts = child.textContent.split('\n');
            let name = "";
            let comment = "";
            const nameMatch = textParts[0].match(/^([^:]+):?(.*)/);
            if (nameMatch) {
                name = nameMatch[1].trim();
                comment = (nameMatch[2] ? nameMatch[2].trim() + " " : "") + textParts.slice(1).join(" ").trim();
                comment = comment.trim();
            } else {
                name = "Unknown";
                comment = child.textContent.trim();
                consola.warn(`  Could not find speaker name pattern in testimony at index ${currentIndex}: ${child.textContent.substring(0,100)}`);
            }

            if (name && comment) {
                // Look ahead for the "Present" table(s)
                const presentEvidence = getPresentEvidence(contentWrapper, currentIndex + 1, endOfSectionIndex);
                testimonies.push({ testimony: comment, person: name, present: presentEvidence });
                consola.debug(`  Added testimony by ${name}: "${comment.substring(0, 50)}..."`);
                if (presentEvidence.length > 0) {
                    consola.debug(`    Present evidence found: ${presentEvidence.join(', ')}`);
                }
            } else {
                consola.debug(`  Could not parse testimony structure in paragraph at index ${currentIndex}: ${child.textContent.substring(0,100)}`);
            }
        }

        // Check if it's a "Present" table (even if not directly after a testimony)
        if (child && child.tagName === "TABLE") {
             const titleElement = child.querySelector("th.navbox1title");
             if (titleElement && titleElement.textContent && /Present/i.test(titleElement.textContent)) {
                 isPresentTable = true;
                 consola.debug(`  Skipping 'Present' table at index ${currentIndex} for context accumulation.`);
             }
        }

        // Accumulate text for context ONLY if it's not a testimony or a present table
        // IMPORTANT: Removed "child.tagName !== 'TABLE'" to include normal tables in context
        if (!isTestimony && !isPresentTable &&
            child.textContent &&
            child.tagName !== 'NAVBOX' &&
            !child.classList.contains('toc') &&
            child.tagName !== 'CENTER' && // Skip the header itself if somehow included
            child.tagName !== 'H1' && child.tagName !== 'H2' && child.tagName !== 'H3')
        {
            // Special handling for tables to extract meaningful content
            if (child.tagName === 'TABLE') {
                // Extract text from the table - focus on content cells, not headers
                const tableCells = Array.from(child.querySelectorAll('td'));
                if (tableCells.length > 0) {
                    // Extract text from each cell, skip empty ones
                    const tableTexts = tableCells
                        .map(cell => cell.textContent?.trim().replace(/\s+/g, ' '))
                        .filter(text => text && text.length > 0);
                    
                    if (tableTexts.length > 0) {
                        rebuttalSectionText += tableTexts.join(" ") + "\n";
                        consola.debug(`  Added table text to context (${tableTexts.length} cells)`);
                    }
                }
            } else {
                // Regular element handling (non-table)
                const text = child.textContent.trim().replace(/\s+/g, ' ');
                if (text.length > 0) {
                    rebuttalSectionText += text + "\n";
                }
            }
        }

        currentIndex++;
    } // End while loop for section content

    const hasPresent = testimonies.some(t => t.present && t.present.length > 0);

    // Combine context before the section with the *filtered* text from within the section
    const finalNewContext = (contextBeforeSection.trim() + "\n\n" + rebuttalSectionText.trim()).trim();

    return {
        category: "rebuttal",
        newContext: finalNewContext, // Use the filtered context
        testimonies,
        noPresent: !hasPresent
    };
}

// Get presentable evidence for a testimony
function getPresentEvidence(contentWrapper: Element, startIndex: number, sectionEndIndex: number): string[] {
    let evidence: string[] = [];
    let currentIndex = startIndex; // Start checking from the element after the testimony

    consola.debug(`Starting evidence check at index ${currentIndex} within section bounds ${sectionEndIndex}`);

    // Loop forward from the start index
    while (currentIndex < contentWrapper.children.length && currentIndex < sectionEndIndex) {
        const child = contentWrapper.children[currentIndex] as HTMLElement;

        // Check if this element is a table
        if (child && child.tagName === "TABLE") {
            const titleElement = child.querySelector("th.navbox1title"); // Selector for the title cell
            consola.log("titleElement: ", titleElement?.textContent)
            if (titleElement && titleElement.textContent) {
                const titleText = titleElement.textContent.trim();
                consola.debug(`    Found table with title: "${titleText}"`);

                // Check if it's a "Present" table title
                if (/Present/i.test(titleText)) {
                    let evidenceNames: string[] = [];
                    // Prefer text from links inside the title if they exist
                    const linkElements = titleElement.querySelectorAll("a");
                    if (linkElements.length > 0) {
                        evidenceNames = Array.from(linkElements)
                            .map(link => link.textContent?.trim())
                            .filter((name): name is string => !!name);
                    } else {
                        // Fallback: remove "Present" and split on "or" if present
                        const cleanedTitle = titleText.replace(/Present/i, "").trim();
                        evidenceNames = cleanedTitle.split(/\s+or\s+/i)
                            .map(name => name.trim())
                            .filter(name => name.length > 0);
                    }

                    // Process each evidence name
                    for (const evidenceName of evidenceNames) {
                        const inval_evidence = "Anything Else"
                        const valid_evidence = evidenceName.toLowerCase().trim() != inval_evidence.toLowerCase().trim();

                        if (valid_evidence) {
                            evidence.push(evidenceName);
                            consola.debug(`      Added presentable evidence: "${evidenceName}"`);
                        } else {
                            consola.warn(`    Evidence name not found in evidence list: "${evidenceName}" at index ${currentIndex}`);
                        }
                    }

                    // IMPORTANT: Increment index only if we processed a 'Present' table
                    currentIndex++;
                    continue; // Continue the loop to check the next element
                } else {
                    // If it's a table without the expected title structure, stop looking.
                    consola.warn(`    Table does not have 'Present' in the title.`);
                }
            } else {
                // If the element is not a table, stop looking for evidence for the current testimony.
                consola.debug(`  Found a TABLE but the title is not present: "${child.textContent}" at index ${currentIndex}`);
            }
        } else {
            // If the element is not a table, stop looking for evidence for the current testimony.
            consola.warn(`  Element is not a TABLE. Stopping evidence check at index ${currentIndex}: ${child.tagName}`);
            break;
        }
        currentIndex++;
    } // End while loop

    if (evidence.length > 0) {
        consola.debug(`Finished evidence check. Found: ${evidence.join(', ')}`);
    } else {
        consola.debug(`Finished evidence check. No presentable evidence found starting at index ${startIndex}.`);
    }

    // Return all evidence found consecutively after the testimony
    return evidence;
}

// Extracts plain text content from the main content wrapper, skipping common non-prose elements
function parseContent(contentWrapper: Element): string {
    const textParts: string[] = [];

    for (const child of Array.from(contentWrapper.children)) {
        // Skip elements that are typically navigation, tables, or headers for rebuttals
        if (child.classList.contains('toc') ||
            child.id === 'toc' ||
            child.tagName === 'TABLE' ||
            child.tagName === 'NAVBOX' || // Added NAVBOX skip
            child.tagName === 'CENTER' || // Skip rebuttal headers
            child.tagName === 'H1' || child.tagName === 'H2' || child.tagName === 'H3' // Skip headers
           )
        {
            continue;
        }

        // Get text content, clean it, and add if not empty
        const text = child.textContent?.trim();
        if (text && text.length > 0) {
            // Basic cleaning - replace multiple whitespace chars with single space
            textParts.push(text.replace(/\s+/g, ' '));
        }
    }

    // Join all text parts with newlines for separation
    return textParts.join("\n");
}

// --- Run Main Function ---
main().catch(error => {
    consola.fatal("Unhandled error during script execution:");
    consola.error(error);
    process.exit(1);
});
