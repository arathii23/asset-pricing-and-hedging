"""Streamlit chat UI; secret values never appear in widgets, history or diagnostics."""

from __future__ import annotations

import os

import streamlit as st

from .assistant import ASSISTANT_BUILD, MAX_QUESTION, SECRET_PATTERN, answer_question, settings_from
from .knowledge import KnowledgeBase

VERSION_LABELS = {"resume_v1": "Original résumé experiment", "review_v2": "Later reviewed extension · October 2026"}
EXAMPLES = ["Who are you?", "What can you do?", "Explain this project without finance jargon.",
            "What is a share?", "Where does the 10.96% required return come from?", "What does the Sharpe ratio mean?"]


def load_settings():
    def get_value(name, default):
        try:
            return st.secrets.get(name, os.environ.get(name, default))
        except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
            return os.environ.get(name, default)
    return settings_from(get_value)


@st.cache_resource
def load_knowledge():
    return KnowledgeBase()


def show_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander("Sources and supporting notes"):
        for source in sources:
            if "text" not in source:
                st.caption(source["title"])
                continue
            st.markdown(f"**[{source['id']}] {source['title']}**")
            st.caption(f"{source['heading']} · {source['version']}")
            if source["path"].startswith("facts/"):
                st.json(source["text"], expanded=False)
            else:
                st.markdown(source["text"])
            st.caption(f"Knowledge-base file: {source['path']}")


def show_reply(message: dict) -> None:
    if message.get("warning"):
        st.warning(message["warning"])
    st.markdown(message["content"])
    mode = "Gemini + retrieved project notes" if message["route"] == "gemini_rag" else "Local project notes" if message["route"] == "project_notes" else "Local assistant guidance"
    st.caption(mode)
    show_sources(message.get("sources", []))


def clear_chat() -> None:
    st.session_state["assistant_messages"] = []
    # Deliberately keep usage counters and consent unchanged.


def render_assistant(summary: dict | None = None) -> None:
    st.markdown('<div class="eyebrow">Project learning assistant</div>', unsafe_allow_html=True)
    st.title("Ask the project")
    st.write("Understand the finance, follow the saved calculations and explore the ML experiment. Ask one small question at a time; the supporting project notes are shown with each answer.")
    kb, settings = load_knowledge(), load_settings()
    controls, actions = st.columns([3, 1])
    with controls:
        version = st.selectbox("Which analysis should we discuss?", list(VERSION_LABELS), format_func=VERSION_LABELS.get,
                               key="assistant_version", help="Original résumé scores and later reviewed methods are different experiments. Changing this selection starts a fresh chat.")
    with actions:
        st.write("")
        st.button("Clear chat", on_click=clear_chat, key="assistant_clear", width="stretch")
    if st.session_state.get("assistant_context_version") != version:
        clear_chat()
        st.session_state["assistant_context_version"] = version
    dashboard_version = "review_v2" if (summary or {}).get("audit_version") == 2 else "resume_v1"
    if dashboard_version != version:
        st.info(f"Chat context: {VERSION_LABELS[version]}. Dashboard charts: {VERSION_LABELS[dashboard_version]}. Select the matching version to discuss the chart values.")
    st.caption(f"Evidence: {VERSION_LABELS[version]} · Market snapshot: 22 September 2026 · Assistant build: {ASSISTANT_BUILD}")
    if settings.configured:
        st.caption(f"Gemini is configured · model: {settings.model} · connection is checked when you ask an AI question")
    else:
        st.info("Project-note mode is available. Gemini explanations will work once the owner configures a valid key in Streamlit Secrets and deploys this code.")
    allow_ai = st.checkbox("Use Gemini for explanations", value=False, disabled=not settings.configured, key="assistant_allow_ai",
                           help="Optional. Basic identity/help replies stay local. Other questions use the owner's Gemini quota.")
    st.caption("When enabled, your question, a few recent chat messages and selected public project notes are sent to Google. Don't enter API keys, personal financial records or confidential information. Without Gemini, you can still read matching project passages.")
    with st.expander("What this assistant can—and cannot—do"):
        st.write("Explain terminology, assumptions, recorded results and limitations; help navigate the website; show supporting notes. It cannot fetch live prices, trade, verify your personal contribution or run new financial calculations. Website sliders are separate from this chat.")
        st.write("The first RAG version uses local keyword retrieval, not semantic embeddings. AI answers can still be wrong: check their sources. Session limits and a best-effort server allowance reduce accidental usage; they are not a guaranteed billing cap.")
    st.subheader("Try a question")
    selected_question = None
    columns = st.columns(2)
    for index, question in enumerate(EXAMPLES):
        if columns[index % 2].button(question, key=f"assistant_example_{index}", width="stretch"):
            selected_question = question
    messages = st.session_state.setdefault("assistant_messages", [])
    if not messages:
        with st.chat_message("assistant"):
            st.write("I'm the Asset Pricing and Hedging Assistant. I can explain this project step by step. Try ‘What problem does this project solve?’ or ‘What is a share?’")
    for message in messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                show_reply(message)
            else:
                st.markdown(message["content"])
    typed = st.chat_input("Ask about this project…", max_chars=MAX_QUESTION, key="assistant_input")
    question = typed or selected_question
    if not question:
        return
    if SECRET_PATTERN.search(question):
        st.error("That looks like a credential. It wasn't sent to Gemini or added to chat history. If it was a real key, replace it privately in your provider account.")
        return
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Finding the relevant project notes…"):
            response = answer_question(kb, question, version, settings=settings, allow_ai=allow_ai,
                                       history=messages, usage=st.session_state.setdefault("assistant_usage", {}))
        show_reply(response)
    messages.extend([{"role": "user", "content": question, "version": version}, {"role": "assistant", **response}])
    # Keep a bounded session transcript; no on-disk chat logging or shared answer cache.
    st.session_state["assistant_messages"] = messages[-24:]
