from google.genai import types
from datetime import datetime
import os.path
import base64
import email
import json # Import the json module
from email.mime.text import MIMEText # Import MIMEText for creating email messages
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup # Import BeautifulSoup for HTML parsing
from database_utils import process_unprocessed_events, update_user_session

# If modifying these scopes, delete the file token.json.
# 'https://www.googleapis.com/auth/gmail.send' allows sending messages.
# This scope implicitly allows reading headers and subjects for drafts,
# but for full read access, 'gmail.readonly' or 'gmail.modify' would be needed.
# Since the user asked for read and send, gmail.send is sufficient for the sending part.
# For full read and send capability, 'https://www.googleapis.com/auth/gmail.compose' or 'https://www.googleapis.com/auth/gmail.modify' is generally used.
# However, for just sending, 'gmail.send' is less permissive.
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify'] # Added gmail.modify to keep read/unread functionality

# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def parse_sender_info(sender_string: str | None, default_name: str = "Unknown Sender", default_email: str = "unknown@example.com") -> dict:
    """
    Parses a display name and email address from an email sender string.
    Example: "John Doe <john.doe@example.com>" -> {"name": "John Doe", "email": "john.doe@example.com"}
             "jane.doe@example.com" -> {"name": "jane.doe", "email": "jane.doe@example.com"}
    Returns:
        dict: A dictionary with "name" and "email" keys.
    """
    if not sender_string:
        return {"name": default_name, "email": default_email}

    name = default_name
    email = default_email

    try:
        if '<' in sender_string and '>' in sender_string:
            name_part = sender_string.split('<', 1)[0].strip()
            if name_part:
                name = name_part
            email_address_part = sender_string.split('<', 1)[1].split('>', 1)[0].strip()
            if email_address_part:
                email = email_address_part
        elif '@' in sender_string: # Assumes the string is just an email address
            email = sender_string.strip()
            # Attempt to create a name from the email part before @
            name = email.split('@', 1)[0]
        else: # If no < > and no @, treat the whole string as name, email remains default
            name = sender_string.strip()

    except Exception:
        # In case of any parsing error, fall back to default
        pass

    return {"name": name, "email": email}

async def display_state(
    session_service, app_name, user_id, session_id, label="Current State"
):
    """Display the current session state in a formatted way."""
    try:
        session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

        # Format the output with clear sections
        print(f"\n{'-' * 10} {label} {'-' * 10}")

        # Handle the user name
        account_info = session.state.get("account_information", {})
        user_name = account_info.get("user_name", "Unknown")
        email_id = account_info.get("email_id", "N/A")
        phone_no = account_info.get("phone_no", "N/A")
        print(f"👤 User: {user_name} (Email: {email_id}, Phone: {phone_no})")

        # Handle purchased courses
        purchased_products = session.state.get("purchased_products", [])
        if purchased_products and any(purchased_products):
            print("📚 Products:")
            for product in purchased_products:
                if isinstance(product, dict):
                    product_id = product.get("id", "Unknown")
                    purchase_date = product.get("purchase_date", "Unknown date")
                    print(f"  - {product_id} (purchased on {purchase_date})")
                elif product:  # Handle string format for backward compatibility
                    print(f"  - {product}")
        else:
            print("📚 Products: None")

        # Handle interaction history in a more readable way
        interaction_history = session.state.get("interaction_history", [])
        if interaction_history:
            print("📝 Interaction History:")
            for idx, interaction in enumerate(interaction_history, 1):
                # Pretty format dict entries, or just show strings
                if isinstance(interaction, dict):
                    action = interaction.get("action", "interaction")
                    timestamp = interaction.get("timestamp", "unknown time")

                    if action == "user_query":
                        query = interaction.get("query", "")
                        print(f'  {idx}. User query at {timestamp}: "{query}"')
                    elif action == "agent_response":
                        agent = interaction.get("agent", "unknown")
                        response = interaction.get("response", "")
                        # Truncate very long responses for display
                        if len(response) > 100:
                            response = response[:97] + "..."
                        print(f'  {idx}. {agent} response at {timestamp}: "{response}"')
                    else:
                        details = ", ".join(
                            f"{k}: {v}"
                            for k, v in interaction.items()
                            if k not in ["action", "timestamp"]
                        )
                        print(
                            f"  {idx}. {action} at {timestamp}"
                            + (f" ({details})" if details else "")
                        )
                else:
                    print(f"  {idx}. {interaction}")
        else:
            print("📝 Interaction History: None")

        # Handle assigned support staff
        assigned_staff = session.state.get("assigned_support_staff", {})
        if assigned_staff:
            print("🤝 Assigned Support:")
            staff_name = assigned_staff.get("name", "N/A")
            staff_status = assigned_staff.get("status", "N/A")
            print(f"  - Specialist: {staff_name} ({staff_status})")
        else:
            print("🤝 Assigned Support: None")

        # Handle pending tasks
        pending_tasks = session.state.get("pending_tasks", [])
        if pending_tasks:
            print("⏳ Pending Tasks:")
            for task in pending_tasks:
                print(f"  - {task.get('description', 'No description')}")
        else:
            print("⏳ Pending Tasks: None")

        # Show any additional state keys that might exist
        other_keys = [
            k
            for k in session.state.keys()
            if k not in ["account_information", "purchased_products", "interaction_history", "assigned_support_staff", "pending_tasks"]
        ]
        if other_keys:
            print("🔑 Additional State:")
            for key in other_keys:
                print(f"  {key}: {session.state[key]}")

        print("-" * (22 + len(label)))
    except Exception as e:
        print(f"Error displaying state: {e}")


