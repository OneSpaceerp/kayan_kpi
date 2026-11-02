import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model import no_value_fields
from frappe.permissions import add_permission, update_permission_property

from kayan_kpi.constants.custom_fields import CRM_DEAL_FIELDS, CUSTOM_FIELDS

ROLES = ("KPI Manager", "Application Engineer", "Sales Engineer")

# Who may edit / read the manager-only (permlevel 1) KPI fields on core documents
LEVEL_1 = {
    "Opportunity": {"write": ("KPI Manager", "Sales Manager"), "read": ("Sales User",)},
    "Quotation": {"write": ("KPI Manager", "Sales Manager"), "read": ("Sales User",)},
    "CRM Deal": {"write": ("KPI Manager", "Sales Manager"), "read": ("Sales User",)},
}


def after_install():
    after_migrate()
    from kayan_kpi.patches.v1_0.backfill_quotation_kpi_fields import backfill
    from kayan_kpi.setup.seed import seed

    seed()
    # patches are not run on install; existing quotations are filled in the background
    frappe.enqueue(backfill, queue="long", timeout=3000, enqueue_after_commit=True)


def after_migrate():
    """Runs after install and every migrate; every step is idempotent."""
    create_roles()
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    if frappe.db.exists("DocType", "CRM Deal"):
        create_custom_fields({"CRM Deal": CRM_DEAL_FIELDS}, ignore_validate=True)
    add_field_permissions()
    set_settings_defaults()


def create_roles():
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
                ignore_permissions=True
            )


def add_field_permissions():
    for doctype, levels in LEVEL_1.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        for ptype, roles in levels.items():
            for role in roles:
                if not frappe.db.exists("Role", role):
                    continue
                add_permission(doctype, role, permlevel=1)
                if ptype == "write":
                    update_permission_property(doctype, role, 1, "write", 1, validate=False)


def set_settings_defaults():
    """Single DocTypes do not store their defaults until first saved; store them once."""
    meta = frappe.get_meta("Kayan KPI Settings")
    singles = frappe.qb.Table("tabSingles")
    stored = set(
        frappe.qb.from_(singles)
        .select(singles.field)
        .where(singles.doctype == "Kayan KPI Settings")
        .run(pluck=True)
    )
    for df in meta.fields:
        if df.default is not None and df.fieldname not in stored and df.fieldtype not in no_value_fields:
            frappe.db.set_single_value("Kayan KPI Settings", df.fieldname, df.default, update_modified=False)
    frappe.clear_document_cache("Kayan KPI Settings", "Kayan KPI Settings")


def before_uninstall():
    frappe.db.delete("Custom Field", {"fieldname": ["like", "kpi\\_%"]})
