import os
import json

csv_path = os.path.join(os.path.dirname(__file__), '../server/background_services/mock-leads-data.csv')
json_path = os.path.join(os.path.dirname(__file__), '../server/background_services/mock-leads-data.json')

leads = []
with open(csv_path, 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        # Remove outer quotes if present
        if line[0] == '"' and line[-1] == '"':
            line = line[1:-1]
        # Replace doubled double-quotes with single double-quote
        line = line.replace('""', '"')
        try:
            obj = json.loads(line)
            leads.append(obj)
        except Exception as e:
            print(f"Error parsing line: {line[:80]}...\n{e}")

with open(json_path, 'w') as f:
    json.dump(leads, f, indent=2)

print(f"Converted {len(leads)} leads to {json_path}") 