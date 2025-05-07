import { consola } from "consola";
import { existsSync } from "fs";
import { mkdir, writeFile } from "fs/promises";
import * as path from "path";
import fetch from "node-fetch";
import iconv from "iconv-lite";
// @ts-ignore
import { CASE_DATA_ROOT_DIRECTORY } from "../legacy/utils.ts";

// Follow-up: Download transcripts linked from category page:
// https://aceattorney.fandom.com/wiki/Category:Transcripts
const FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGES = [
    // "https://aceattorney.fandom.com/wiki/The_First_Turnabout_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Sisters_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Sisters_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Sisters_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Sisters_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_5",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Samurai_-_Transcript_-_Part_6",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_5",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Goodbyes_-_Transcript_-_Part_6",
    "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_Phoenix_Wright:_Ace_Attorney",
    // "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_Phoenix_Wright:_Ace_Attorney_-_Justice_for_All",
    // "https://strategywiki.org/wiki/Phoenix_Wright:_Ace_Attorney/Episode_1:_The_First_Turnabout",
    // "https://strategywiki.org/wiki/Phoenix_Wright:_Ace_Attorney/Episode_2:_Turnabout_Sisters",
    // "https://strategywiki.org/wiki/Phoenix_Wright:_Ace_Attorney/Episode_3:_Turnabout_Samurai",
    // "https://strategywiki.org/wiki/Phoenix_Wright:_Ace_Attorney/Episode_4:_Turnabout_Goodbyes",
    "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_Phoenix_Wright:_Ace_Attorney",
    // "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_Phoenix_Wright:_Ace_Attorney_-_Justice_for_All",
    // "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_Phoenix_Wright:_Ace_Attorney_-_Trials_and_Tribulations",
    // "https://aceattorney.fandom.com/wiki/The_Lost_Turnabout_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/Reunion,_and_Turnabout_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Reunion,_and_Turnabout_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Reunion,_and_Turnabout_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Reunion,_and_Turnabout_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Big_Top_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Big_Top_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Big_Top_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Big_Top_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Farewell,_My_Turnabout_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Farewell,_My_Turnabout_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Farewell,_My_Turnabout_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Farewell,_My_Turnabout_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Memories_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/The_Stolen_Turnabout_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/The_Stolen_Turnabout_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/The_Stolen_Turnabout_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/The_Stolen_Turnabout_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Recipe_for_Turnabout_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Recipe_for_Turnabout_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Recipe_for_Turnabout_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Recipe_for_Turnabout_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Beginnings_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/Bridge_to_the_Turnabout_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Bridge_to_the_Turnabout_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Bridge_to_the_Turnabout_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Bridge_to_the_Turnabout_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_Phoenix_Wright:_Ace_Attorney_-_Trials_and_Tribulations"
    // "https://aceattorney.fandom.com/wiki/Turnabout_Trump_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_Apollo_Justice:_Ace_Attorney",
    // "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_Apollo_Justice:_Ace_Attorney",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Corner_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Corner_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Corner_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Corner_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Serenade_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Serenade_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Serenade_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Serenade_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/The_Adventure_of_the_Great_Departure_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/The_Adventure_of_the_Unbreakable_Speckled_Band_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/The_Adventure_of_the_Runaway_Room_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/The_Adventure_of_the_Clouded_Kokoro_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/The_Adventure_of_the_Clouded_Kokoro_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/The_Adventure_of_the_Unspeakable_Story_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/The_Adventure_of_the_Unspeakable_Story_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_The_Great_Ace_Attorney:_Adventures",
    // "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_The_Great_Ace_Attorney:_Adventures",
    // "https://aceattorney.huijiwiki.com/wiki/最初的逆转/抄本",
    // "https://aceattorney.fandom.com/wiki/The_Adventure_of_the_Blossoming_Attorney_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/The_Memoirs_of_the_Clouded_Kokoro_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/The_Memoirs_of_the_Clouded_Kokoro_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/The_Memoirs_of_the_Clouded_Kokoro_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/The_Memoirs_of_the_Clouded_Kokoro_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/The_Return_of_the_Great_Departed_Soul_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/The_Return_of_the_Great_Departed_Soul_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/The_Return_of_the_Great_Departed_Soul_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/The_Return_of_the_Great_Departed_Soul_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Twisted_Karma_and_His_Last_Bow_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Twisted_Karma_and_His_Last_Bow_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Twisted_Karma_and_His_Last_Bow_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/The_Resolve_of_Ryunosuke_Naruhodo_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/The_Resolve_of_Ryunosuke_Naruhodo_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/The_Resolve_of_Ryunosuke_Naruhodo_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_The_Great_Ace_Attorney_2:_Resolve",
    // "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_The_Great_Ace_Attorney_2:_Resolve",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_5",
    // "http://www.aya.or.jp/%7Ekidparty/gyakuten/word001.htm",
    // "http://www.aya.or.jp/%7Ekidparty/gyakuten/word002.htm",
    // "http://www.aya.or.jp/%7Ekidparty/gyakuten/word003.htm",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Trump_-_Transcript",
    // "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_Apollo_Justice:_Ace_Attorney",
    // "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_Apollo_Justice:_Ace_Attorney",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Corner_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Corner_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Corner_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Corner_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Serenade_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Serenade_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Serenade_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Serenade_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_1",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_2",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_3",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_4",
    // "https://aceattorney.fandom.com/wiki/Turnabout_Succession_-_Transcript_-_Part_5",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word001.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word002.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word003.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word004.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word005.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word006.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word007.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word008.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word009.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word010.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word011.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word012.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word013.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word014.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word015.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word016.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word017.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word018.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word019.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word020.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word021.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word022.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word023.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word024.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word025.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word026.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word027.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word028.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word029.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word030.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word031.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word032.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word033.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word034.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word035.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word036.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word037.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word038.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word039.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word040.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word041.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word042.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word043.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word044.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word045.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word046.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word113.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word114.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word115.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word116.htm",
    // // "http://www.aya.or.jp/~kidparty/gyakuten/word117.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word118.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word119.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word120.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word121.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word121.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word122.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word123.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word124.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word125.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word126.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word127.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word128.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word129.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word130.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word131.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word132.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word133.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word134.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word135.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word136.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word137.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word138.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word139.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word140.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word141.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word142.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word143.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word144.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word145.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word146.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word147.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word148.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word149.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word150.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word151.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word152.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word153.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word154.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word155.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word156.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word157.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word158.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word159.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word160.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word161.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word162.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word163.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word164.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word165.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word166.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word167.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word168.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word169.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word170.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word171.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word172.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word173.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word174.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word175.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word176.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word177.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word178.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word179.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word180.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word181.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word182.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word183.htm",
    // "http://www.aya.or.jp/~kidparty/gyakuten/word184.htm",
    "https://aceattorney.fandom.com/wiki/Turnabout_Visitor_-_Transcript",
    "https://aceattorney.fandom.com/wiki/Turnabout_Airlines_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/Turnabout_Airlines_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/The_Kidnapped_Turnabout_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/The_Kidnapped_Turnabout_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/Turnabout_Reminiscence_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/Turnabout_Reminiscence_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/Turnabout_Reminiscence_-_Transcript_-_Part_3",
    "https://aceattorney.fandom.com/wiki/Turnabout_Ablaze_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/Turnabout_Ablaze_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/Turnabout_Ablaze_-_Transcript_-_Part_3",
    "https://aceattorney.fandom.com/wiki/Turnabout_Trigger_-_Transcript",
    "https://aceattorney.fandom.com/wiki/The_Captive_Turnabout_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/The_Captive_Turnabout_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/Turnabout_Legacy_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/Turnabout_Legacy_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/A_Turnabout_Forsaken_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/A_Turnabout_Forsaken_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/Turnabout_for_the_Ages_-_Transcript_-_Part_1",
    "https://aceattorney.fandom.com/wiki/Turnabout_for_the_Ages_-_Transcript_-_Part_2",
    "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_Ace_Attorney_Investigations:_Miles_Edgeworth",
    "https://aceattorney.fandom.com/wiki/List_of_Evidence_in_Ace_Attorney_Investigations_2:_Prosecutor%27s_Gambit",
    "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_Ace_Attorney_Investigations:_Miles_Edgeworth",
    "https://aceattorney.fandom.com/wiki/List_of_Profiles_in_Ace_Attorney_Investigations_2:_Prosecutor%27s_Gambit",
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

  try {
    for (let i = 0; i < FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGES.length; i++) {
      consola.log("Downloading " + FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGES[i] + "...");
      const PAGE = FANDOM_FIRST_TURNABOUT_TRANSCRIPT_PAGES[i];
      const isJapanese = PAGE.includes("http://www.aya.or.jp/~kidparty/gyakuten/");

      let pageName = PAGE?.split("/")?.pop()?.replace(":", "");
      if (existsSync(path.join(CASE_DATA_RAW_DIRECTORY, pageName + ".html"))) {
        consola.log("File already exists, skipping...");
        continue;
      }
      
      try {
        consola.log("Fetching " + PAGE + "...");
        const categoryResult = await fetch(PAGE);
        
        if (!categoryResult.ok) {
          throw new Error(`Failed to fetch ${PAGE}: ${categoryResult.statusText}`);
        }

        let categoryText;
        if (isJapanese) {
          const buffer = await categoryResult.arrayBuffer();
          categoryText = iconv.decode(Buffer.from(buffer), 'Shift_JIS');
        } else {
          categoryText = await categoryResult.text();
        }

        if (pageName?.startsWith("Episode")) {
            pageName = "List_of_People_in_" + pageName;
        }
        if (pageName?.startsWith("List_of_Evidence")) {
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
      } catch (fetchError) {
        consola.error("Error fetching page: ", fetchError);
      }
    }
  } catch (e) {
    consola.fatal("Failed to download category page: ", e);
    return;
  }

  consola.success("Downloaded all html files successfully");
}

main();
