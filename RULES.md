# Rules

## Must Always
- Compare task due dates against the current date formatted as `YYYY-MM-DD (Day)` to resolve relative terms (e.g. "tomorrow", "next Friday").
- Use standard ISO `YYYY-MM-DD` format for all task due dates saved in the database.
- Determine priority based on strict deadline urgency rules:
  - **HIGH**: Due today, overdue, due within 3 days, or contains urgent keywords (`urgent`, `asap`, `immediately`, `critical`).
  - **MEDIUM**: Due within 4 to 14 days.
  - **LOW**: Due more than 14 days away, backlog, or optional tasks without urgency.
- Execute all database operations through asynchronous LangChain tools wrapping `aiosqlite`.
- Pass user requests through the Supervisor Router for intent classification before invoking worker agents.
- Pass worker agent outputs through the Reviewer Agent for validation (`APPROVED` or `NEEDS_RETRY`).
- Enforce a maximum retry limit of 2 cycles when a `NEEDS_RETRY` review status is emitted to prevent infinite execution loops.

## Must Never
- Invent tasks, due dates, or status details not present in the database or user request.
- Allow the Reviewer Agent to execute database CRUD operations directly.
- Combine unrelated actions into a single task when decomposing complex goals in the Planner Agent.
- Assign both Maker/Creator and Checker/Approver duties to the same agent node or line.
- Execute blocking synchronous database I/O operations on the main FastAPI or Telegram bot event loops.
- Accept vague task titles like "Work on project", "Study", or "Prepare things" without actionable details.
