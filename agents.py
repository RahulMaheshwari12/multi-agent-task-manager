from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict
from datetime import datetime
import os
from dotenv import load_dotenv
from tools import (
    create_task,
    get_tasks,
    update_task,
    complete_task,
    delete_task,
    get_overdue_tasks,
    search_tasks
)

load_dotenv()

# ── LLM Setup ─────────────────────────────────────────
USE_GROQ = os.getenv("USE_GROQ", "false").lower() == "true"

if USE_GROQ:
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )
else:
    llm = ChatOllama(model="llama3")

# ── Tools per agent ────────────────────────────────────
task_manager_tools = [create_task, get_tasks, update_task, complete_task, delete_task, get_overdue_tasks, search_tasks]
recommender_tools = [get_tasks, get_overdue_tasks, search_tasks]
planner_tools = [create_task, get_tasks]

# ── Agent State ────────────────────────────────────────
class AgentState(TypedDict):
    user_message: str
    intent: str
    agent_response: str
    tool_output: str
    review_status: str
    final_response: str
    current_agent: str
    retry_count: int

# ── Supervisor Agent ───────────────────────────────────
async def supervisor_agent(state: AgentState) -> AgentState:
    """Reads user message and decides which agent to call"""
    messages = [
        SystemMessage(content="""You are a supervisor of a task management system.
        Read the user message and classify the intent into one of these:
        - create_task: user wants to create a new task
        - get_tasks: user wants to see tasks
        - update_task: user wants to update a task
        - complete_task: user wants to mark task as done
        - delete_task: user wants to delete a task
        - overdue_tasks: user wants to see overdue tasks
        - search_tasks: user wants to search for tasks
        - recommend: user wants recommendations or productivity advice
        - plan: user wants to plan multiple tasks at once
        
        Reply with ONLY the intent word, nothing else."""),
        HumanMessage(content=state["user_message"])
    ]
    
    response = await llm.ainvoke(messages)
    intent = response.content.strip().lower()
    
    # Map intent to next agent
    intent_map = {
        "create_task": "task_manager",
        "get_tasks": "task_manager",
        "update_task": "task_manager",
        "complete_task": "task_manager",
        "delete_task": "task_manager",
        "overdue_tasks": "task_manager",
        "search_tasks": "task_manager",
        "recommend": "recommender",
        "plan": "planner"
    }
    
    next_agent = intent_map.get(intent, "task_manager")
    
    return {**state, "intent": intent, "current_agent": next_agent}

# ── Task Manager Agent ─────────────────────────────────
async def task_manager_agent(state: AgentState) -> AgentState:
    """Handles all task CRUD operations"""
    
    # 1. Prevent duplicate task creation during retries
    if state.get("tool_output") and "successfully" in state["tool_output"]:
        return {**state, "current_agent": "reviewer"}
        
    current_date = datetime.now().strftime("%Y-%m-%d (%A)")
    
    # Bind tools to llm
    llm_with_tools = llm.bind_tools(task_manager_tools)
    
    # 2. Inject current_date into the SystemMessage content
    messages = [
        SystemMessage(content=f"""You are a task manager agent.
        Today's date is {current_date}. Use this date as reference for relative days (like 'tomorrow', 'next Friday', etc.).
        Based on the user message, use the appropriate tool to manage tasks.
        Always use a tool to complete the request.
        For dates use YYYY-MM-DD format.
        For priority use: low, medium, or high.
        Rules for determining priority of tasks:

        1. HIGH Priority
        - Due today or overdue.
        - Due within the next 3 days.
        - Tasks containing urgent keywords such as: urgent, asap, immediately, critical, emergency.

        2. MEDIUM Priority
        - Due within the next 4–14 days.
        - Important tasks with a defined deadline but not immediately urgent.

        3. LOW Priority
        - Due more than 14 days away.
        - Optional, someday, learning, research, or backlog tasks without urgency.
        - Tasks with no due date unless the description clearly indicates urgency.

        Instructions:
        - Compare the due date against the current date.
        - Determine urgency primarily from the due date.
        - If both the due date and task description are provided, the due date takes precedence.
        - Set the priority argument of the tool call accordingly.
        
        """),
        HumanMessage(content=state["user_message"])
    ]
    
    response = await llm_with_tools.ainvoke(messages)
    
    # Handle tool calls
    tool_output = ""
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            # Find and execute the tool
            tool_map = {t.name: t for t in task_manager_tools}
            if tool_name in tool_map:
                tool_output = await tool_map[tool_name].ainvoke(tool_args)
    else:
        tool_output = str(response.content) if hasattr(response, 'content') else str(response)
    
    return {**state, "tool_output": tool_output, "current_agent": "reviewer"}

