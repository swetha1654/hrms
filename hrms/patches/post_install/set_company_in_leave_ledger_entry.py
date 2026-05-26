import frappe


def execute():
	frappe.reload_doc("HR", "doctype", "Leave Allocation")
	frappe.reload_doc("HR", "doctype", "Leave Ledger Entry")
	# Use correlated subquery without aliases — valid in both MariaDB and PostgreSQL.
	# The frappe dict syntax {"mariadb": ..., "postgres": ...} is not supported by
	# all frappe versions and passes the dict as raw SQL, causing a syntax error.
	frappe.db.sql(
		"""
		UPDATE `tabLeave Ledger Entry`
		SET company = (
			SELECT company FROM `tabEmployee`
			WHERE employee = `tabLeave Ledger Entry`.employee
		)
		WHERE company IS NULL
		"""
	)
	frappe.db.sql(
		"""
		UPDATE `tabLeave Allocation`
		SET company = (
			SELECT company FROM `tabEmployee`
			WHERE employee = `tabLeave Allocation`.employee
		)
		WHERE company IS NULL
		"""
	)
