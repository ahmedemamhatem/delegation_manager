import frappe

def doc_delegate_update(doc, method=None):
    """
    Frappe hook: on insert, validate, and update, reassigns owner and/or modifier
    from delegator to delegatee if delegation is active for the current user.
    """
    delegation = frappe.db.get_value(
        "Delegation",
        {
            "logged": 1,
            "current_user": frappe.session.user
        },
        ["delegator", "delegatee"],
        as_dict=True
    )

    if not delegation:
        return

    # On insert: if owner is delegator, set to delegatee
    if getattr(doc, "owner", None) == delegation.delegator:
        doc.owner = delegation.delegatee

    # On any update/validate: always set modified_by to delegatee if needed
    if hasattr(doc, "modified_by") and getattr(doc, "modified_by", None) == delegation.delegator:
        doc.modified_by = delegation.delegatee