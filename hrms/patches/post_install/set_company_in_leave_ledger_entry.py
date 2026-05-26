import frappe


def execute():
	frappe.reload_doc("HR", "doctype", "Leave Allocation")
	frappe.reload_doc("HR", "doctype", "Leave Ledger Entry")
	frappe.db.sql(
		{
			"mariadb": """
			UPDATE `tabLeave Ledger Entry` as lle
			SET company = (select company from `tabEmployee` where employee = lle.employee)
			WHERE company IS NULL
			""",
			"postgres": """
			UPDATE `tabLeave Ledger Entry`
			SET company = e.company
			FROM `tabEmployee` e
			WHERE `tabLeave Ledger Entry`.employee = e.employee
			AND `tabLeave Ledger Entry`.company IS NULL
			""",
		}
	)
	frappe.db.sql(
		{
			"mariadb": """
			UPDATE `tabLeave Allocation` as la
			SET company = (select company from `tabEmployee` where employee = la.employee)
			WHERE company IS NULL
			""",
			"postgres": """
			UPDATE `tabLeave Allocation`
			SET company = e.company
			FROM `tabEmployee` e
			WHERE `tabLeave Allocation`.employee = e.employee
			AND `tabLeave Allocation`.company IS NULL
			""",
		}
	)
