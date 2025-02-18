import * as path from "path";
import consola from "consola";
import { mkdir, readdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";
import { parseContent } from "./utils/index.ts";

const CASE_DATA_ROOT_DIRECTORY = "./data/aceattorney_data/generated";
const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed_full_context");

// Define case information with their details
const CASES = [
    {
        name: "The_Stolen_Turnabout",
        chapterName: "The Stolen Turnabout",
        casePrefix: "3-2",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json"
    },
    {
        name: "Bridge_to_the_Turnabout",
        chapterName: "Bridge to the Turnabout",
        casePrefix: "3-5",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json"
    },
    {
        name: "Farewell,_My_Turnabout",
        chapterName: "Farewell, My Turnabout",
        casePrefix: "2-4",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json"
    },
    {
        name: "The_First_Turnabout",
        chapterName: "The First Turnabout",
        casePrefix: "1-1",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney.json"
    },
    {
        name: "Recipe_for_Turnabout",
        chapterName: "Recipe for Turnabout",
        casePrefix: "3-3",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json"
    },
    {
        name: "Reunion,_and_Turnabout",
        chapterName: "Reunion, and Turnabout",
        casePrefix: "2-2",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json"
    },
    {
        name: "The_Lost_Turnabout",
        chapterName: "The Lost Turnabout",
        casePrefix: "2-1",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json"
    },
    {
        name: "Turnabout_Beginnings",
        chapterName: "Turnabout Beginnings",
        casePrefix: "3-4",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json"
    },
    {
        name: "Turnabout_Big_Top",
        chapterName: "Turnabout Big Top",
        casePrefix: "2-3",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json"
    },
    {
        name: "Turnabout_Corner",
        chapterName: "Turnabout Corner",
        casePrefix: "4-2",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Apollo_Justice_Ace_Attorney.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Apollo_Justice_Ace_Attorney.json"
    },
    {
        name: "Turnabout_Goodbyes",
        chapterName: "Turnabout Goodbyes",
        casePrefix: "1-4",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Justice_for_All.json"
    },
    {
        name: "Turnabout_Memories",
        chapterName: "Turnabout Memories",
        casePrefix: "3-1",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json"
    },
    {
        name: "Turnabout_Samurai",
        chapterName: "Turnabout Samurai",
        casePrefix: "1-3",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Apollo_Justice_Ace_Attorney.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Apollo_Justice_Ace_Attorney.json"
    },
    {
        name: "Turnabout_Serenade",
        chapterName: "Turnabout Serenade",
        casePrefix: "4-4",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Apollo_Justice_Ace_Attorney.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Apollo_Justice_Ace_Attorney.json"
    },
    {
        name: "Turnabout_Sisters",
        chapterName: "Turnabout Sisters",
        casePrefix: "1-2",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney.json"
    },
    {
        name: "Turnabout_Succession",
        chapterName: "Turnabout Succession",
        casePrefix: "4-3",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Apollo_Justice_Ace_Attorney.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Apollo_Justice_Ace_Attorney.json"
    },
    {
        name: "Turnabout_Trump",
        chapterName: "Turnabout Trump",
        casePrefix: "4-1",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Apollo_Justice_Ace_Attorney.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Apollo_Justice_Ace_Attorney.json"
    },
    {
        name: "Turnabout_Countdown",
        chapterName: "Turnabout Countdown",
        casePrefix: "5-1",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json"
    },
    {
        name: "The_Monstrous_Turnabout",
        chapterName: "The Monstrous Turnabout",
        casePrefix: "5-2",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json"
    },
    {
        name: "Turnabout_Academy",
        chapterName: "Turnabout Academy",
        casePrefix: "5-3",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json"
    },
    {
        name: "The_Cosmic_Turnabout",
        chapterName: "The Cosmic Turnabout",
        casePrefix: "5-4",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json"
    },
    {
        name: "Turnabout_for_Tomorrow",
        chapterName: "Turnabout for Tomorrow",
        casePrefix: "5-5",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json"
    },
    {
        name: "Turnabout_Reclaimed",
        chapterName: "Turnabout Reclaimed",
        casePrefix: "5-6",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Dual_Destinies.json"
    },
    {
        name: "The_Foreign_Turnabout",
        chapterName: "The Foreign Turnabout",
        casePrefix: "6-1",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json"
    },
    {
        name: "The_Magical_Turnabout",
        chapterName: "The Magical Turnabout",
        casePrefix: "6-2",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json"
    },
    {
        name: "The_Rite_of_Turnabout",
        chapterName: "The Rite of Turnabout",
        casePrefix: "6-3",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json"
    },
    {
        name: "Turnabout_Storyteller",
        chapterName: "Turnabout Storyteller",
        casePrefix: "6-4",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json"
    },
    {
        name: "Turnabout_Revolution",
        chapterName: "Turnabout Revolution",
        casePrefix: "6-5",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json"
    },
    {
        name: "Turnabout_Time_Traveler",
        chapterName: "Turnabout Time Traveler",
        casePrefix: "6-6",
        evidencesPath: "./data/aceattorney_data/generated/objects_parsed/List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json",
        charactersPath: "./data/aceattorney_data/generated/characters_parsed/List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Spirit_of_Justice.json"
    }
];

async function parse(caseName: string, evidencesPath: string, charactersPath: string, chapterName: string, casePrefix: string) {
    // Load evidence data
    let CURR_CHAPTER_EVIDENCES;
    try {
        const FULL_EVIDENCES = JSON.parse(await readFile(evidencesPath, "utf-8"));
        FULL_EVIDENCES.forEach((e) => {
            // consola.log(`Chapter Name: ${chapterName}; e.chapter: ${e.chapter}`)
            if (e.chapter === chapterName) {
                CURR_CHAPTER_EVIDENCES = e.evidences;
            }
        });
    } catch (e) {
        consola.error(`Failed to load evidences for ${caseName}`);
        return;
    }

    // Load character data
    let CURR_CHAPTER_CHARACTERS;
    try {
        const FULL_CHARACTERS = JSON.parse(await readFile(charactersPath, "utf-8"));
        FULL_CHARACTERS.forEach((e) => {
            if (e.chapter === chapterName) {
                CURR_CHAPTER_CHARACTERS = e.characters;
            }
        });
    } catch (e) {
        consola.error(`Failed to load characters for ${caseName}`);
        return;
    }

    // Get HTML files for this case and sort them to ensure sequential processing
    let HTML_FILE_PATHS: string[] = [];
    try {
        const files = await readdir(path.join(CASE_DATA_ROOT_DIRECTORY, "raw"));
        HTML_FILE_PATHS = files
            .filter(file => file.startsWith(caseName) && file.endsWith(".html"))
            .sort((a, b) => {
                // Extract numbers from filenames and sort numerically
                const numA = parseInt(a.match(/\d+/)?.[0] || "0");
                const numB = parseInt(b.match(/\d+/)?.[0] || "0");
                return numA - numB;
            })
            .map(file => path.join(CASE_DATA_ROOT_DIRECTORY, "raw", file));
    } catch (e) {
        consola.error(`Could not read HTML files for ${caseName}`);
        return;
    }

    let accumulatedPreviousContext = "";

    for (let i = 0; i < HTML_FILE_PATHS.length; i++) {
        const HTML_FILE_PATH = HTML_FILE_PATHS[i];
        
        // Read and parse HTML
        let dom: JSDOM;
        try {
            const rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
            dom = new JSDOM(rawHtml);
        } catch (e) {
            consola.error(`Failed to process HTML file ${HTML_FILE_PATH}`);
            continue;
        }

        const document = dom.window.document;
        const contentWrapper = document.querySelector(".mw-parser-output");
        if (!contentWrapper) {
            consola.error(`No content wrapper found in ${HTML_FILE_PATH}`);
            continue;
        }

        const crossExaminations = parseHtmlContent(contentWrapper, document, CURR_CHAPTER_EVIDENCES);

        const processedContext = accumulatedPreviousContext
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .join('\n');

        const parsedData = {
            previousContext: processedContext,
            characters: CURR_CHAPTER_CHARACTERS,
            evidences: CURR_CHAPTER_EVIDENCES,
            turns: crossExaminations
        };

        const newContent = parseContent(contentWrapper)
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .join('\n');
        
        accumulatedPreviousContext += newContent + '\n';

        // Ensure output directory exists
        if (!existsSync(OUTPUT_DIRECTORY)) {
            await mkdir(OUTPUT_DIRECTORY);
        }

        // Write parsed data using both casePrefix and index
        const outputPath = path.join(OUTPUT_DIRECTORY, `${casePrefix}-${i+1}_${caseName}.json`);
        await writeFile(outputPath, JSON.stringify(parsedData, null, 2));
        consola.success(`Processed ${caseName} part ${i+1}`);
    }
}

async function main() {
    consola.start("Starting parsing process for all cases");

    for (const caseInfo of CASES) {
        consola.info(`Processing ${caseInfo.name}`);
        await parse(
            caseInfo.name,
            caseInfo.evidencesPath,
            caseInfo.charactersPath,
            caseInfo.chapterName,
            caseInfo.casePrefix
        );
    }

    consola.success("Completed parsing all cases");
}

// Helper functions from The_Stolen_Turnabout_Parse.ts
function parseHtmlContent(contentWrapper: Element, document: Document, evidence_objects) {
    const data = [];
    let childIndex = 0;
    let newContext = "";

    while (childIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[childIndex];
        newContext += parseContent(child);

        if (child.tagName === "CENTER" && 
            child.querySelector("span[style*='color:red']") && 
            (child.textContent?.trim() === "Cross Examination" || child.textContent?.trim() === "Cross-Examination")) {
            const crossExamination = parseCrossExamination(
                contentWrapper, 
                childIndex, 
                document, 
                newContext,
                evidence_objects
            );
            data.push(crossExamination);
            newContext = "";
        }

        ++childIndex;
    }

    return data;
}

function parseCrossExamination(
    contentWrapper: Element, 
    startIndex: number, 
    document: Document, 
    newContext: string, 
    evidence_objects: any[]
) {
    const testimonies: Array<{testimony: string, person: string, present: string[]}> = [];
    let childIndex = startIndex;
    let secondBarIndex = startIndex;

    while (secondBarIndex < contentWrapper.children.length) {
        const child = contentWrapper.children[secondBarIndex] as HTMLElement;
        if (child.tagName === "HR") {
            ++secondBarIndex;
            break;
        }

        newContext += parseContent(child);
        ++secondBarIndex;
    }

    for (; childIndex < contentWrapper.children.length; ++childIndex) {
        const child = contentWrapper.children[childIndex] as HTMLElement;
        if (child.tagName === "HR") break;

        if (child.tagName === "P" && child.querySelector("span[style*='color:green']")) {
            const text = child.textContent || "";
            const [name = "", comment = ""] = text.split('\n').map(s => s.trim());
            const presentEvidence = getPresentEvidence(contentWrapper, childIndex, document, secondBarIndex);
            testimonies.push({ 
                testimony: comment, 
                person: name.replace(":", ""), 
                present: presentEvidence 
            });
        }
    }

    const hasPresent = testimonies.some(t => t.present && t.present.length > 0);

    return {
        category: "cross_examination",
        new_context: newContext,
        testimonies,
        noPresent: !hasPresent
    };
}

function getPresentEvidence(contentWrapper: Element, index: number, document: Document, secondBarIndex: number) {
    const evidence: string[] = [];
    index++;
    let child = contentWrapper.children[index] as HTMLElement;

    while (child.tagName === "TABLE") {
        child = contentWrapper.children[index] as HTMLElement;
        const boxText = child.textContent?.trim() || "";
        if (boxText.includes("Present ")) {
            const texts = boxText.split("\n");
            for (let i = 0; i < texts.length; i++) {
                if (texts[i].includes("Present ")) {
                    evidence.push(texts[i].replace("Present ", "").trim());
                }
                break;
            }
        }
        index++;
    }
    return evidence;
}

main(); 