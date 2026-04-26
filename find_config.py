import json
import os

log_path = r'C:\Users\Leonit\.gemini\antigravity\brain\89951b77-704a-401d-a8af-d530af7ce585\.system_generated\logs\overview.txt'

if not os.path.exists(log_path):
    print(f"Log not found at {log_path}")
    exit(1)

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        if 'storyConfig' in line:
            print(line)
