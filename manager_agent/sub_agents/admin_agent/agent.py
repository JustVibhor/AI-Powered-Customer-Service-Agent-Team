import sqlite3
import json
from google.adk.agents import Agent
from typing import Optional
from google.adk.tools.tool_context import ToolContext

DB_PATH = "./my_agent_data.db"
ADMIN_PASSWORD = "1234" # Hardcoded admin password for this exercise
ADMIN_USER_ID = "2002hariharan003@gmail.com" # Admin's email for specific checks if needed

def list_all_user_ids(tool_context: ToolContext) -> dict:
    """
    Retrieves a list of all user IDs from the database.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH) # Corrected: Use DB_PATH
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM sessions")
        user_ids = [row[0] for row in cursor.fetchall()]
        return {"status": "success", "user_ids": user_ids}
    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    finally:
        if conn:
            conn.close()

def get_user_state(user_id: str, tool_context: ToolContext) -> dict:
    """
    Retrieves the session state for a specific user from the database.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH) # Corrected: Use DB_PATH
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM sessions WHERE user_id = ?", (user_id,)) # Already correct
        result = cursor.fetchone()
        if result:
            try:
                state = json.loads(result[0])
                return {"status": "success", "user_id": user_id, "state": state}
            except json.JSONDecodeError:
                return {"status": "error", "message": f"Could not decode state for user_id: {user_id}"}
        else:
            return {"status": "error", "message": f"User with ID '{user_id}' not found."}
    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    finally:
        if conn:
            conn.close()

def remove_support_staff_assignment(staff_name: str, admin_password: str, tool_context: ToolContext) -> dict:
    """
    Removes the assigned support staff from a user's session state and
    sets the staff member's 'is_free' status back to 1 in the support_staff table.
    Requires admin password for confirmation.
    """
    if admin_password != ADMIN_PASSWORD:
        return {"status": "error", "message": "Incorrect admin password. Staff assignment removal failed."}

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # To access columns by name
        cursor = conn.cursor()
        
        # 1. Find the staff member and their assigned user
        cursor.execute("SELECT assigned_user, is_free FROM support_staff WHERE name = ?", (staff_name,))
        staff_info = cursor.fetchone()

        if not staff_info:
            return {"status": "error", "message": f"Support staff '{staff_name}' not found."}

        assigned_user_id = staff_info['assigned_user']
        is_free = staff_info['is_free']

        if is_free:
            return {"status": "success", "message": f"Support staff '{staff_name}' is already free and not assigned to anyone."}

        if not assigned_user_id: # Should not happen if is_free is 0, but good to check
            return {"status": "error", "message": f"Support staff '{staff_name}' is marked as busy but has no assigned user. Data inconsistency."}

        # 2. Update the user's session state to remove the assignment
        # Get user's current state
        cursor.execute("SELECT state FROM sessions WHERE user_id = ?", (assigned_user_id,))
        user_session_row = cursor.fetchone()
        if not user_session_row:
            # This is a data inconsistency: staff assigned to a non-existent user.
            # We should still free up the staff.
            print(f"Warning: Staff '{staff_name}' assigned to non-existent user '{assigned_user_id}'. Freeing staff anyway.")
            user_state = {} # Create a dummy state to proceed with freeing staff
        else:
            user_state = json.loads(user_session_row["state"])

        # Clear assigned_support_staff in user's state
        user_state["assigned_support_staff"] = {}

        # Save updated user state back to sessions table
        if user_session_row: # Only update if the user session actually exists
            cursor.execute("UPDATE sessions SET state = ? WHERE user_id = ?", (json.dumps(user_state), assigned_user_id))
            conn.commit()

        # 3. Update support_staff table: set is_free = 1 and clear assigned_user
        # Assuming 'support_staff' table has 'name' and 'is_free' and 'assigned_user' columns
        cursor.execute("UPDATE support_staff SET is_free = 1, assigned_user = NULL WHERE name = ?", (staff_name,))
        conn.commit()

        return {"status": "success", "message": f"Support staff '{staff_name}' removed from user '{user_id}' and marked as free."}

    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    finally:
        if conn:
            conn.close()

