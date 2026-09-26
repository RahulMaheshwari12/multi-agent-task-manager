# Segregation of Duties (SOD) & Agent Roles

## Agent Role Definitions

- Role: Supervisor Agent (Router)
  - Category: Router
  - Responsibilities: Classifies user intent from natural language input and routes execution to the appropriate worker node (`task_manager`, `planner`, or `recommender`).
  - Boundaries: Does not execute database operations or generate task content directly.

- Role: Task Manager Agent (Maker)
  - Category: Maker / Executor
  - Responsibilities: Handles all single-task CRUD operations (create, update, complete, delete, list, search, overdue) using async database tools. Determines task priorities based on deadline urgency rules.
  - Boundaries: Cannot self-approve outputs without Reviewer Agent audit.

- Role: Planner Agent (Maker)
  - Category: Maker / Creator
  - Responsibilities: Decomposes complex multi-step user requests into actionable subtasks with specific deadlines, action-verb titles, and priority levels, invoking `create_task` tool.
  - Boundaries: Cannot self-approve generated subtask plans without Reviewer Agent audit.

- Role: Recommender Agent (Maker)
  - Category: Maker / Advisor
  - Responsibilities: Analyzes active and overdue tasks, calculates workload bottlenecks, and generates structured morning productivity summaries and action plans.
  - Boundaries: Read-only access to task database; cannot approve or bypass final output review.

- Role: Reviewer Agent (Checker)
  - Category: Checker / Approver
  - Responsibilities: Evaluates tool outputs and response quality against completeness, accuracy, and date formatting criteria. Emits `APPROVED` or `NEEDS_RETRY` signals.
  - Boundaries: Cannot perform database CRUD actions or create task content directly.

## Segregation of Duties Matrix

| Role Name | Category | Create/Modify Tasks | Read Database | Audit & Approve Output | Route Intent |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Supervisor Agent | Router | ❌ | ❌ | ❌ | ✅ |
| Task Manager Agent | Maker | ✅ | ✅ | ❌ | ❌ |
| Planner Agent | Maker | ✅ | ✅ | ❌ | ❌ |
| Recommender Agent | Maker | ❌ | ✅ | ❌ | ❌ |
| Reviewer Agent | Checker | ❌ | ❌ | ✅ | ❌ |
