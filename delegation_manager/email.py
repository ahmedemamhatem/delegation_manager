import requests
import frappe
import json
from frappe.utils import today
from typing import Any, Dict, Optional, List

def reset_email_forwarding_fields(doc: frappe.model.document.Document) -> None:
    """
    Resets email forwarding-related fields on the Delegation document.
    """
    doc.email_forwarded = 0
    doc.email_forwarded_id = None
    doc.email_ids = None
    doc.response = None
    doc.save(ignore_permissions=True)

@frappe.whitelist()
def get_settings() -> frappe.model.document.Document:
    """
    Fetch the singleton Email Delegation Settings DocType.
    """
    return frappe.get_single('Email Delegation Settings')

def delegation_feature_is_active() -> bool:
    """
    Returns True if Email Delegation automation is enabled in settings.
    """
    settings = get_settings()
    return bool(getattr(settings, "is_active", 0))

@frappe.whitelist()
def get_access_token() -> str:
    """
    Retrieve an OAuth2 access token from Microsoft using the settings.
    """
    settings = get_settings()
    url = f"https://login.microsoftonline.com/{settings.tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": settings.grant_type,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "scope": settings.scope
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

@frappe.whitelist()
def create_message_rule(delegation: str) -> Dict[str, Any]:
    """
    Create an auto-forwarding message rule for the delegatee's mailbox.
    """
    if not delegation_feature_is_active():
        return {"message": "Email Delegation automation is disabled in settings."}

    delegation_doc = frappe.get_doc("Delegation", delegation)
    token = get_access_token()

    url = f"https://graph.microsoft.com/v1.0/users/{delegation_doc.delegatee}/mailFolders/inbox/messageRules"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "displayName": f"Auto-forward to {delegation_doc.delegator}",
        "sequence": 1,
        "isEnabled": True,
        "conditions": {},
        "actions": {
            "forwardTo": [
                {
                    "emailAddress": {
                        "address": delegation_doc.delegator
                    }
                }
            ]
        },
        "stopProcessingRules": False
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()

    result = response.json()

    delegation_doc.email_forwarded = 1
    delegation_doc.email_forwarded_id = result.get("id")
    delegation_doc.response = json.dumps(result, indent=2)
    delegation_doc.save(ignore_permissions=True)

    return result

@frappe.whitelist()
def get_message_rules(delegation: str) -> Dict[str, Any]:
    """
    Retrieve all inbox message rules for the delegatee.
    """
    if not delegation_feature_is_active():
        return {"message": "Email Delegation automation is disabled in settings."}

    delegation_doc = frappe.get_doc("Delegation", delegation)
    token = get_access_token()

    url = f"https://graph.microsoft.com/v1.0/users/{delegation_doc.delegatee}/mailFolders/inbox/messageRules"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    rules = data.get('value', [])

    if not rules:
        reset_email_forwarding_fields(delegation_doc)
        return {"message": "No rules found.", "data": data}

    email_ids = [rule.get('id') for rule in rules if rule.get('id')]
    delegation_doc.email_forwarded = 1
    delegation_doc.email_forwarded_id = None
    delegation_doc.email_ids = ",".join(email_ids) if email_ids else None
    delegation_doc.response = json.dumps(data, indent=2)
    delegation_doc.save(ignore_permissions=True)

    return data

@frappe.whitelist()
def delete_message_rule(delegation: str) -> str:
    """
    Delete the message rule(s) for the delegatee specified in the Delegation document.
    """
    if not delegation_feature_is_active():
        return "Email Delegation automation is disabled in settings."

    delegation_doc = frappe.get_doc('Delegation', delegation)
    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }
    rule_names = []
    if delegation_doc.email_forwarded_id:
        rule_names = [delegation_doc.email_forwarded_id]
    elif delegation_doc.email_ids:
        rule_names = [rule_id.strip() for rule_id in delegation_doc.email_ids.split(',') if rule_id.strip()]

    if not rule_names:
        reset_email_forwarding_fields(delegation_doc)
        return "No rules to delete."

    errors = []
    for rule_id in rule_names:
        url = f"https://graph.microsoft.com/v1.0/users/{delegation_doc.delegatee}/mailFolders/inbox/messageRules/{rule_id}"
        response = requests.delete(url, headers=headers)
        if response.status_code not in (204, 200):
            error_msg = f"Failed to delete rule {rule_id} (Delegation: {delegation_doc.name}): {response.text}"
            frappe.log_error(frappe.get_traceback(), error_msg)
            errors.append(error_msg)

    reset_email_forwarding_fields(delegation_doc)

    if errors:
        raise frappe.ValidationError('\n'.join(errors))

    return "Deleted all specified rules."

def handle_delegation_rules() -> None:
    """
    Scheduled task to create rules for delegations starting today and
    delete rules for delegations ending today. Logs actions and errors.
    Also adds a comment on each Delegation doc with the action taken.
    """
    if not delegation_feature_is_active():
        frappe.logger().info("[Delegation Scheduler] Skipped: Email Delegation automation is disabled in settings.")
        return

    today_date = today()

    # Start rules for delegations starting today
    start_delegations = frappe.get_all("Delegation", filters={
        "start_date": today_date,
        "docstatus": 1
    })

    for d in start_delegations:
        doc = frappe.get_doc("Delegation", d["name"])
        try:
            create_message_rule(d["name"])
            doc.add_comment(
                "Comment",
                text=f"✅ Auto-forward rule created for delegatee {doc.delegatee} to delegator {doc.delegator} on {today_date}."
            )
            frappe.logger().info(f"[Delegation Scheduler] Rule created for: {d['name']}")
        except Exception as e:
            error_msg = f"❌ Failed to create rule for {d['name']}: {str(e)}"
            frappe.log_error(frappe.get_traceback(), error_msg)
            doc.add_comment(
                "Comment",
                text=error_msg
            )

    # Remove rules for delegations ending today
    end_delegations = frappe.get_all("Delegation", filters={
        "end_date": today_date,
        "docstatus": 1
    })

    for d in end_delegations:
        doc = frappe.get_doc("Delegation", d["name"])
        try:
            get_message_rules(d["name"])
            delete_message_rule(d["name"])
            doc.add_comment(
                "Comment",
                text=f"🗑️ Auto-forward rule deleted for delegatee {doc.delegatee} on {today_date}."
            )
            frappe.logger().info(f"[Delegation Scheduler] Rule deleted for: {d['name']}")
        except Exception as e:
            error_msg = f"❌ Failed to delete rule for {d['name']}: {str(e)}"
            frappe.log_error(frappe.get_traceback(), error_msg)
            doc.add_comment(
                "Comment",
                text=error_msg
            )