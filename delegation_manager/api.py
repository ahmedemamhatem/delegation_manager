import frappe
from frappe.utils import now_datetime
from typing import List, Dict, Any

@frappe.whitelist()
def get_active_delegations() -> List[Dict[str, Any]]:
    """
    Returns a list of active delegations for the current user,
    both as delegatee and as delegator (if logged).
    """
    user = frappe.session.user
    today = frappe.utils.nowdate()

    # As delegatee
    delegations = frappe.get_all("Delegation",
        filters={
            "docstatus": 1,
            "start_date": ["<=", today],
            "end_date": [">=", today],
            "delegatee": user
        },
        fields=["name", "delegator", "delegatee", "logged", "current_user"]
    )

    # As delegator (currently delegated)
    delegations_as_delegator = frappe.get_all("Delegation",
        filters={
            "docstatus": 1,
            "start_date": ["<=", today],
            "end_date": [">=", today],
            "delegator": user,
            "logged": 1
        },
        fields=["name", "delegator", "delegatee", "logged", "current_user"]
    )

    # Add full names
    for d in delegations + delegations_as_delegator:
        d["delegator_full_name"] = frappe.db.get_value("User", d["delegator"], "full_name") or d["delegator"]
        d["delegatee_full_name"] = frappe.db.get_value("User", d["delegatee"], "full_name") or d["delegatee"]

    # Remove duplicates by delegation name
    all_delegations = {d["name"]: d for d in delegations + delegations_as_delegator}
    return list(all_delegations.values())

@frappe.whitelist()
def assume_identity(delegation_name: str) -> Dict[str, str]:
    """
    Allows the delegatee to assume the identity of the delegator for a given delegation.
    """
    user = frappe.session.user
    delegation_doc = frappe.get_doc("Delegation", delegation_name)

    if delegation_doc.delegatee != user:
        frappe.throw("You are not the delegatee for this delegation.")

    # Prevent multiple active delegations for the same delegator
    active_for_delegator = frappe.db.exists(
        "Delegation",
        {
            "logged": 1,
            "current_user": delegation_doc.delegator
        }
    )
    if active_for_delegator:
        frappe.throw(f"{delegation_doc.delegator} is already being delegated to by another session. Please try again later.")

    # Use login_manager to switch identity
    frappe.local.login_manager.login_as(delegation_doc.delegator)
    frappe.db.commit()

    frappe.db.set_value("Delegation", delegation_name, {
        "logged": 1,
        "current_user": delegation_doc.delegator
    })

    # Append to delegation log
    delegation_doc.reload()
    delegation_doc.append("delegation_log", {
        "log": f"[{now_datetime()}] {user} delegated as {delegation_doc.delegator}."
    })
    delegation_doc.save(ignore_permissions=True)
    return {"redirect": "/app"}

@frappe.whitelist()
def revert_identity(delegation_name: str) -> Dict[str, str]:
    """
    Allows the delegator to revert the session back to the delegatee.
    """
    delegation_doc = frappe.get_doc("Delegation", delegation_name)
    delegatee = delegation_doc.delegatee

    if frappe.session.user != delegation_doc.delegator:
        frappe.throw("You are not the delegator for this delegation.")

    frappe.local.login_manager.login_as(delegatee)
    frappe.db.commit()
    frappe.db.set_value("Delegation", delegation_name, {
        "logged": 0,
        "current_user": None
    })

    delegation_doc.reload()
    delegation_doc.append("delegation_log", {
        "log": f"[{now_datetime()}] {delegatee} reverted from {delegation_doc.delegator} to themselves."
    })
    delegation_doc.save(ignore_permissions=True)
    return {"redirect": "/app"}