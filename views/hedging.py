"""Dollar receipts and hedge outcomes."""
from src.dashboard import load_summary, render_hedging

render_hedging(load_summary())
