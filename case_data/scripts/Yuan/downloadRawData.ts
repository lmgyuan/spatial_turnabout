import { consola } from "consola";
import { existsSync } from "fs";
import { mkdir, writeFile } from "fs/promises";
import * as path from "path";
import fetch from "node-fetch";
// @ts-ignore
import { CASE_DATA_ROOT_DIRECTORY } from "../legacy/utils.ts";

// Follow-up: Download transcripts linked from category page:
// https://aceattorney.fandom.com/wiki/Category:Transcripts
const FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGES = [
    "https://aceattorney.fandom.com/wiki/The_First_Turnabout_-_Transcript",
    "https://aceattorney.fandom.com/wiki/Turnabout_Sisters_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/Turnabout_Sisters_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/Turnabout_Sisters_-_Transcript_-_Part_3",
    "https://aceattorney.fandom.com/wiki/Turnabout_Sisters_-_Transcript_-_Part_4",
    "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_3",
    "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_4",
    "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_5",
    "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_6",
    "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_3",
    "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_4",
    "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_5",
    "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_6",
    "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_Phoenix_Wright:_Ace_Attorney",
    "https://strategywiki.org/wiki/Phoenix_Wright:_Ace_Attorney/Episode_1:_The_First_Turnabout",
    "https://strategywiki.org/wiki/Phoenix_Wright:_Ace_Attorney/Episode_2:_Turnabout_Sisters",
    "https://strategywiki.org/wiki/Phoenix_Wright:_Ace_Attorney/Episode_3:_Turnabout_Samurai",
    "https://strategywiki.org/wiki/Phoenix_Wright:_Ace_Attorney/Episode_4:_Turnabout_Goodbyes"
];


const CASE_OBJECT_RAW_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "objects_raw");
const CASE_DATA_RAW_DIRECTORY = path.join(CASE_DATA_ROOT_DIRECTORY, "raw");

async function main() {
  consola.start("Downloading raw transcript data to case_data/generated/raw");

  if (!existsSync(CASE_DATA_RAW_DIRECTORY)) {
    await mkdir(CASE_DATA_RAW_DIRECTORY, { recursive: true });
  }

    if (!existsSync(CASE_OBJECT_RAW_DIRECTORY)) {
        await mkdir(CASE_OBJECT_RAW_DIRECTORY, { recursive: true });
    }

  consola.log("Downloading First Turnabout...");
  try {
    for (let i = 0; i < FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGES.length; i++) {
      const PAGE = FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGES[i];
      const categoryResult = await fetch(PAGE);
      const categoryText = await categoryResult.text();
      let pageName = PAGE.split("/").pop().replace(":", "");
      if (pageName.startsWith("Episode")) {
          pageName = "List_of_People_in_" + pageName;
      }
      if (pageName.startsWith("List_of_Evidence")) {
        await writeFile(
            path.join(CASE_OBJECT_RAW_DIRECTORY, pageName + ".html"),
            categoryText
        );
      } else {
        await writeFile(
            path.join(CASE_DATA_RAW_DIRECTORY, pageName + ".html"),
            categoryText
        );
      }
    }
  } catch (e) {
    consola.fatal("Failed to download category page", e);
    return;
  }

  consola.success("Downloaded 1-1.hml");
}

main();
