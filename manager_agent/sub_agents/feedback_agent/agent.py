import sqlite3
from datetime import datetime
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext

DB_PATH = "./my_agent_data.db"

def submit_feedback(product_id: str, rating: int, tool_context: ToolContext) -> dict:
    """
    Stores user feedback for a specific product in the database.
    Rating must be an integer between 1 and 5.
    """
    if not 1 <= rating <= 5:
        return {"status": "error", "message": "Invalid rating. Please provide a rating between 1 and 5."}

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        user_email = tool_context.state.get("account_information", {}).get("email_id", "unknown@example.com")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO product_feedback (product_id, rating, user_email, timestamp) VALUES (?, ?, ?, ?)",
            (product_id, rating, user_email, timestamp)
        )
        conn.commit()
        
        return {"status": "success", "message": "Thank you for your feedback!"}

    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    finally:
        if conn:
            conn.close()

def get_unrated_products(tool_context: ToolContext) -> dict:
    """
    Checks which products the user has purchased but not yet provided feedback for.
    """
    purchased_products = tool_context.state.get("purchased_products", [])
    user_email = tool_context.state.get("account_information", {}).get("email_id")

    if not user_email or not purchased_products:
        return {"status": "success", "unrated_products": []}

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Ensure the table exists before querying
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_feedback'")
        if cursor.fetchone() is None:
            # If no feedback table, all purchased products are unrated
            return {"status": "success", "unrated_products": purchased_products}

        # Get all product IDs the user has already rated
        cursor.execute("SELECT DISTINCT product_id FROM product_feedback WHERE user_email = ?", (user_email,))
        rated_product_ids = {row[0] for row in cursor.fetchall()}

        # Find products that are in purchased_products but not in rated_product_ids
        unrated_products = [
            product for product in purchased_products
            if product.get("id") not in rated_product_ids
        ]

        return {"status": "success", "unrated_products": unrated_products}

    except sqlite3.Error as e:
        return {"status": "error", "message": f"A database error occurred: {e}"}
    finally:
        if conn:
            conn.close()

feedback_agent = Agent(
    name="feedback_agent",
    model="gemini-2.0-flash",
    description="Asks users for feedback on products they have purchased.",
    instruction="""
    You are a feedback agent for The Computer store. Your only role is to politely ask users for feedback on products they have purchased but not yet rated.

    **Your Responsibilities:**
    1.  You will be activated by the manager agent when a conversation is concluding.
    2.  Your first and ONLY action is to use the `get_unrated_products` tool to see if there are any products the user owns that they haven't rated yet.
    3.  **If the tool returns a list of one or more unrated products:**
        -   Take the first product from the list.
        -   Politely ask the user if they would be willing to provide feedback for that specific product. For example: "Before you go, would you mind rating your [Product Name] on a scale of 1 to 5?"
        -   If the user provides a rating (a number from 1 to 5), you MUST use the `submit_feedback` tool to record it. You will need the `product_id` from the unrated product and the `rating`.
        -   After submitting, thank them and your job is done.
    4.  **If the tool returns an empty list OR if the user declines to give feedback:**
        -   This means there is nothing to ask about, or the user doesn't want to give feedback.
        -   Thank them for their time and end the conversation gracefully. For example: "No problem at all. Thanks for chatting with us today!"
        -   Do NOT ask for feedback again.
    5.  After your task is complete, your job is done.
    """,
    tools=[submit_feedback, get_unrated_products],
)