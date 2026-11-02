app_name = "kayan_kpi"
app_title = "Kayan KPI"
app_publisher = "nsdLabs - Nest Software Development"
app_description = "KPI scorecards for Application and Sales Engineers on ERPNext and HRMS"
app_email = "info@nsd-eg.com"
app_license = "MIT"

required_apps = ["frappe/erpnext", "frappe/hrms"]

app_logo_url = "/assets/kayan_kpi/images/kayan-kpi-logo.png"
app_home = "/desk/kayan-kpi"

add_to_apps_screen = [
    {
        "name": "kayan_kpi",
        "logo": "/assets/kayan_kpi/images/kayan-kpi-logo.png",
        "title": "Kayan KPI",
        "route": app_home,
    }
]

# Frappe v16 dock and sidebar-header icons (kayan-kpi-*, kayan-kpi-setup-* in -duotone and -soft)
app_include_icons = ["/assets/kayan_kpi/icons/kayan-kpi-icons.svg"]

# Installation
# ------------
after_install = "kayan_kpi.setup.after_install"
after_migrate = "kayan_kpi.setup.after_migrate"
before_uninstall = "kayan_kpi.setup.before_uninstall"

# Desk form scripts on core doctypes
# ----------------------------------
doctype_js = {
    "Quotation": "public/js/quotation.js",
    "Opportunity": "public/js/opportunity.js",
}

# Document Events
# ---------------
doc_events = {
    "Quotation": {
        "validate": "kayan_kpi.events.quotation.validate",
        "before_submit": "kayan_kpi.events.quotation.before_submit",
    },
    "Opportunity": {
        "validate": "kayan_kpi.events.deal.validate",
        "on_update": "kayan_kpi.events.deal.on_update",
    },
    # Frappe CRM on the same site; harmless when it is not installed
    "CRM Deal": {
        "on_update": "kayan_kpi.events.deal.on_update",
    },
    "Communication": {
        "after_insert": "kayan_kpi.events.communication.after_insert",
    },
}

# Permissions
# -----------
permission_query_conditions = {
    "KPI Scorecard": "kayan_kpi.permissions.scorecard_query",
    "Technical Query": "kayan_kpi.permissions.technical_query_query",
    "Competitor Study": "kayan_kpi.permissions.competitor_study_query",
    "KPI Deal Update Log": "kayan_kpi.permissions.deal_log_query",
}

has_permission = {
    "KPI Scorecard": "kayan_kpi.permissions.has_permission",
    "Technical Query": "kayan_kpi.permissions.has_permission",
    "Competitor Study": "kayan_kpi.permissions.has_permission",
    "KPI Deal Update Log": "kayan_kpi.permissions.has_permission",
}

# Scheduled Tasks
# ---------------
scheduler_events = {
    "daily": ["kayan_kpi.tasks.recalculate_open_scorecards"],
    "weekly": ["kayan_kpi.tasks.assign_random_reviews"],
}

# Testing
# -------
before_tests = "kayan_kpi.tests.utils.before_tests"
