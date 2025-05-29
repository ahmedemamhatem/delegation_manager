
# 📧 Email Delegation App for Frappe

**Secure and auditable delegation of email inboxes and user operations in Frappe.**  
This app enables time-bound delegation between users with seamless Microsoft Graph API integration and a traceable, self-service experience.

---

## 🚀 Features

- **📬 Automatic Mailbox Delegation**  
  Create and remove Outlook/Exchange inbox message rules via Microsoft Graph API.

- **🧑‍💼 User Session Delegation**  
  Temporarily act as another user (delegator or delegatee) in Frappe with full audit logging.

- **⏳ Time-Based Activation**  
  Delegations are active only between the configured start and end dates.

- **📜 Complete Audit Trail**  
  Every delegation and email action is recorded in the document timeline.

- **📊 Admin Dashboard**  
  View all active, upcoming, and past delegations in one place.

- **🧑‍💻 Self-Service UI**  
  Delegates can "Assume Identity" or "Revert Identity" with one click.

- **🔌 API Access**  
  Use built-in endpoints for automation and integrations.

- **🛡️ Secure by Design**  
  One session per delegation. All actions are traceable and logged.

- **⏰ Scheduled Automation**  
  Daily background job automatically manages rule creation/removal.

---

## 🛠️ Installation

```bash
bench get-app email_delegation
bench --site your-site-name install-app email_delegation
bench --site your-site-name migrate
```

---

## 🔗 Microsoft Graph API Setup

1. **Create an Azure App Registration**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Navigate to: **App registrations → New registration**

2. **Add Required API Permissions**
   - `Mail.ReadWrite`
   - `Mail.ReadWrite.Shared`
   - (Add more if needed for your use case)

3. **Generate a Client Secret**
   - Go to **Certificates & Secrets** in your app
   - Create a new client secret and copy it

---

## ⚙️ Frappe Configuration

1. In Frappe, go to **Email Delegation Settings**
2. Fill in the following details:
   - **Tenant ID**
   - **Client ID**
   - **Client Secret**
   - **Scope** (e.g., `https://graph.microsoft.com/.default`)

---

## 📄 Usage

### 1. Create a Delegation

- Go to the **Delegation** doctype.
- Set:
  - **Delegator** (mailbox owner)
  - **Delegatee** (the acting user)
  - **Start Date** and **End Date**
- Submit the document.

### 2. Email Forwarding Rules

- **Automatically**:
  - A forwarding rule is created at the start of delegation.
  - The rule is removed when the delegation ends.
- **Manually** (if needed):
  - Use buttons:
    - ✅ *Add Message Rule*
    - 🔄 *Fetch Message Rules*
    - ❌ *Remove Message Rule(s)*

### 3. Session Delegation

- Delegatee will see an **"Assume Identity"** button.
- Actions are performed as the **Delegator** but logged as delegated.
- Click **"Revert Identity"** to return to your own session.

### 4. Tracking & Logs

- All delegation events, message rule changes, and identity switches are logged in the **timeline** of the Delegation document.

---

## ⏱️ Automation (Scheduler Job)

A scheduled job runs daily to:

- Create message rules when a delegation **starts**
- Fetch and remove rules when a delegation **ends**

No manual intervention needed!

---

