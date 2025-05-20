import argparse
import typing
import os
import json
import collections


FOLDERS = [
  "data/aceattorney_data/final",
  "data/danganronpa_data/final",
]


class Turn:
  def __init__(self, filename, characters, evidences, turn):
    self.filename = filename
    self.characters = characters
    self.evidences = evidences
    self.turn = turn

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

  def num_characters(self) -> typing.Optional[int]:
    if not self.characters:
      return None
    else:
      return len(self.characters)

  def character_names(self) -> typing.List[str]:
    if not self.characters:
      return []
    else:
      return [character["name"] for character in self.characters]

  def context_length(self) -> int:
    return len(self.turn["newContext"])

  def num_evidences(self) -> int:
    return len(self.evidences)

  def num_testimonies(self) -> int:
    return len(self.turn["testimonies"])

  def num_reasoning_kinds(self) -> int:
    if "labels" in self.turn:
      return len(self.turn["labels"])
    else:
      return 1

  def len_reasoning_chain(self) -> int:
    if "reasoning" in self.turn:
      return len(self.turn["reasoning"])
    else:
      return 1

  def reasoning_kinds(self) -> int:
    if "labels" in self.turn:
      return self.turn["labels"]
    else:
      return []


class Chapter:
  def __init__(self, filename: str):
    print(f"Loading {filename}")
    self.filename = filename
    self.is_aa = filename.startswith("data/ace")
    self._source_json = json.load(open(filename))

  def turns(self) -> typing.List[Turn]:
    print(f"Loading turns in {self.filename}")
    return [
      Turn(
        self.filename,
        self._source_json["characters"] if "characters" in self._source_json else None,
        self._source_json["evidences"] if "evidences" in self._source_json else self._source_json["evidence_objects"],
        turn
      )
      for turn in self._source_json["turns"]
    ]


def get_all_chapters():
  all_chapters = []
  for folder in FOLDERS:
    for filename in os.listdir(folder):
      print(filename)
      if filename.endswith(".json") and not filename.startswith("_"):
        chapter = Chapter(f"{folder}/{filename}")
        all_chapters.append(chapter)
  return all_chapters


def get_all_turns(chapters):
  all_turns = []
  for chapter in chapters:
    # Yuan Edit: only include turns with noPresent = False
    for turn in chapter.turns():
      if turn.turn["noPresent"] == False:
        all_turns.append(turn)
  return all_turns


def get_num_problems(turns):
  return len(turns)


def get_num_characters(turns):
  characters = set()
  for turn in turns:
    for character_name in turn.character_names():
      characters.add(character_name)
  return len(characters)


def get_avg_num_characters(turns):
  count = 0
  num_characters = 0
  for turn in turns:
    nc = turn.num_characters()
    if nc is not None:
      num_characters += nc
      count += 1
  if count != 0:
    return num_characters / count
  else:
    return 0


def get_avg_context_length(turns):
  lengths = [turn.context_length() for turn in turns]
  return sum(lengths) / len(lengths)


def get_avg_testimonies(turns):
  return sum([turn.num_testimonies() for turn in turns]) / len(turns)


def get_max_testimonies(turns):
  return max([turn.num_testimonies() for turn in turns])


def get_avg_evidences(turns):
  return sum([turn.num_evidences() for turn in turns]) / len(turns)


def get_max_evidences(turns):
  return max([turn.num_evidences() for turn in turns])


def get_avg_num_reasoning_kinds(turns):
  return sum([turn.num_reasoning_kinds() for turn in turns]) / len(turns)


def get_max_num_reasoning_kinds(turns):
  return max([turn.num_reasoning_kinds() for turn in turns])


def get_avg_len_reasoning_chain(turns):
  return sum([turn.len_reasoning_chain() for turn in turns]) / len(turns)


def get_max_len_reasoning_chain(turns):
  return max([turn.len_reasoning_chain() for turn in turns])

