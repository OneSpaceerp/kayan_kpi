"""The two KPI frameworks from Kayan's Q3-Q4 goals documents, and the Q3 / Q4 2026 periods.

Created on install only, so templates and periods edited or deleted later are left alone.
"""

import frappe

APPLICATION_NOTES = """<ul>
<li><b>Cross-Functional Collaboration:</b> Support sales team via data sheets, presentations, and meetings.</li>
<li><b>Value Engineering &amp; Win Rate:</b> Focus on cost-effective alternatives to increase order volume.</li>
<li><b>Service Level Agreement (SLA):</b> Maintain green status for turnaround time &amp; selection accuracy.</li>
<li><b>Quality Assurance:</b> Ensure zero drafts left in CRM / document system and all files updated.</li>
</ul>"""

SALES_NOTES = """<ul>
<li><b>Hit Rate Calculation (Core Metric):</b> Hit Rate (%) = (No. of Paid Orders (In Hand) / No. of Issued Quotations) x 100</li>
<li><b>Conversion Rate:</b> Rate for conversion of pipeline items into closed deals.</li>
<li><b>Win/Loss Ratio:</b> Sector win/loss ratio for engineers focused on fast-selling products.</li>
<li><b>Cross-Selling &amp; Product Mix:</b> Drive cross-selling and optimize product mix for challenging accounts.</li>
<li><b>Support Sales / Application Engineer Alignment:</b> Collect useful field data from site visits to help Application Engineers and avoid rework.</li>
</ul>
<p><b>Profit Margin Bonus Scheme (Incentive):</b> Deals closed with an exceptional profit margin (above 50%) earn additional reward points outside the core evaluation weights. Every deal exceeding the 50% margin threshold qualifies for extra incentive points based on the final achieved percentage (Kayan KPI Settings → Margin Bonus).</p>"""

STUDY_TARGET = (
    "Build and share a deep, detailed report on the commercial and technical information of competitors for "
    "each project (competitor offers, pricing position, technical specifications, strengths / weaknesses, and "
    "a recommendation to win the order)."
)
STUDY_CHECK = (
    "Document system and reviewed by the manager against a checklist (competitors identified, commercial data, "
    "technical comparison, recommendation); submitted with the quotation and on time; rated in the manager's review."
)

