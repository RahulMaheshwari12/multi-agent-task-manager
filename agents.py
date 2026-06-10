from langchain_ollama import OllamaLLM
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict
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
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY")
    )
else:
    llm = OllamaLLM(model="llama3.2:3b")

# ── Tools per agent ────────────────────────────────────
task_manager_tools = [create_task, get_tasks, update_task, complete_task, delete_task]
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
def supervisor_agent(state: AgentState) -> AgentState:
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
    
    response = llm.invoke(messages)
    intent = response.strip().lower()
    
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
def task_manager_agent(state: AgentState) -> AgentState:
    """Handles all task CRUD operations"""
    
    # Bind tools to llm
    llm_with_tools = llm.bind_tools(task_manager_tools)
    
    messages = [
        SystemMessage(content="""You are a task manager agent. 
        Based on the user message, use the appropriate tool to manage tasks.
        Always use a tool to complete the request.
        For dates use YYYY-MM-DD format.
        For priority use: low, medium, or high."""),
        HumanMessage(content=state["user_message"])
    ]
    
    response = llm_with_tools.invoke(messages)
    
    # Handle tool calls
    tool_output = ""
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            # Find and execute the tool
            tool_map = {t.name: t for t in task_manager_tools}
            if tool_name in tool_map:
                tool_output = tool_map[tool_name].invoke(tool_args)
    else:
        tool_output = str(response.content) if hasattr(response, 'content') else str(response)
    
    return {**state, "tool_output": tool_output, "current_agent": "reviewer"}

# ── Planner Agent ──────────────────────────────────────
def planner_agent(state: AgentState) -> AgentState:
    """Breaks complex requests into multiple tasks"""
    
    llm_with_tools = llm.bind_tools(planner_tools)
    
    messages = [
        SystemMessage(content="""You are a task planner.
        Break down the user's complex request into multiple smaller tasks.
        Create each task separately using the create_task tool.
        Assign priorities and due dates intelligently."""),
        HumanMessage(content=state["user_message"])
    ]
    
    response = llm_with_tools.invoke(messages)
    
    tool_output = ""
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            tool_map = {t.name: t for t in planner_tools}
            if tool_name in tool_map:
                result = tool_map[tool_name].invoke(tool_args)
                tool_output += result + "\n"
    else:
        tool_output = str(response.content) if hasattr(response, 'content') else str(response)
    
    return {**state, "tool_output": tool_output, "current_agent": "reviewer"}

# ── Recommender Agent ──────────────────────────────────
def recommender_agent(state: AgentState) -> AgentState:
    """Provides task recommendations and productivity advice"""
    
    # Get current tasks for context
    current_tasks = get_tasks.invoke({"status": ""})
    overdue = get_overdue_tasks.invoke({})
    
    messages = [
        SystemMessage(content=f"""You are a productivity recommender agent.
        Current tasks: {current_tasks}
        Overdue tasks: {overdue}
        
        Based on this data, provide intelligent recommendations.
        Be specific and actionable."""),
        HumanMessage(content=state["user_message"])
    ]
    
    response = llm.invoke(messages)
    tool_output = str(response.content) if hasattr(response, 'content') else str(response)
    
    return {**state, "tool_output": tool_output, "current_agent": "reviewer"}

# ── Reviewer Agent ─────────────────────────────────────
def reviewer_agent(state: AgentState) -> AgentState:
    """Validates agent output and formats final response"""
    
    messages = [
        SystemMessage(content="""You are a reviewer agent.
        Review the tool output and format a clean, friendly response for the user.
        If the output looks correct, start with APPROVED.
        If something went wrong, start with NEEDS_RETRY.
        Keep the response concise and clear."""),
        HumanMessage(content=f"""
        User asked: {state['user_message']}
        Tool output: {state['tool_output']}
        Format a clean response for the user.""")
    ]
    
    response = llm.invoke(messages)
    review = str(response.content) if hasattr(response, 'content') else str(response)
    
    if "NEEDS_RETRY" in review.upper():
        status = "retry"
    else:
        status = "approved"
    
    # Clean response — remove APPROVED prefix
    final = review.replace("APPROVED", "").replace("NEEDS_RETRY", "").strip()
    
    return {**state, "review_status": status, "final_response": final, "current_agent": "done"}

# ── Router ─────────────────────────────────────────────
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