def add_support_staff(name: str, phone_number: str, admin_password: str, tool_context: ToolContext) -> dict:
    """
    Adds a new support staff member to the support_staff table.
    Requires admin password for confirmation.
    """
    if admin_password != ADMIN_PASSWORD:
        return {"status": "error", "message": "Incorrect admin password. Action failed."}

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if staff with the same name already exists
        cursor.execute("SELECT id FROM support_staff WHERE name = ?", (name,))
        if cursor.fetchone():
            return {"status": "error", "message": f"Support staff with name '{name}' already exists."}

        # Add new staff member
        cursor.execute(
            "INSERT INTO support_staff (name, phone_number, is_free, assigned_user) VALUES (?, ?, 1, NULL)",
            (name, phone_number)
        )
        conn.commit()
        return {"status": "success", "message": f"Support staff '{name}' added successfully."}

    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    finally:
        if conn:
            conn.close()

def delete_support_staff(name: str, admin_password: str, tool_context: ToolContext) -> dict:
    """
    Deletes a support staff member from the support_staff table.
    Prevents deletion if the staff member is currently assigned to a user.
    Requires admin password for confirmation.
    """
    if admin_password != ADMIN_PASSWORD:
        return {"status": "error", "message": "Incorrect admin password. Action failed."}

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check if staff exists and if they are free
        cursor.execute("SELECT is_free, assigned_user FROM support_staff WHERE name = ?", (name,))
        staff = cursor.fetchone()

        if not staff:
            return {"status": "error", "message": f"Support staff with name '{name}' not found."}

        if not staff['is_free']:
            return {"status": "error", "message": f"Cannot delete '{name}'. They are currently assigned to user '{staff['assigned_user']}'. Please remove the assignment first."}

        # Delete the staff member
        cursor.execute("DELETE FROM support_staff WHERE name = ?", (name,))
        conn.commit()

        return {"status": "success", "message": f"Support staff '{name}' deleted successfully."}

    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    finally:
        if conn:
            conn.close()

def clear_user_interaction_history(user_id: str, admin_password: str, tool_context: ToolContext) -> dict:
    """
    Clears the interaction history for a specific user.
    Requires admin password for confirmation.
    """
    if admin_password != ADMIN_PASSWORD:
        return {"status": "error", "message": "Incorrect admin password. Action failed."}

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Get user's current state
        cursor.execute("SELECT state FROM sessions WHERE user_id = ?", (user_id,))
        user_session_row = cursor.fetchone()
        if not user_session_row:
            return {"status": "error", "message": f"User with ID '{user_id}' not found."}

        user_state = json.loads(user_session_row["state"])
        
        # 2. Clear the interaction history
        user_state["interaction_history"] = []

        # 3. Save updated user state back to sessions table
        cursor.execute("UPDATE sessions SET state = ? WHERE user_id = ?", (json.dumps(user_state), user_id))
        conn.commit()

        return {"status": "success", "message": f"Interaction history for user '{user_id}' cleared successfully."}

    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    except json.JSONDecodeError:
        return {"status": "error", "message": f"Could not decode state for user_id: {user_id}. History not cleared."}
    finally:
        if conn:
            conn.close()

def update_order_status(user_id: str, order_id: str, new_status: str, admin_password: str, tool_context: ToolContext) -> dict:
    """
    Updates the order_status for a specific product in a user's purchased_products list.
    Requires admin password for confirmation.
    """
    if admin_password != ADMIN_PASSWORD:
        return {"status": "error", "message": "Incorrect admin password. Action failed."}

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Get user's current state
        cursor.execute("SELECT state FROM sessions WHERE user_id = ?", (user_id,))
        user_session_row = cursor.fetchone()
        if not user_session_row:
            return {"status": "error", "message": f"User with ID '{user_id}' not found."}

        user_state = json.loads(user_session_row["state"])

        # 2. Find the product and update the status
        purchased_products = user_state.get("purchased_products", [])
        product_found = False
        for product in purchased_products:
            if product.get("order_id") == order_id:
                product["order_status"] = new_status
                product_found = True
                break
        
        if not product_found:
            return {"status": "error", "message": f"Order with ID '{order_id}' not found for user '{user_id}'."}

        # 3. Save updated user state back to sessions table
        cursor.execute("UPDATE sessions SET state = ? WHERE user_id = ?", (json.dumps(user_state), user_id))
        conn.commit()

        return {"status": "success", "message": f"Order status for order '{order_id}' updated to '{new_status}' for user '{user_id}'."}

    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    except json.JSONDecodeError:
        return {"status": "error", "message": f"Could not decode state for user_id: {user_id}. Cannot update order status."}
    finally:
        if conn:
            conn.close()