async def process_agent_response(event):
    """Process and display agent response events."""
    # Log basic event info
    print(f"Event ID: {event.id}, Author: {event.author}")

    # Check for specific parts first
    has_specific_part = False
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "executable_code") and part.executable_code:
                # Access the actual code string via .code
                print(
                    f"  Debug: Agent generated code:\n```python\n{part.executable_code.code}\n```"
                )
                has_specific_part = True
            elif hasattr(part, "code_execution_result") and part.code_execution_result:
                # Access outcome and output correctly
                print(
                    f"  Debug: Code Execution Result: {part.code_execution_result.outcome} - Output:\n{part.code_execution_result.output}"
                )
                has_specific_part = True
            elif hasattr(part, "tool_response") and part.tool_response:
                # Print tool response information
                print(f"  Tool Response: {part.tool_response.output}")
                has_specific_part = True
            # Also print any text parts found in any event for debugging
            elif hasattr(part, "text") and part.text and not part.text.isspace():
                print(f"  Text: '{part.text.strip()}'")

    # Check for final response after specific parts
    final_response = None
    if event.is_final_response():
        if (
            event.content
            and event.content.parts
            and hasattr(event.content.parts[0], "text")
            and event.content.parts[0].text
        ):
            final_response = event.content.parts[0].text.strip()
            # Use colors and formatting to make the final response stand out
            print(
                f"\n{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╔══ AGENT RESPONSE ═════════════════════════════════════════{Colors.RESET}"
            )
            print(f"{Colors.CYAN}{Colors.BOLD}{final_response}{Colors.RESET}")
            print(
                f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╚═════════════════════════════════════════════════════════════{Colors.RESET}\n"
            )
        else:
            print(
                f"\n{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD}==> Final Agent Response: [No text content in final event]{Colors.RESET}\n"
            )

    return final_response


async def call_agent_async(runner, user_id, session_id, query):
    """Call the agent asynchronously with the user's query."""
    content = types.Content(role="user", parts=[types.Part(text=query)])
    print(
        f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}--- Running Query: {query} ---{Colors.RESET}"
    )
    final_response_text = None
    agent_name = None

    # Display state before processing
    await display_state(
        runner.session_service,
        runner.app_name,
        user_id,
        session_id,
        "State BEFORE processing",
    )

    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            # Capture the agent name from the event if available
            if event.author:
                agent_name = event.author

            response = await process_agent_response(event)
            if response:
                final_response_text = response
    except Exception as e:
        print(f"{Colors.BG_RED}{Colors.WHITE}ERROR during agent run: {e}{Colors.RESET}")
    
    # Configuration
    database_file = 'my_agent_data.db'
    events_table = 'events'
    sessions_table = 'sessions'

    # Step 1: Process unprocessed events
    print("--- Starting Event Processing ---")
    # process_unprocessed_events now returns a dictionary: {user_id: [interactions]}
    all_new_user_interactions = process_unprocessed_events(database_file, events_table)

    # Step 2: Update user sessions with their respective new interactions
    if all_new_user_interactions:
        print(f"\n--- Starting Session Updates for {len(all_new_user_interactions)} user(s) ---")
        for user_id, new_interactions_for_user in all_new_user_interactions.items():
            if new_interactions_for_user: # Ensure there's actually history to append
                update_user_session(database_file, sessions_table, user_id, new_interactions_for_user)
            else:
                print(f"No new interactions to append for user_id: {user_id}, skipping session update for this user.")
    else:
        print("\nNo new user interactions found in events, skipping all session updates.")
    
    print("\n--- Database processing finished ---")

    # Display state after processing the message
    await display_state(
        runner.session_service,
        runner.app_name,
        user_id,
        session_id,
        "State AFTER processing",
    )

    return final_response_text

