"""Where a quotation's clock starts, for both ERPNext CRM and Frappe CRM.

KPI timing is copied onto the Quotation itself, so every metric reads one place no
matter which CRM the client request was recorded in (or if Frappe CRM runs on
another site and nothing can be looked up).
"""

import frappe
from frappe.utils import cint, flt, get_datetime, getdate

from kayan_kpi.kpi.common import get_holidays, get_settings
from kayan_kpi.kpi.working_days import add_working_days, end_of_day, working_hours_between

ERPNEXT_CRM = "ERPNext CRM"
FRAPPE_CRM = "Frappe CRM"


def _has_doctype(doctype):
    return bool(frappe.db.exists("DocType", doctype))


def _get(doctype, name, fields):
    """get_value limited to the fields that exist on this site (CRM custom fields may be missing)."""
    meta = frappe.get_meta(doctype)
    fields = [f for f in fields if f in ("name", "creation", "modified", "owner") or meta.has_field(f)]
    return frappe.db.get_value(doctype, name, fields, as_dict=True)


def opportunity_for(quotation):
    if quotation.get("opportunity"):
        return quotation.opportunity
    for item in quotation.get("items") or []:
        if item.get("prevdoc_doctype") == "Opportunity" and item.get("prevdoc_docname"):
            return item.prevdoc_docname
    return None


def crm_deal_for(quotation):
    if quotation.get("kpi_crm_deal"):
        return quotation.kpi_crm_deal
    party_type = quotation.get("quotation_to")
    party = quotation.get("party_name")
    if party_type in ("Customer", "Prospect") and party and frappe.get_meta(party_type).has_field("crm_deal"):
        return frappe.db.get_value(party_type, party, "crm_deal")
    return None


def _from_opportunity(name):
    opp = _get(
        "Opportunity",
        name,
        [
            "name",
            "creation",
            "opportunity_from",
            "party_name",
            "kpi_request_received_on",
            "kpi_inquiry_complexity",
            "kpi_agreed_due_on",
            "kpi_application_engineer",
            "kpi_sales_engineer",
        ],
    )
    if not opp:
        return None
    received = get_datetime(opp.get("kpi_request_received_on") or opp.creation)
    first = received
    if opp.opportunity_from == "Lead" and opp.party_name:
        lead_created = frappe.db.get_value("Lead", opp.party_name, "creation")
        if lead_created:
            first = min(first, get_datetime(lead_created))
    return frappe._dict(
        received_on=received,
        first_contact_on=first,
        source=f"Opportunity {opp.name}",
        complexity=opp.get("kpi_inquiry_complexity"),
        agreed_due_on=opp.get("kpi_agreed_due_on"),
        application_engineer=opp.get("kpi_application_engineer"),
        sales_engineer=opp.get("kpi_sales_engineer"),
    )


def _from_crm_deal(name):
    if not name or not _has_doctype("CRM Deal"):
        return None
    deal = _get(
        "CRM Deal",
        name,
        [
            "name",
            "creation",
            "lead",
            "kpi_request_received_on",
            "kpi_inquiry_complexity",
            "kpi_agreed_due_on",
        ],
    )
    if not deal:
        return None
    received = get_datetime(deal.get("kpi_request_received_on") or deal.creation)
    first = received
    if deal.get("lead") and _has_doctype("CRM Lead"):
        lead_created = frappe.db.get_value("CRM Lead", deal.lead, "creation")
        if lead_created:
            first = min(first, get_datetime(lead_created))
    return frappe._dict(
        received_on=received,
        first_contact_on=first,
        source=f"CRM Deal {deal.name}",
        complexity=deal.get("kpi_inquiry_complexity"),
        agreed_due_on=deal.get("kpi_agreed_due_on"),
    )


def request_info(quotation):
    """Request time, first contact and complexity for a quotation, from the configured CRM first."""
    settings = get_settings()
    opportunity = opportunity_for(quotation)
    deal = crm_deal_for(quotation)

    lookups = [lambda: opportunity and _from_opportunity(opportunity), lambda: _from_crm_deal(deal)]
    if settings.crm_source == FRAPPE_CRM:
        lookups.reverse()

    for lookup in lookups:
        info = lookup()
        if info:
            info.crm_deal = deal
            return info
    return frappe._dict(crm_deal=deal)


