"""Streamlit chat screen for the RAG API."""

import httpx
import streamlit as st

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="Harbor Desk", page_icon=":speech_balloon:")
st.title("Harbor Desk")
st.caption("Ask a question. Answers come from the vector database plus the language model.")

if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    health = httpx.get(f"{API}/api/health", timeout=5.0).json()
    st.caption(
        f"{health['documents']} document chunks in the vector database. Model: {health['model']}."
    )
except httpx.HTTPError:
    st.warning(f"API is not reachable at {API}.")

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.write(item["content"])
        if item.get("sources"):
            with st.expander(f"{len(item['sources'])} source(s)"):
                for source in item["sources"]:
                    st.markdown(f"**{source['source']}**")
                    st.write(source["text"])

if st.button("Clear"):
    st.session_state.messages = []
    st.rerun()

prompt = st.chat_input("Ask about Northwind Outfitters")
if prompt:
    history = [
        {"role": item["role"], "content": item["content"]}
        for item in st.session_state.messages
        if not item.get("error")
    ]
    st.session_state.messages.append({"role": "user", "content": prompt})
    try:
        with st.spinner("Thinking…"):
            response = httpx.post(
                f"{API}/api/chat",
                json={"message": prompt, "history": history},
                timeout=60.0,
            )
        data = response.json()
        if response.status_code >= 400:
            detail = data.get("detail") if isinstance(data, dict) else None
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": detail if isinstance(detail, str) else "Request failed.",
                    "error": True,
                }
            )
        else:
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": data.get("answer", ""),
                    "sources": data.get("sources") or [],
                }
            )
    except httpx.HTTPError:
        st.session_state.messages.append(
            {"role": "assistant", "content": "Could not reach the API.", "error": True}
        )
    st.rerun()
