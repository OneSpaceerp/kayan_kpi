import frappe


def after_insert(doc, method=None):
    """The first email sent from a Technical Query is its first reply."""
    if doc.reference_doctype != "Technical Query" or doc.sent_or_received != "Sent" or not doc.reference_name:
        return
    if doc.communication_type not in ("Communication", None, ""):
        return
    query = frappe.get_doc("Technical Query", doc.reference_name)
    if query.first_reply_on:
        return
    query.first_reply_on = doc.communication_date or doc.creation
    query.flags.ignore_permissions = True
    query.save()