def apply_request_info(quotation):
    """Fill the quotation's KPI fields that are still empty from its opportunity or deal."""
    info = request_info(quotation)
    if info.get("crm_deal") and not quotation.get("kpi_crm_deal"):
        quotation.kpi_crm_deal = info.crm_deal
    if info.get("received_on") and not quotation.get("kpi_request_received_on"):
        quotation.kpi_request_received_on = info.received_on
        quotation.kpi_request_source = info.source
    if not quotation.get("kpi_inquiry_complexity"):
        quotation.kpi_inquiry_complexity = info.get("complexity") or "Standard"
    if info.get("agreed_due_on") and not quotation.get("kpi_agreed_due_on"):
        quotation.kpi_agreed_due_on = info.agreed_due_on
    first = info.get("first_contact_on") or quotation.get("kpi_request_received_on")
    if first and not quotation.get("kpi_first_contact_on"):
        quotation.kpi_first_contact_on = first
    return info


def compute_due(received_on, complexity=None, agreed_due_on=None, company=None):
    if not received_on:
        return None
    if complexity == "Complex" and agreed_due_on:
        return get_datetime(agreed_due_on)
    settings = get_settings()
    return add_working_days(
        get_datetime(received_on), cint(settings.sla_working_days) or 3, get_holidays(company)
    )


def apply_sla(quotation, ready_on=None):
    """Set due date, ready time, turnaround hours and the on-time flag on a quotation."""
    received = quotation.get("kpi_request_received_on")
    if not received:
        return
    quotation.kpi_due_on = compute_due(
        received,
        quotation.get("kpi_inquiry_complexity"),
        quotation.get("kpi_agreed_due_on"),
        quotation.company,
    )
    ready = ready_on or quotation.get("kpi_ready_on")
    if ready:
        quotation.kpi_ready_on = ready
        quotation.kpi_tat_hours = working_hours_between(
            get_datetime(received), get_datetime(ready), get_holidays(quotation.company)
        )
        quotation.kpi_within_sla = 1 if get_datetime(ready) <= get_datetime(quotation.kpi_due_on) else 0


# --- in-hand orders ---------------------------------------------------------


def in_hand_dates(orders, settings=None):
    """{sales order: date it became a paid order in hand} for the rows given.

    Rows need name, transaction_date, po_no, po_date, advance_paid, base_grand_total,
    grand_total. An order with neither condition met is left out.
    """
    settings = settings or get_settings()
    basis = settings.in_hand_basis or "Any of Them"
    min_pct = flt(settings.min_advance_percent)
    names = [o.name for o in orders]
    first_payment = {}
    if names and basis in ("Any of Them", "Advance Payment"):
        PER = frappe.qb.DocType("Payment Entry Reference")
        PE = frappe.qb.DocType("Payment Entry")
        from frappe.query_builder.functions import Min

        rows = (
            frappe.qb.from_(PER)
            .join(PE)
            .on(PE.name == PER.parent)
            .select(PER.reference_name, Min(PE.posting_date).as_("first_date"))
            .where(
                (PER.reference_doctype == "Sales Order")
                & (PER.reference_name.isin(names))
                & (PE.docstatus == 1)
            )
            .groupby(PER.reference_name)
        ).run(as_dict=True)
        first_payment = {r.reference_name: getdate(r.first_date) for r in rows}

    result = {}
    for order in orders:
        dates = []
        if basis in ("Any of Them", "Customer PO") and order.get("po_no"):
            dates.append(getdate(order.get("po_date") or order.transaction_date))
        if basis in ("Any of Them", "Advance Payment"):
            paid = flt(order.get("advance_paid"))
            total = flt(order.get("grand_total"))
            enough = paid > 0 and (not min_pct or (total and paid / total * 100 >= min_pct))
            if enough:
                dates.append(first_payment.get(order.name) or getdate(order.transaction_date))
        if dates:
            result[order.name] = min(dates)
    return result


def po_event_time(order):
    """When the customer's order was received, read leniently as the end of the PO date."""
    if order.get("po_date"):
        return end_of_day(getdate(order.po_date))
    return None
