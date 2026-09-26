---
name: productivity-recommendations
description: Analytical skill that evaluates task workload, overdue items, and deadlines to generate structured productivity advice.
license: MIT
---
# Productivity Recommendations Skill

## Instructions

1. **Task Workload Ingestion**:
   - Fetch active tasks using `get_tasks.ainvoke({"status": ""})`.
   - Fetch overdue tasks using `get_overdue_tasks.ainvoke({})`.
   - Inject today's date formatted as `YYYY-MM-DD (Day)`.

2. **Workload & Risk Analysis**:
   - Count total active tasks, overdue tasks, and upcoming deadlines within 3 days.
   - Identify workload bottlenecks, stale tasks, and high-priority task overload.

3. **Structured Output Formatting**:
   - Compile advisory output using the following mandatory sections:
     - 📊 Productivity Summary
     - 🚨 Immediate Attention
     - 📅 Upcoming Priorities
     - ✅ Suggested Plan
     - 💡 Productivity Tips

4. **Strict Data Grounding**:
   - Base all suggestions strictly on existing database items; never invent non-existent tasks.
   - Address overdue tasks first in suggested execution order.
   - Return structured text to Reviewer Agent.
