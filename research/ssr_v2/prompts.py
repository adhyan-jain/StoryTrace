"""Prompt conditions for V2 (Attack K). Text is frozen by sha256 (recorded in every raw record). Output for all final-state conditions is a JSON
object {claim_id: value} with each value enum-constrained to the claim's domain; K1-delta uses V1-style labels."""
from __future__ import annotations
import hashlib, json, os
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))

LAWS_IMPERATIVE = """You maintain facts about a small story world. Story sentences are tagged with the day on which they happen; they may be told out of chronological order, so use the day tags, not the order of telling. Sentences tagged "At the start" describe the world before day 1.

World rules (these always hold):
1. Facts persist: a character's location, a prop's holder, and a character's health stay the same until an event on a later day changes them.
2. An event on day D changes the facts of day D and of later days (until a further event changes them again). It never changes earlier days.
3. An injured character cannot travel: a move by an injured character is impossible. A character stays injured until healed.
4. A prop held by a character is in that character's location and travels with them. A prop that is put down stays where it was put down.
5. Giving requires that the giver holds the prop and that the receiver is in the same place. Picking up requires the prop to be held by nobody and to be in the same place as the person. Putting down requires holding the prop.
6. Each day has at most one event."""

K1_TASK = """You will also receive ONE NEW SENTENCE about an event on some day (it may be in the past or in the future of the story).
- If the event is possible under the rules at its day, it happens: the facts of that day and of later days change accordingly, including dependent facts (for example a prop travels with its holder), until a later event changes them again.
- If the event is impossible under the rules at its day, it did not happen: the world stays exactly as the story says.

Procedure. (1) Rebuild, for each character and prop that matters, what happens on which day. (2) Decide whether the new sentence is possible at its day under the rules. (3) Compute what the world looks like after the new sentence (or unchanged if it did not happen). (4) Answer each question about that resulting world. Do not change facts that the new sentence does not affect."""

K2_TASK = """You will also receive ONE NEW SENTENCE about an event on some day. Answer each question about the world after the new sentence has been taken into account."""

K3A = """Here is a short story about some people and objects. Each line of the story is labelled with the day it takes place on, and lines may be listed out of order, so rely on the labels. Lines labelled "At the start" describe how things were before the first day.

How this world works:
- Nothing changes by itself. Where someone is, who carries an object, and whether someone is hurt all remain as they were until something later alters them.
- Whatever happens on a given day shapes that day and every day afterwards, until another event alters it again; earlier days are never touched.
- Someone who is hurt is unable to walk anywhere until they have recovered.
- Carried objects are wherever their carrier is, and move along with the carrier. An object that has been set down remains in that spot.
- To hand an object over, the giver must be carrying it and both people must be in one spot. To pick an object up, nobody may be carrying it and the person must be in its spot. To set an object down, the person must be carrying it.
- At most one thing happens per day.

After the story you get one extra sentence describing something that happened on a particular day (earlier or later than the rest). If that could really have happened given the situation on that day, treat it as part of the story and work out the consequences, including indirect ones such as an object following its carrier. If it could not have happened, the story stays as it was. Then answer the questions about the resulting world, leaving everything the extra sentence does not touch exactly as it was."""

K3B = """Read the following account of a tiny world. Dated lines tell you what happened and when (the telling order may be scrambled, so trust the dates). Lines that start with "At the start" give the initial situation.

Ground rules of the world:
(a) Situations are sticky: a person's whereabouts, an object's carrier and a person's injury status carry on unchanged until a later event says otherwise.
(b) An event affects its own day and all later days, never earlier ones, and only until another event overrides it.
(c) A person with an injury cannot travel until they are healed.
(d) An object in someone's hands is in that person's place and goes wherever they go; a dropped object stays where it was dropped.
(e) You can only give away what you hold, to someone who is with you; you can only pick up what nobody holds and what lies where you are; you can only drop what you hold.
(f) No day contains more than one event.

You are then given a single extra statement about one more event on some day. Work out whether that event could have occurred given the situation on that day. If yes, recompute the world including it and all knock-on effects. If no, the world is unchanged. Finally answer the questions about the world as it ends up, without altering anything the extra statement has no bearing on."""

