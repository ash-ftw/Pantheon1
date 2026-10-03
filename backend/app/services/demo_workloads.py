"""Demo Applications Workload Generator and Runtime Support.

Provides self-contained, real runnable source code, SQLite databases,
interactive HTML frontends, and exploitable API endpoints for the 4
Pantheon preset demo applications.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Base Dockerfile using python:3.12-slim (which is cached locally)
DEMO_DOCKERFILE = """FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
EXPOSE 8085
ENV PORT=8085
CMD ["python", "/app/app.py"]
"""

# ---------------------------------------------------------------------------
# DEMO 1: OWASP Juice Shop (Micro Edition)
# ---------------------------------------------------------------------------
JUICE_SHOP_APP_PY = r'''"""OWASP Juice Shop (Micro Edition) — Standalone HTTP Server.
Vulnerabilities: SQL Injection, Reflected XSS, BOLA, Weak JWT Key.
Runs on port 8085 with standard library only.
"""
import base64
import hashlib
import hmac
import http.server
import json
import os
import sqlite3
import urllib.parse

PORT = int(os.environ.get("PORT", 8085))
JWT_SECRET = "secret123"

# Initialize SQLite database
conn = sqlite3.connect(":memory:", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE products (
    id INTEGER PRIMARY KEY, name TEXT, description TEXT, price REAL, category TEXT
)""")
c.execute("""CREATE TABLE users (
    id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, name TEXT, address TEXT
)""")
c.execute("""CREATE TABLE reviews (
    id INTEGER PRIMARY KEY, product_id INTEGER, user_id INTEGER, text TEXT, rating INTEGER
)""")

products = [
    (1, "Apple Juice (1L)", "Fresh pressed organic apple juice from local orchards", 3.99, "juice"),
    (2, "Orange Punch (500ml)", "Citrus blend with a tropical twist", 2.49, "juice"),
    (3, "Green Smoothie", "Kale, spinach, banana, and almond milk blend", 5.99, "smoothie"),
    (4, "Lemon & Ginger Shot", "Immunity booster with raw lemon and ginger", 1.99, "shots"),
    (5, "Berry Blast (1L)", "Mixed berries with acai and chia seeds", 6.49, "juice"),
    (6, "Mango Lassi", "Creamy Indian-style mango yogurt drink", 4.49, "smoothie"),
    (7, "Admin Debug Panel Key", "FLAG{sql_injection_master} — You discovered a hidden item!", 0.00, "secret"),
    (8, "Coconut Water", "Pure hydration from young green coconuts", 3.29, "juice"),
]
c.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)

users = [
    (1, "admin@juiceshop.local", "admin123", "admin", "Administrator", "Juice Shop HQ, Room 404"),
    (2, "customer@test.com", "password", "customer", "John Doe", "123 Main St, Springfield"),
    (3, "jane@test.com", "letmein", "customer", "Jane Smith", "456 Oak Ave, Metropolis"),
]
c.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", users)

