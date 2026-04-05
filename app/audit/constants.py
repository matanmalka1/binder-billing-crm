"""
Entity type and action constants for the generic audit log.

Use these constants in service code — never raw strings.
"""

# Entity types
ENTITY_BUSINESS = "business"
ENTITY_TAX_PROFILE = "business_tax_profile"
ENTITY_CLIENT = "client"
ENTITY_CHARGE = "charge"
ENTITY_ANNUAL_REPORT = "annual_report"

# Shared actions
ACTION_CREATED = "created"
ACTION_UPDATED = "updated"
ACTION_DELETED = "deleted"
ACTION_RESTORED = "restored"

# Business tax profile
ACTION_PROFILE_UPDATED = "profile_updated"

# Charge-specific status transitions
ACTION_ISSUED = "issued"
ACTION_PAID = "paid"
ACTION_CANCELED = "canceled"

# Annual report status transition
ACTION_STATUS_CHANGED = "status_changed"

# Annual report financial lines
ACTION_INCOME_ADDED = "income_added"
ACTION_INCOME_UPDATED = "income_updated"
ACTION_INCOME_DELETED = "income_deleted"
ACTION_EXPENSE_ADDED = "expense_added"
ACTION_EXPENSE_UPDATED = "expense_updated"
ACTION_EXPENSE_DELETED = "expense_deleted"
