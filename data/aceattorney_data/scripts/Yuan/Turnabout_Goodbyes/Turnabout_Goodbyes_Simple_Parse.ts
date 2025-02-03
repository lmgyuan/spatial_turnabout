import * as path from "path";
import { fileURLToPath } from 'url';
import consola from "consola";
import { dirname } from 'path';
import { readdir, readFile, writeFile, mkdir } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";

function getProjectPaths() {
    // Get the current script's directory
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);
    
    // Get the project root directory by going up the directory tree
    const projectRoot = path.resolve(__dirname, '../../../../../');
    
    // Create absolute paths for data and output directories
    const dataDir = path.join(projectRoot, "case_data/generated");
    const outputDir = path.join(projectRoot, "case_data/generated/parsed_simple");
    
    // Log the paths for debugging
    consola.info('Project root:', projectRoot);
    consola.info('Data directory:', dataDir);
    consola.info('Output directory:', outputDir);
    
    return { dataDir, outputDir };
}

// Get absolute paths
const { dataDir: CASE_DATA_ROOT_DIRECTORY, outputDir: OUTPUT_DIRECTORY } = getProjectPaths();

consola.info("Starting to parse Turnabout Goodbyes");

async function main() {
    // Get all Turnabout Goodbyes HTML files
    let htmlFilePaths;
    try {
        const rawDir = path.join(CASE_DATA_ROOT_DIRECTORY, "raw");
        const files = await readdir(rawDir);
        htmlFilePaths = files
            .filter(file => file.startsWith("Turnabout_Goodbyes") && file.endsWith(".html"))
            .map(file => path.join(rawDir, file));
    } catch (e) {
        consola.fatal("Could not read the directory or filter HTML files.");
        consola.error(e);
        return;
    }

    // Initialize accumulated content
    let accumulatedContent = "";

    // Process each file
    for (let i = 0; i < htmlFilePaths.length; i++) {
        const filePath = htmlFilePaths[i];
        consola.info(`Processing file ${i + 1}/${htmlFilePaths.length}`);

        try {
            // Read and parse HTML
            const rawHtml = await readFile(filePath, "utf-8");
            const dom = new JSDOM(rawHtml);
            const document = dom.window.document;

            // Get main content wrapper
            const contentWrapper = document.querySelector(".mw-parser-output");
            if (!contentWrapper) {
                consola.warn(`No content wrapper found in file ${i + 1}`);
                continue;
            }

            // Extract text content
            const currentContent = parseContent(contentWrapper);
            
            // Append new content to accumulated content
            accumulatedContent += (accumulatedContent ? "\n\n" : "") + currentContent;

            // Create output directory if it doesn't exist
            if (!existsSync(OUTPUT_DIRECTORY)) {
                await mkdir(OUTPUT_DIRECTORY, { recursive: true });
            }

            // Write to JSON file with accumulated content
            await writeFile(
                path.join(OUTPUT_DIRECTORY, `1-4-${i+1}_Turnabout_Goodbyes_Simple.json`),
                JSON.stringify({
                    part: i + 1,
                    content: accumulatedContent
                }, null, 2)
            );

            consola.success(`Successfully processed file ${i + 1}`);
        } catch (e) {
            consola.error(`Error processing file ${filePath}`);
            consola.error(e);
        }
    }
}

function parseContent(contentWrapper: Element): string {
    const textParts: string[] = [];
    
    // Process each child element
    for (const child of Array.from(contentWrapper.children)) {
        // Skip navigation elements and other non-content elements
        if (child.classList.contains('toc') || 
            child.tagName === 'TABLE' || 
            child.id === 'toc') {
            continue;
        }

        // Get text content and clean it
        const text = child.textContent?.trim();
        if (text && text.length > 0) {
            textParts.push(text);
        }
    }

    // Join all text parts with newlines
    return textParts.join("\n");
}

main().catch(console.error); 