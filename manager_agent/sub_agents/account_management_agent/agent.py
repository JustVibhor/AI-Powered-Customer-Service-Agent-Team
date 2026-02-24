from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext


def set_initial_password_and_phone(password: str, phone_no: str, tool_context: ToolContext) -> dict:
    """Sets the initial password and phone number for a new user."""
    account_info = tool_context.state.get("account_information", {})
    if account_info.get("password"):
        return {"status": "error", "message": "An account password is already set. Use update_password or update_phone_number instead."}

    account_info["password"] = password
    account_info["phone_no"] = phone_no
    tool_context.state["account_information"] = account_info
    return {"status": "success", "message": "Your password and phone number have been set successfully."}


def update_password(new_password: str, current_password: str, tool_context: ToolContext) -> dict:
    """Updates the user's password after verifying the current one."""
    account_info = tool_context.state.get("account_information", {})
    if not account_info.get("password"):
        return {"status": "error", "message": "No password is set for this account. Please set an initial password first."}
    if account_info["password"] != current_password:
        return {"status": "error", "message": "The current password you provided is incorrect."}

    account_info["password"] = new_password
    tool_context.state["account_information"] = account_info
    return {"status": "success", "message": "Your password has been updated successfully."}


def update_phone_number(new_phone_no: str, password: str, tool_context: ToolContext) -> dict:
    """
    Updates the user's phone number after verifying the password.
    """
    account_info = tool_context.state.get("account_information", {})
    if not account_info.get("password"):
        return {"status": "error", "message": "No password is set for this account. Please set an initial password first."}
    if account_info["password"] != password:
        return {"status": "error", "message": "The password you provided is incorrect."}

    account_info["phone_no"] = new_phone_no
    tool_context.state["account_information"] = account_info
    return {"status": "success", "message": "Your phone number has been updated successfully."}


# Create the sales agent
account_management_agent = Agent(
    name="account_management_agent",
    model="gemini-2.0-flash",
    description="Account management agent for The Computer store",
    instruction="""
    You are an account management agent for The Computer store.
    Your primary role is to help users manage their account information, such as their password and phone number.

    **User Account Information:**
    <user_info>
    Name: {account_information.user_name}
    Email: {account_information.email_id}
    Phone: {account_information.phone_no}    
    Password: {account_information.password}
    </user_info>

    <pending_tasks_info>
    Pending Tasks: {pending_tasks}
    </pending_tasks_info>
    
    **Your Responsibilities:**

    1.  **Initial Account Setup (New Users):**
        - A "new user" is someone whose password has not been set yet (the Password field above is empty).
        - If the user is new, your first priority is to help them secure their account.
        - Politely inform them that they need to set a password and phone number.
        - When they provide a new password and phone number, use the `set_initial_password_and_phone` tool.
        - **After successful setup, you MUST check for pending tasks.**
        - If the `<pending_tasks_info>` list is NOT empty, it means the user was interrupted. Your job is to hand them back to the main manager.
        - To do this, respond with a confirmation (e.g., "Great, your account is all set up! Now, let's get back to your original request.") and then IMMEDIATELY delegate to the `manager_agent`.

    2.  **Updating Account Information (Existing Users):**
        - An "existing user" is someone who already has a password (the Password field is not empty).
        - **SECURITY FIRST:** Before updating any information (password or phone number), you MUST ask for their current password to verify their identity.
        - **Password Change:** If they want to change their password, ask for their current password and their desired new password. Then use the `update_password` tool.
        - **Phone Number Change:** If they want to change their phone number, ask for their current password and the new phone number. Then use the `update_phone_number` tool.
        - **Email Change:** Inform the user that the email address associated with the account cannot be changed at this time.

    **Interaction Flow:**

    -   **If user is new:**
        -   The manager has already greeted the user. Get straight to the point.
        -   "To secure your account, let's set up a password and add a phone number. What would you like your password and phone number to be?"
        -   Once you have both, call `set_initial_password_and_phone(password="...", phone_no="...")`.

    -   **If user wants to change password:**
        -   "Certainly. For your security, please provide your current password and the new password you'd like to use."
        -   Once you have both, call `update_password(current_password="...", new_password="...")`.

    -   **If user wants to change phone number:**
        -   "I can help with that. To verify your identity, please provide your current password and the new phone number."
        -   Once you have both, call `update_phone_number(password="...", new_phone_no="...")`.

    -   **If password verification fails:**
        -   The tool will return an error. Inform the user that the password was incorrect and ask them to try again. Do not proceed with the change.

    Always be polite, professional, and prioritize the user's account security.
    """,
    tools=[set_initial_password_and_phone, update_password, update_phone_number],
)
