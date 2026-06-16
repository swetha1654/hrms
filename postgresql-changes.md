# PostgreSQL Compatibility Changes

This document summarises all changes made to support PostgreSQL in HRMS, and their MariaDB compatibility status.

## Docker Setup

### `docker/docker-compose.yml`
- Replaced `mariadb:10.8` service with `postgres:15`
- Updated volume from `mariadb-data` to `postgres-data`
- Replaced `MYSQL_ROOT_PASSWORD` env var with `POSTGRES_PASSWORD` / `POSTGRES_USER`

### `docker/init.sh`
- Replaced `bench set-mariadb-host mariadb` with `bench set-config -g db_host postgres`
- Updated `bench new-site` flags: replaced `--mariadb-root-password` / `--no-mariadb-socket` with `--db-type postgres --db-host postgres --db-port 5432 --db-root-username postgres --db-root-password`
- Changed `bench get-app hrms` to install from the fork (`https://github.com/swetha1654/hrms`) on branch `feat/postgresql-develop`

---

## Code Fixes

### 1. `hrms/overrides/employee_master.py`
**Issue:** Raw SQL used `unix_timestamp()` and `date_sub(curdate(), interval 1 year)` — MySQL/MariaDB-only functions.  
**Fix:** Replaced `frappe.db.sql` with `frappe.db.multisql`, providing separate queries for each database:
- MariaDB: original query unchanged
- PostgreSQL: `EXTRACT(EPOCH FROM attendance_date::timestamp)::bigint` and `CURRENT_DATE - INTERVAL '1 year'`

**MariaDB compatibility:** ✅ MariaDB gets the original query via `multisql`.

---

### 2. `hrms/payroll/doctype/payroll_entry/payroll_entry.py`
**Issue:** Raw SQL used MySQL's two-argument `LIMIT start, count` syntax, which is not valid in PostgreSQL.  
**Fix:** Replaced `frappe.db.sql` with `frappe.db.multisql`:
- MariaDB: original `LIMIT %(start)s, %(page_len)s` unchanged
- PostgreSQL: `LIMIT %(page_len)s OFFSET %(start)s` with single-quoted string literals

**MariaDB compatibility:** ✅ MariaDB gets the original query via `multisql`.

---

### 3. `hrms/hr/utils.py`
**Issue 1:** `parentfield = "earnings"` and `parenttype = "Salary Slip"` — double-quoted string literals.  
In PostgreSQL, `"..."` is an *identifier* (column/table name), not a string value, causing `UndefinedColumn` errors.  
**Fix:** Changed to single-quoted string literals: `parentfield = 'earnings'`, `parenttype = 'Salary Slip'`.

**Issue 2:** Column alias `as 'total_amount'` — single-quoted aliases are non-standard.  
**Fix:** Changed to unquoted alias: `as total_amount`.

**MariaDB compatibility:** ✅ Single-quoted string literals and unquoted aliases are valid standard SQL, working identically in both databases. The result dict key is `total_amount` either way. No `multisql` needed — these were bugs in the original code, not database-specific syntax.

---

### 4. `hrms/patches/post_install/move_payroll_setting_separately_from_hr_settings.py`
**Issue:** SQL WHERE clause used double-quoted string literals: `doctype = "HR Settings"`, `field in ("encrypt_salary_slips_in_emails", ...)`.  
PostgreSQL interpreted these as column references, causing `UndefinedColumn: column "HR Settings" does not exist`.  
**Fix:** Replaced all double-quoted string literals with single quotes.

**MariaDB compatibility:** ✅ Standard SQL single quotes work in both databases. No `multisql` needed.

---

### 5. `hrms/patches/post_install/move_tax_slabs_from_payroll_period_to_income_tax_slab.py`
**Issue:** SQL SET used `parenttype = "Income Tax Slab"` — double-quoted string literal.  
**Fix:** Changed to `parenttype = 'Income Tax Slab'`.

**MariaDB compatibility:** ✅ Same reasoning as above — standard SQL single quotes work in both databases.

---

### 6. `hrms/patches/post_install/update_employee_advance_status.py`
**Issue:** frappe QueryBuilder expressions `(advance.return_amount)` and `(advance.claimed_amount & advance.return_amount)` used numeric fields as boolean expressions.  
MariaDB accepts non-zero numerics as truthy in WHERE clauses; PostgreSQL requires an explicit boolean expression.  
**Fix:** Replaced with explicit `> 0` comparisons:
- `(advance.return_amount)` → `(advance.return_amount > 0)`
- `(advance.claimed_amount & advance.return_amount)` → `(advance.claimed_amount > 0) & (advance.return_amount > 0)`

**MariaDB compatibility:** ✅ `> 0` is semantically equivalent to the truthy check for non-negative monetary amounts, and is valid in both databases.

---

### 7. `hrms/overrides/goal.py` *(new file)*
**Issue:** `frappe/utils/goal.py` (frappe core) calls `Function(aggregation, goal_field)` where `goal_field` is a plain string (e.g. `"base_grand_total"`). PostgreSQL's `sum()` cannot resolve the type of a string literal argument, raising `function sum(unknown) is not unique`.  
**Fix:** Created `hrms/overrides/goal.py` — a fixed copy of `get_monthly_goal_graph_data` that passes `Table[goal_field]` (a column reference) instead of a raw string to `Function()`.

Registered in `hrms/hooks.py` via `override_whitelisted_methods`:
```python
override_whitelisted_methods = {
    "frappe.utils.goal.get_monthly_goal_graph_data": "hrms.overrides.goal.get_monthly_goal_graph_data",
}
```

Also imported in `hrms/__init__.py` to ensure the `@frappe.whitelist()` decorator registers the function in frappe's whitelist at app startup (required for `override_whitelisted_methods` to take effect).

**MariaDB compatibility:** ✅ `Table[goal_field]` produces a proper column reference in both databases. The `date_format` variable already uses `frappe.db.db_type` to select the correct format string for each database (`%m-%Y` for MariaDB, `MM-YYYY` for PostgreSQL).

---

## Why `multisql` Was Not Used for All Fixes

`frappe.db.multisql` is necessary only when the SQL **function/syntax itself** differs between databases (e.g. `unix_timestamp()` vs `EXTRACT(EPOCH FROM ...)`).

For changes 3–6 above, the fixes use standard SQL that is valid in **both** databases:
- Single-quoted string literals (`'value'`) are the SQL standard — double quotes were the original bug
- Unquoted or double-quoted column aliases work in both
- Explicit `> 0` comparisons are cleaner and work in both

Using `multisql` unnecessarily would duplicate code and make future maintenance harder.
