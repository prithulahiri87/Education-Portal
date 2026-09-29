import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("Checking API…");

  useEffect(() => {
    fetch(`${API}/api/health`)
      .then((response) => response.json())
      .then((data) => {
        setStatus(`${data.documents} document chunks in the vector database. Model: ${data.model}.`);
      })
      .catch(() => setStatus(`API is not reachable at ${API}.`));
  }, []);

  async function onSubmit(event) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || busy) return;
    const history = messages
      .filter((item) => !item.error)
      .map((item) => ({ role: item.role, content: item.content }));
    setMessages((current) => [...current, { role: "user", content: message }]);
    setDraft("");
    setBusy(true);
    try {
      const response = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail = typeof data.detail === "string" ? data.detail : "Request failed.";
        setMessages((current) => [...current, { role: "assistant", content: detail, error: true }]);
        return;
      }
      setMessages((current) => [
        ...current,
        { role: "assistant", content: data.answer, sources: data.sources || [] },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: "Could not reach the API.", error: true },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <header>
        <h1>Harbor Desk</h1>
        <p>Ask a question. Answers come from the vector database plus the language model.</p>
        <div className="status">{status}</div>
      </header>
      <section className="log" aria-live="polite">
        {messages.map((item, index) => (
          <article key={index} className={item.role === "user" ? "bubble user" : "bubble"}>
            <div className={item.error ? "error" : undefined}>{item.content}</div>
            {item.sources && item.sources.length > 0 && (
              <details className="sources">
                <summary>
                  {item.sources.length} source{item.sources.length === 1 ? "" : "s"}
                </summary>
                {item.sources.map((source) => (
                  <p key={source.id}>
                    {source.source}: {source.text}
                  </p>
                ))}
              </details>
            )}
          </article>
        ))}
        {busy && <article className="bubble">Thinking…</article>}
      </section>
      <form onSubmit={onSubmit}>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask about Northwind Outfitters"
          autoComplete="off"
          required
        />
        <button type="button" className="secondary" onClick={() => setMessages([])}>
          Clear
        </button>
        <button type="submit" disabled={busy}>
          Send
        </button>
      </form>
    </main>
  );
}