def authenticate_gmail_api():
    """
    Authenticates with the Gmail API, handling OAuth 2.0 flow.
    It checks for an existing token.json, refreshes it if needed,
    or performs a new authentication flow.
    Returns:
        google.oauth2.credentials.Credentials: Authenticated credentials.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token...")
            try:
                # Ensure the flow is initialized with the correct scopes for refresh
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds.refresh(flow.credentials)
            except Exception as e:
                print(f"Error refreshing token: {e}. Please re-authenticate.")
                # Fallback to new flow if refresh fails
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            print("No valid token found. Initiating new authentication flow...")
            # Use 'credentials.json' downloaded from Google Cloud Console
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_message_content(service, msg_id):
    """
    Retrieves and decodes the full content of a specific email message,
    and extracts sender, receiver, subject, and message body.
    Args:
        service: Authenticated Gmail API service object.
        msg_id (str): The ID of the message to retrieve.
    Returns:
        dict: A dictionary containing 'sender_email', 'receiver_email', 'subject', and 'message_body',
              or None if an error occurs or content cannot be extracted.
    """
    try:
        msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        
        # Initialize variables for email details
        sender_email = 'N/A'
        receiver_email = 'N/A'
        subject = 'N/A'
        email_body_plain = "" # Changed to accumulate plain text only

        # Extract headers
        headers = msg['payload']['headers']
        for h in headers:
            if h['name'] == 'From':
                sender_email = h['value']
            elif h['name'] == 'To':
                receiver_email = h['value']
            elif h['name'] == 'Subject':
                subject = h['value']
        
        # Decode the message payload
        payload = msg['payload']
        parts = payload.get('parts', [])

        # Helper to extract plain text from parts, prioritizing plain over HTML
        def find_and_decode_text_part(parts_list):
            plain_text = ""
            html_text = ""

            for part in parts_list:
                mime_type = part.get('mimeType')
                if 'data' in part['body']:
                    data = part['body']['data']
                    decoded_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    if mime_type == 'text/plain':
                        plain_text += decoded_data + "\n" # Accumulate all plain text parts
                    elif mime_type == 'text/html':
                        html_text += decoded_data + "\n" # Accumulate all HTML parts
                elif 'parts' in part:
                    # Recursively search in nested parts
                    nested_plain, nested_html = find_and_decode_text_part(part['parts'])
                    plain_text += nested_plain
                    html_text += nested_html
            return plain_text, html_text

        # First, try to get plain text from the parts
        extracted_plain_from_parts, extracted_html_from_parts = find_and_decode_text_part(parts)
        
        if extracted_plain_from_parts:
            email_body_plain = extracted_plain_from_parts
        elif extracted_html_from_parts:
            # If only HTML parts are found, strip HTML to get plain text
            soup = BeautifulSoup(extracted_html_from_parts, 'html.parser')
            email_body_plain = soup.get_text(separator='\n') # Get text with newlines for better readability
        
        # Fallback for simpler messages if body is not extracted from parts, but raw exists
        if not email_body_plain and 'raw' in msg:
            raw_msg = base64.urlsafe_b64decode(msg['raw']).decode('utf-8', errors='ignore')
            parsed_email = email.message_from_string(raw_msg)
            
            raw_plain_text = ""
            raw_html_text = ""

            for part in parsed_email.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))

                if 'attachment' not in cdispo: # Ignore attachments
                    if ctype == 'text/plain':
                        raw_plain_text += part.get_payload(decode=True).decode('utf-8', errors='ignore') + "\n"
                    elif ctype == 'text/html':
                        raw_html_text += part.get_payload(decode=True).decode('utf-8', errors='ignore') + "\n"
            
            if raw_plain_text:
                email_body_plain = raw_plain_text
            elif raw_html_text:
                # If only raw HTML is found, strip it
                soup = BeautifulSoup(raw_html_text, 'html.parser')
                email_body_plain = soup.get_text(separator='\n')

        email_data = {
            "sender_email": sender_email,
            "receiver_email": receiver_email,
            "subject": subject,
            "message_body": email_body_plain.strip() # Remove leading/trailing whitespace
        }
        return email_data

    except HttpError as error:
        print(f'An HTTP error occurred: {error}')
        return None
    except Exception as e:
        print(f"An error occurred during message content extraction: {e}")
        return None

def mark_message_as_read(service, msg_id):
    """
    Marks a specific message as read by removing the 'UNREAD' label.
    Args:
        service: Authenticated Gmail API service object.
        msg_id (str): The ID of the message to mark as read.
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        print(f"Message {msg_id} marked as read.")
        return True
    except HttpError as error:
        print(f'An HTTP error occurred when marking as read: {error}')
        return False
    except Exception as e:
        print(f"An error occurred while marking message as read: {e}")
        return False

def create_message_and_send(service, sender_email, to_email, subject, message_text):
    """
    Creates an email message and sends it.
    Args:
        service: Authenticated Gmail API service object.
        sender_email (str): The email address of the sender ('me' is recommended).
        to_email (str): The email address of the recipient.
        subject (str): The subject of the email.
        message_text (str): The plain text content of the email.
    Returns:
        dict: The sent message object if successful, None otherwise.
    """
    try:
        message = MIMEText(message_text)
        message['to'] = to_email
        message['from'] = sender_email # Use 'me' for the authenticated user
        message['subject'] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        print(f"\nEmail sent successfully! Message ID: {sent_message['id']}")
        return sent_message
    except HttpError as error:
        print(f'An HTTP error occurred while sending email: {error}')
        return None
    except Exception as e:
        print(f"An error occurred while creating/sending message: {e}")
        return None