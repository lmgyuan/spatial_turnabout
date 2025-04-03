import fs from "fs";

const source_directory = "./data/aceattorney_data/generated/parsed_full_context";
const target_directory = "./data/aceattorney_data/final";

const source_files = fs.readdirSync(source_directory)
    .filter(file => file.endsWith('.json'));

for (const file of source_files) {
    let source_file, target_file, source_data, target_data;
    try {
        source_file = fs.readFileSync(`${source_directory}/${file}`, "utf8");
        target_file = fs.readFileSync(`${target_directory}/${file}`, "utf8");
    } catch (error) {
        console.log(`Error reading file ${file}: ${error}`);
        continue;
    }

    try {
        source_data = JSON.parse(source_file);
        target_data = JSON.parse(target_file);
    } catch (error) {
        console.log(`Error parsing file ${file}: ${error}`);
        continue;
    }
  
    target_data.previousContext = source_data.previousContext;
    var index = 0;
    while (index < target_data.turns.length) {
        target_data.turns[index].new_context = source_data.turns[index].new_context;
        index++;
    }

    fs.writeFileSync(`${target_directory}/${file}`, JSON.stringify(target_data, null, 2));
}

console.log("Done updating previousContext in cases");