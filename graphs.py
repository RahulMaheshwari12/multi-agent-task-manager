from langgraph.graph import StateGraph, END
from agents import (
    AgentState,
    supervisor_agent,
    task_manager_agent,
    planner_agent,
    recommender_agent,
    trip_planner_agent,
    reviewer_agent,
    router
)
from database import init_db

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("task_manager", task_manager_agent)
    graph.add_node("planner", planner_agent)
    graph.add_node("recommender", recommender_agent)
    graph.add_node("trip_planner", trip_planner_agent)
    graph.add_node("reviewer", reviewer_agent)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges("supervisor", router, {
        "task_manager" : "task_manager",
        "planner" : "planner",
        "recommender" : "recommender",
        "trip_planner" : "trip_planner",
        "done" : END
    })

    graph.add_conditional_edges("task_manager", router, {
        "reviewer" : "reviewer",
        "done" : END
    })

    graph.add_conditional_edges("planner", router, {
        "reviewer" : "reviewer",
        "done" : END
    })

    graph.add_conditional_edges("recommender", router, {
        "reviewer": "reviewer",
        "done" : END
    })

    graph.add_conditional_edges("trip_planner", router, {
        "reviewer": "reviewer",
        "done" : END
    })

    graph.add_conditional_edges("reviewer", router, {
        "task_manager": "task_manager",
        "planner": "planner",
        "recommender": "recommender",
        "trip_planner": "trip_planner",
        "done": END
    })

    return graph.compile()

pipeline = build_graph()

async def run_pipeline(user_message: str) -> dict:
    """Main function called by FastAPI"""
    initial_state = {
        "user_message": user_message,
        "intent": "",
        "agent_response": "",
        "tool_output": "",
        "review_status": "",
        "final_response": "",
        "current_agent": "supervisor",
        "retry_count": 0
    }
    result = await pipeline.ainvoke(initial_state)

    return result