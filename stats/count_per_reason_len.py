import argparse
import os
import json
from collections import defaultdict

# Same folders as in plot_stats.py
FOLDERS = [
  "data/aceattorney_data/final",
  "data/danganronpa_data/final",
]

class Turn:
  def __init__(self, filename, turn):
    self.filename = filename
    self.turn = turn

  def len_reasoning_chain(self) -> int:
    if "reasoning" in self.turn:
      return len(self.turn["reasoning"])
    else:
      return 0

  def has_difficulty(self, difficulty):
    if "difficulty" in self.turn:
      if difficulty == "hard":
        return self.turn["difficulty"] == "hard" or \
               self.turn["difficulty"] == "common sense" or \
               self.turn["difficulty"] == "difficult"
      else:
        return self.turn["difficulty"] == difficulty
    else:
      return False

  def from_title(self, title: str):
    is_aa = self.filename.startswith("data/ace")
    name = self.filename.split("/")[-1]
    if is_aa:
      if title == "AA123": return name.startswith("1-") or name.startswith("2-") or name.startswith("3-")
      elif title == "AA456": return name.startswith("4-") or name.startswith("5-") or name.startswith("6-")
      elif title == "GAA12": return name.startswith("7-") or name.startswith("8-")
      elif title == "AAI12": return name.startswith("9-") or name.startswith("10-")
    else:
      if title == "DGRP1": return name.startswith("1-")
    return False

class Chapter:
  def __init__(self, filename: str):
    self.filename = filename
    self._source_json = json.load(open(filename))

  def turns(self):
    return [Turn(self.filename, turn) for turn in self._source_json["turns"]]

def get_all_chapters():
  all_chapters = []
  for folder in FOLDERS:
    for filename in os.listdir(folder):
      if filename.endswith(".json") and not filename.startswith("_"):
        chapter = Chapter(f"{folder}/{filename}")
        all_chapters.append(chapter)
  return all_chapters

def get_all_turns(chapters, no_present_only=True):
  all_turns = []
  for chapter in chapters:
    for turn in chapter.turns():
      # Only include turns with noPresent = False if specified
      if not no_present_only or turn.turn.get("noPresent") == False:
        all_turns.append(turn)
  return all_turns

def count_reasoning_lengths(turns):
  """Count how many questions have each reasoning length"""
  counts = defaultdict(int)
  for turn in turns:
    length = turn.len_reasoning_chain()
    counts[length] += 1
  return counts

def main(args):
  # Load all chapters and turns
  print("Loading chapters...")
  chapters = get_all_chapters()
  all_turns = get_all_turns(chapters, no_present_only=True)
  print(f"Loaded {len(all_turns)} turns")
  
  # Count reasoning lengths
  counts = count_reasoning_lengths(all_turns)
  
  # Print summary of counts
  print("\nReasoning Length Counts:")
  print("=======================")
  print("Length | Count")
  print("-------|------")
  total = 0
  for length in sorted(counts.keys()):
    print(f"{length:6d} | {counts[length]:5d}")
    total += counts[length]
  print("-------|------")
  print(f"Total   | {total:5d}")
  
  # Print by difficulty
  difficulties = ["easy", "medium", "hard"]
  print("\nBreakdown by Difficulty:")
  print("======================")
  print("Length | Easy  | Medium | Hard")
  print("-------|-------|--------|-------")
  
  for length in sorted(counts.keys()):
    easy_count = sum(1 for turn in all_turns if turn.has_difficulty("easy") and turn.len_reasoning_chain() == length)
    medium_count = sum(1 for turn in all_turns if turn.has_difficulty("medium") and turn.len_reasoning_chain() == length)
    hard_count = sum(1 for turn in all_turns if turn.has_difficulty("hard") and turn.len_reasoning_chain() == length)
    print(f"{length:6d} | {easy_count:5d} | {medium_count:6d} | {hard_count:5d}")
  
  # Print by game series
  titles = ["AA123", "AA456", "GAA12", "AAI12", "DGRP1"]
  print("\nBreakdown by Game Series:")
  print("=======================")
  header = "Length |" + "|".join(f" {title:5s} " for title in titles)
  print(header)
  separator = "-------|" + "|".join("-------" for _ in titles)
  print(separator)
  
  for length in sorted(counts.keys()):
    counts_by_title = []
    for title in titles:
      title_count = sum(1 for turn in all_turns if turn.from_title(title) and turn.len_reasoning_chain() == length)
      counts_by_title.append(title_count)
    
    row = f"{length:6d} |" + "|".join(f" {count:5d} " for count in counts_by_title)
    print(row)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Count questions per reasoning length")
  args = parser.parse_args()
  main(args)
