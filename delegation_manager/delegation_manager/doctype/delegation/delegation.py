import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, date
from typing import Optional, Any

from delegation_manager.email import get_message_rules, delete_message_rule

class Delegation(Document):
    def before_validate(self) -> None:
        """
        If the document is in draft (docstatus == 0),
        reset all email forwarding fields.
        """
        if self.docstatus == 0:
            self.reset_email_forwarding_fields()

    def reset_email_forwarding_fields(self) -> None:
        """
        Helper to reset email forwarding-related fields to their default values.
        """
        self.email_forwarded = 0
        self.email_forwarded_id = None
        self.email_ids = None
        self.response = None

    def validate(self) -> None:
        """
        Runs during validation. Checks for overlapping delegations.
        """
        self.validate_date_overlap()

    def validate_date_overlap(self) -> None:
        """
        Ensure no overlapping delegations exist for the same delegator and delegatee
        for submitted records.
        """
        existing_delegations = frappe.get_all(
            "Delegation",
            filters={
                "name": ["!=", self.name],
                "docstatus": 1,  # Only consider submitted
                "delegator": self.delegator,
                "delegatee": self.delegatee
            },
            fields=["name", "start_date", "end_date"]
        )

        start1 = self.ensure_date(self.start_date)
        end1 = self.ensure_date(self.end_date)

        for d in existing_delegations:
            start2 = self.ensure_date(d.start_date)
            end2 = self.ensure_date(d.end_date)
            if self.dates_overlap(start1, end1, start2, end2):
                frappe.throw(
                    _("A delegation already exists for these users during the selected period: {0}").format(d.name)
                )

    @staticmethod
    def ensure_date(val: Optional[Any]) -> Optional[date]:
        """
        Converts a value to a date object, if it's a string or None.
        Args:
            val (str, date, or None): The value to convert.
        Returns:
            date or None: The converted date, or None if input is None/empty.
        Raises:
            ValueError: If the value cannot be converted.
        """
        if val is None or val == "":
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            try:
                return datetime.strptime(val, "%Y-%m-%d").date()
            except ValueError:
                return datetime.strptime(val.split(" ")[0], "%Y-%m-%d").date()
        raise ValueError(f"Cannot convert {val!r} to date.")

    @staticmethod
    def dates_overlap(start1: Optional[date], end1: Optional[date], start2: Optional[date], end2: Optional[date]) -> bool:
        """
        Check if two date ranges overlap (inclusive).
        Returns False if any date is missing.
        """
        if None in (start1, end1, start2, end2):
            return False
        return start1 <= end2 and start2 <= end1

    def before_cancel(self) -> None:
        """
        Before cancellation, remove any auto-forward message rules via the email manager,
        reset email forwarding fields, and add a comment to the timeline.
        """
        comment = ""
        try:
            get_message_rules(self.name)
            delete_message_rule(self.name)
            comment = _("🗑️ Auto-forward rule(s) deleted before cancellation.")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"[Delegation: {self.name}] Error deleting message rules before cancel")
            comment = _("❌ Failed to delete auto-forward rule(s) before cancellation: {0}").format(str(e))
        finally:
            self.reset_email_forwarding_fields()
            # Add the timeline comment (after fields are reset)
            self.add_comment("Comment", text=comment)