K4_LAWS = """The following describes a small world and a new report about it. Story lines are labelled with the day they happen; their order may be scrambled. Lines labelled "At the start" describe the initial situation.

Facts about this world: a character's location, the holder of a prop and a character's health persist until a later event alters them; an event changes its own day and later days but never earlier days; an injured character cannot travel until healed; a prop in a character's hands is where that character is and travels with them, while a prop that was put down stays where it was put down; a prop can be given only by its holder to someone in the same place, picked up only when nobody holds it and it is where the person is, and put down only by its holder; at most one event happens on any day. An event that cannot happen under these facts did not happen, and the world is as the story describes it.

A new report describes one event on some day. Answer each question about the world once the report has been taken into account."""

PROMPT_STORY = """STORY
{story}

NEW SENTENCE
{evidence}

QUESTIONS (answer with one of the listed options)
{claims}

Answer with a JSON object mapping each question id to the value after the new sentence has been taken into account."""

PROMPT_S0 = """STORY
{story}

QUESTIONS (answer with one of the listed options)
{claims}

Answer with a JSON object mapping each question id to the value according to the story."""

PROMPT_PG = """STORY
{story}

NEW SENTENCE
{evidence}

QUESTIONS (each shows its value in the story BEFORE the new sentence; answer with one of the listed options)
{claims_prior}

Answer with a JSON object mapping each question id to the value after the new sentence has been taken into account."""

PROMPT_DELTA = """STORY
{story}

NEW SENTENCE
{evidence}

QUESTIONS
{claims_plain}

For each question answer KEEP if its value is unchanged by the new sentence, "REVISE: <new value>" if the new sentence changes it (use one of the listed options as the new value), or CONFLICT if the new sentence is impossible at its day and this question is the fact it contradicts. Answer with a JSON object mapping each question id to your answer."""

CONDITIONS = {"K1": LAWS_IMPERATIVE + "\n\n" + K1_TASK, "K1-fs": LAWS_IMPERATIVE + "\n\n" + K1_TASK, "K2": K2_TASK, "K3a": K3A, "K3b": K3B, "K4": K4_LAWS,
              "PG": LAWS_IMPERATIVE + "\n\n" + K1_TASK, "S0": LAWS_IMPERATIVE + "\n\nAnswer each question about the world described by the story.",
              "K1-delta": LAWS_IMPERATIVE + "\n\n" + K1_TASK}


EXT_HEAD = """You are given a log of shell commands that were run in order, one per step, starting in a fresh empty directory called /work (bash, default settings). Facts about this environment:
- `cd` changes the working directory for every later command; relative paths are always relative to the current working directory.
- A command that fails (for example `cd` into a missing directory, or `git commit` with nothing valid to commit) has no effect, and later commands still run.
- `mkdir -p` creates directories; `touch f` creates an empty file if missing; `echo w > f` overwrites f with one line; `echo w >> f` appends a line; `rm f` deletes a file.
- `git init -q -b main` creates a repository on branch main in the current directory; `git commit -q --allow-empty -m m` always creates a commit once a repository exists; `git checkout -q -b b` creates and switches to branch b; a new branch starts at the current commit."""

EXT_TASK = """You will also be told about ONE additional command that was run at some point in the log. Treat the log as if that command had really been executed at that point, then answer each question about the final state after ALL commands have run. Do not change anything that the additional command does not affect."""

PROMPT_EXT = """COMMAND LOG
{story}

ADDITIONAL COMMAND
{evidence}

QUESTIONS (answer with one of the listed options)
{claims}

Answer with a JSON object mapping each question id to the value after all commands, including the additional one, have run."""

PROMPT_EXT_PG = """COMMAND LOG
{story}

ADDITIONAL COMMAND
{evidence}

QUESTIONS (each shows its value after the original log WITHOUT the additional command; answer with one of the listed options)
{claims_prior}

Answer with a JSON object mapping each question id to the value after all commands, including the additional one, have run."""