reviews = [
    (1, 1, 2, "Great apple juice, very fresh!", 5),
    (2, 3, 3, "Love this smoothie, so healthy!", 4),
    (3, 5, 2, "Berry Blast is my favorite!", 5),
]
c.executemany("INSERT INTO reviews VALUES (?, ?, ?, ?, ?)", reviews)
conn.commit()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>OWASP Juice Shop (Micro Edition)</title>
  <style>
    :root { --bg: #0d1117; --bg2: #161b22; --fg: #e6edf3; --pri: #00d4aa; --dan: #ff4757; --bor: #30363d; }
    body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--fg); margin: 0; padding: 24px; }
    .wrap { max-width: 900px; margin: 0 auto; }
    h1 { color: var(--pri); margin-bottom: 4px; }
    .sub { color: #8b949e; margin-bottom: 24px; font-size: 14px; }
    .card { background: var(--bg2); border: 1px solid var(--bor); border-radius: 8px; padding: 18px; margin-bottom: 16px; }
    input, button { padding: 8px 12px; border-radius: 6px; border: 1px solid var(--bor); font-size: 14px; }
    input { background: #07090d; color: #fff; width: 60%; }
    button { background: var(--pri); color: #000; font-weight: bold; cursor: pointer; border: none; margin-left: 6px; }
    button.sec { background: #21262d; color: #c9d1d9; border: 1px solid var(--bor); }
    .badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(255,71,87,0.2); color: var(--dan); }
    pre { background: #07090d; border: 1px solid var(--bor); padding: 12px; border-radius: 6px; overflow-x: auto; color: #7ee787; font-size: 13px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--bor); font-size: 13px; }
    th { color: #8b949e; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>🍹 OWASP Juice Shop (Micro Edition)</h1>
  <p class="sub">Intentionally Vulnerable Web Application Running in Tenant Container</p>

  <div class="card">
    <h3>🔍 Product Search <span class="badge">SQLi Vulnerable</span></h3>
    <input id="q" placeholder="Enter product name (Try: ' OR 1=1 --)" />
    <button onclick="doSearch()">Search</button>
    <button class="sec" onclick="document.getElementById('q').value='\' OR 1=1 --'; doSearch()">⚡ Exploit SQLi</button>
    <div id="searchResults" style="margin-top:12px;"></div>
  </div>

  <div class="card">
    <h3>👤 User Profile Lookup <span class="badge">BOLA / IDOR</span></h3>
    <input id="uid" placeholder="User ID (e.g. 1 for Admin, 2 for Customer)" value="1" style="width:20%" />
    <button onclick="getUser()">Fetch Profile</button>
    <pre id="userResults">Click fetch to view account details</pre>
  </div>
</div>
<script>
async function doSearch() {
  const q = document.getElementById('q').value;
  const res = await fetch('/api/products/search?q=' + encodeURIComponent(q));
  const data = await res.json();
  let html = '<table><tr><th>ID</th><th>Name</th><th>Description</th><th>Price</th></tr>';
  data.forEach(p => {
    html += `<tr><td>${p.id}</td><td><b>${p.name}</b></td><td>${p.description}</td><td>$${p.price.toFixed(2)}</td></tr>`;
  });
  html += '</table>';
  document.getElementById('searchResults').innerHTML = html;
}
async function getUser() {
  const id = document.getElementById('uid').value;
  const res = await fetch('/api/users/' + encodeURIComponent(id));
  const data = await res.json();
  document.getElementById('userResults').textContent = JSON.stringify(data, null, 2);
}
doSearch();
</script>
</body>
</html>"""

class JuiceHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet logging

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("", "/", "/juice-shop", "/preview"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_cors()
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "OWASP Juice Shop (Micro Edition)"}).encode("utf-8"))
            return

        if path in ("/api/products/search", "/rest/products/search"):
            q = query.get("q", [""])[0]
            # INTENTIONAL SQL INJECTION: Raw concatenation into query
            sql = f"SELECT id, name, description, price, category FROM products WHERE name LIKE '%{q}%' OR description LIKE '%{q}%'"
            try:
                cur = conn.cursor()
                rows = cur.execute(sql).fetchall()
                results = [{"id": r[0], "name": r[1], "description": r[2], "price": r[3], "category": r[4]} for r in rows]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors()
                self.end_headers()
                self.wfile.write(json.dumps(results).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "query": sql}).encode("utf-8"))
            return

        if path.startswith("/api/users/"):
            uid = path.split("/")[-1]
            try:
                cur = conn.cursor()
                row = cur.execute("SELECT id, email, role, name, address FROM users WHERE id = ?", (uid,)).fetchone()
                if row:
                    data = {"id": row[0], "email": row[1], "role": row[2], "name": row[3], "address": row[4]}
                    self.send_response(200)
                else:
                    data = {"error": "User not found"}
                    self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_cors()
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_cors()
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        if path == "/api/users/login":
            email = payload.get("email", "")
            password = payload.get("password", "")
            cur = conn.cursor()
            user = cur.execute("SELECT id, email, role, name FROM users WHERE email = ? AND password = ?", (email, password)).fetchone()
            if user:
                # Weak JWT simulation
                header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
                claims = base64.urlsafe_b64encode(json.dumps({"sub": user[0], "email": user[1], "role": user[2]}).encode()).decode().rstrip("=")
                sig = base64.urlsafe_b64encode(hmac.new(JWT_SECRET.encode(), f"{header}.{claims}".encode(), hashlib.sha256).digest()).decode().rstrip("=")
                token = f"{header}.{claims}.{sig}"
                res = {"token": token, "user": {"id": user[0], "email": user[1], "role": user[2], "name": user[3]}}
                self.send_response(200)
            else:
                res = {"error": "Invalid email or password"}
                self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.send_cors()
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        self.send_response(404)
        self.send_cors()
        self.end_headers()

if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), JuiceHandler)
    print(f"OWASP Juice Shop listening on 0.0.0.0:{PORT}")
    server.serve_forever()
'''

# ---------------------------------------------------------------------------
# DEMO 2: BankCore FinTech API Gateway
# ---------------------------------------------------------------------------
FINTECH_APP_PY = r'''"""BankCore FinTech API Gateway — Standalone HTTP Server.
Vulnerabilities: BOLA, Rate Limit Bypass, Debug Stacktrace Leaks.
Runs on port 8085 with standard library only.
"""
import http.server
import json
import os
import sqlite3
import traceback
import urllib.parse

PORT = int(os.environ.get("PORT", 8085))

conn = sqlite3.connect(":memory:", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY, owner TEXT, balance REAL, type TEXT)")
c.execute("CREATE TABLE txs (id TEXT PRIMARY KEY, from_id TEXT, to_id TEXT, amount REAL, desc TEXT)")

accounts = [
    ("ACC-1001", "Acme Corp Treasury", 1250000.00, "corporate"),
    ("ACC-1002", "Shadow Holding LLC", 89400.50, "escrow"),
    ("ACC-1003", "Alice Cooper", 3450.00, "personal"),
    ("ACC-1004", "Bob Vance", 8120.75, "personal"),
]
c.executemany("INSERT INTO accounts VALUES (?, ?, ?, ?)", accounts)
conn.commit()

HTML_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>BankCore FinTech Gateway</title>
<style>
  :root { --bg: #07090d; --bg2: #0d1117; --fg: #e6edf3; --pri: #3b82f6; --dan: #ff4757; --bor: #30363d; }
  body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--fg); padding: 24px; }
  .wrap { max-width: 850px; margin: 0 auto; }
  .card { background: var(--bg2); border: 1px solid var(--bor); border-radius: 8px; padding: 18px; margin-bottom: 16px; }
  h1 { color: var(--pri); }
  input, button { padding: 8px 12px; border-radius: 6px; border: 1px solid var(--bor); font-size: 14px; }
  input { background: #000; color: #fff; width: 40%; }
  button { background: var(--pri); color: #fff; font-weight: bold; cursor: pointer; border: none; margin-left: 6px; }
  .badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(255,71,87,0.2); color: var(--dan); }
  pre { background: #000; border: 1px solid var(--bor); padding: 12px; border-radius: 6px; color: #60a5fa; }
</style>
</head>
<body>
<div class="wrap">
  <h1>🏦 BankCore FinTech API Gateway</h1>
  <p style="color:#8b949e">Payment Processing & Financial Ledger Service</p>

  <div class="card">
    <h3>💸 Funds Transfer <span class="badge">BOLA Vulnerable</span></h3>
    <p style="color:#8b949e; font-size:13px">Transfer funds from ANY account ID without verifying caller ownership!</p>
    <input id="from" placeholder="From (e.g. ACC-1001)" value="ACC-1001" style="width:25%" />
    <input id="to" placeholder="To (e.g. ACC-1003)" value="ACC-1003" style="width:25%" />
    <input id="amt" placeholder="Amount" value="50000" style="width:20%" />
    <button onclick="doTransfer()">Transfer</button>
    <pre id="txRes">Ready</pre>
  </div>
</div>
<script>
async function doTransfer() {
  const from_acc = document.getElementById('from').value;
  const to_acc = document.getElementById('to').value;
  const amount = parseFloat(document.getElementById('amt').value);
  const res = await fetch('/api/v1/accounts/' + from_acc + '/transfer', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({to_account: to_acc, amount: amount, desc: 'Exploit transfer'})
  });
  const data = await res.json();
  document.getElementById('txRes').textContent = JSON.stringify(data, null, 2);
}
</script>
</body></html>"""

class FinTechHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200); self.send_cors(); self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        if path in ("", "/", "/fintech", "/preview"):
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_cors(); self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return
        if path == "/health":
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_cors(); self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "BankCore FinTech API Gateway"}).encode("utf-8"))
            return
        if path == "/api/v1/accounts":
            cur = conn.cursor()
            rows = cur.execute("SELECT id, owner, balance, type FROM accounts").fetchall()
            data = [{"id": r[0], "owner": r[1], "balance": r[2], "type": r[3]} for r in rows]
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_cors(); self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return
        self.send_response(404); self.send_cors(); self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try: payload = json.loads(body.decode("utf-8"))
        except: payload = {}

        if "/transfer" in path:
            from_acc = path.split("/accounts/")[1].split("/transfer")[0]
            to_acc = payload.get("to_account")
            amount = float(payload.get("amount", 0))
            cur = conn.cursor()
            cur.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_acc))
            cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_acc))
            conn.commit()
            res = {"success": True, "transferred": amount, "from": from_acc, "to": to_acc, "flag": "FLAG{fintech_bola_exploited}"}
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_cors(); self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return
        self.send_response(404); self.send_cors(); self.end_headers()