TEMPLATES = [
    {
        "template_name": "Application Engineer KPIs",
        "kpi_role": "Application Engineer",
        "description": "Framework for the team that handles technical selection, prepares quotations, works on "
        "client inquiries, and answers technical questions to support the commercial offer.",
        "notes": APPLICATION_NOTES,
        "items": [
            (
                "Turn around quotes fast",
                "TAT (Turnaround Time) / Service Level Agreement (SLA)",
                "Quote Turnaround (SLA)",
                100,
                "%",
                25,
                "72 hours or less from client request to a finished, ready-to-send quotation: standard inquiries "
                "within 3 working days of the client request; larger or more complex inquiries follow a timeline "
                "agreed with the manager. Measured as % of quotations ready on time.",
                "Request and completion times, tracked in CRM system",
            ),
            (
                "Pick the right equipment",
                "Selection Accuracy",
                "Selection Accuracy",
                98,
                "%",
                20,
                "98% or more of technical selections pass review with no correction needed (applies to in-hand "
                "projects only).",
                "Technical review checklist, reviewed by the manager or by random selection of different quotations",
            ),
            (
                "Follow the rules and standards",
                "",
                "Standards Compliance",
                100,
                "%",
                10,
                "100% of technical selections meet the required industry standards.",
                "Compliance check records, reviewed by the manager or by random selection of different quotations.",
            ),
            (
                "Answer client questions well",
                "Get Feedback",
                "Client Query Service",
                100,
                "%",
                5,
                "Reply within 24 hours; client rates the help 4.5 out of 5 or higher. Half reply-on-time rate, half "
                "rating against 4.5.",
                "Client survey, Manager Feedback, or CRM system",
            ),
            (
                "Help close the sale",
                "Follow / create solution",
                "Quotation Win Rate",
                25,
                "%",
                15,
                "25% or more of technical quotations lead to a won order.",
                "Won / lost sales report from CRM system",
            ),
            (
                "Keep paperwork complete and updated on CRM system",
                "No drafts / Update",
                "Paperwork Complete",
                100,
                "%",
                15,
                "100% of quotations have complete datasheets and calculations filed.",
                "CRM system / Document system",
            ),
            ("Project competitor study", "", "Competitor Study", 100, "%", 10, STUDY_TARGET, STUDY_CHECK),
        ],
    },
    {
        "template_name": "Sales Engineer KPIs",
        "kpi_role": "Sales Engineer",
        "description": "Framework for engineers who sell pump, water utility, and heat-exchanger equipment "
        "(Direct Sales).",
        "notes": SALES_NOTES,
        "items": [
            (
                "Hit the sales target",
                "Sales Target Achievement",
                "Sales Target Achievement",
                100,
                "%",
                25,
                "100% or more of the quarterly sales goal.",
                "Sales report",
            ),
            (
                "Turn quotes into orders",
                "Hit Rate / Quotation Hit Rate",
                "Quotation Hit Rate",
                30,
                "%",
                10,
                "30% or more of quotes sent become paid orders (In-hand).",
                "Sales pipeline report",
            ),
            (
                "Bring in new clients",
                "Acquisition (New Customer)",
                "New Clients",
                3,
                "Count",
                10,
                "3 or more new active clients per quarter.",
                "Client list from CRM System.",
            ),
            (
                "Close deals reasonably fast",
                "Without Heavy Follow-up",
                "Sales Cycle Time",
                100,
                "%",
                15,
                "60 days or less from first contact to signed order. Measured as % of orders signed within 60 days.",
                "Sales stage tracking through CRM System.",
            ),
            (
                "Keep clients coming back",
                "Commitment & Sub-recurring Visit",
                "Repeat Client Revenue",
                50,
                "%",
                15,
                "50% or more of revenue comes from repeat clients.",
                "Revenue-by-client report",
            ),
            (
                "Keep records up to date",
                "",
                "Records Up To Date",
                95,
                "%",
                15,
                "95% or more of deals updated in the system within 48 hours of any change.",
                "System audit",
            ),
            (
                "Project competitor study",
                "Competitor Study",
                "Competitor Study",
                100,
                "%",
                10,
                "For each project, build and share a detailed report on the competitor's commercial and technical "
                "information: pricing position, technical specification, strengths and weaknesses, and a "
                "recommendation to win the order.",
                "Report filled in the document system and reviewed by the manager against a checklist: competitor "
                "identified, commercial data, technical comparison, recommendation, submitted with the quotation "
                "and on time.",
            ),
        ],
    },
]

PERIODS = [
    ("Q3 2026", "2026-07-01", "2026-09-30"),
    ("Q4 2026", "2026-10-01", "2026-12-31"),
]


def seed():
    for t in TEMPLATES:
        if frappe.db.exists("KPI Template", t["template_name"]):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "KPI Template",
                "template_name": t["template_name"],
                "kpi_role": t["kpi_role"],
                "description": t["description"],
                "notes": t["notes"],
                "is_active": 1,
                "items": [
                    {
                        "goal": goal,
                        "sub_goal": sub,
                        "metric": metric,
                        "target_value": target,
                        "uom": uom,
                        "weight": weight,
                        "scoring_method": "Linear",
                        "target_description": target_text,
                        "how_checked": check,
                    }
                    for goal, sub, metric, target, uom, weight, target_text, check in t["items"]
                ],
            }
        )
        doc.insert(ignore_permissions=True)

    company = frappe.defaults.get_global_default("company")
    for name, start, end in PERIODS:
        if not frappe.db.exists("KPI Period", name):
            frappe.get_doc(
                {
                    "doctype": "KPI Period",
                    "period_name": name,
                    "start_date": start,
                    "end_date": end,
                    "status": "Open",
                    "company": company,
                }
            ).insert(ignore_permissions=True)
