# Continuity Autopsy (Investigation)

## Overview
The Continuity Autopsy is the centerpiece of StoryTrace. It shows exactly how the Investigation Agent reached its verdict for a given candidate conflict.

## Logic Flow
When a user views an autopsy, they see:
1. **Prior State**: The evidence that established the state before the conflict.
2. **Observed State**: The evidence that contradicted the expected state.
3. **Investigation Trace**: A summary of actions the agent took (e.g., "Retrieved entity history", "Examined Scenes 17-21").
4. **Conclusion**: The reasoning for the verdict.

## Investigation Examples

### Example 1: Verified Conflict
- **Candidate**: John's gun lost in Scene 16, but held in Scene 22.
- **Agent Action**: Queries `get_entity_timeline("johns_gun", 16, 22)`.
- **Agent Result**: No recovery event found in timeline.
- **Agent Action**: Queries `get_scene_text(17)`, `get_scene_text(18)`, etc. to double check.
- **Agent Result**: Text does not mention finding the gun.
- **Verdict**: `VERIFIED CONFLICT`. Conclusion: No screenplay evidence explains how John regained the gun.

### Example 2: Resolved Conflict
- **Candidate**: Character jacket changed.
- **Agent Action**: Queries timeline and surrounding scene text.
- **Agent Result**: Finds scene 33 mentions "John changes his jacket".
- **Verdict**: `RESOLVED`. Conclusion: Scene 33 explicitly establishes the wardrobe change, explaining the state transition.
