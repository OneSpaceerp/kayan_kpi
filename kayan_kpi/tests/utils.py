import frappe


def before_tests():
    frappe.clear_cache()
    from kayan_kpi.setup import after_migrate

    after_migrate()
