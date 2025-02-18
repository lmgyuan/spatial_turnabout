import * as fs from 'fs';
import * as path from 'path';
import xlsx from 'xlsx';

const FINAL_DIR = './data/aceattorney_data/final';

interface Turn {
    category: string;
    new_context: string;
    testimonies: Array<{
        testimony: string;
        person: string;
        present: string[];
    }>;
    noPresent: boolean;
}

interface CaseData {
    previousContext: string;
    characters: Array<any>;
    evidences: Array<any>;
    turns: Turn[];
}

interface Stats {
    totalCases: number;
    totalTurns: number;
    turnsWithPresent: number;
    turnsWithoutPresent: number;
    totalTestimonies: number;
    totalCharacters: number;
    totalEvidence: number;
    avgTurnsPerCase: number;
    avgTestimoniesPerTurn: number;
    avgEvidencePerCase: number;
    avgCharactersPerCase: number;
    longestTestimony: number;
    shortestTestimony: number;
    avgTestimonyLength: number;
    maxEvidencePresents: number;
    longestContext: number;
    shortestContext: number;
    avgContextLength: number;
}

interface CaseStats {
    turns: number;
    turnsWithPresent: number;
    turnsWithNoPresent: number;
    testimonies: number;
    contextLength: number;
}

// Helper function to count words with multiple delimiters
function countWords(text: string): number {
    // First replace all newlines with spaces
    const normalized = text.replace(/\n/g, ' ');
    // Then split by one or more whitespace characters and filter out empty strings
    return normalized.split(/\s+/).filter(word => word.length > 0).length;
}

