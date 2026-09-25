"""Vercel Python Function entry point for the CareSathi API."""

from server import CareSathiHandler, init_db


init_db()
handler = CareSathiHandler
