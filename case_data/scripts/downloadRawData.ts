import { consola } from "consola";
import { existsSync } from "fs";
import { mkdir, writeFile } from "fs/promises";
import * as path from "path";
import { fileURLToPath } from "url";
import fetch from "node-fetch";

// Follow-up: Download transcripts linked from category page:
// https://aceattorney.fandom.com/wiki/Category:Transcripts
const FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGE =
  "https://aceattorney.fandom.com/wiki/The_First_Turnabout_-_Transcript";

// https://stackoverflow.com/a/50053801/5868796
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CASE_DATA_ROOT_DIRECTORY = path.resolve(
  path.join(__dirname, "../generated")
);
const CASE_DATA_RAW_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "raw");

async function main() {
  consola.start("Downloading raw transcript data to case_data/generated/raw");

  if (!existsSync(CASE_DATA_RAW_DIRECTORY)) {
    await mkdir(CASE_DATA_RAW_DIRECTORY);
  }

  consola.log("Downloading First Turnabout...");
  try {
    const categoryResult = await fetch(FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGE);
    const categoryText = await categoryResult.text();
    await writeFile(
      path.join(CASE_DATA_RAW_DIRECTORY, "1-1.html"),
      categoryText
    );
  } catch (e) {
    consola.fatal("Failed to download category page", e);
    return;
  }

  consola.success("Downloaded 1-1.hml");
}

void main();
