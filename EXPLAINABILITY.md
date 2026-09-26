# Explainability Standard

## Decision Logic

The Multi-Agent Task Management System uses a state-graph architecture implemented via LangGraph (`graphs.py`) to process user requests through specialized cognitive nodes:

1. **Intent Classification & Routing**: Incoming user messages enter the `supervisor_agent` node in `agents.py`. The supervisor invokes `llama-3.3-70b-versatile` to classify intent into 9 structured categories (`create_task`, `get_tasks`, `update_task`, `complete_task`, `delete_task`, `overdue_tasks`, `search_tasks`, `recommend`, `plan`). The supervisor returns a state dictionary updating `current_agent` to `task_manager`, `planner`, or `recommender`.
2. **Context-Aware Deadline & Priority Resolution**: Worker agents inject today's date dynamically (`datetime.now().strftime("%Y-%m-%d (%A)")`) into system prompts to resolve relative expressions ("tomorrow", "next Friday"). Task priorities (`high`, `medium`, `low`) are calculated deterministically based on due date proximity (due today/overdue/urgent keywords = `high`; 4–14 days = `medium`; >14 days = `low`).
3. **Tool Execution & De-duplication**: The `task_manager` and `planner` agents invoke asynchronous database tools defined in `tools.py` (`create_task`, `update_task`, `complete_task`, `delete_task`, `get_overdue_tasks`, `search_tasks`). To prevent duplicate DB creation during retry loops, the Task Manager node checks `tool_output` status before re-executing.
4. **Validation & Retry State Machine**: Worker outputs pass to the `reviewer_agent` node. The Reviewer evaluates output validity, emitting `APPROVED` or `NEEDS_RETRY`. If `NEEDS_RETRY` is returned, `retry_count` is incremented and the state routes back to `task_manager`. If `retry_count >= 2`, the router terminates execution to `END` to avoid infinite loops.

## Data Sources

The system ingests and processes data across the following storage layers, APIs, and communication protocols:

- **Asynchronous SQLite Database (`tasks.db`)**: Primary storage managed via `aiosqlite` (`database.py`) consisting of two main tables:
  - `tasks`: Stores `id` (INTEGER PRIMARY KEY), `title` (TEXT), `description` (TEXT), `priority` (TEXT), `status` (TEXT), `assigned_to` (TEXT), `due_date` (TEXT), `created_at`, `updated_at`.
  - `settings`: Stores key-value configuration strings such as Telegram `chat_id` for automated notifications.
- **Groq Cloud LLM API (`ChatGroq`)**: Provides high-throughput inference using `llama-3.3-70b-versatile` for intent routing, tool calling, subtask decomposition, and productivity advice generation.
- **FastAPI Web Dashboard Interface (`app.py` & `static/`)**: Serves RESTful JSON payloads (`/api/chat`, `/api/tasks`, `/api/tasks/{id}`) and hosts an interactive frontend (`index.html`, `script.js`).
- **Telegram Bot Interface (`bot.py`)**: Asynchronous Telegram client using `python-telegram-bot` supporting command shortcuts (`/tasks`, `/overdue`, `/summary`) and natural language message updates.
- **Background Scheduler (`APScheduler` / `JobQueue`)**: Async scheduler running inside `bot.py` executing autonomous morning summaries at 9:00 AM IST by querying overdue/pending tasks.

## Limitations

The current system implementation operates under the following technical boundaries and operational constraints:

- **Single-Tenant Database Scope**: The `tasks` database table currently lacks a `user_id` foreign key constraint, meaning all web and Telegram users share a single global task repository.
- **SQLite Concurrency & Scaling**: File-based `aiosqlite` guarantees async thread-safety for single-node deployments but cannot scale horizontally across multi-region container clusters compared to connection-pooled PostgreSQL.
- **Server Local Timezone Dependency**: Date resolution relies on server system time (`datetime.now()`). Users in different timezones may experience slight date calculation offsets if server time differs from client local time.
- **Fixed Retry Hard Ceiling**: The review state machine terminates after 2 failed retries (`retry_count >= 2`), returning the latest raw tool output to prevent infinite API billing loops during persistent tool failures.
- **External LLM Provider Dependency**: System cognitive capabilities depend on Groq API uptime and internet connectivity; offline environments cannot execute natural language routing or subtask planning.