function getStats() {
    // Check if directory exists
    if (!fs.existsSync(FINAL_DIR)) {
        console.error(`Directory ${FINAL_DIR} does not exist`);
        return;
    }

    const files = fs.readdirSync(FINAL_DIR);
    if (!files || files.length === 0) {
        console.error('No files found in directory');
        return;
    }

    const stats: Stats = {
        totalCases: 0,
        totalTurns: 0,
        turnsWithPresent: 0,
        turnsWithoutPresent: 0,
        totalTestimonies: 0,
        totalCharacters: 0,
        totalEvidence: 0,
        avgTurnsPerCase: 0,
        avgTestimoniesPerTurn: 0,
        avgEvidencePerCase: 0,
        avgCharactersPerCase: 0,
        longestTestimony: 0,
        shortestTestimony: Number.MAX_SAFE_INTEGER,
        avgTestimonyLength: 0,
        maxEvidencePresents: 0,
        longestContext: 0,
        shortestContext: Number.MAX_SAFE_INTEGER,
        avgContextLength: 0
    };

    // Track unique case prefixes
    const uniqueCases = new Set<string>();
    let totalTestimonyLength = 0;

    // Track contexts for each unique case
    const caseContexts = new Map<string, string>();

    // Track stats for each case
    const caseStats = new Map<string, CaseStats>();
    
    files.forEach(file => {
        if (file.endsWith('.json')) {
            try {
                const casePrefix = file.split('_')[0].split('-').slice(0, 2).join('-');
                const caseName = file.split('_').slice(1).join('_').replace('.json', '');
                uniqueCases.add(casePrefix);

                // Initialize case stats if not exists
                if (!caseStats.has(casePrefix)) {
                    caseStats.set(casePrefix, {
                        turns: 0,
                        turnsWithPresent: 0,
                        turnsWithNoPresent: 0,
                        testimonies: 0,
                        contextLength: 0
                    });
                }

                const currentStats = caseStats.get(casePrefix)!;
                
                const filePath = path.join(FINAL_DIR, file);
                const data = JSON.parse(fs.readFileSync(filePath, 'utf8')) as CaseData;
                
                // Build context for this file
                let context = data.previousContext || '';
                if (Array.isArray(data.turns)) {
                    data.turns.forEach(turn => {
                        context += ' ' + (turn.new_context || '');
                    });
                }

                // Update context for this case
                if (caseContexts.has(casePrefix)) {
                    // Only keep the latest file's context (with higher part number)
                    const partNumber = parseInt(file.split('_')[0].split('-')[2] || '0');
                    const existingPartNumber = parseInt(
                        caseContexts.get(casePrefix)?.split('_')[0].split('-')[2] || '0'
                    );
                    if (partNumber > existingPartNumber) {
                        caseContexts.set(casePrefix, context);
                    }
                } else {
                    caseContexts.set(casePrefix, context);
                }

                // Safely access arrays with null checks
                stats.totalCharacters += data.characters?.length || 0;
                stats.totalEvidence += data.evidences?.length || 0;
                
                if (Array.isArray(data.turns)) {
                    data.turns.forEach(turn => {
                        stats.totalTurns++;
                        currentStats.turns++;
                        
                        if (turn.noPresent === false) {
                            stats.turnsWithPresent++;
                            currentStats.turnsWithPresent++;
                        } else {
                            stats.turnsWithoutPresent++;
                            currentStats.turnsWithNoPresent++;
                        }

                        if (Array.isArray(turn.testimonies)) {
                            stats.totalTestimonies += turn.testimonies.length;
                            currentStats.testimonies += turn.testimonies.length;
                            
                            turn.testimonies.forEach(testimony => {
                                if (testimony.testimony) {
                                    const length = countWords(testimony.testimony);
                                    totalTestimonyLength += length;
                                    stats.longestTestimony = Math.max(stats.longestTestimony, length);
                                    stats.shortestTestimony = Math.min(stats.shortestTestimony, length);
                                    
                                    if (Array.isArray(testimony.present)) {
                                        stats.maxEvidencePresents = Math.max(
                                            stats.maxEvidencePresents, 
                                            testimony.present.length
                                        );
                                    }
                                }
                            });
                        }
                    });
                }
            } catch (error) {
                console.error(`Error processing file ${file}:`, error);
            }
        }
    });

    stats.totalCases = uniqueCases.size;

    if (stats.totalCases === 0) {
        console.error('No valid cases found');
        return;
    }

    // Calculate averages
    stats.avgTurnsPerCase = stats.totalTurns / stats.totalCases;
    stats.avgTestimoniesPerTurn = stats.totalTestimonies / stats.totalTurns;
    stats.avgEvidencePerCase = stats.totalEvidence / stats.totalCases;
    stats.avgCharactersPerCase = stats.totalCharacters / stats.totalCases;
    stats.avgTestimonyLength = totalTestimonyLength / stats.totalTestimonies;

    // Calculate context statistics
    let totalContextLength = 0;
    caseContexts.forEach((context) => {
        const length = countWords(context);
        totalContextLength += length;
        stats.longestContext = Math.max(stats.longestContext, length);
        stats.shortestContext = Math.min(stats.shortestContext, length);
    });
    stats.avgContextLength = totalContextLength / caseContexts.size;

    // Print stats
    console.log('\n=== Dataset Statistics ===');
    console.log('\nCase Statistics:');
    console.log(`Total Unique Cases: ${stats.totalCases}`);
    console.log(`Total JSON Files: ${files.filter(f => f.endsWith('.json')).length}`);
    console.log(`Average Character Count per Case: ${stats.avgCharactersPerCase.toFixed(2)}`);

    console.log('\nTurn Statistics:');
    console.log(`Total Turns: ${stats.totalTurns}`);
    console.log(`Turns with Evidence to Present: ${stats.turnsWithPresent}`);
    console.log(`Turns without Evidence to Present: ${stats.turnsWithoutPresent}`);
    console.log(`Percentage of Turns with Evidence: ${((stats.turnsWithPresent / stats.totalTurns) * 100).toFixed(2)}%`);

    console.log('\nTestimony Statistics:');
    console.log(`Total Testimonies: ${stats.totalTestimonies}`);
    console.log(`Average Testimonies per Turn: ${stats.avgTestimoniesPerTurn.toFixed(2)}`);
    console.log(`Longest Testimony (words): ${stats.longestTestimony}`);
    console.log(`Shortest Testimony (words): ${stats.shortestTestimony}`);
    console.log(`Average Testimony Length (words): ${stats.avgTestimonyLength.toFixed(2)}`);
    console.log(`Maximum Evidence Presents in a Testimony: ${stats.maxEvidencePresents}`);

    console.log('\nContext Statistics:');
    console.log(`Longest Context (words): ${stats.longestContext}`);
    console.log(`Shortest Context (words): ${stats.shortestContext}`);
    console.log(`Average Context Length (words): ${stats.avgContextLength.toFixed(2)}`);

    // Print per-case statistics
    console.log('\nPer-Case Statistics:');
    console.log('Case\tTurns\tPresent\tNo Present\tTestimonies');
    console.log('-'.repeat(60));
    
    const sortedCases = Array.from(caseStats.entries()).sort((a, b) => {
        const [prefixA] = a[0].split('-').map(Number);
        const [prefixB] = b[0].split('-').map(Number);
        return prefixA - prefixB || 
               parseInt(a[0].split('-')[1]) - parseInt(b[0].split('-')[1]);
    });

    // Print table in console
    sortedCases.forEach(([prefix, stats]) => {
        console.log(
            `${prefix}\t${stats.turns}\t${stats.turnsWithPresent}\t${stats.turnsWithNoPresent}\t\t${stats.testimonies}`
        );
    });

    // Create worksheet data for Excel
    const wsData = [
        ['Case', 'Turns', 'Can Present', 'No Present', 'Testimonies'], // Headers
        ...sortedCases.map(([prefix, stats]) => [
            prefix,
            stats.turns,
            stats.turnsWithPresent,
            stats.turnsWithNoPresent,
            stats.testimonies
        ])
    ];

    // Create summary data
    const summaryData = [
        ['Dataset Summary'],
        ['Total Cases', stats.totalCases],
        ['Total Turns', stats.totalTurns],
        ['Total Testimonies', stats.totalTestimonies],
        [''],
        ['Averages'],
        ['Avg Turns per Case', Number(stats.avgTurnsPerCase.toFixed(2))],
        ['Avg Testimonies per Turn', Number(stats.avgTestimoniesPerTurn.toFixed(2))],
        ['Avg Context Length', Number(stats.avgContextLength.toFixed(2))],
        [''],
        ['Context Statistics'],
        ['Longest Context', stats.longestContext],
        ['Shortest Context', stats.shortestContext],
        [''],
        ['Testimony Statistics'],
        ['Longest Testimony', stats.longestTestimony],
        ['Shortest Testimony', stats.shortestTestimony],
        ['Max Evidence Presents', stats.maxEvidencePresents]
    ];

    // Create workbook
    const wb = xlsx.utils.book_new();
    
    // Create case stats worksheet
    const ws = xlsx.utils.aoa_to_sheet(wsData);
    xlsx.utils.book_append_sheet(wb, ws, 'Case Statistics');

    // Create summary worksheet
    const summaryWs = xlsx.utils.aoa_to_sheet(summaryData);
    xlsx.utils.book_append_sheet(wb, summaryWs, 'Summary');

    // Save to file
    xlsx.writeFile(wb, './data/aceattorney_data/aceattorney_stat/dataset_statistics.xlsx');
}

getStats();