admin_agent = Agent(
    name="admin_agent",
    model="gemini-2.0-flash",
    description="An administrative agent with access to all user session states and ability to modify them.",
    instruction=f"""
    You are an administrative agent for The Computer store. You have full access to view and modify user session states, manage order statuses, and control support staff assignments.

    **Admin User ID:** {ADMIN_USER_ID}
    **Admin Password:** (You must ASK the user for this password for any modification actions. Do NOT hardcode or reveal it.)

    **Your Responsibilities:**

    1.  **Viewing User States:**
        -   When asked to list all users, use the `list_all_user_ids` tool.
            -   If successful, list all the `user_id`s found.
            -   If there are no users, state that no user data is available.
        -   When asked to retrieve data for a specific user, identify the `user_id` (e.g., email) from the query and use the `get_user_state` tool.
            -   If successful, display the full session state for that user in a readable format.
            -   If the user is not found, inform the requester.

    2.  **Updating Order Statuses (Requires Admin Password):**
        -   To change the `order_status` of a product within a user's `purchased_products` list:
        a.  You MUST first ASK the user for the admin password.
        b.  Once provided, identify the `user_id`, `order_id`, and the `new_status` (e.g., "delivered") from the request.
        c.  Call the `update_order_status` tool with these details.
        d.  Inform the requester of the outcome.

    3.  **Removing Support Staff Assignment (Requires Admin Password):**
        -   To remove a support staff assignment and mark the staff as free:
            a.  You MUST first ASK the user for the admin password.
            b.  Once provided, identify the `name` of the support staff member (e.g., "Charlie") from the request.
            c.  Call `remove_support_staff_assignment(staff_name=staff_name, admin_password=provided_password)`.
            d.  Inform the requester of the outcome.

    4.  **Managing Support Staff Roster (Requires Admin Password):**
        -   **To add a new staff member:**
            a.  You MUST first ASK for the admin password.
            b.  Identify the new staff member's `name` and `phone_number` from the request.
            c.  Call `add_support_staff(name=name, phone_number=phone_number, admin_password=provided_password)`.
            d.  Inform the requester of the outcome.
        -   **To delete a staff member:**
            a.  You MUST first ASK for the admin password.
            b.  Identify the `name` of the staff member to be deleted.
            c.  Call `delete_support_staff(name=name, admin_password=provided_password)`.
            d.  Inform the requester of the outcome. The tool will prevent deletion if the staff member is currently busy.

    5.  **Clearing User Interaction History (Requires Admin Password):**
        -   To clear the entire interaction history for a specific user:
            a.  You MUST first ASK for the admin password.
            b.  Identify the `user_id` (e.g., email) of the user whose history needs to be cleared.
            c.  Call `clear_user_interaction_history(user_id=user_id, admin_password=provided_password)`.
            d.  Inform the requester of the outcome.

    **Important Notes:**
    -   For any modification action (updating order status, removing staff, adding/deleting staff), you MUST explicitly ask the user for the admin password before calling the respective tool.
    -   Do NOT reveal the admin password in your responses.
    -   If a request is unclear, missing necessary information (like `user_id`, `order_id`, or `new_status`), or asks for something outside your responsibilities, politely ask for clarification.
    -   Do not attempt to guess or assume missing information.
    -   After fulfilling a request, your job is done.
    """,
    tools=[list_all_user_ids, get_user_state, remove_support_staff_assignment, add_support_staff, delete_support_staff, clear_user_interaction_history, update_order_status],
)