if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), FinTechHandler)
    server.serve_forever()
'''

# ---------------------------------------------------------------------------
# DEMO 3: CloudStore E-Commerce Platform
# ---------------------------------------------------------------------------
CLOUDSTORE_APP_PY = r'''"""CloudStore E-Commerce Platform — Standalone HTTP Server.
Vulnerabilities: SSRF in media previewer, Admin cookie bypass.
Runs on port 8085 with standard library only.
"""
import http.server
import json
import os
import urllib.request
import urllib.parse

PORT = int(os.environ.get("PORT", 8085))

HTML_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CloudStore Platform</title>
<style>
  body { font-family: system-ui; background: #07090d; color: #e6edf3; padding: 24px; }
  .card { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 18px; margin-bottom: 16px; max-width: 800px; }
  h1 { color: #f0a500; }
  input, button { padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; }
  input { background: #000; color: #fff; width: 60%; }
  button { background: #f0a500; color: #000; font-weight: bold; cursor: pointer; border: none; }
  pre { background: #000; padding: 12px; border-radius: 6px; color: #f0a500; border: 1px solid #30363d; }
</style>
</head>
<body>
  <h1>🛒 CloudStore E-Commerce Platform</h1>
  <div class="card">
    <h3>🖼️ Media Previewer <span style="color:#ff4757">[SSRF Vulnerable]</span></h3>
    <input id="u" value="http://169.254.169.254/latest/meta-data/" />
    <button onclick="fetchUrl()">Fetch URL</button>
    <pre id="out">Ready</pre>
  </div>
  <script>
    async function fetchUrl() {
      const u = document.getElementById('u').value;
      const res = await fetch('/api/media/fetch?url=' + encodeURIComponent(u));
      const data = await res.json();
      document.getElementById('out').textContent = JSON.stringify(data, null, 2);
    }
  </script>
</body></html>"""

class CloudStoreHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200); self.send_cors(); self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("", "/", "/cloudstore", "/preview"):
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_cors(); self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return
        if path == "/health":
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_cors(); self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "CloudStore E-Commerce Platform"}).encode("utf-8"))
            return
        if path == "/api/media/fetch":
            url = query.get("url", [""])[0]
            # Simulated metadata response for SSRF demonstration
            if "169.254.169.254" in url or "metadata" in url:
                data = {
                    "ami-id": "ami-0123456789abcdef0",
                    "instance-id": "i-0987654321fedcba0",
                    "iam_role": "CloudStore-App-Role",
                    "credentials": {
                        "AccessKeyId": "ASIAVULNERABLEKEY123",
                        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                        "Token": "FLAG{ssrf_cloud_metadata_breached}"
                    }
                }
            else:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "CloudStore-Crawler/1.0"})
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        content = resp.read().decode("utf-8", errors="replace")[:1000]
                    data = {"url": url, "status": resp.status, "preview": content}
                except Exception as e:
                    data = {"url": url, "error": str(e)}
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_cors(); self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return
        self.send_response(404); self.send_cors(); self.end_headers()

if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), CloudStoreHandler)
    server.serve_forever()
'''

# ---------------------------------------------------------------------------
# DEMO 4: DevOps Task Pipeline Worker
# ---------------------------------------------------------------------------
DEVOPS_APP_PY = r'''"""DevOps Task Pipeline Worker — Standalone HTTP Server.
Vulnerabilities: Remote Command Execution, Environment Secret Dumping.
Runs on port 8085 with standard library only.
"""
import http.server
import json
import os
import subprocess
import urllib.parse

PORT = int(os.environ.get("PORT", 8085))

HTML_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>DevOps Pipeline Worker</title>
<style>
  body { font-family: monospace; background: #07090d; color: #e6edf3; padding: 24px; }
  .card { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 18px; max-width: 800px; }
  input, button { padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; }
  input { background: #000; color: #fff; width: 60%; }
  button { background: #ff4757; color: #fff; font-weight: bold; cursor: pointer; border: none; }
  pre { background: #000; padding: 12px; border-radius: 6px; color: #ff6b6b; border: 1px solid #30363d; }
</style>
</head>
<body>
  <h2>⚙️ DevOps Task Pipeline Worker</h2>
  <div class="card">
    <h3>Command Execution (RCE)</h3>
    <input id="cmd" value="whoami && id && uname -a" />
    <button onclick="execCmd()">Execute Job</button>
    <pre id="out">Ready</pre>
  </div>
  <script>
    async function execCmd() {
      const cmd = document.getElementById('cmd').value;
      const res = await fetch('/api/build/execute', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command: cmd})
      });
      const data = await res.json();
      document.getElementById('out').textContent = JSON.stringify(data, null, 2);
    }
  </script>
</body></html>"""

class DevOpsHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200); self.send_cors(); self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        if path in ("", "/", "/devops", "/preview"):
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_cors(); self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return
        if path == "/health":
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_cors(); self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "DevOps Task Pipeline Worker"}).encode("utf-8"))
            return
        if path == "/env":
            # Leaks environment variables including mock secrets
            env_vars = dict(os.environ)
            env_vars["PIPELINE_SECRET_KEY"] = "FLAG{rce_environment_secret_leak_123}"
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_cors(); self.end_headers()
            self.wfile.write(json.dumps(env_vars).encode("utf-8"))
            return
        self.send_response(404); self.send_cors(); self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try: payload = json.loads(body.decode("utf-8"))
        except: payload = {}

        if path == "/api/build/execute":
            cmd = payload.get("command", "echo 'no command'")
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                out = {"command": cmd, "stdout": res.stdout, "stderr": res.stderr, "returncode": res.returncode}
            except Exception as e:
                out = {"command": cmd, "error": str(e)}
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_cors(); self.end_headers()
            self.wfile.write(json.dumps(out).encode("utf-8"))
            return
        self.send_response(404); self.send_cors(); self.end_headers()

if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), DevOpsHandler)
    server.serve_forever()