PROMPT_EXT_S0 = """COMMAND LOG
{story}

QUESTIONS (answer with one of the listed options)
{claims}

Answer with a JSON object mapping each question id to the value after the commands in the log have run."""


def claim_lines(t: dict, prior: Dict[str, str] = None, with_opts: bool = True, prior_label: str = "value in the story before the new sentence") -> str:
    out = []
    for c in t["claims"]:
        s = f'{c["id"]}. {c["question"]}'
        if prior is not None:
            s += f' ({prior_label}: {prior[c["id"]]})'
        if with_opts:
            s += "  [options: " + ", ".join(c["domain"]) + "]"
        out.append(s)
    return "\n".join(out)


def build_prompt(cond: str, t: dict, prior: Dict[str, str] = None, shots: List[str] = None) -> str:
    if t["item_id"].startswith("external-"):
        story = "\n".join(t["story"])
        if cond == "S0":
            return EXT_HEAD + "\n\n" + PROMPT_EXT_S0.format(story=story, claims=claim_lines(t))
        if cond == "PG":
            return EXT_HEAD + "\n\n" + EXT_TASK + "\n\n" + PROMPT_EXT_PG.format(story=story, evidence=t["evidence"], claims_prior=claim_lines(t, prior, prior_label="value after the original log, without the additional command"))
        return EXT_HEAD + "\n\n" + EXT_TASK + "\n\n" + PROMPT_EXT.format(story=story, evidence=t["evidence"], claims=claim_lines(t))
    head = CONDITIONS[cond]
    story = "\n".join(t["story"])
    if cond == "S0":
        body = PROMPT_S0.format(story=story, claims=claim_lines(t))
    elif cond == "PG":
        body = PROMPT_PG.format(story=story, evidence=t["evidence"], claims_prior=claim_lines(t, prior))
    elif cond == "K1-delta":
        body = PROMPT_DELTA.format(story=story, evidence=t["evidence"], claims_plain=claim_lines(t))
    else:
        body = PROMPT_STORY.format(story=story, evidence=t["evidence"], claims=claim_lines(t))
    if cond == "K1-fs" and shots:
        head += "\n\n" + "\n\n".join(shots) + "\n\nNow the real task."
    return head + "\n\n" + body


def example_text(t: dict, final: Dict[str, str]) -> str:
    ans = json.dumps({c["id"]: final[c["id"]] for c in t["claims"]})
    return "EXAMPLE\n" + PROMPT_STORY.format(story="\n".join(t["story"]), evidence=t["evidence"], claims=claim_lines(t)) + f"\nANSWER\n{ans}"


def schema_for(cond: str, t: dict) -> dict:
    ids = [c["id"] for c in t["claims"]]
    if cond == "K1-delta":
        return {"type": "object", "properties": {i: {"type": "string"} for i in ids}, "required": ids}
    return {"type": "object", "properties": {c["id"]: {"type": "string", "enum": list(c["domain"])} for c in t["claims"]}, "required": ids}


def prompt_hashes() -> Dict[str, str]:
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in CONDITIONS.items()} | {
        "PROMPT_STORY": hashlib.sha256(PROMPT_STORY.encode()).hexdigest(), "PROMPT_PG": hashlib.sha256(PROMPT_PG.encode()).hexdigest(),
        "PROMPT_S0": hashlib.sha256(PROMPT_S0.encode()).hexdigest(), "PROMPT_DELTA": hashlib.sha256(PROMPT_DELTA.encode()).hexdigest(),
        "EXT": hashlib.sha256((EXT_HEAD + EXT_TASK + PROMPT_EXT + PROMPT_EXT_PG + PROMPT_EXT_S0).encode()).hexdigest()}


def ngram_jaccard(a: str, b: str, n: int = 3) -> float:
    import re
    ta, tb = re.findall(r"[a-z]+", a.lower()), re.findall(r"[a-z]+", b.lower())
    A = {tuple(ta[i:i + n]) for i in range(len(ta) - n + 1)}
    B = {tuple(tb[i:i + n]) for i in range(len(tb) - n + 1)}
    return len(A & B) / max(1, len(A | B))
