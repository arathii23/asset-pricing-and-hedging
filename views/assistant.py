"""Beginner-friendly project RAG assistant."""
from src.assistant_ui import render_assistant
from src.dashboard import load_summary

render_assistant(load_summary())
