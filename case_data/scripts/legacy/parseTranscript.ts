// import * as path from "path";
// import { CASE_DATA_ROOT_DIRECTORY } from "./utils.js";
// import consola from "consola";
// import { mkdir, readFile, writeFile } from "fs/promises";
// import { JSDOM } from "jsdom";
// import { existsSync } from "fs";
//
// const FIRST_TURNABOUT_RAW_FILE = path.join(
//   CASE_DATA_ROOT_DIRECTORY,
//   "raw/1-1.html"
// );
//
// const CASE_DATA_PARSED_DIRECTORY = path.join(
//   CASE_DATA_ROOT_DIRECTORY,
//   "parsed"
// );
//
// let document: Document = null;
//
// async function main() {
//   consola.start("Parsing transcript for 1-1");
//
//   let rawTranscript: string;
//   try {
//     rawTranscript = await readFile(FIRST_TURNABOUT_RAW_FILE, "utf-8");
//   } catch (e) {
//     consola.fatal("Could not read from case_data/generated/raw/1-1.html");
//     consola.log(e);
//     return;
//   }
//
//   let dom: JSDOM;
//   try {
//     dom = new JSDOM(rawTranscript);
//   } catch (e) {
//     consola.fatal("Malformed HTML in case_data/generated/raw/1-1.html");
//     consola.log(e);
//     return;
//   }
//
//   document = dom.window.document;
//
//   // const contentWrapper = $('.mw-parser-output');
//   const contentWrapper = document.querySelector(".mw-parser-output");
//   if (contentWrapper == null) {
//     consola.fatal("Could not find trascript wrapper element in 1-1.html");
//     return;
//   }
//
//   const caseData = parseRawHtmlCaseTranscript(contentWrapper);
//   consola.log("Writing 1-1.json");
//   if (!existsSync(CASE_DATA_PARSED_DIRECTORY)) {
//     await mkdir(CASE_DATA_PARSED_DIRECTORY);
//   }
//   await writeFile(
//     path.join(CASE_DATA_PARSED_DIRECTORY, "1-1.json"),
//     JSON.stringify(caseData, null, 2)
//   );
//
//   consola.success("Parsed First Turnabout to 1-1.json");
// }
//
// function parseRawHtmlCaseTranscript(contentWrapper: Element) {
//   const caseData = [];
//
//   let contextBufferLines: string[] = [];
//
//   // Skip the first two children since they are the nav tabs and the image
//   let childIndex = 2;
//   while (childIndex < contentWrapper.children.length) {
//     const child = contentWrapper.children[childIndex];
//
//     // CASE 1: MULTIPLE CHOICE QUESTION
//     if (child.tagName === "TABLE") {
//       // If we see a table, then we're at a decision point. The last line
//       // of context is the question.
//       const context = contextBufferLines.join("\n").trim();
//
//       // Find all the choices for this question (they're all table children)
//       const choicesTables = [child];
//       childIndex += 1;
//       for (; childIndex < contentWrapper.children.length; ++childIndex) {
//         if (contentWrapper.children[childIndex].tagName !== "TABLE") {
//           break;
//         }
//         choicesTables.push(contentWrapper.children[childIndex]);
//       }
//
//       const choices = choicesTables.map((choiceTable) => {
//         const choiceTableRows = choiceTable.querySelectorAll("tr");
//         if (choiceTableRows.length !== 2) {
//           throw new Error(
//             `Unexpected choice table format, got an action table with ${choiceTableRows.length} rows`
//           );
//         }
//         const choice = getTextContentFromElement(choiceTableRows[0]);
//         const { isCorrect, responseText } = getResponseText(choiceTableRows[1]);
//         return {
//           choice,
//           is_correct: isCorrect ? 1 : 0,
//           response: responseText,
//         };
//       });
//
//       caseData.push({
//         context,
//         category: "multiple_choice",
//         choices,
//       });
//
//       ++childIndex;
//       contextBufferLines = [];
//     }
//     // CASE 2: CROSS EXAMINATION
//     else if (
//       child.tagName === "CENTER" &&
//       child.textContent.trim() === "Cross Examination"
//     ) {
//       consola.debug("Encountered cross examination");
//       const context = contextBufferLines.join("\n").trim();
//
//       const testimonies = [];
//       let testimonyLineBuffer = [];
//       ++childIndex;
//       while (childIndex < contentWrapper.children.length) {
//         const testimonyChild = contentWrapper.children[childIndex];
//         if (testimonyChild.tagName === "HR") {
//           // The testimony ends when we reach a <hr />
//           break;
//         } else if (testimonyChild.tagName === "TABLE") {
//           // Table indicates we've reached the end of one part of testimony.
//           const testimony = testimonyLineBuffer.join("\n").trim();
//           testimonyLineBuffer = [];
//
//           // First gather all possible actions
//           const actionTables = [testimonyChild];
//           ++childIndex;
//           for (; childIndex < contentWrapper.children.length; ++childIndex) {
//             if (contentWrapper.children[childIndex].tagName !== "TABLE") {
//               break;
//             }
//             actionTables.push(contentWrapper.children[childIndex]);
//           }
//           // For each action, gather metadata
//           const parsedActionTables = actionTables.map((actionTable) => {
//             const rows = Array.from(actionTable.querySelectorAll("tr"));
//             const actionRow = rows.shift();
//             const action = getTextContentFromElement(actionRow)
//               .toLowerCase()
//               .replace(/^present /, "");
//             const { isCorrect, actionText } = getActionText(rows);
//             return {
//               action,
//               isCorrect,
//               actionText,
//             };
//           });
//
//           const press = parsedActionTables.find((t) => t.action === "press");
//           const testimonyMetadata = {
//             testimony,
//             critical_press: press.isCorrect, // TODO: Check that this is correct
//             press_response: press.actionText,
//           };
//
//           const presentActions = parsedActionTables.filter(
//             (t) => t.action !== "press"
//           );
//           const correctPressAction = presentActions.filter((a) => a.isCorrect);
//           if (correctPressAction.length !== 0) {
//             // TODO: Handle alternative dialogue when presenting incorrect evidence
//             testimonyMetadata["correct_present"] = correctPressAction.map(
//               (a) => a.action
//             );
//             testimonyMetadata["present_response"] = "Objection!"; // TODO: Can we glean the correct present response?
//           }
//           testimonies.push(testimonyMetadata);
//         } else {
//           // Default case: Text is part of the testimony
//           const line = getTextContentFromElement(testimonyChild);
//           if (line !== "-- Witness's Account --") {
//             testimonyLineBuffer.push(line);
//           }
//           ++childIndex;
//         }
//       }
//       consola.debug("Finishing parsing cross examination");
//
//       caseData.push({
//         context,
//         category: "cross_examination",
//         testimonies,
//       });
//     }
//     // DEFAULT CASE: Grab the text and append to the temporary "context"
//     // buffer
//     else {
//       contextBufferLines.push(getTextContentFromElement(child));
//       ++childIndex;
//     }
//   }
//
//   const finalCaseData = {};
//   caseData.forEach((caseStep, i) => (finalCaseData[i.toString()] = caseStep));
//   return finalCaseData;
// }
//
// function getTextContentFromElement(el: Element): string {
//   // First replace all <br /> with "\n"
//   el.querySelectorAll("br").forEach((lineBreakEl) => {
//     const newLineEl = document.createElement("span");
//     newLineEl.textContent = "\n";
//     lineBreakEl.replaceWith(newLineEl);
//   });
//   return el.textContent.trim();
// }
//
// function getResponseText(el: Element): {
//   isCorrect: boolean;
//   responseText: string;
// } {
//   const isCorrect = Array.from(el.querySelectorAll("i")).some((iEl) =>
//     iEl.textContent.includes("Leads to")
//   );
//   let responseText = getTextContentFromElement(el);
//   if (isCorrect) {
//     // Remove everything after "Leads to:" since they'll be part of the next
//     // segment's context.
//     responseText = responseText.replaceAll(/Leads (back )?to[\s\S]*\n/gm, "");
//   } else {
//     // Remove the "Leads back to:", but retain the next lines since they
//     // have leading questions from the judge/prosecutor.
//     // (`.` does not match newlines.)
//     responseText = responseText.replaceAll(/Leads (back )?to.*\n/gm, "");
//   }
//   return { isCorrect, responseText };
// }
//
// function getActionText(els: Element[]): {
//   isCorrect: boolean;
//   actionText: string;
// } {
//   const isCorrect = els.some((row) =>
//     Array.from(row.querySelectorAll("i")).some((iEl) =>
//       iEl.textContent.includes("Leads to")
//     )
//   );
//   let actionText = els
//     .map((el) => getTextContentFromElement(el))
//     .join("\n")
//     .trim();
//
//   // TODO: Find GIFs and replace with text (like "Hold it!")
//   if (isCorrect) {
//     // Remove everything after "Leads to:" since they'll be part of the next
//     // segment's context.
//     actionText = actionText.replaceAll(/Leads (back )?to[\s\S]*\n/gm, "");
//   } else {
//     // Remove the "Leads back to:", but retain the next lines since they
//     // have leading questions from the judge/prosecutor.
//     // (`.` does not match newlines.)
//     actionText = actionText.replaceAll(/Leads (back )?to.*\n/gm, "");
//   }
//   return { isCorrect, actionText };
// }
//
// main();
