from utils import authenticate_gmail_api, get_message_content, create_message_and_send, mark_message_as_read, call_agent_async, parse_sender_info
import json
from database_utils import create_and_populate_support_staff_table
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Agent devevlopment kit includes
import asyncio
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from manager_agent.agent import manager_agent

load_dotenv()

# ===== PART 1: Initialize Persistent Session Service =====
# Using SQLite database for persistent storage
DB_PATH = "./my_agent_data.db"
db_url = f"sqlite:///{DB_PATH}"
session_service = DatabaseSessionService(db_url=db_url)


async def main_async():
    # Setup constants

    # Create support staff table on startup if it doesn't exist
    create_and_populate_support_staff_table(DB_PATH)

    APP_NAME = "Customer Service Agent"
    USER_ID = "Hariharan"
    # ===== PART 1: Authenticate Gmail API and Reading the Gmail=====
    try:
        creds = authenticate_gmail_api()
        service = build('gmail', 'v1', credentials=creds)
        while True:
            try:
                # Fetch unread messages
                results = service.users().messages().list(userId='me', q='is:unread').execute()
                messages = results.get('messages', [])

                if not messages:
                    #print('\nNo unread messages found.')
                    continue

                print(f'\nFound {len(messages)} unread email(s). Processing one by one:')
                print('----------------------------------------------------')
                
                for i, message in enumerate(messages):
                    msg_id = message['id']
                    print(f"\n--- Processing Unread Email {i + 1}/{len(messages)} ---")
                    
                    # Get email content
                    email_data = get_message_content(service, msg_id)
                    if email_data:
                        # Print all extracted data (optional)
                        print(json.dumps(email_data, indent=4))
                        
                        # Specifically access and print the sender's email ID
                        sender_id_str = email_data.get('sender_email')
                        email_subject = email_data.get('subject', 'No Subject')
                        email_body = email_data.get('message_body', 'No Body')
                        print(f"Sender Email ID: {sender_id_str}")
                        print(f"Email Subject: {email_subject}")
                        print(f"Email Body: {email_body}")
                        sender_info_dict = parse_sender_info(sender_id_str)
                        print(f"Parsed Sender Info: {sender_info_dict}")
                        USER_ID = sender_info_dict['email']
                        print(f"Using User ID: {USER_ID}")
                        
                        # ===== Mark the message as read =====
                        mark_message_as_read(service, msg_id)

                        # ===== PART 2: Define Initial State =====
                        # This will only be used when creating a new session
                        initial_state = {
                            "account_information": {
                                "user_name": sender_info_dict['name'],
                                "password": "",  # Not available from email
                                "email_id": sender_info_dict['email'],
                                "phone_no": ""  # Not available from email
                            },
                            "purchased_products": [],
                            "interaction_history": [],
                            "assigned_support_staff": {},
                            "pending_tasks": [],
                        }

                        # ===== PART 3: Session Management - Find or Create =====
                        # Check for existing sessions for this user
                        existing_sessions_response = await session_service.list_sessions(
                            app_name=APP_NAME,
                            user_id=USER_ID,
                        )

                        # If there's an existing session, use it, otherwise create a new one
                        if existing_sessions_response and len(existing_sessions_response.sessions) > 0:
                            # Use the most recent session
                            SESSION_ID = existing_sessions_response.sessions[0].id
                            print(f"Continuing existing session: {SESSION_ID}")
                        else:
                            # Create a new session with initial state
                            new_session = await session_service.create_session(
                                app_name=APP_NAME,
                                user_id=USER_ID,
                                state=initial_state,
                            )
                            SESSION_ID = new_session.id
                            print(f"Created new session: {SESSION_ID}")
                        # ===== PART 4: Agent Runner Setup =====
                        # Create a runner with the memory agent
                        runner = Runner(
                            agent=manager_agent,
                            app_name=APP_NAME,
                            session_service=session_service,
                        )
                        # ===== PART 5: Interactive Conversation Loop =====
                        print("\nWelcome to Customer Service Agent!")

                        final_response = await call_agent_async(runner, USER_ID, SESSION_ID, email_body)

                        if final_response:
                            create_message_and_send(
                                service=service,
                                sender_email='me', # The authenticated user sends the reply
                                to_email=USER_ID, # Send back to the original sender
                                subject=email_subject,
                                message_text=final_response
                            )
                        else:
                            print("No response generated by the agent.")
                    else:
                        print(f"Failed to retrieve content for message ID: {msg_id}")
                        continue
            except HttpError as error:
                print(f'An HTTP error occurred: {error}')
            except Exception as e:
                print(f"An overall error occurred during unread email processing: {e}")
    except HttpError as error:
        print(f'An HTTP error occurred: {error}')
    except Exception as e:
        print(f"An overall error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main_async())