# ── Planner Agent ──────────────────────────────────────
async def planner_agent(state: AgentState) -> AgentState:
    """Breaks complex requests into multiple tasks"""
    
    llm_with_tools = llm.bind_tools(planner_tools)

    current_date = datetime.now().strftime("%Y-%m-%d (%A)")
    
    messages = [
        SystemMessage(content=f"""You are a Task Planning Agent.

        Today's date is {current_date}. Always use this date as the reference when interpreting relative dates such as "today", "tomorrow", "next week", "Friday", "end of month", etc.

        Your responsibilities:

        1. Analyze the user's request.
        2. If the request is complex, break it into multiple actionable tasks.
        3. Each task must:
        - Be clear and specific.
        - Represent a single action whenever possible.
        - Have an appropriate due date.
        - Have a priority: low, medium, or high.
        4. Create every task individually using the create_task tool.
        5. Never combine unrelated actions into one task.

        Priority Rules:
        - HIGH:
        - Due today, overdue, or within the next 3 days.
        - Critical or urgent tasks.
        - MEDIUM:
        - Due within 4–14 days.
        - Important tasks that require planning.
        - LOW:
        - Due more than 14 days away.
        - Learning, research, optional, or backlog tasks.

        Due Date Rules:
        - Convert all relative dates into exact dates.
        - If the user specifies a deadline, use it.
        - If no deadline is provided, infer a reasonable one based on the task complexity.
        - For multi-step projects, distribute deadlines logically across subtasks.

        Task Quality Rules:
        - Tasks must begin with an action verb whenever possible.
        - Avoid vague tasks such as:
        - "Work on project"
        - "Study"
        - "Prepare things"
        - Prefer:
        - "Create project structure"
        - "Research LangGraph documentation"
        - "Implement Telegram bot commands"
        - "Test task creation workflow"

        Before creating tasks:
        - Determine whether the request is simple or complex.
        - If it is simple, create a single task.
        - If it contains multiple goals, milestones, or deliverables, create multiple tasks.

        Use the create_task tool for every task you generate."""),
        HumanMessage(content=state["user_message"])
    ]
    
    response = await llm_with_tools.ainvoke(messages)
    
    tool_output = ""
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            tool_map = {t.name: t for t in planner_tools}
            if tool_name in tool_map:
                result = await tool_map[tool_name].ainvoke(tool_args)
                tool_output += result + "\n"
    else:
        tool_output = str(response.content) if hasattr(response, 'content') else str(response)
    
    return {**state, "tool_output": tool_output, "current_agent": "reviewer"}