def get_num_self_contained_problems(turns):
  return len([turn for turn in turns if "is_self_contained" in turn.turn and turn.turn["is_self_contained"] == "yes"])


DIFFICULTIES = ["easy", "medium", "hard"]


STAT_FNS = {
  "num_problems": get_num_problems,
  "num_characters": get_num_characters,
  "num_self_contained_problems": get_num_self_contained_problems,
  "avg_num_characters": get_avg_num_characters,
  "avg_context_length": get_avg_context_length,
  "avg_context_tokens": get_avg_context_tokens,
  "avg_testimonies": get_avg_testimonies,
  "max_testimonies": get_max_testimonies,
  "avg_evidences": get_avg_evidences,
  "max_evidences": get_max_evidences,
  "avg_reasoning_kinds": get_avg_num_reasoning_kinds,
  "avg_len_reasoning_chain": get_avg_len_reasoning_chain,
  "max_len_reasoning_chain": get_max_len_reasoning_chain,
}


def get_categorized_stats(all_turns):
  categorized_turns = {diff: [turn for turn in all_turns if turn.has_difficulty(diff)] for diff in DIFFICULTIES}
  categorized_turns["overall"] = all_turns
  categorized_stats = {cate: {name: fn(turns) for (name, fn) in STAT_FNS.items()} for (cate, turns) in categorized_turns.items()}
  return categorized_stats


def get_per_title_stats(all_turns):
  titles = ["AA123", "AA456", "GAA12", "AAI12", "DGRP1"]
  per_title_turns = {title: [turn for turn in all_turns if turn.from_title(title)] for title in titles}
  per_title_turns["overall"] = all_turns
  per_title_stats = {cate: {name: fn(turns) for (name, fn) in STAT_FNS.items()} for (cate, turns) in per_title_turns.items()}
  return per_title_stats


def dump_testimony_evidence_stats(all_turns):
  lines = ["testimonies evidences count\n"]
  stats = collections.defaultdict(lambda: 0)
  for turn in all_turns:
    stats[(turn.num_testimonies(), turn.num_evidences())] += 1
  for ((x, y), count) in stats.items():
    lines.append(f"{x} {y} {count}\n")
  with open("stats/testimonies_evidences.txt", "w") as f:
    f.writelines(lines)


def get_reasoning_kind_stats(turns):
  counts = collections.defaultdict(lambda: 0)
  for turn in turns:
    for reasoning_kind in turn.reasoning_kinds():
      counts[reasoning_kind] += 1
  return counts


def dump_reasoning_kind_stats(all_turns):
  titles = ["AA123", "AA456", "GAA12", "AAI12", "DGRP1"]
  per_title_turns = {title: [turn for turn in all_turns if turn.from_title(title)] for title in titles}
  per_title_stats = {title: get_reasoning_kind_stats(turns) for (title, turns) in per_title_turns.items()}
  with open("stats/reasoning_kind_stats.json", "w") as f:
    json.dump(per_title_stats, f, indent=2)


def main():
  chapters = get_all_chapters()
  all_turns = get_all_turns(chapters)

  # 1. For Main stats table
  per_title_stats = get_per_title_stats(all_turns)
  json.dump(per_title_stats, open("stats/per_title_stats.json", "w"), indent=2)

  # 2. For testimony_evidence scatter density plot
  dump_testimony_evidence_stats(all_turns)

  # 3. For reasoning kind plot
  dump_reasoning_kind_stats(all_turns)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  args = parser.parse_args()

  main()

# Overall statistics (overall, easy, medium, hard)
#  - #problems
#  - #characters
#  - avg #context length
#  - avg #testimony
#  - avg #evidences
#  - avg #reasoning type
#  - avg #reasoning chain length

# Search Space: (dot)
#  - #Testimony & #Evidences Plot

# Reasoning Difficulty (line)
#  - #reasoning length vs amount
#  - #proposition vs amount
#  - #reasoning kind vs amount

# Different kinds (bar)
#  - reasoning kind vs amount
