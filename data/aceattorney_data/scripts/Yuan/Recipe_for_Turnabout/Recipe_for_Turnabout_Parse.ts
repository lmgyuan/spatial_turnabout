import * as path from "path";
import consola from "consola";
import { mkdir, readdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";
import { parseContent } from "../utils/index.ts";

// Load evidence and character data
let FULL_EVIDENCES = JSON.parse(await readFile(
	"./data/aceattorney_data/generated/objects_parsed/" +
	"List_of_Evidence_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json", "utf-8"));
let CURR_CHAPTER_EVIDENCES;
FULL_EVIDENCES.forEach((e) => {
	if (e.chapter == "Recipe for Turnabout") {
		CURR_CHAPTER_EVIDENCES = e.evidences;
	}
});

let FULL_CHARACTERS = JSON.parse(await readFile(
	"./data/aceattorney_data/generated/characters_parsed/" +
	"List_of_Profiles_in_Phoenix_Wright_Ace_Attorney_-_Trials_and_Tribulations.json", "utf-8"));
let CURR_CHAPTER_CHARACTERS;
FULL_CHARACTERS.forEach((e) => {
	if (e.chapter == "Recipe for Turnabout") {
		CURR_CHAPTER_CHARACTERS = e.characters;
	}
});

const CASE_DATA_ROOT_DIRECTORY = "./data/aceattorney_data/generated";
let HTML_FILE_PATHS = [];
try {
	const files = await readdir(path.join(CASE_DATA_ROOT_DIRECTORY, "raw"));
	HTML_FILE_PATHS = files
			.filter(file => file.startsWith("Recipe_for_Turnabout") && file.endsWith(".html"))
			.map(file => path.join(CASE_DATA_ROOT_DIRECTORY, "raw", file));
} catch (e) {
	consola.fatal("Could not read the directory or filter HTML files.");
	consola.log(e);
}

const OUTPUT_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "parsed_full_context");

async function main() {
	consola.start("Parsing HTML file");

	let accumulatedPreviousContext = "";

	for (let i = 0; i < HTML_FILE_PATHS.length; i++) {
		let rawHtml: string;
		const HTML_FILE_PATH = HTML_FILE_PATHS[i];
		try {
			rawHtml = await readFile(HTML_FILE_PATH, "utf-8");
			consola.log("Raw HTML content read successfully.");
		} catch (e) {
			consola.fatal(`Could not read file at ${HTML_FILE_PATH}`);
			consola.log(e);
			return;
		}

		let dom: JSDOM;
		try {
			dom = new JSDOM(rawHtml);
			console.log("JSDOM instance created successfully.");
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

		consola.log("Writing parsed data to JSON file");
		if (!existsSync(OUTPUT_DIRECTORY)) {
			await mkdir(OUTPUT_DIRECTORY);
		}

		await writeFile(
				path.join(OUTPUT_DIRECTORY, `3-3-${i + 1}_Recipe_for_Turnabout.json`),
				JSON.stringify(parsedData, null, 2)
		);
	}
}

function parseHtmlContent(contentWrapper: Element, document: Document, evidence_objects) {
	const data = [];
	let childIndex = 0;
	let newContext = "";

	while (childIndex < contentWrapper.children.length) {
		const child = contentWrapper.children[childIndex];

		newContext += parseContent(child);

		if (child.tagName === "CENTER" &&
				child.querySelector("span[style*='color:red']") &&
				child.textContent?.trim() === "Cross Examination") {
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
	const testimonies = [];
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
			const name = child.textContent.split('\n')[0].replace(":", "").trim();
			const comment = child.textContent.split('\n')[1].trim();
			const presentEvidence = getPresentEvidence(contentWrapper, childIndex, document, secondBarIndex);
			testimonies.push({ testimony: comment, person: name, present: presentEvidence });
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
	let evidence = [];
	index++;
	let child = contentWrapper.children[index] as HTMLElement;

	while (child.tagName === "TABLE") {
		child = contentWrapper.children[index] as HTMLElement;
		const boxText = child.textContent.trim();
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