# ── Recommender Agent ──────────────────────────────────
async def recommender_agent(state: AgentState) -> AgentState:
    """Provides task recommendations and productivity advice"""
    
    # Get current tasks for context
    current_tasks = await get_tasks.ainvoke({"status": ""})
    overdue = await get_overdue_tasks.ainvoke({})

    current_date = datetime.now().strftime("%Y-%m-%d (%A)")
    
    messages = [
        SystemMessage(content=f"""You are a Productivity Recommendation Agent.

        Today's date is {current_date}. Use this date when reasoning about deadlines, overdue tasks, and upcoming work.

        Current Tasks:
        {current_tasks}

        Overdue Tasks:
        {overdue}

        Your goal is to help the user complete their work efficiently and stay organized.

        Analyze:
        1. Number of active tasks.
        2. Task priorities.
        3. Upcoming deadlines.
        4. Overdue tasks.
        5. Workload balance.
        6. Potential risks (missed deadlines, too many high-priority tasks, task accumulation).

        Provide recommendations that are:
        - Specific
        - Actionable
        - Prioritized
        - Concise

        Guidelines:
        - Overdue tasks should generally be addressed first.
        - Highlight tasks due within the next 3 days.
        - Identify if the user has too many high-priority tasks.
        - Suggest which tasks can be postponed or deprioritized.
        - Recommend a logical order of execution.
        - Point out workload bottlenecks.
        - Encourage breaking large tasks into smaller actionable steps when appropriate.
        - Identify tasks that appear stale, forgotten, or unrealistic.

        Output Structure:

        📊 Productivity Summary
        - Brief overview of current workload.

        🚨 Immediate Attention
        - Tasks requiring urgent action.

        📅 Upcoming Priorities
        - Important tasks due soon.

        ✅ Suggested Plan
        - Recommended order of work for the next few days.

        💡 Productivity Tips
        - 2–3 personalized suggestions based on the user's current task list.

        Rules:
        - Base recommendations only on the provided task data.
        - Never invent tasks.
        - Be practical rather than motivational.
        - Focus on helping the user take action today.
        """),
        HumanMessage(content=state["user_message"])
    ]
    
    response = await llm.ainvoke(messages)
    tool_output = str(response.content) if hasattr(response, 'content') else str(response)
    
    return {**state, "tool_output": tool_output, "current_agent": "reviewer"}

# ── Reviewer Agent ─────────────────────────────────────
async def reviewer_agent(state: AgentState) -> AgentState:
    """Validates agent output and formats final response"""
    
    messages = [
        SystemMessage(content = f"""You are a Reviewer Agent.

        Your job is to review the output produced by another agent or tool before it is shown to the user.

        Responsibilities:
        1. Verify that the output successfully fulfills the user's request.
        2. Check for missing, incomplete, inconsistent, or invalid information.
        3. Validate dates, priorities, task details, and tool results when applicable.
        4. Detect tool failures, empty responses, malformed outputs, or obvious errors.
        5. Format the final response in a clear, user-friendly manner.

        Decision Rules:

        Return APPROVED if:
        - The task was completed successfully.
        - The output is valid and complete.
        - No critical information is missing.
        - The response is safe to present to the user.

        Return NEEDS_RETRY if:
        - A tool failed.
        - Required information is missing.
        - The output is empty or malformed.
        - The result does not satisfy the user's request.
        - Another agent should attempt the task again.

        Output Format:

        If successful:
        APPROVED

        <clean, concise user-facing response>

        If unsuccessful:
        NEEDS_RETRY

        Reason: <brief explanation of what went wrong>

        Review Criteria:
        - Accuracy
        - Completeness
        - Clarity
        - Consistency
        - Correct formatting

        Keep responses concise, professional, and easy to understand.
        Do not invent information that is not present in the tool output.
        """),
        HumanMessage(content=f"""
        User asked: {state['user_message']}
        Tool output: {state['tool_output']}
        Format a clean response for the user.""")
    ]
    
    response = await llm.ainvoke(messages)
    review = str(response.content) if hasattr(response, 'content') else str(response)
    
    if "NEEDS_RETRY" in review.upper():
        status = "retry"
    else:
        status = "approved"
    

    final = review.replace("APPROVED", "").replace("NEEDS_RETRY", "").strip()
    

    if status == "retry":
        return {
            **state,
            "review_status": status,
            "final_response": final,
            "current_agent": "retry",
            "retry_count": state.get("retry_count", 0) + 1
        }
    
    return {**state, "review_status": status, "final_response": final, "current_agent": "done"}


def router(state: AgentState) -> str:
    """Routes to next agent based on current_agent"""
    current = state.get("current_agent", "done")
    
    # Handle retry logic
    if current == "retry":
        retry_count = state.get("retry_count", 0)
        if retry_count >= 2:
            return "done"
        return "task_manager"
    
    return current