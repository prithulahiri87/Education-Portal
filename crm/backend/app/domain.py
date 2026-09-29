"""Shared CRM vocabulary. Stored values and UI filters both use these lists."""

LEAD_STATUSES = ("New", "Working", "Qualified", "Unqualified", "Converted")
EDITABLE_LEAD_STATUSES = tuple(status for status in LEAD_STATUSES if status != "Converted")
LEAD_SOURCES = ("Web", "Phone", "Referral", "Partner", "Campaign", "Other")
LEAD_RATINGS = ("Hot", "Warm", "Cold")

ACCOUNT_TYPES = ("Prospect", "Customer", "Partner", "Other")

OPPORTUNITY_STAGES = (
    "Prospecting",
    "Qualification",
    "Needs Analysis",
    "Proposal",
    "Negotiation",
    "Closed Won",
    "Closed Lost",
)
CLOSED_STAGES = ("Closed Won", "Closed Lost")
STAGE_PROBABILITY = {
    "Prospecting": 10,
    "Qualification": 20,
    "Needs Analysis": 40,
    "Proposal": 60,
    "Negotiation": 80,
    "Closed Won": 100,
    "Closed Lost": 0,
}

QUOTE_STATUSES = ("Draft", "In Review", "Presented", "Accepted", "Rejected", "Expired")
OPEN_QUOTE_STATUSES = ("Draft", "In Review", "Presented")


def in_list(column, values, allow_null=False):
    choices = ", ".join("'" + value + "'" for value in values)
    clause = column + " IN (" + choices + ")"
    if allow_null:
        return "(" + column + " IS NULL OR " + clause + ")"
    return clause


def percent_check(column):
    return column + " >= 0 AND " + column + " <= 100"
