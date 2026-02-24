from google.adk.tools.tool_context import ToolContext


def add_pending_task(
    task_description: str,
    target_agent: str,
    task_type: str,
    context: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Adds a pending task to the session state to be addressed later.
    This is used when a user's request is interrupted by a required action, like account setup.
    """
    pending_tasks = tool_context.state.get("pending_tasks", [])
    new_task = {
        "description": task_description,
        "target_agent": target_agent,
        "type": task_type,
        "context": context,
    }
    pending_tasks.append(new_task)
    tool_context.state["pending_tasks"] = pending_tasks
    return {
        "status": "success",
        "message": f"Pending task '{task_description}' has been added.",
    }


def remove_pending_task(
    task_type: str,
    context_key: str,
    context_value: str,
    tool_context: ToolContext,
) -> dict:
    """
    Removes a specific pending task from the session state.
    Tasks are identified by their type and a key-value pair within their context.
    """
    pending_tasks = tool_context.state.get("pending_tasks", [])
    remaining_tasks = [
        task for task in pending_tasks
        if not (task.get("type") == task_type and task.get("context", {}).get(context_key) == context_value)
    ]
    tool_context.state["pending_tasks"] = remaining_tasks
    return {"status": "success", "message": f"Pending task of type '{task_type}' with {context_key}='{context_value}' has been removed."}