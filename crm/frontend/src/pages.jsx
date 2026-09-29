import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "./api";
import { money, pillClass, plusDays, shortDate } from "./format";
import { OBJECTS, blankForm, formFromRecord, recordLabel } from "./meta";

function cellText(object, row, column) {
  if (column.key === "name") return recordLabel(object, row);
  const value = row[column.key];
  if (value == null || value === "") return "—";
  if (column.money) return money(value);
  if (column.date) return shortDate(value);
  if (column.key === "probability") return value + "%";
  return String(value);
}

export function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api("/api/dashboard")
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p className="banner" role="alert">{error}</p>;
  if (!data) return <p className="muted">Loading the desk…</p>;
  const maxAmount = Math.max(...data.pipeline.map((stage) => Number(stage.amount)), 1);

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <h1>Overview</h1>
          <p className="muted">Open work across leads, pipeline, and quotes.</p>
        </div>
      </header>
      <div className="stats">
        <article>
          <span>Open leads</span>
          <strong>{data.counts.open_leads}</strong>
        </article>
        <article>
          <span>Accounts</span>
          <strong>{data.counts.accounts}</strong>
        </article>
        <article>
          <span>Open pipeline</span>
          <strong>{money(data.open_pipeline_amount)}</strong>
        </article>
        <article>
          <span>Accepted quotes</span>
          <strong>{money(data.accepted_quote_total)}</strong>
        </article>
      </div>
      <div className="split">
        <section className="panel">
          <h2>Pipeline by stage</h2>
          <ul className="bars">
            {data.pipeline.map((stage) => (
              <li key={stage.stage}>
                <div className="bar-label">
                  <span>{stage.stage}</span>
                  <span>{stage.count} · {money(stage.amount)}</span>
                </div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: Math.round((Number(stage.amount) / maxAmount) * 100) + "%" }}></div>
                </div>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <h2>Recent leads</h2>
          {data.recent_leads.length === 0 ? <p className="muted">No leads yet.</p> : null}
          <ul className="plain-list">
            {data.recent_leads.map((lead) => (
              <li key={lead.id}>
                <Link to={"/leads/" + lead.id}>{lead.first_name} {lead.last_name}</Link>
                <span className={pillClass(lead.status)}>{lead.status}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}

export function ListPage() {
  const { object } = useParams();
  const spec = OBJECTS[object];
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState(params.get("q") || "");

  useEffect(() => {
    if (!spec) return undefined;
    let cancelled = false;
    const search = new URLSearchParams();
    ["q", "status", "stage", "offset"].forEach((key) => {
      const value = params.get(key);
      if (value) search.set(key, value);
    });
    if (!search.get("limit")) search.set("limit", "50");
    api("/api/" + spec.key + "?" + search.toString())
      .then((body) => {
        if (!cancelled) {
          setData(body);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [spec, params]);

  if (!spec) return <p className="banner">That object is not in Harbor.</p>;

  function applyFilter(name, value) {
    const next = new URLSearchParams(params);
    if (!value || params.get(name) === value) next.delete(name);
    else next.set(name, value);
    next.delete("offset");
    setParams(next);
  }

  function submitSearch(event) {
    event.preventDefault();
    const next = new URLSearchParams(params);
    if (query.trim()) next.set("q", query.trim());
    else next.delete("q");
    next.delete("offset");
    setParams(next);
  }

  const offset = Number(params.get("offset") || 0);
  const total = data ? data.total : 0;

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <h1>{spec.plural}</h1>
          <p className="muted">{total} records</p>
        </div>
        <Link className="btn btn-primary" to={"/" + spec.key + "/new"}>New {spec.noun}</Link>
      </header>
      <div className="toolbar">
        <form onSubmit={submitSearch} className="search">
          <label htmlFor="record-search">Search</label>
          <input id="record-search" value={query} onChange={(event) => setQuery(event.target.value)} />
          <button className="btn" type="submit">Search</button>
        </form>
        {spec.filters.map((filter) => (
          <div key={filter.param} className="chips" role="group" aria-label={filter.label}>
            {filter.options.map((option) => (
              <button
                key={option}
                type="button"
                className={params.get(filter.param) === option ? "chip active" : "chip"}
                onClick={() => applyFilter(filter.param, option)}
              >
                {option}
              </button>
            ))}
          </div>
        ))}
      </div>
      {error ? <p className="banner" role="alert">{error}</p> : null}
      {!data ? <p className="muted">Loading {spec.plural.toLowerCase()}…</p> : null}
      {data && data.items.length === 0 ? <p className="muted">No {spec.plural.toLowerCase()} match this view.</p> : null}
      {data && data.items.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {spec.columns.map((column) => (
                  <th key={column.key} scope="col">{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <tr key={row.id}>
                  {spec.columns.map((column) => (
                    <td key={column.key}>
                      {column.key === "name" ? (
                        <Link to={"/" + spec.key + "/" + row.id}>{cellText(spec.key, row, column)}</Link>
                      ) : column.pill ? (
                        <span className={pillClass(row[column.key])}>{cellText(spec.key, row, column)}</span>
                      ) : (
                        cellText(spec.key, row, column)
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {data && total > 50 ? (
        <div className="pager">
          <button type="button" className="btn" disabled={offset === 0} onClick={() => applyOffset(params, setParams, Math.max(offset - 50, 0))}>Previous</button>
          <button type="button" className="btn" disabled={offset + 50 >= total} onClick={() => applyOffset(params, setParams, offset + 50)}>Next</button>
        </div>
      ) : null}
    </section>
  );
}

function applyOffset(params, setParams, offset) {
  const next = new URLSearchParams(params);
  if (offset) next.set("offset", String(offset));
  else next.delete("offset");
  setParams(next);
}

export function RecordPage() {
  const { object, id } = useParams();
  const spec = OBJECTS[object];
  const isNew = !id;
  const navigate = useNavigate();
  const [record, setRecord] = useState(null);
  const [form, setForm] = useState(spec ? blankForm(spec) : {});
  const [lookups, setLookups] = useState({});
  const [lines, setLines] = useState([]);
  const [related, setRelated] = useState([]);
  const [draft, setDraft] = useState({ product_name: "", quantity: "1", unit_price: "", discount_percent: "0" });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!spec) return undefined;
    let cancelled = false;
    Promise.all(
      spec.refs.map(async (ref) => {
        const body = await api("/api/" + ref + "?limit=200");
        return [ref, body.items];
      })
    )
      .then((entries) => {
        if (!cancelled) setLookups(Object.fromEntries(entries));
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [spec]);

  useEffect(() => {
    if (!spec) return undefined;
    let cancelled = false;
    async function load() {
      setError("");
      setNotice("");
      if (isNew) {
        setRecord(null);
        setForm(blankForm(spec));
        setLines([]);
        setRelated([]);
        return;
      }
      try {
        const row = await api("/api/" + spec.key + "/" + id);
        if (cancelled) return;
        setRecord(row);
        setForm(formFromRecord(spec, row));
        if (spec.key === "quotes") {
          const linePage = await api("/api/quotes/" + id + "/line-items");
          if (!cancelled) setLines(linePage.items);
        }
        if (spec.related.length) {
          const groups = await Promise.all(
            spec.related.map(async (item) => {
              const body = await api("/api/" + item.object + "?" + item.param + "=" + id + "&limit=20");
              return { ...item, items: body.items };
            })
          );
          if (!cancelled) setRelated(groups);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [spec, id, isNew]);

  if (!spec) return <p className="banner">That object is not in Harbor.</p>;
  const locked = spec.key === "leads" && record && record.status === "Converted";

  function updateField(name, value) {
    setForm((current) => {
      const next = { ...current, [name]: value };
      if (name === "account_id" && next.primary_contact_id) {
        const contact = (lookups.contacts || []).find((row) => row.id === next.primary_contact_id);
        if (contact && contact.account_id !== value) next.primary_contact_id = "";
      }
      if (name === "opportunity_id" && next.contact_id) {
        const opportunity = (lookups.opportunities || []).find((row) => row.id === value);
        const contact = (lookups.contacts || []).find((row) => row.id === next.contact_id);
        if (opportunity && contact && contact.account_id !== opportunity.account_id) next.contact_id = "";
      }
      return next;
    });
  }

  function buildPayload() {
    const body = {};
    for (const field of spec.fields) {
      let value = form[field.name];
      if (typeof value === "string") value = value.trim();
      if (value === "") value = null;
      if (field.required && (value === null || value === undefined)) {
        throw new Error(field.label + " is required");
      }
      if (field.type === "number") {
        if (value === null) continue;
        body[field.name] = Number(value);
        continue;
      }
      if (value === null && isNew && !field.required) continue;
      body[field.name] = value;
    }
    return body;
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const saved = await api(isNew ? "/api/" + spec.key : "/api/" + spec.key + "/" + id, {
        method: isNew ? "POST" : "PATCH",
        body: buildPayload(),
      });
      if (isNew) navigate("/" + spec.key + "/" + saved.id);
      else {
        setRecord(saved);
        setForm(formFromRecord(spec, saved));
        setNotice("Saved.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete this " + spec.noun + "?")) return;
    try {
      await api("/api/" + spec.key + "/" + id, { method: "DELETE" });
      navigate("/" + spec.key);
    } catch (err) {
      setError(err.message);
    }
  }

  async function refreshQuote() {
    const [quote, linePage] = await Promise.all([
      api("/api/quotes/" + id),
      api("/api/quotes/" + id + "/line-items"),
    ]);
    setRecord(quote);
    setLines(linePage.items);
  }

  async function addLine(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/quotes/" + id + "/line-items", {
        method: "POST",
        body: {
          product_name: draft.product_name.trim(),
          quantity: Number(draft.quantity),
          unit_price: Number(draft.unit_price),
          discount_percent: Number(draft.discount_percent || 0),
        },
      });
      setDraft({ product_name: "", quantity: "1", unit_price: "", discount_percent: "0" });
      await refreshQuote();
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveLine(line) {
    setError("");
    try {
      await api("/api/quotes/" + id + "/line-items/" + line.id, {
        method: "PATCH",
        body: {
          product_name: String(line.product_name).trim(),
          quantity: Number(line.quantity),
          unit_price: Number(line.unit_price),
          discount_percent: Number(line.discount_percent || 0),
          description: line.description || null,
        },
      });
      await refreshQuote();
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeLine(lineId) {
    setError("");
    try {
      await api("/api/quotes/" + id + "/line-items/" + lineId, { method: "DELETE" });
      await refreshQuote();
    } catch (err) {
      setError(err.message);
    }
  }

  const accountName = record && record.account_id
    ? recordLabel("accounts", (lookups.accounts || []).find((row) => row.id === record.account_id) || { name: "Linked account" })
    : "";

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <p className="crumb"><Link to={"/" + spec.key}>{spec.plural}</Link></p>
          <h1>{isNew ? "New " + spec.noun : recordLabel(spec.key, record) || spec.singular}</h1>
        </div>
        <div className="actions">
          {id && !locked ? <button type="button" className="btn btn-danger" onClick={remove}>Delete</button> : null}
          {!locked ? (
            <button type="submit" form="record-form" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          ) : null}
        </div>
      </header>
      {error ? <p className="banner" role="alert">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}
      <div className="record">
        <div>
          <form id="record-form" className="panel form-grid" onSubmit={save}>
            {spec.fields.map((field) => (
              <Field
                key={field.name}
                field={field}
                value={form[field.name] ?? ""}
                disabled={locked}
                lookups={lookups}
                form={form}
                onChange={updateField}
              />
            ))}
          </form>
          {spec.key === "quotes" && record ? (
            <section className="panel lines">
              <h2>Quote line items</h2>
              {lines.length === 0 ? <p className="muted">No lines yet.</p> : null}
              {lines.map((line) => (
                <div className="line" key={line.id}>
                  <label>
                    Product
                    <input value={line.product_name} onChange={(event) => setLines(updateLine(lines, line.id, "product_name", event.target.value))} />
                  </label>
                  <label>
                    Qty
                    <input value={line.quantity} onChange={(event) => setLines(updateLine(lines, line.id, "quantity", event.target.value))} />
                  </label>
                  <label>
                    Price
                    <input value={line.unit_price} onChange={(event) => setLines(updateLine(lines, line.id, "unit_price", event.target.value))} />
                  </label>
                  <label>
                    Discount %
                    <input value={line.discount_percent} onChange={(event) => setLines(updateLine(lines, line.id, "discount_percent", event.target.value))} />
                  </label>
                  <div className="line-total">
                    <span>Line total</span>
                    <strong>{money(line.line_total)}</strong>
                  </div>
                  <div className="line-actions">
                    <button type="button" className="btn" onClick={() => saveLine(line)}>Update</button>
                    <button type="button" className="btn btn-danger" onClick={() => removeLine(line.id)}>Remove</button>
                  </div>
                </div>
              ))}
              <form className="line" onSubmit={addLine}>
                <label>
                  Product
                  <input required value={draft.product_name} onChange={(event) => setDraft({ ...draft, product_name: event.target.value })} />
                </label>
                <label>
                  Qty
                  <input required value={draft.quantity} onChange={(event) => setDraft({ ...draft, quantity: event.target.value })} />
                </label>
                <label>
                  Price
                  <input required value={draft.unit_price} onChange={(event) => setDraft({ ...draft, unit_price: event.target.value })} />
                </label>
                <label>
                  Discount %
                  <input value={draft.discount_percent} onChange={(event) => setDraft({ ...draft, discount_percent: event.target.value })} />
                </label>
                <div className="line-actions">
                  <button className="btn btn-primary" type="submit">Add line</button>
                </div>
              </form>
            </section>
          ) : null}
          {spec.key === "quotes" && isNew ? <p className="muted">Save the quote before adding line items.</p> : null}
        </div>
        <aside className="side">
          {spec.key === "quotes" && record ? (
            <section className="panel">
              <h2>Totals</h2>
              <dl className="totals">
                <div><dt>Account</dt><dd>{accountName}</dd></div>
                <div><dt>Subtotal</dt><dd>{money(record.subtotal)}</dd></div>
                <div><dt>Discount</dt><dd>{money(record.discount_amount)}</dd></div>
                <div><dt>Tax</dt><dd>{money(record.tax_amount)}</dd></div>
                <div><dt>Grand total</dt><dd>{money(record.grand_total)}</dd></div>
              </dl>
              <p className="muted">Accepting the quote copies the grand total onto the opportunity amount.</p>
            </section>
          ) : null}
          {spec.key === "leads" && record && !locked ? (
            <ConvertPanel lead={record} onDone={(result) => navigate(result.opportunity ? "/opportunities/" + result.opportunity.id : "/accounts/" + result.account.id)} />
          ) : null}
          {locked ? (
            <section className="panel">
              <h2>Converted</h2>
              <ul className="plain-list">
                {record.converted_account_id ? <li><Link to={"/accounts/" + record.converted_account_id}>Open account</Link></li> : null}
                {record.converted_contact_id ? <li><Link to={"/contacts/" + record.converted_contact_id}>Open contact</Link></li> : null}
                {record.converted_opportunity_id ? <li><Link to={"/opportunities/" + record.converted_opportunity_id}>Open opportunity</Link></li> : null}
              </ul>
            </section>
          ) : null}
          {related.map((group) => (
            <section className="panel" key={group.title}>
              <h2>{group.title}</h2>
              {group.items.length === 0 ? <p className="muted">None yet.</p> : null}
              <ul className="plain-list">
                {group.items.map((item) => (
                  <li key={item.id}>
                    <Link to={"/" + group.object + "/" + item.id}>{recordLabel(group.object, item)}</Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </aside>
      </div>
    </section>
  );
}

function updateLine(lines, lineId, key, value) {
  return lines.map((line) => (line.id === lineId ? { ...line, [key]: value } : line));
}

function Field({ field, value, disabled, lookups, form, onChange }) {
  const id = "field-" + field.name;
  const className = field.wide ? "field field-wide" : "field";
  let control = null;
  if (field.type === "textarea") {
    control = <textarea id={id} rows="4" disabled={disabled} value={value} onChange={(event) => onChange(field.name, event.target.value)} />;
  } else if (field.type === "select") {
    control = (
      <select id={id} disabled={disabled} required={field.required} value={value} onChange={(event) => onChange(field.name, event.target.value)}>
        {field.required ? null : <option value="">None</option>}
        {(field.options.includes(value) || !value ? field.options : [...field.options, value]).map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    );
  } else if (field.type === "ref") {
    let rows = lookups[field.ref] || [];
    if (field.name === "primary_contact_id") {
      rows = rows.filter((row) => row.account_id === form.account_id);
    }
    if (field.name === "contact_id") {
      const opportunity = (lookups.opportunities || []).find((row) => row.id === form.opportunity_id);
      rows = opportunity ? rows.filter((row) => row.account_id === opportunity.account_id) : [];
    }
    control = (
      <select id={id} disabled={disabled} required={field.required} value={value} onChange={(event) => onChange(field.name, event.target.value)}>
        {field.required ? <option value="">Select</option> : <option value="">None</option>}
        {rows.map((row) => (
          <option key={row.id} value={row.id}>{recordLabel(field.ref, row)}</option>
        ))}
      </select>
    );
  } else {
    control = (
      <input
        id={id}
        type={field.type === "number" ? "number" : field.type}
        disabled={disabled}
        required={field.required}
        min={field.min}
        max={field.max}
        step={field.step}
        value={value}
        onChange={(event) => onChange(field.name, event.target.value)}
      />
    );
  }
  return (
    <div className={className}>
      <label htmlFor={id}>{field.label}</label>
      {control}
    </div>
  );
}

function ConvertPanel({ lead, onDone }) {
  const [accountName, setAccountName] = useState(lead.company || lead.first_name + " " + lead.last_name);
  const [createOpportunity, setCreateOpportunity] = useState(true);
  const [opportunityName, setOpportunityName] = useState((lead.company || lead.last_name) + " opportunity");
  const [closeDate, setCloseDate] = useState(plusDays(30));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api("/api/leads/" + lead.id + "/convert", {
        method: "POST",
        body: {
          account_name: accountName,
          create_opportunity: createOpportunity,
          opportunity_name: createOpportunity ? opportunityName : null,
          close_date: createOpportunity ? closeDate : null,
        },
      });
      onDone(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <h2>Convert lead</h2>
      <p className="muted">Creates an account, a contact, and an optional opportunity.</p>
      <label htmlFor="convert-account">Account name</label>
      <input id="convert-account" value={accountName} onChange={(event) => setAccountName(event.target.value)} required />
      <label className="check">
        <input type="checkbox" checked={createOpportunity} onChange={(event) => setCreateOpportunity(event.target.checked)} />
        Create opportunity
      </label>
      {createOpportunity ? (
        <>
          <label htmlFor="convert-opp">Opportunity name</label>
          <input id="convert-opp" value={opportunityName} onChange={(event) => setOpportunityName(event.target.value)} required />
          <label htmlFor="convert-close">Close date</label>
          <input id="convert-close" type="date" value={closeDate} onChange={(event) => setCloseDate(event.target.value)} required />
        </>
      ) : null}
      {error ? <p className="banner" role="alert">{error}</p> : null}
      <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Converting…" : "Convert"}</button>
    </form>
  );
}
