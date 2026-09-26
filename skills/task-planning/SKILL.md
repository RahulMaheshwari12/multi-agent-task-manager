---
name: task-planning
description: Goal decomposition skill that breaks complex multi-step user requests into actionable, prioritized subtasks.
license: MIT
---
# Task Planning Skill

## Instructions

1. **Request Complexity Analysis**:
   - Analyze user request to determine if it represents a single simple action or a complex multi-goal project/event.
   - If complex, decompose the project into logical, sequential subtasks representing distinct single actions.

2. **Action-Verb Subtask Formatting**:
   - Every generated subtask title must start with an explicit action verb (e.g. "Create project structure", "Implement API endpoints", "Test workflow").
   - Avoid vague task names such as "Work on project", "Study", or "Prepare things".

3. **Schedule & Deadline Distribution**:
   - Obtain current server date `YYYY-MM-DD (Day)`.
   - Distribute deadlines logically across subtasks from start date to project target completion.
   - Calculate priority (`high`, `medium`, `low`) for each subtask based on deadline proximity.

4. **Batch Subtask Creation**:
   - Iterate through each decomposed subtask and invoke `create_task` tool individually.
   - Concatenate all execution result strings into `tool_output`.
   - Route `tool_output` to the Reviewer Agent for structural audit.
