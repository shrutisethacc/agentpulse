import time, json, urllib.request

QUERIES = [
    "My VPN keeps disconnecting every few minutes",
    "I forgot my password and cannot log in to my account",
    "My laptop screen is flickering and has black bars",
    "I need to install Microsoft Teams on my new laptop",
    "Cannot connect to the company Wi-Fi network",
    "My email inbox is not syncing on Outlook",
    "How do I reset my MFA authenticator after getting a new phone?",
    "The printer on floor 3 is showing offline status",
    "I need admin rights to install a software approved by my manager",
    "My computer is extremely slow and freezing frequently",
    "VPN certificate error when connecting from home",
    "I need to request a new hardware laptop, my current one is broken",
]

URL = "http://127.0.0.1:8001/invoke"

for i, q in enumerate(QUERIES, 1):
    print(f"[{i}/12] Sending: {q[:60]}", flush=True)
    t0 = time.time()
    payload = json.dumps({"query": q}).encode("utf-8")
    req = urllib.request.Request(URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read())
            intent = body.get("intent", "?")
            elapsed = time.time() - t0
            print(f"       -> intent={intent}  [{elapsed:.1f}s]", flush=True)
    except Exception as e:
        print(f"       -> ERROR: {e}", flush=True)
    if i < len(QUERIES):
        time.sleep(2)

print("All 12 queries done.", flush=True)
