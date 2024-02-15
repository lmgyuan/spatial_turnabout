import * as path from "path";
import { CASE_DATA_ROOT_DIRECTORY } from "./utils.js";
import consola from "consola";
import { mkdir, readFile, writeFile } from "fs/promises";
import { JSDOM } from "jsdom";
import { existsSync } from "fs";

const FIRST_TURNABOUT_RAW_FILE = path.join(
  CASE_DATA_ROOT_DIRECTORY,
  "raw/1-1.html"
);

const CASE_DATA_PARSED_DIRECTORY = path.join(
  CASE_DATA_ROOT_DIRECTORY,
  "parsed"
);

async function main() {
  consola.start("Parsing transcript for 1-1");

  let rawTranscript: string;
  try {
    rawTranscript = await readFile(FIRST_TURNABOUT_RAW_FILE, "utf-8");
  } catch (e) {
    consola.fatal("Could not read from case_data/generated/raw/1-1.html");
    consola.log(e);
    return;
  }

  let dom: JSDOM;
  try {
    dom = new JSDOM(rawTranscript);
  } catch (e) {
    consola.fatal("Malformed HTML in case_data/generated/raw/1-1.html");
    consola.log(e);
    return;
  }

  const document = dom.window.document;

  // const contentWrapper = $('.mw-parser-output');
  const contentWrapper = document.querySelector(".mw-parser-output");
  if (contentWrapper == null) {
    consola.fatal("Could not find trascript wrapper element in 1-1.html");
    return;
  }

  const caseData = parseRawHtmlCaseTranscript(contentWrapper);
  consola.log("Writing 1-1.json");
  if (!existsSync(CASE_DATA_PARSED_DIRECTORY)) {
    await mkdir(CASE_DATA_PARSED_DIRECTORY);
  }
  await writeFile(
    path.join(CASE_DATA_PARSED_DIRECTORY, "1-1.json"),
    JSON.stringify(caseData, null, 2)
  );

  consola.success("Parsed First Turnabout to 1-1.json");
}

function parseRawHtmlCaseTranscript(contentWrapper: Element) {
  const caseData = [];

  let contextBufferLines: string[] = [];

  // Skip the first two children since they are the nav tabs and the image
  let childIndex = 2;
  while (childIndex < contentWrapper.children.length) {
    const child = contentWrapper.children[childIndex];

    // Normal case: Grab the text and append to the temporary "context"
    // buffer
    if (child.tagName !== "TABLE") {
      contextBufferLines.push(child.textContent);
      ++childIndex;
      continue;
    }

    // TODO: This script assumes that a transcript contains ONLY MCQs
    // (Can't handle cross-examinations yet.)

    // If we see a table, then we're at a decision point. The last line
    // of context is the question.
    const context = contextBufferLines.map((line) => line.trim()).join("\n");

    // Find all the choices for this question (they're all table children)
    const choicesTables = [child];
    childIndex += 1;
    for (; childIndex < contentWrapper.children.length; ++childIndex) {
      if (contentWrapper.children[childIndex].tagName !== "TABLE") {
        break;
      }
      choicesTables.push(contentWrapper.children[childIndex]);
    }

    const choices = choicesTables.map((choiceTable) => {
      const choiceTableRows = choiceTable.querySelectorAll("tr");
      if (choiceTableRows.length !== 2) {
        throw new Error(
          `Unexpected choice table format, got an action table with ${choiceTableRows.length} rows`
        );
      }
      const choice = choiceTableRows[0].textContent.trim();
      const response = choiceTableRows[1].textContent.trim();
      if (response.includes("Leads to")) {
        return {
          choice,
          is_correct: 1,
          response: "",
        };
      }
      return {
        choice,
        is_correct: 0,
        response,
      };
    });

    caseData.push({
      context,
      type: "multiple_choice",
      choices,
    });

    ++childIndex;
    contextBufferLines = [];
  }

  const finalCaseData = {};
  caseData.forEach((caseStep, i) => (finalCaseData[i.toString()] = caseStep));
  return finalCaseData;
}

main();
