"""Custom fields Kayan KPI adds to ERPNext and HRMS. Created on install and on every migrate."""

COMPLEXITY = "\nStandard\nComplex"

REQUEST_FIELDS = [
    {
        "fieldname": "kpi_request_received_on",
        "label": "Client Request Received On",
        "fieldtype": "Datetime",
        "description": "When the client asked for the quotation. Leave empty to use the time this record was created.",
    },
    {
        "fieldname": "kpi_inquiry_complexity",
        "label": "Inquiry Size",
        "fieldtype": "Select",
        "options": COMPLEXITY,
        "description": "Standard inquiries follow the working-day SLA in Kayan KPI Settings; complex ones use the due date agreed with the manager.",
    },
    {
        "fieldname": "kpi_agreed_due_on",
        "label": "Due Date Agreed With Manager",
        "fieldtype": "Datetime",
        "permlevel": 1,
        "depends_on": "eval:doc.kpi_inquiry_complexity=='Complex'",
    },
]

EVENT_FIELD = {
    "fieldname": "kpi_event_on",
    "label": "Change Happened On",
    "fieldtype": "Datetime",
    "no_copy": 1,
    "description": "When the stage or status change actually happened (meeting, call, client decision). Measures how quickly records are updated.",
}


def _chain(fields, first_after):
    """Set insert_after so the fields follow each other, starting after `first_after`."""
    out = []
    previous = first_after
    for field in fields:
        field = dict(field)
        field["insert_after"] = previous
        out.append(field)
        previous = field["fieldname"]
    return out


CUSTOM_FIELDS = {
    "Employee": _chain(
        [
            {
                "fieldname": "kpi_template",
                "label": "KPI Template",
                "fieldtype": "Link",
                "options": "KPI Template",
                "description": "The KPI scorecard this employee is evaluated on (Kayan KPI).",
            }
        ],
        "reports_to",
    ),
    "Opportunity": _chain(
        [
            {"fieldname": "kpi_tab", "label": "KPI Tracking", "fieldtype": "Tab Break"},
            {"fieldname": "kpi_request_section", "label": "Client Request", "fieldtype": "Section Break"},
            *REQUEST_FIELDS,
            {"fieldname": "kpi_column_break_1", "fieldtype": "Column Break"},
            {
                "fieldname": "kpi_application_engineer",
                "label": "Application Engineer",
                "fieldtype": "Link",
                "options": "Employee",
            },
            {
                "fieldname": "kpi_sales_engineer",
                "label": "Sales Engineer",
                "fieldtype": "Link",
                "options": "Employee",
            },
            {"fieldname": "kpi_updates_section", "label": "Record Updates", "fieldtype": "Section Break"},
            EVENT_FIELD,
        ],
        "notes",
    ),
    "Quotation": _chain(
        [
            {"fieldname": "kpi_tab", "label": "KPI", "fieldtype": "Tab Break"},
            {"fieldname": "kpi_engineers_section", "label": "Engineers", "fieldtype": "Section Break"},
            {
                "fieldname": "kpi_engineers",
                "label": "KPI Engineers",
                "fieldtype": "Table",
                "options": "KPI Quotation Engineer",
                "description": "Who prepared and who sells this quotation. Their KPIs are credited from here.",
            },
            {"fieldname": "kpi_sla_section", "label": "Turnaround (SLA)", "fieldtype": "Section Break"},
            *REQUEST_FIELDS,
            {
                "fieldname": "kpi_crm_deal",
                "label": "CRM Deal",
                "fieldtype": "Data",
                "description": "Frappe CRM deal this quotation answers. Filled from the Customer or Prospect when empty.",
            },
            {"fieldname": "kpi_column_break_1", "fieldtype": "Column Break"},
            {
                "fieldname": "kpi_due_on",
                "label": "Due On",
                "fieldtype": "Datetime",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "kpi_ready_on",
                "label": "Ready to Send On",
                "fieldtype": "Datetime",
                "read_only": 1,
                "no_copy": 1,
                "description": "Recorded when the quotation is submitted.",
            },
            {
                "fieldname": "kpi_tat_hours",
                "label": "Turnaround (Working Hours)",
                "fieldtype": "Float",
                "precision": "2",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "kpi_within_sla",
                "label": "Within SLA",
                "fieldtype": "Check",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "kpi_request_source",
                "label": "Request Time Taken From",
                "fieldtype": "Data",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "kpi_first_contact_on",
                "label": "First Client Contact On",
                "fieldtype": "Datetime",
                "no_copy": 1,
                "description": "Start of the sales cycle. Filled from the Lead or CRM Lead when empty.",
            },
            {
                "fieldname": "kpi_documents_section",
                "label": "Datasheets and Calculations",
                "fieldtype": "Section Break",
            },
            {
                "fieldname": "kpi_documents",
                "label": "Quotation Documents",
                "fieldtype": "Table",
                "options": "KPI Quotation Document",
            },
        ],
        "supplier_quotation",
    ),
    "Quotation Item": _chain(
        [
            {
                "fieldname": "kpi_estimated_cost",
                "label": "Estimated Unit Cost",
                "fieldtype": "Currency",
                "options": "Company:company:default_currency",
                "description": "Cost per unit in company currency, used for the margin bonus when the item has no valuation.",
            }
        ],
        "gross_profit",
    ),
    "Sales Order Item": _chain(
        [
            {
                "fieldname": "kpi_estimated_cost",
                "label": "Estimated Unit Cost",
                "fieldtype": "Currency",
                "options": "Company:company:default_currency",
            }
        ],
        "gross_profit",
    ),
    "Sales Invoice Item": _chain(
        [
            {
                "fieldname": "kpi_estimated_cost",
                "label": "Estimated Unit Cost",
                "fieldtype": "Currency",
                "options": "Company:company:default_currency",
            }
        ],
        "incoming_rate",
    ),
}

# Added only when Frappe CRM is installed on the same site. Add them to the deal
# side panel through CRM → Settings → Fields Layout to show them in the CRM app.
CRM_DEAL_FIELDS = [
    {"fieldname": "kpi_section", "label": "KPI Tracking", "fieldtype": "Section Break"},
    *REQUEST_FIELDS,
    EVENT_FIELD,
]
