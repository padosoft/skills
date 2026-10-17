"""report.py - Deliberately non-conforming fixture: a third-party import with no declared dependency,
and an interactive prompt an agent shell cannot answer."""
import requests

name = input("Report name: ")
print(requests.__name__, name)
