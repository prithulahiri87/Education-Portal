import { plusDays } from "./format";

const LEAD_STATUSES = ["New", "Working", "Qualified", "Unqualified"];
const SOURCES = ["Web", "Phone", "Referral", "Partner", "Campaign", "Other"];
const RATINGS = ["Hot", "Warm", "Cold"];
const ACCOUNT_TYPES = ["Prospect", "Customer", "Partner", "Other"];
const STAGES = [
  "Prospecting",
  "Qualification",
  "Needs Analysis",
  "Proposal",
  "Negotiation",
  "Closed Won",
  "Closed Lost",
];
const QUOTE_STATUSES = ["Draft", "In Review", "Presented", "Accepted", "Rejected", "Expired"];

export const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/leads", label: "Leads" },
  { to: "/accounts", label: "Accounts" },
  { to: "/contacts", label: "Contacts" },
  { to: "/opportunities", label: "Opportunities" },
  { to: "/quotes", label: "Quotes" },
];

export const OBJECTS = {
  leads: {
    key: "leads",
    singular: "Lead",
    plural: "Leads",
    noun: "lead",
    refs: [],
    related: [],
    filters: [{ param: "status", label: "Status", options: [...LEAD_STATUSES, "Converted"] }],
    columns: [
      { key: "name", label: "Name" },
      { key: "company", label: "Company" },
      { key: "status", label: "Status", pill: true },
      { key: "source", label: "Source" },
      { key: "rating", label: "Rating" },
    ],
    fields: [
      { name: "first_name", label: "First name", type: "text", required: true },
      { name: "last_name", label: "Last name", type: "text", required: true },
      { name: "company", label: "Company", type: "text" },
      { name: "title", label: "Title", type: "text" },
      { name: "email", label: "Email", type: "email" },
      { name: "phone", label: "Phone", type: "tel" },
      { name: "status", label: "Status", type: "select", required: true, options: LEAD_STATUSES, default: "New" },
      { name: "source", label: "Source", type: "select", options: SOURCES, default: "Web" },
      { name: "rating", label: "Rating", type: "select", options: RATINGS },
      { name: "description", label: "Notes", type: "textarea", wide: true },
    ],
  },
  accounts: {
    key: "accounts",
    singular: "Account",
    plural: "Accounts",
    noun: "account",
    refs: [],
    related: [
      { title: "Contacts", object: "contacts", param: "account_id" },
      { title: "Opportunities", object: "opportunities", param: "account_id" },
      { title: "Quotes", object: "quotes", param: "account_id" },
    ],
    filters: [],
    columns: [
      { key: "name", label: "Name" },
      { key: "type", label: "Type", pill: true },
      { key: "industry", label: "Industry" },
      { key: "phone", label: "Phone" },
      { key: "annual_revenue", label: "Revenue", money: true },
    ],
    fields: [
      { name: "name", label: "Account name", type: "text", required: true, wide: true },
      { name: "type", label: "Type", type: "select", required: true, options: ACCOUNT_TYPES, default: "Prospect" },
      { name: "industry", label: "Industry", type: "text" },
      { name: "website", label: "Website", type: "text" },
      { name: "phone", label: "Phone", type: "tel" },
      { name: "annual_revenue", label: "Annual revenue", type: "number", min: 0, step: "0.01" },
      { name: "employee_count", label: "Employees", type: "number", min: 0, step: "1" },
      { name: "billing_street", label: "Street", type: "text", wide: true },
      { name: "billing_city", label: "City", type: "text" },
      { name: "billing_state", label: "State", type: "text" },
      { name: "billing_postal_code", label: "Postal code", type: "text" },
      { name: "billing_country", label: "Country", type: "text" },
      { name: "description", label: "Notes", type: "textarea", wide: true },
    ],
  },
  contacts: {
    key: "contacts",
    singular: "Contact",
    plural: "Contacts",
    noun: "contact",
    refs: ["accounts"],
    related: [
      { title: "Opportunities", object: "opportunities", param: "primary_contact_id" },
      { title: "Quotes", object: "quotes", param: "contact_id" },
    ],
    filters: [],
    columns: [
      { key: "name", label: "Name" },
      { key: "title", label: "Title" },
      { key: "email", label: "Email" },
      { key: "phone", label: "Phone" },
    ],
    fields: [
      { name: "account_id", label: "Account", type: "ref", ref: "accounts", required: true, wide: true },
      { name: "first_name", label: "First name", type: "text", required: true },
      { name: "last_name", label: "Last name", type: "text", required: true },
      { name: "title", label: "Title", type: "text" },
      { name: "department", label: "Department", type: "text" },
      { name: "email", label: "Email", type: "email" },
      { name: "phone", label: "Phone", type: "tel" },
      { name: "description", label: "Notes", type: "textarea", wide: true },
    ],
  },
  opportunities: {
    key: "opportunities",
    singular: "Opportunity",
    plural: "Opportunities",
    noun: "opportunity",
    refs: ["accounts", "contacts"],
    related: [{ title: "Quotes", object: "quotes", param: "opportunity_id" }],
    filters: [{ param: "stage", label: "Stage", options: STAGES }],
    columns: [
      { key: "name", label: "Name" },
      { key: "stage", label: "Stage", pill: true },
      { key: "amount", label: "Amount", money: true },
      { key: "probability", label: "Probability" },
      { key: "close_date", label: "Close date", date: true },
    ],
    fields: [
      { name: "name", label: "Opportunity name", type: "text", required: true, wide: true },
      { name: "account_id", label: "Account", type: "ref", ref: "accounts", required: true },
      { name: "primary_contact_id", label: "Primary contact", type: "ref", ref: "contacts" },
      { name: "stage", label: "Stage", type: "select", required: true, options: STAGES, default: "Prospecting" },
      { name: "amount", label: "Amount", type: "number", min: 0, step: "0.01" },
      { name: "probability", label: "Probability", type: "number", min: 0, max: 100, step: "1" },
      { name: "close_date", label: "Close date", type: "date", required: true, default: "today+30" },
      { name: "description", label: "Notes", type: "textarea", wide: true },
    ],
  },
  quotes: {
    key: "quotes",
    singular: "Quote",
    plural: "Quotes",
    noun: "quote",
    refs: ["opportunities", "contacts", "accounts"],
    related: [],
    filters: [{ param: "status", label: "Status", options: QUOTE_STATUSES }],
    columns: [
      { key: "name", label: "Name" },
      { key: "status", label: "Status", pill: true },
      { key: "grand_total", label: "Total", money: true },
      { key: "expiration_date", label: "Expires", date: true },
    ],
    fields: [
      { name: "name", label: "Quote name", type: "text", required: true, wide: true },
      { name: "opportunity_id", label: "Opportunity", type: "ref", ref: "opportunities", required: true },
      { name: "contact_id", label: "Contact", type: "ref", ref: "contacts" },
      { name: "status", label: "Status", type: "select", required: true, options: QUOTE_STATUSES, default: "Draft" },
      { name: "expiration_date", label: "Expiration date", type: "date", default: "today+30" },
      { name: "discount_percent", label: "Header discount %", type: "number", min: 0, max: 100, step: "0.01", default: "0" },
      { name: "tax_percent", label: "Tax %", type: "number", min: 0, max: 100, step: "0.01", default: "0" },
      { name: "description", label: "Notes", type: "textarea", wide: true },
    ],
  },
};

export function recordLabel(object, row) {
  if (!row) return "";
  if (object === "leads" || object === "contacts") {
    return (row.first_name + " " + row.last_name).trim();
  }
  return row.name || "";
}

export function blankForm(spec) {
  const form = {};
  spec.fields.forEach((field) => {
    if (field.default === "today+30") form[field.name] = plusDays(30);
    else form[field.name] = field.default ?? "";
  });
  return form;
}

export function formFromRecord(spec, record) {
  const form = blankForm(spec);
  spec.fields.forEach((field) => {
    const value = record[field.name];
    form[field.name] = value == null ? "" : String(value);
  });
  return form;
}
