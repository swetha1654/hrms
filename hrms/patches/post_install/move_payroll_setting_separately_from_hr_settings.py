# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	fields = [
		"encrypt_salary_slips_in_emails",
		"email_salary_slip_to_employee",
		"daily_wages_fraction_for_half_day",
		"disable_rounded_total",
		"include_holidays_in_total_working_days",
		"max_working_hours_against_timesheet",
		"payroll_based_on",
		"password_policy",
	]

	# frappe.get_all("Singles", ...) fails because "Singles" is an internal storage
	# table, not a registered DocType. Use direct SQL with single-quoted literals
	# which are valid in both MariaDB and PostgreSQL.
	placeholders = ", ".join(["%s"] * len(fields))
	data = frappe.db.sql(
		f"SELECT field, value FROM `tabSingles` WHERE doctype = 'HR Settings' AND field IN ({placeholders})",
		fields,
		as_dict=True,
	)

	for d in data:
		frappe.db.set_value("Payroll Settings", None, d.field, d.value)
