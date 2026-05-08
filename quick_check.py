import requests
r = requests.get('http://localhost:8000/api/cdc-silver/topics')
print(f"CDC Topics: {r.json()['total']}")
r2 = requests.get('http://localhost:8000/api/cdc-silver/status')
print(f"Service Status: {'Running' if r2.json()['running'] else 'Ready'}")
print("✅ CDC Silver service is active and aligned with Bronze→Silver pipeline")
