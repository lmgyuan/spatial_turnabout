import * as path from "path";
import * as fs from "fs";
import * as fsPromises from "fs/promises";
import consola from "consola";

// Define paths
const FINAL_DIR = path.join(
  process.cwd(),
  "data",
  "aceattorney_data",
  "final"
);

const OUTPUT_PATH = path.join(
  process.cwd(),
  "data",
  "aceattorney_data",
  "spatial",
  "spatial_turns.json"
);

// Types
type Testimony = {
  testimony: string;
  person: string;
  present: string[];
  source?: any;
};

type Turn = {
  category: string;
  newContext: string;
  testimonies: Testimony[];
  noPresent: boolean;
  summarizedContext?: string;
  summarized_context?: string;
  labels?: string[];
  reasoning?: string[];
};

type Case = {
  previousContext: string;
  characters: any[];
  evidences: any[];
  turns: Turn[];
};

type SpatialTurn = {
  case_name: string;
  cross_examination_id: string;
  context: string;
  summarizedContext: string;
  testimonies: Testimony[];
  labels?: string[];
  reasoning?: string[];
  source_file: string;
  characters: any[];
  evidences: any[];
};

async function main() {
  try {
    consola.start("Finding spatial turns from all cases");
    
    // Create output directory if it doesn't exist
    await fsPromises.mkdir(path.dirname(OUTPUT_PATH), { recursive: true });
    
    // Get all JSON files in the final directory
    const files = fs.readdirSync(FINAL_DIR)
      .filter(filename => filename.endsWith('.json'));
    
    consola.info(`Found ${files.length} case files to process`);
    
    const spatialTurns: SpatialTurn[] = [];
    
    // Process each file
    for (const filename of files) {
      const filePath = path.join(FINAL_DIR, filename);
      
      // Extract case name from filename (remove extension and any leading numbers/dashes)
      const caseName = filename.replace(/^\d+-\d+-\d+_/, '').replace('.json', '');
      const chapter_id = filename.split('_')[0];
      
      consola.info(`Processing case: ${caseName}`);
      
      try {
        // Read and parse the case file
        const caseData = JSON.parse(fs.readFileSync(filePath, 'utf8')) as Case;
        
        // Build context progressively
        let cumulativeContext = caseData.previousContext || "";
        
        // Process each turn
        for (let i = 0; i < caseData.turns.length; i++) {
          const turn = caseData.turns[i];
          const cross_examination_id = `${chapter_id}-${i}`;
          
          // Add the current turn's newContext to the cumulative context
          const currentTurnContext = turn.newContext || "";
          const contextForThisTurn = cumulativeContext + (currentTurnContext ? "\n" + currentTurnContext : "");
          
          // Update cumulative context for next turn
          cumulativeContext = contextForThisTurn;
          
          // Check if this turn has the "spatial" label and is presentable
          if (turn.labels && turn.labels.includes("spatial") && turn.noPresent === false) {
            consola.success(`Found spatial turn in ${caseName}`);
            // Ensure summarizedContext is always a string, defaulting to "" if neither field exists
            const summarizedContext = turn.summarizedContext ?? turn.summarized_context ?? "";
            
            // Create spatial turn object, including characters and evidences
            const spatialTurn: SpatialTurn = {
              case_name: caseName,
              cross_examination_id: cross_examination_id,
              characters: caseData.characters || [],
              evidences: caseData.evidences || [],
              context: contextForThisTurn,
              summarizedContext: summarizedContext, // Assign the guaranteed string value
              testimonies: turn.testimonies,
              labels: turn.labels,
              reasoning: turn.reasoning,
              source_file: filename,
            };
            
            spatialTurns.push(spatialTurn);
          }
        }
      } catch (e) {
        consola.error(`Error processing file ${filename}:`, e);
        // Add a check for the specific error and log the problematic turn data if possible
        if (e instanceof TypeError && e.message.includes("summarizedContext")) {
            consola.error("Problematic turn data:", JSON.stringify(caseData.turns.find(t => !t.summarizedContext && !t.summarized_context), null, 2));
        }
      }
    }
    
    consola.info(`Found a total of ${spatialTurns.length} spatial turns`);
    
    // Write to output file
    await fsPromises.writeFile(
      OUTPUT_PATH,
      JSON.stringify(spatialTurns, null, 2)
    );
    
    consola.success(`Successfully wrote spatial turns to ${OUTPUT_PATH}`);
  } catch (e) {
    consola.error("Error during execution:", e);
  }
}

main();
