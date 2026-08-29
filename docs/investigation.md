# Continuity Autopsy (Investigation)

The Continuity Autopsy is how StoryTrace handles candidates detected by ClickHouse analytics. Rather than throwing false positives at the user, the Investigation Agent actively searches the story universe to resolve them.

## Investigation Scope
Because StoryTrace supports multi-document universes (e.g., Book 1 -> Book 2 -> Book 3), the agent dynamically selects its scope of investigation:
1. **Surrounding Narrative Units**: Checking the immediate context (e.g. Chapter 40-42).
2. **Entity History**: Querying the full temporal history of the entity in the current document.
3. **Document-wide History**: Querying all mentions of an entity across the document.
4. **Story-Universe-wide History**: Querying events from previous books/screenplays.

## Example Flow

**Candidate**: Mara possesses the locket in Chapter 41. (But previously lost it in Chapter 10).

**Agent Actions**:
1. Inspects Chapter 41 text for clues.
2. Retrieves Mara's locket history across the story universe.
3. Searches intervening events between Chapter 10 and 41.
4. Discovers a transfer event: "Elias returned the locket" in Chapter 40.
5. Emits `status: resolved`.

The user interface then displays this exact trace, showing the evidence used to reach the verdict.
