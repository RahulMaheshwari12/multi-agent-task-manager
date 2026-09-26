---
name: task-management
description: Core CRUD operations for single tasks including creation, updating, completion, deletion, listing, and keyword search.
license: MIT
---
# Task Management Skill

## Instructions

1. **Intent Identification**:
   - Inspect the incoming user message to identify the specific task operation: `create_task`, `get_tasks`, `update_task`, `complete_task`, `delete_task`, `get_overdue_tasks`, or `search_tasks`.

2. **Date Resolution & Urgency Priority Calculation**:
   - Obtain today's current date formatted as `YYYY-MM-DD (Day)`.
   - Convert all relative user date references ("tomorrow", "next Friday", "end of week") into ISO `YYYY-MM-DD` strings.
   - Assign priority based on deadline proximity:
     - `HIGH`: Due today, overdue, due within the next 3 days, or contains urgent keywords (`urgent`, `asap`, `immediately`, `critical`).
     - `MEDIUM`: Due within 4 to 14 days.
     - `LOW`: Due more than 14 days away, backlog, learning, or optional tasks.

3. **Tool Execution**:
   - Bind and execute the corresponding async LangChain tool from `tools.py`:
     - `create_task(title, description, assigned_to, priority, due_date)`
     - `get_tasks(status)`
     - `update_task(task_id, updates)`
     - `complete_task(task_id)`
     - `delete_task(task_id)`
     - `get_overdue_tasks()`
     - `search_tasks(keyword)`

4. **Retry & Output Forwarding**:
   - Verify tool output string returned from `aiosqlite`.
   - Prevent duplicate task creation if `tool_output` already contains a success confirmation during retry loops.
   - Forward `tool_output` to the Reviewer Agent for validation.