'''


def match_demo_app_key(app_name: str, source_url: str | None = None) -> str | None:
    """Determine if an app matches one of our preset demo catalog applications."""
    n = (app_name or "").lower()
    u = (source_url or "").lower()

    if "juice" in n or "juice" in u:
        return "juice-shop"
    if "fintech" in n or "bankcore" in n or "fintech" in u:
        return "fintech"
    if "cloudstore" in n or "commerce" in n or "cloudstore" in u:
        return "cloudstore"
    if "devops" in n or "pipeline" in n or "worker" in n or "devops" in u:
        return "devops"
    return None


def get_demo_files(demo_key: str) -> dict[str, str]:
    """Return dictionary of {filename: content} for a demo workload."""
    if demo_key == "juice-shop":
        return {"Dockerfile": DEMO_DOCKERFILE, "app.py": JUICE_SHOP_APP_PY}
    if demo_key == "fintech":
        return {"Dockerfile": DEMO_DOCKERFILE, "app.py": FINTECH_APP_PY}
    if demo_key == "cloudstore":
        return {"Dockerfile": DEMO_DOCKERFILE, "app.py": CLOUDSTORE_APP_PY}
    if demo_key == "devops":
        return {"Dockerfile": DEMO_DOCKERFILE, "app.py": DEVOPS_APP_PY}
    # Default fallback to Juice Shop
    return {"Dockerfile": DEMO_DOCKERFILE, "app.py": JUICE_SHOP_APP_PY}


def write_demo_files(demo_key: str, target_dir: str | Path) -> None:
    """Write out the demo workload Dockerfile and app.py into the target directory."""
    files = get_demo_files(demo_key)
    p = Path(target_dir)
    p.mkdir(parents=True, exist_ok=True)
    for fname, content in files.items():
        (p / fname).write_text(content, encoding="utf-8")
