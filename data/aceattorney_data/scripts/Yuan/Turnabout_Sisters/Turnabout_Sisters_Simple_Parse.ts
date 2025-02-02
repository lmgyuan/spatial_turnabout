import * as path from "path";
import consola from "consola";
import { readdir, readFile, writeFile, mkdir } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";

const CASE_DATA_ROOT_DIRECTORY = "../../../../../case_data/generated/raw";
const OUTPUT_DIRECTORY = "../../../../../case_data/generated/parsed_simple";

async function main() {
    // Get all Turnabout Sisters HTML files
    let htmlFilePaths;
    try {
        const files = await readdir(CASE_DATA_ROOT_DIRECTORY);
        htmlFilePaths = files
            .filter(file => file.startsWith("Turnabout_Sisters") && file.endsWith(".html"))
            .map(file => path.join(CASE_DATA_ROOT_DIRECTORY, file));
    } catch (e) {
        consola.fatal("Could not read the directory or filter HTML files.");
        consola.error(e);
        return;
    }

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
            const parsedContent = parseContent(contentWrapper);

            // Create output directory if it doesn't exist
            if (!existsSync(OUTPUT_DIRECTORY)) {
                await mkdir(OUTPUT_DIRECTORY, { recursive: true });
            }

            // Write to JSON file
            await writeFile(
                path.join(OUTPUT_DIRECTORY, `1-2-${i+1}_Turnabout_Sisters_Simple.json`),
                JSON.stringify({
                    part: i + 1,
                    content: parsedContent
                }, null, 2)
            );

            consola.success(`Successfully processed file ${i + 1}`);
        } catch (e) {
            consola.error(`Error processing file ${filePath}`);
            consola.error(e);
        }
    }
}

function parseContent(contentWrapper: Element): string[] {
    const textContent: string[] = [];
    
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
            textContent.push(text);
        }
    }

    return textContent;
}

main().catch(console.error); 