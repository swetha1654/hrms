# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# Override of frappe.utils.goal to fix PostgreSQL compatibility.
# frappe's get_monthly_results passes goal_field as a raw string to Function(),
# which PostgreSQL interprets as a string literal ('base_grand_total') instead
# of a column reference, causing: "function sum(unknown) is not unique".
# Fix: wrap goal_field in Table[goal_field] to produce a proper column reference.

from contextlib import suppress

import frappe
from frappe import _
from frappe.query_builder.functions import DateFormat, Function
from frappe.query_builder.utils import DocType
from frappe.utils.data import add_to_date, cstr, flt, now_datetime
from frappe.utils.formatters import format_value


def _get_monthly_results(
	goal_doctype: str,
	goal_field: str,
	date_col: str,
	filters: dict,
	aggregation: str = "sum",
) -> dict:
	"""Get monthly aggregation values for given field of doctype.

	Fixed version: uses Table[goal_field] so the field is treated as a column
	reference rather than a string literal — required for PostgreSQL compatibility.
	"""
	if aggregation.lower() not in {"sum", "avg", "count", "min", "max"}:
		frappe.throw(f"Invalid aggregation type: {aggregation}")

	valid_fields = frappe.get_meta(goal_doctype).get_valid_fields()
	if goal_field not in valid_fields:
		frappe.throw(f"Invalid goal field: {goal_field}")
	if date_col not in valid_fields:
		frappe.throw(f"Invalid date field: {date_col}")

	Table = DocType(goal_doctype)
	date_format = "%m-%Y" if frappe.db.db_type != "postgres" else "MM-YYYY"

	return dict(
		frappe.qb.get_query(
			table=goal_doctype,
			fields=[
				DateFormat(Table[date_col], date_format).as_("month_year"),
				Function(aggregation, Table[goal_field]),  # Table[goal_field] = column ref, not literal
			],
			filters=filters,
			ignore_permissions=False,
		)
		.groupby("month_year")
		.run()
	)


@frappe.whitelist()
def get_monthly_goal_graph_data(
	title: str,
	doctype: str,
	docname: str,
	goal_value_field: str,
	goal_total_field: str,
	goal_history_field: str,
	goal_doctype: str,
	goal_doctype_link: str,
	goal_field: str,
	date_field: str,
	aggregation: str = "sum",
	filters: str | dict | None = None,
) -> dict:
	"""Override of frappe.utils.goal.get_monthly_goal_graph_data with PostgreSQL fix."""
	doc = frappe.get_doc(doctype, docname)
	doc.check_permission()

	meta = doc.meta
	goal = doc.get(goal_value_field)
	today_date = now_datetime().date()

	current_month_value = doc.get(goal_total_field)
	current_month_year = today_date.strftime("%m-%Y")
	formatted_value = format_value(current_month_value, meta.get_field(goal_total_field), doc)
	history = doc.get(goal_history_field)

	month_to_value_dict = None
	if history and "{" in cstr(history):
		with suppress(ValueError):
			month_to_value_dict = frappe.parse_json(history)

	if month_to_value_dict is None:  # nosemgrep
		doc_filter = {}
		with suppress(ValueError):
			doc_filter = frappe.parse_json(filters or "{}")
		if doctype != goal_doctype:
			doc_filter[goal_doctype_link] = docname

		month_to_value_dict = _get_monthly_results(
			goal_doctype, goal_field, date_field, doc_filter, aggregation
		)

	month_to_value_dict[current_month_year] = current_month_value

	month_labels = []
	dataset_values = []
	values_formatted = []
	y_markers = {}

	summary_values = [
		{"title": _("This month"), "color": "#ffa00a", "value": formatted_value},
	]

	if flt(goal) > 0:
		formatted_goal = format_value(goal, meta.get_field(goal_value_field), doc)
		summary_values += [
			{"title": _("Goal"), "color": "#5e64ff", "value": formatted_goal},
			{
				"title": _("Completed"),
				"color": "#28a745",
				"value": f"{round(flt(current_month_value) / flt(goal) * 100)}%",
			},
		]
		y_markers = {"yMarkers": [{"label": _("Goal"), "lineType": "dashed", "value": flt(goal)}]}

	for i in range(12):
		date_value = add_to_date(today_date, months=-i, as_datetime=True)
		month_word = date_value.strftime("%b %y")
		month_labels.insert(0, month_word)

		month_value = date_value.strftime("%m-%Y")
		val = month_to_value_dict.get(month_value, 0)
		dataset_values.insert(0, val)
		values_formatted.insert(0, format_value(val, meta.get_field(goal_total_field), doc))

	return {
		"title": title,
		"data": {
			"datasets": [{"values": dataset_values, "formatted": values_formatted}],
			"labels": month_labels,
			**y_markers,
		},
		"summary": summary_values,
	}
