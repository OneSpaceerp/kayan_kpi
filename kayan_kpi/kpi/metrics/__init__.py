"""Every KPI the templates can use, by the label shown in KPI Template Item → Measured By."""

from frappe import _

from kayan_kpi.kpi.common import MetricResult
from kayan_kpi.kpi.metrics import application, sales, shared

MANUAL = "Manual Entry"

REGISTRY = {
    "Quote Turnaround (SLA)": application.quote_turnaround,
    "Selection Accuracy": application.selection_accuracy,
    "Standards Compliance": application.standards_compliance,
    "Client Query Service": application.client_query_service,
    "Quotation Win Rate": application.quotation_win_rate,
    "Paperwork Complete": application.paperwork_complete,
    "Sales Target Achievement": sales.sales_target_achievement,
    "Quotation Hit Rate": sales.quotation_hit_rate,
    "New Clients": sales.new_clients,
    "Sales Cycle Time": sales.sales_cycle_time,
    "Repeat Client Revenue": sales.repeat_client_revenue,
    "Records Up To Date": sales.records_up_to_date,
    "Competitor Study": shared.competitor_study,
    MANUAL: lambda ctx: MetricResult(None, details=_("Entered by the manager")),
}


def run_metric(metric, ctx):
    fn = REGISTRY.get(metric)
    if not fn:
        return MetricResult(None, details=_("Unknown metric {0}").format(metric))
    return fn(ctx)
