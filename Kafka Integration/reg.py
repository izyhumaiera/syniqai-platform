import urllib.request, json, sys
data = open("/tmp/pg-connector.json", "rb").read()
req = urllib.request.Request("http://localhost:8083/connectors", data=data, headers={"Content-Type":"application/json"})
try:
    resp = urllib.request.urlopen(req)
    print("SUCCESS:", resp.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP ERROR", e.code, ":", e.read().decode())
except Exception as e:
    print("ERROR:", type(e).__name__, str(e))