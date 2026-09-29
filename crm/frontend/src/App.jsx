import { useEffect, useState } from "react";
import { NavLink, Outlet, Route, Routes } from "react-router-dom";
import { api, setToken } from "./api";
import { NAV } from "./meta";
import { Dashboard, ListPage, RecordPage } from "./pages";

export function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");
  const [unlocked, setUnlocked] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api("/api/health")
      .then((body) => {
        if (cancelled) return;
        setHealth(body);
        if (!body.auth_required) setUnlocked(true);
      })
      .catch(() => {
        if (!cancelled) setHealthError("The Harbor API is not running. Start it on 127.0.0.1:8090.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (healthError) {
    return (
      <main className="gate">
        <p className="banner" role="alert">{healthError}</p>
      </main>
    );
  }
  if (!health) {
    return (
      <main className="gate">
        <p>Opening the desk…</p>
      </main>
    );
  }
  if (health.auth_required && !unlocked) {
    return <TokenGate onUnlock={() => setUnlocked(true)} />;
  }
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path=":object/new" element={<RecordPage />} />
        <Route path=":object/:id" element={<RecordPage />} />
        <Route path=":object" element={<ListPage />} />
      </Route>
    </Routes>
  );
}

function Shell() {
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <span className="mark" aria-hidden="true"></span>
          <div>
            <strong>Harbor</strong>
            <span>Sales desk</span>
          </div>
        </div>
        <nav aria-label="Records">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="workspace">
        <Outlet />
      </div>
    </div>
  );
}

function TokenGate({ onUnlock }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setToken(value.trim());
    try {
      await api("/api/leads?limit=1");
      onUnlock();
    } catch (err) {
      setToken("");
      setError(err.status === 401 ? "That token was not accepted." : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="gate">
      <form className="gate-card" onSubmit={submit}>
        <h1>Harbor</h1>
        <p>This API expects a bearer token. It stays in memory for this tab only.</p>
        <label htmlFor="token">API token</label>
        <input id="token" type="password" value={value} autoComplete="off" onChange={(event) => setValue(event.target.value)} />
        {error ? <p className="banner" role="alert">{error}</p> : null}
        <button className="btn btn-primary" type="submit" disabled={busy || !value.trim()}>
          {busy ? "Checking…" : "Continue"}
        </button>
      </form>
    </main>
  );
}
