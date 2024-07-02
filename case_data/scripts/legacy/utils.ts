import * as path from "path";
import { fileURLToPath } from "url";

// https://stackoverflow.com/a/50053801/5868796
const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const CASE_DATA_ROOT_DIRECTORY = path.resolve(
  path.join(__dirname, "../generated")
);
