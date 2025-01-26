import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

// Create __dirname manually for ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const finalDir = path.join(__dirname, '../final');
const fullContextDir = path.join(__dirname, '../full_context');
const outputDir = path.join(__dirname, '../final_full_context');

// Ensure the output directory exists
if (!fs.existsSync(outputDir)) {
	fs.mkdirSync(outputDir);
}

// Function to process each JSON file containing an array of JSON objects
const processFile = (fileName: string) => {
	const finalFilePath = path.join(finalDir, fileName);
	const fullContextFilePath = path.join(fullContextDir, fileName);
	const outputFilePath = path.join(outputDir, fileName);

	try {
		if (fs.existsSync(finalFilePath) && fs.existsSync(fullContextFilePath)) {
			// Log the file being processed
			console.log(`Processing file: ${fileName}`);

			// Read both final and full_context JSON files
			const finalData = JSON.parse(fs.readFileSync(finalFilePath, 'utf-8'));
			const fullContextData = JSON.parse(fs.readFileSync(fullContextFilePath, 'utf-8'));

			// Both finalData and fullContextData are expected to be arrays of objects
			if (Array.isArray(finalData) && Array.isArray(fullContextData)) {
				// Loop through each item in the finalData array and replace the context
				finalData.forEach((item, index) => {
					if (fullContextData[index]) {
						item.context = fullContextData[index].context;
						item.newContext = fullContextData[index].newContext;
					}
				});

				// Write the updated array to the output directory
				fs.writeFileSync(outputFilePath, JSON.stringify(finalData, null, 2), 'utf-8');
				console.log(`Processed and updated: ${fileName}`);
			} else {
				console.log(`File data is not an array in: ${fileName}`);
			}
		} else {
			console.log(`File missing in one of the directories: ${fileName}`);
		}
	} catch (error) {
		console.error(`Error processing file ${fileName}: ${error.message}`);
	}
};

// Read all files in the final directory
const files = fs.readdirSync(finalDir);

// Process each file
files.forEach(file => {
	if (file.endsWith('.json')) {
		processFile(file);
	}
});

console.log('All files processed successfully.');
