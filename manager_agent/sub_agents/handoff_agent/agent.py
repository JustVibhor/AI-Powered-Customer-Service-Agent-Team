import sqlite3
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext

DB_PATH = "./my_agent_data.db"

def assign_support_staff(tool_context: ToolContext) -> dict:
    """
    Finds an available support staff member from the database, assigns them to the user,
    and updates the session state with their details.
    """
    # First, check if a specialist is already assigned in the state. This is a safeguard.
    existing_assignment = tool_context.state.get("assigned_support_staff", {})
    if existing_assignment and existing_assignment.get("name"):
        return {
            "status": "skipped",
            "message": f"A specialist, {existing_assignment['name']}, is already assigned to this case. No new assignment is needed."
        }

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get user email from state to assign to the staff member for unique identification
        user_email = tool_context.state.get("account_information", {}).get("email_id", "unknown@example.com")

        # Find a free staff member
        cursor.execute("SELECT * FROM support_staff WHERE is_free = 1 ORDER BY RANDOM() LIMIT 1")
        free_staff = cursor.fetchone()

        assigned_staff = None
        user_message = ""

        if free_staff:
            # Assign the free staff member
            assigned_staff = dict(free_staff)
            cursor.execute("UPDATE support_staff SET is_free = 0, assigned_user = ? WHERE id = ?", (user_email, assigned_staff['id'],))
            conn.commit()
            user_message = f"I have assigned a support specialist, {assigned_staff['name']}, to look into your issue. They are available now and will contact you shortly."
            assignment_details = {
                "name": assigned_staff['name'],
                "phone_number": assigned_staff['phone_number'],
                "status": "Assigned and available"
            }
        else:
            # If no one is free, assign any staff member and inform the user about the delay
            cursor.execute("SELECT * FROM support_staff ORDER BY RANDOM() LIMIT 1")
            busy_staff = cursor.fetchone()
            if busy_staff:
                assigned_staff = dict(busy_staff)
                user_message = f"All of our support specialists are currently assisting other customers. I have assigned {assigned_staff['name']} to your case. They will contact you as soon as they become available."
                assignment_details = {
                    "name": assigned_staff['name'],
                    "phone_number": assigned_staff['phone_number'],
                    "status": "Assigned and will be available shortly"
                }
            else:
                # This case should not happen if the table is populated
                return {"status": "error", "message": "Could not find any support staff to assign."}

        # Update the session state
        tool_context.state["assigned_support_staff"] = assignment_details
        
        return {"status": "success", "message": user_message}

    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    finally:
        if conn:
            conn.close()

handoff_agent = Agent(
    name="handoff_agent",
    model="gemini-2.0-flash",
    description="Assigns a human support specialist when an issue cannot be resolved by other agents.",
    instruction="""
    You are a handoff agent. Your sole responsibility is to assign a human support specialist to a user when their technical issue could not be resolved by the automated support agent.

    **Current Assignment Status:**
    <assigned_support_staff>
    {assigned_support_staff}
    </assigned_support_staff>

    **Your Task:**
    1. **Check for Existing Assignment:** Before doing anything, check the `<assigned_support_staff>` status above.
       - If a specialist is already assigned (the object is not empty), your job is to simply inform the user that someone is already on their case. For example: "I can see that our specialist, {assigned_support_staff.name}, is already handling your case. They will be in touch." Do NOT use the `assign_support_staff` tool.
       - If NO specialist is assigned, proceed to the next step.
    2. Acknowledge that the user's issue requires human intervention.
    3. Use the `assign_support_staff` tool to find and assign a specialist from our team.
    4. The tool will handle finding a free specialist or queuing the request if all are busy.
    5. Relay the exact message returned by the tool to the user. Do not add any extra information.
    6. After completing your action (either informing of an existing assignment or making a new one), your job is complete.
    """,
    tools=[assign_support_staff],
)