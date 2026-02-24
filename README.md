# AI-Powered Customer Service Agent Team

> A sophisticated, multi-agent customer service system built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/). The system monitors a Gmail inbox, interprets user intent, and routes requests to a team of specialized AI agents — each purpose-built to handle a specific aspect of customer service.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Installation](#installation)
- [Gmail OAuth Setup](#gmail-oauth-setup)
- [Agent Reference](#agent-reference)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Architecture Overview

The system follows a **hierarchical multi-agent model** orchestrated by a central Manager Agent.

```
Incoming Email
      │
      ▼
 Email Monitor (main.py)
      │
      ▼
Session Manager (SQLite)
      │
      ▼
 Manager Agent ──────────────────────────────────────────────────────────┐
      │                                                                   │
      ├──► Admin Agent          (admin queries only)                      │
      ├──► Account Agent        (registration, password, phone)           │
      ├──► Sales Agent          (catalog, pricing, purchases)             │
      ├──► Order Agent          (status, cancellation, returns)           │
      ├──► Support Agent        (troubleshooting, escalation)             │
      ├──► Feedback Agent       (ratings collection)                      │
      └──► Handoff Agent        (human specialist assignment)  ◄──────────┘
```

**Flow summary:**

1. `main.py` continuously polls the connected Gmail inbox for unread messages.
2. Each email triggers a session lookup or creation in a local SQLite database (`my_agent_data.db`), preserving full interaction history.
3. The **Manager Agent** analyzes the query and delegates to the appropriate sub-agent.
4. The sub-agent executes its task using dedicated tools and database access.
5. All state changes are persisted back to the user's session.

---

## Installation

**Prerequisites:** [Conda](https://docs.conda.io/en/latest/) must be installed.

```bash
# 1. Clone the repository
git clone https://github.com/Hariharan0309/customer-service-agent-adk.git
cd customer-service-agent-adk

# 2. Create and activate the environment
conda env create -f environment.yml
conda activate customer-service-agent

# 3. Run the application
python main.py
```

Once running, the application will monitor the configured Gmail account and process incoming emails automatically.

---

## Gmail OAuth Setup

The application reads and responds to emails via the **Gmail API**. Follow these steps to generate your `credentials.json` file:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services → Library**, search for **Gmail API**, and click **Enable**.
4. Go to **APIs & Services → Credentials** and click **+ CREATE CREDENTIALS → OAuth client ID**.
   - If prompted, configure the **OAuth consent screen** first:
     - Select **External** user type.
     - Fill in the required fields (app name, support email, etc.) and save.
5. On the OAuth Client ID page:
   - Set **Application type** to **Desktop App**.
   - Name it (e.g., `Customer Service Agent`) and click **Create**.
6. Download the JSON file from the confirmation modal.
7. Rename it to `credentials.json` and place it in the **root directory** of the project.

---

## Agent Reference

### 🧭 Manager Agent
The central router of the system. Does not respond to users directly — instead, it analyzes every incoming query and delegates to the correct sub-agent based on a strict routing policy. Handles admin verification, new user onboarding checks, and pending task resolution.

---

### 🔐 Admin Agent
Activated exclusively for queries originating from the designated admin email address. All write operations require an admin password.

**Capabilities:**
- View all users and their complete session state
- Update order statuses (e.g., `dispatched` → `delivered`)
- Add or remove support staff members
- Clear a user's staff assignment after issue resolution
- Clear a user's interaction history

---

### 👤 Account Management Agent
Handles all user account lifecycle operations.

**Capabilities:**
- Guide new users through initial password and phone number setup
- Allow existing users to update credentials after identity verification

---

### 🛒 Sales Agent
Manages the product catalog and purchase flow.

**Capabilities:**
- Provide detailed product information including pricing and value proposition
- Surface average user ratings before purchase to aid decision-making
- Process purchases and generate unique `order_id` values per transaction
- Handle edge cases such as re-purchasing an already-owned product
- Store pending purchase requests for new users completing account setup

---

### 📦 Order Agent
Manages all post-purchase order inquiries.

**Capabilities:**
- Report current order status (`dispatched` or `delivered`)
- Calculate and display estimated delivery dates (2 days from purchase)
- Cancel orders that have not yet been delivered
- Process returns or exchanges within 30 days of the purchase date

---

### 🛠️ Support Agent
Provides technical assistance for purchased products.

**Capabilities:**
- Access a built-in knowledge base for common troubleshooting scenarios
- Verify product ownership before providing support
- Escalate unresolved issues to the Handoff Agent

---

### ⭐ Feedback Agent
Collects customer ratings to improve service quality and inform other users.

**Capabilities:**
- Prompt users to rate purchased products on a 1–5 scale
- Track which products have already been rated to avoid duplicate requests
- Persist all feedback to the database

---

### 📞 Handoff Agent
Manages escalation from AI to human support specialists.

**Capabilities:**
- Assign an available human support staff member to an escalated user case
- Update session state to prevent other agents from re-handling the issue

---

## Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

Please ensure your changes are well-documented and tested before submitting.

---

## License

Distributed under the **MIT License**. See [`LICENSE.txt`](LICENSE.txt) for full terms.

---

## Contact

**Hariharan R** — [hariharan2002psg@gmail.com](mailto:vibhorebhatneriya@gmail.com)

GitHub: [github.com/Hariharan0309/customer-service-agent-adk](https://github.com/JustVibhor/AI-Powered-Customer-Service-Agent-Team)
