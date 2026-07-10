"""
utils.py — logging helpers for Rover.
"""
import json, os
from datetime import datetime

def log_run(repo: str, issue_num: int, summary: str, duration: float):
    os.makedirs('logs', exist_ok=True)
    filename = f'logs/run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    data = {
        'timestamp':        datetime.now().isoformat(),
        'repo':             repo,
        'issue_number':     issue_num,
        'summary':          summary,
        'duration_seconds': duration
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'Logged to {filename}')