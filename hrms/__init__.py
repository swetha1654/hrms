import frappe

__version__ = "17.0.0-dev"

# Ensure PostgreSQL-compatible overrides are registered in frappe's whitelist at startup
import hrms.overrides.goal  # noqa: E402, F401


def refetch_resource(cache_key: str | list, user=None):
	frappe.publish_realtime(
		"hrms:refetch_resource",
		{"cache_key": cache_key},
		user=user or frappe.session.user,
		after_commit=True,
	)
