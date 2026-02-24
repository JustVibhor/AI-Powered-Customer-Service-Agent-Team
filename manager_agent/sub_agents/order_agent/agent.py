from datetime import datetime, timedelta
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext


def cancel_order(order_id: str, tool_context: ToolContext) -> dict:
    """Cancels an order if it has not been delivered yet."""
    purchased_products = tool_context.state.get("purchased_products", [])
    order_to_cancel = None
    for product in purchased_products:
        if product.get("order_id") == order_id:
            order_to_cancel = product
            break

    if not order_to_cancel:
        return {"status": "error", "message": f"Order with ID '{order_id}' not found."}

    if order_to_cancel.get("order_status") == "delivered":
        return {"status": "error", "message": "This order has already been delivered and cannot be cancelled."}

    # Remove the order
    remaining_products = [p for p in purchased_products if p.get("order_id") != order_id]
    tool_context.state["purchased_products"] = remaining_products

    return {"status": "success", "message": f"Order {order_id} has been successfully cancelled."}


def return_or_exchange_product(order_id: str, tool_context: ToolContext) -> dict:
    """Processes a return or exchange for a product within 30 days of purchase."""
    purchased_products = tool_context.state.get("purchased_products", [])
    order_to_return = None
    for product in purchased_products:
        if product.get("order_id") == order_id:
            order_to_return = product
            break

    if not order_to_return:
        return {"status": "error", "message": f"Order with ID '{order_id}' not found."}

    purchase_date_str = order_to_return.get("purchase_date")
    try:
        purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() > purchase_date + timedelta(days=30):
            return {"status": "error", "message": "This product is outside the 30-day return/exchange window."}
    except (ValueError, TypeError):
        return {"status": "error", "message": "Could not parse the purchase date for this order."}

    # Remove the order to simulate return/exchange
    remaining_products = [p for p in purchased_products if p.get("order_id") != order_id]
    tool_context.state["purchased_products"] = remaining_products

    return {"status": "success", "message": f"Your return/exchange for order {order_id} has been processed."}


order_agent = Agent(
    name="order_agent",
    model="gemini-2.0-flash",
    description="Handles user queries about order status, cancellations, returns, and exchanges.",
    instruction="""
    You are an order management agent for The Computer store. Your role is to help users with questions about their orders, including status, cancellations, returns, and exchanges.

    **User Account Information:**
    <user_info>
    Name: {account_information.user_name}
    Email: {account_information.email_id}
    </user_info>

    **Purchased Products Information:**
    <purchased_products_list>
    {purchased_products}
    </purchased_products_list>
    
    **Your Responsibilities:**

    1.  **Order Status and Delivery Date:**
        -   When a user asks for their order status, find the relevant order in the `<purchased_products_list>` by matching the `order_id` the user provides.
        -   From that product's entry in the `purchased_products` context, get the `purchase_date` and `order_status`.
        -   **Delivery is expected 2 days after the `purchase_date`.** You must calculate this.
        -   If the current date is 2 or more days after the `purchase_date`, you should consider the item "delivered".
        -   Inform the user with a clear message. For example: "Your order [the order ID you found] was delivered on [the calculated delivery date]."
        -   If it's not yet 2 days past the purchase date, inform them it's "dispatched" and provide the expected delivery date. For example: "Your order [the order ID you found] has been dispatched and is expected to be delivered by [the calculated delivery date]."

    2.  **Order Cancellation:**
        -   A user can cancel an order **only if it has not been delivered yet**.
        -   An order is considered delivered if its status is 'delivered' OR if it's 2 or more days past the purchase date (which you must check from the `<purchased_products_list>`).
        -   If the user wants to cancel an eligible order, ask for the `order_id` and then use the `cancel_order` tool.
        -   If an order is not eligible for cancellation, politely explain why (e.g., "I'm sorry, but this order has already been delivered and cannot be cancelled.").

    3.  **Product Returns and Exchanges:**
        -   A user can return or exchange a product within **30 days of the `purchase_date`**.
        -   To check this, find the order in `<purchased_products_list>` using the order ID and get its `purchase_date`.
        -   If they are eligible, ask for the `order_id` and use the `return_or_exchange_product` tool.
        -   If the 30-day window has passed, you MUST politely inform them that the return/exchange period is over. For example: "I'm sorry, but the 30-day period for returns and exchanges for order [the order ID you identified] has passed."

    **Interaction Flow:**

    -   **If a user asks about an order:**
        -   First, check if they have any purchased products. If not, inform them they have no orders.
        -   If they have orders, but don't provide an `order_id`, and they have multiple orders, list the recent orders with their product ID and order ID, and ask which one they're asking about.
        -   If they provide an `order_id`, use it to find the order details within the `<purchased_products_list>`.

    -   **Always be clear and helpful.** Use the `order_id` you find in your responses to avoid confusion, especially if the user has purchased the same product multiple times.

    **Conversation Handoff:**
    - When you have successfully answered the user's question or completed a task (like a cancellation or return), and the user indicates they are finished (e.g., "thanks", "that's all"), you MUST delegate back to the `manager_agent`.
    - Do not provide a final closing statement. This allows the manager to initiate the feedback process.
    """,
    tools=[cancel_order, return_or_exchange_product],
)