"""Vulnerable Demo Applications Router — PRD §6.1 Phase 14+.

Self-contained micro-applications with **intentional** security vulnerabilities
for attack simulation demos. Each demo has:
  - Real exploitable API endpoints
  - A lightweight HTML frontend for live preview
  - Documented vulnerabilities for Pantheon scenario presets

WARNING: These endpoints are INTENTIONALLY VULNERABLE for educational/testing purposes.
They should only run inside the Pantheon tenant sandbox environment.
"""

import hashlib
import html as html_mod
import json
import os
import sqlite3
import subprocess
import tempfile
import time
import uuid
from typing import Any

from fastapi import APIRouter, Cookie, Header, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/demo-apps", tags=["demo-apps"])

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

DEMO_CSS = """
:root {
  --bg: #07090d; --bg2: #0d1117; --bg3: #161b22; --border: #21262d;
  --fg: #e6edf3; --fg2: #8b949e; --primary: #00d4aa; --danger: #ff4757;
  --warning: #f0a500; --success: #00d4aa; --font: 'Inter', system-ui, sans-serif;
  --mono: 'JetBrains Mono', 'Fira Code', monospace;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--fg); font-family: var(--font); line-height: 1.6; padding: 24px; }
.container { max-width: 960px; margin: 0 auto; }
h1 { font-size: 28px; font-weight: 800; margin-bottom: 6px; background: linear-gradient(135deg, var(--primary), #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
h2 { font-size: 18px; font-weight: 700; margin: 24px 0 12px; color: var(--fg); }
h3 { font-size: 14px; font-weight: 600; margin: 16px 0 8px; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em; font-family: var(--mono); }
.subtitle { color: var(--fg2); font-size: 14px; margin-bottom: 24px; }
.card { background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; transition: border-color 0.2s; }
.card:hover { border-color: rgba(0, 212, 170, 0.3); }
.card-title { font-size: 14px; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; font-family: var(--mono); }
.badge-danger { background: rgba(255, 71, 87, 0.15); color: #ff4757; border: 1px solid rgba(255, 71, 87, 0.25); }
.badge-warn { background: rgba(240, 165, 0, 0.12); color: #f0a500; border: 1px solid rgba(240, 165, 0, 0.2); }
.badge-success { background: rgba(0, 212, 170, 0.12); color: #00d4aa; border: 1px solid rgba(0, 212, 170, 0.2); }
.badge-info { background: rgba(59, 130, 246, 0.12); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.2); }
input, textarea, select { width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--fg); font-family: var(--mono); font-size: 13px; outline: none; transition: border-color 0.2s; }
input:focus, textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.1); }
button, .btn { padding: 10px 18px; border: none; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; font-family: var(--font); }
.btn-primary { background: var(--primary); color: #07090d; }
.btn-primary:hover { background: #00b38f; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0, 212, 170, 0.3); }
.btn-danger { background: var(--danger); color: #fff; }
.btn-danger:hover { background: #e63e50; }
.btn-secondary { background: var(--bg3); color: var(--fg2); border: 1px solid var(--border); }
.btn-secondary:hover { color: var(--fg); border-color: rgba(255,255,255,0.2); }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 6px; color: var(--fg2); text-transform: uppercase; letter-spacing: 0.04em; font-family: var(--mono); }
.result-box { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; font-family: var(--mono); font-size: 12px; white-space: pre-wrap; word-break: break-all; max-height: 320px; overflow-y: auto; margin-top: 12px; }
.result-box.danger { border-color: rgba(255, 71, 87, 0.3); background: rgba(255, 71, 87, 0.04); }
.result-box.success { border-color: rgba(0, 212, 170, 0.3); background: rgba(0, 212, 170, 0.04); }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg2); font-family: var(--mono); font-weight: 600; }
tr:hover td { background: rgba(0, 212, 170, 0.03); }
.vuln-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-family: var(--mono); margin: 2px; }
.vuln-critical { background: rgba(255, 71, 87, 0.15); color: #ff6b6b; }
.vuln-high { background: rgba(255, 107, 53, 0.15); color: #ff8c42; }
.flex { display: flex; gap: 16px; }
.flex-1 { flex: 1; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 768px) { .grid-2, .flex { flex-direction: column; grid-template-columns: 1fr; } }
.nav-bar { display: flex; gap: 8px; padding: 8px 0; margin-bottom: 20px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.nav-link { font-size: 11px; padding: 6px 14px; border-radius: 6px; text-decoration: none; color: var(--fg2); background: var(--bg3); border: 1px solid var(--border); font-family: var(--mono); transition: all 0.2s; }
.nav-link:hover, .nav-link.active { color: var(--primary); border-color: var(--primary); background: rgba(0, 212, 170, 0.06); }
.exploit-marker { position: relative; }
.exploit-marker::before { content: '⚡'; position: absolute; left: -18px; top: 50%; transform: translateY(-50%); font-size: 12px; }
"""

DEMO_NAV = """
<div class="nav-bar">
  <a href="/api/demo-apps/juice-shop" class="nav-link {active_juice}">🍹 Juice Shop</a>
  <a href="/api/demo-apps/fintech" class="nav-link {active_fintech}">🏦 FinTech Gateway</a>
  <a href="/api/demo-apps/cloudstore" class="nav-link {active_cloudstore}">🛒 CloudStore</a>
  <a href="/api/demo-apps/devops" class="nav-link {active_devops}">⚙️ DevOps Worker</a>
</div>
"""


def _wrap_page(title: str, subtitle: str, body: str, active: str) -> str:
    """Wrap demo app body in full HTML page with shared styles and nav."""
    nav = DEMO_NAV.format(
        active_juice="active" if active == "juice" else "",
        active_fintech="active" if active == "fintech" else "",
        active_cloudstore="active" if active == "cloudstore" else "",
        active_devops="active" if active == "devops" else "",
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Pantheon Demo</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>{DEMO_CSS}</style>
</head>
<body>
  <div class="container">
    {nav}
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
    {body}
  </div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 1: OWASP JUICE SHOP (Micro Edition)
# Vulnerabilities: SQL Injection, Reflected XSS, BOLA, JWT weak key
# ═══════════════════════════════════════════════════════════════════════════════

_JUICE_DB_PATH = os.path.join(tempfile.gettempdir(), "pantheon_juice_shop.db")
_JWT_WEAK_SECRET = "secret123"  # Intentionally weak — exploitable


def _init_juice_db() -> None:
    """Initialize SQLite database with product and user seed data."""
    conn = sqlite3.connect(_JUICE_DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, name TEXT, description TEXT, price REAL, category TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'customer',
        name TEXT, address TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY, product_id INTEGER, user_id INTEGER, text TEXT, rating INTEGER
    )""")
    # Seed products
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        products = [
            (1, "Apple Juice (1L)", "Fresh pressed organic apple juice from local orchards", 3.99, "juice"),
            (2, "Orange Punch (500ml)", "Citrus blend with a tropical twist", 2.49, "juice"),
            (3, "Green Smoothie", "Kale, spinach, banana, and almond milk blend", 5.99, "smoothie"),
            (4, "Lemon & Ginger Shot", "Immunity booster with raw lemon and ginger", 1.99, "shots"),
            (5, "Berry Blast (1L)", "Mixed berries with acai and chia seeds", 6.49, "juice"),
            (6, "Mango Lassi", "Creamy Indian-style mango yogurt drink", 4.49, "smoothie"),
            (7, "Admin Debug Panel Key", "FLAG{sql_injection_master} — You found a hidden item!", 0.00, "secret"),
            (8, "Coconut Water", "Pure hydration from young green coconuts", 3.29, "juice"),
        ]
        c.executemany("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?)", products)
    # Seed users
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        users = [
            (1, "admin@juiceshop.local", "admin123", "admin", "Administrator", "Juice Shop HQ"),
            (2, "customer@test.com", "password", "customer", "John Doe", "123 Main St"),
            (3, "jane@test.com", "letmein", "customer", "Jane Smith", "456 Oak Ave"),
        ]
        c.executemany("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)", users)
    # Seed reviews
    c.execute("SELECT COUNT(*) FROM reviews")
    if c.fetchone()[0] == 0:
        reviews = [
            (1, 1, 2, "Great apple juice, very fresh!", 5),
            (2, 3, 3, "Love this smoothie, so healthy!", 4),
            (3, 5, 2, "Berry Blast is my favorite!", 5),
        ]
        c.executemany("INSERT OR IGNORE INTO reviews VALUES (?, ?, ?, ?, ?)", reviews)
    conn.commit()
    conn.close()


_init_juice_db()


@router.get("/juice-shop", response_class=HTMLResponse)
async def juice_shop_frontend():
    """Juice Shop micro-app frontend with interactive exploit panels."""
    body = """
    <div class="grid-2">
      <div class="card">
        <div class="card-title">🔍 Product Search <span class="badge badge-danger">SQLi Vulnerable</span></div>
        <div class="form-group">
          <label>Search Products</label>
          <input type="text" id="search-input" placeholder="Try: ' OR 1=1 --" />
        </div>
        <button class="btn btn-primary" onclick="searchProducts()">🔎 Search</button>
        <button class="btn btn-secondary" onclick="document.getElementById('search-input').value=\\\"' OR 1=1 --\\\"; searchProducts()" style="margin-left:8px">⚡ Exploit SQLi</button>
        <div id="search-results" class="result-box" style="display:none"></div>
      </div>

      <div class="card">
        <div class="card-title">💬 Review Submission <span class="badge badge-danger">XSS Vulnerable</span></div>
        <div class="form-group">
          <label>Product ID</label>
          <input type="number" id="review-product" value="1" />
        </div>
        <div class="form-group">
          <label>Review Text</label>
          <textarea id="review-text" rows="3" placeholder='Try: <img src=x onerror="alert(document.cookie)">'></textarea>
        </div>
        <button class="btn btn-primary" onclick="submitReview()">📝 Submit Review</button>
        <button class="btn btn-secondary" onclick="loadReviews()" style="margin-left:8px">Load Reviews</button>
        <div id="review-results" class="result-box" style="display:none"></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">🔐 User Login <span class="badge badge-danger">Auth Bypass</span></div>
        <div class="form-group">
          <label>Email</label>
          <input type="text" id="login-email" placeholder="admin@juiceshop.local" />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input type="text" id="login-password" placeholder="Try: ' OR '1'='1" />
        </div>
        <button class="btn btn-primary" onclick="loginUser()">🔑 Login</button>
        <button class="btn btn-secondary" onclick="document.getElementById('login-email').value='admin@juiceshop.local';document.getElementById('login-password').value=\\\"' OR '1'='1\\\";loginUser()" style="margin-left:8px">⚡ Exploit</button>
        <div id="login-result" class="result-box" style="display:none"></div>
      </div>

      <div class="card">
        <div class="card-title">👤 User Profile <span class="badge badge-danger">BOLA / IDOR</span></div>
        <div class="form-group">
          <label>User ID (try accessing other users' data)</label>
          <input type="number" id="profile-id" value="1" />
        </div>
        <button class="btn btn-primary" onclick="getProfile()">👁️ View Profile</button>
        <div style="display:flex;gap:6px;margin-top:8px">
          <button class="btn btn-secondary" onclick="document.getElementById('profile-id').value='1';getProfile()">User 1</button>
          <button class="btn btn-secondary" onclick="document.getElementById('profile-id').value='2';getProfile()">User 2</button>
          <button class="btn btn-secondary" onclick="document.getElementById('profile-id').value='3';getProfile()">User 3</button>
        </div>
        <div id="profile-result" class="result-box" style="display:none"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">📋 All Vulnerabilities</div>
      <table>
        <thead><tr><th>Vulnerability</th><th>Endpoint</th><th>Severity</th><th>Type</th></tr></thead>
        <tbody>
          <tr><td>SQL Injection</td><td><code>/api/demo-apps/juice-shop/api/products/search?q=</code></td><td><span class="vuln-tag vuln-critical">CRITICAL</span></td><td>CWE-89</td></tr>
          <tr><td>Reflected XSS</td><td><code>/api/demo-apps/juice-shop/api/reviews (stored in HTML)</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-79</td></tr>
          <tr><td>Auth Bypass (SQLi)</td><td><code>/api/demo-apps/juice-shop/api/login</code></td><td><span class="vuln-tag vuln-critical">CRITICAL</span></td><td>CWE-89</td></tr>
          <tr><td>BOLA / IDOR</td><td><code>/api/demo-apps/juice-shop/api/users/{id}</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-639</td></tr>
          <tr><td>Weak JWT Secret</td><td><code>/api/demo-apps/juice-shop/api/login</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-347</td></tr>
        </tbody>
      </table>
    </div>

    <script>
      const BASE = '/api/demo-apps/juice-shop/api';

      async function searchProducts() {
        const q = document.getElementById('search-input').value;
        const box = document.getElementById('search-results');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/products/search?q=' + encodeURIComponent(q));
          const data = await r.json();
          if (data.error) { box.className = 'result-box danger'; box.textContent = '❌ Error: ' + data.error; }
          else { box.className = 'result-box success'; box.textContent = JSON.stringify(data, null, 2); }
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function loginUser() {
        const email = document.getElementById('login-email').value;
        const pw = document.getElementById('login-password').value;
        const box = document.getElementById('login-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/login', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({email, password: pw}) });
          const data = await r.json();
          box.className = data.success ? 'result-box success' : 'result-box danger';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function getProfile() {
        const id = document.getElementById('profile-id').value;
        const box = document.getElementById('profile-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/users/' + id);
          const data = await r.json();
          box.className = data.error ? 'result-box danger' : 'result-box success';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function submitReview() {
        const pid = document.getElementById('review-product').value;
        const text = document.getElementById('review-text').value;
        const box = document.getElementById('review-results');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/reviews', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({product_id: parseInt(pid), user_id: 2, text, rating: 5}) });
          const data = await r.json();
          box.className = 'result-box success';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function loadReviews() {
        const pid = document.getElementById('review-product').value;
        const box = document.getElementById('review-results');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/reviews?product_id=' + pid);
          const data = await r.json();
          // INTENTIONALLY render HTML unescaped to demonstrate stored XSS
          box.className = 'result-box';
          box.innerHTML = '<strong>Reviews for Product #' + pid + ':</strong><br/>' +
            data.map(rv => '<div style="padding:6px 0;border-bottom:1px solid var(--border)">⭐' + rv.rating + ' — ' + rv.text + '</div>').join('');
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }
    </script>
    """
    return HTMLResponse(_wrap_page(
        "🍹 OWASP Juice Shop (Micro Edition)",
        "Intentionally vulnerable web app covering OWASP Top 10 — SQL Injection, XSS, BOLA, Auth Bypass",
        body,
        "juice",
    ))


# Juice Shop API Endpoints

@router.get("/juice-shop/api/products/search")
async def juice_shop_search(q: str = Query("", description="Search query — VULNERABLE to SQL injection")):
    """VULNERABLE: Direct string concatenation into SQL query (CWE-89)."""
    conn = sqlite3.connect(_JUICE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # INTENTIONALLY VULNERABLE — raw SQL string interpolation
        query = f"SELECT * FROM products WHERE name LIKE '%{q}%' OR description LIKE '%{q}%' OR category LIKE '%{q}%'"
        results = conn.execute(query).fetchall()
        return [dict(r) for r in results]
    except Exception as e:
        return JSONResponse({"error": str(e), "query": f"SELECT * FROM products WHERE name LIKE '%{q}%'..."}, status_code=200)
    finally:
        conn.close()


class JuiceLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/juice-shop/api/login")
async def juice_shop_login(payload: JuiceLoginRequest):
    """VULNERABLE: SQL injection in login — allows authentication bypass (CWE-89)."""
    conn = sqlite3.connect(_JUICE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # INTENTIONALLY VULNERABLE — SQL injection in auth query
        query = f"SELECT * FROM users WHERE email = '{payload.email}' AND password = '{payload.password}'"
        user = conn.execute(query).fetchone()
        if user:
            user_dict = dict(user)
            # Weak JWT-like token (intentionally crackable)
            token_payload = json.dumps({"user_id": user_dict["id"], "email": user_dict["email"], "role": user_dict["role"]})
            token = hashlib.md5(f"{token_payload}:{_JWT_WEAK_SECRET}".encode()).hexdigest()
            return {
                "success": True,
                "token": token,
                "user": {k: v for k, v in user_dict.items() if k != "password"},
                "message": f"Welcome back, {user_dict['name']}!",
                "jwt_hint": "Token uses MD5 with weak secret 'secret123' — try cracking it!"
            }
        return {"success": False, "message": "Invalid credentials"}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e), "hint": "SQL error leaked — check for injection"}, status_code=200)
    finally:
        conn.close()


@router.get("/juice-shop/api/users/{user_id}")
async def juice_shop_user_profile(user_id: int):
    """VULNERABLE: No authorization check — any user can access any profile (BOLA/IDOR — CWE-639)."""
    conn = sqlite3.connect(_JUICE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # INTENTIONALLY VULNERABLE — no auth check, anyone can view any user
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user:
            user_dict = dict(user)
            return {
                "user": user_dict,
                "vulnerability_note": "No authorization check performed — BOLA/IDOR vulnerability (CWE-639)"
            }
        return {"error": "User not found"}
    finally:
        conn.close()


class ReviewRequest(BaseModel):
    product_id: int
    user_id: int
    text: str
    rating: int


@router.post("/juice-shop/api/reviews")
async def juice_shop_submit_review(payload: ReviewRequest):
    """VULNERABLE: Stores raw HTML/JS content — Stored XSS (CWE-79)."""
    conn = sqlite3.connect(_JUICE_DB_PATH)
    try:
        # INTENTIONALLY VULNERABLE — no sanitization of review text
        conn.execute(
            "INSERT INTO reviews (product_id, user_id, text, rating) VALUES (?, ?, ?, ?)",
            (payload.product_id, payload.user_id, payload.text, payload.rating)
        )
        conn.commit()
        return {"success": True, "message": "Review submitted (stored without sanitization — XSS possible!)"}
    finally:
        conn.close()


@router.get("/juice-shop/api/reviews")
async def juice_shop_get_reviews(product_id: int = Query(1)):
    """Returns reviews with unsanitized content — enables Stored XSS on frontend."""
    conn = sqlite3.connect(_JUICE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        reviews = conn.execute("SELECT * FROM reviews WHERE product_id = ?", (product_id,)).fetchall()
        return [dict(r) for r in reviews]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 2: BANKCORE FINTECH API GATEWAY
# Vulnerabilities: BOLA, Rate-limit bypass, Debug info leak
# ═══════════════════════════════════════════════════════════════════════════════

_FINTECH_ACCOUNTS: dict[str, dict] = {
    "ACC-001": {"id": "ACC-001", "owner": "alice@bank.com", "name": "Alice Chen", "balance": 15420.50, "currency": "USD", "type": "checking"},
    "ACC-002": {"id": "ACC-002", "owner": "bob@bank.com", "name": "Bob Smith", "balance": 89230.00, "currency": "USD", "type": "savings"},
    "ACC-003": {"id": "ACC-003", "owner": "charlie@bank.com", "name": "Charlie Davis", "balance": 3200.75, "currency": "USD", "type": "checking"},
    "ACC-004": {"id": "ACC-004", "owner": "admin@bank.com", "name": "System Admin (Internal)", "balance": 999999.99, "currency": "USD", "type": "internal"},
}
_FINTECH_TRANSFERS: list[dict] = []
_FINTECH_RATE_LIMITS: dict[str, list[float]] = {}


@router.get("/fintech", response_class=HTMLResponse)
async def fintech_frontend():
    """BankCore FinTech API Gateway frontend."""
    body = """
    <div class="grid-2">
      <div class="card">
        <div class="card-title">💳 Account Lookup <span class="badge badge-danger">BOLA Vulnerable</span></div>
        <div class="form-group">
          <label>Account ID (try others without auth)</label>
          <select id="account-id">
            <option value="ACC-001">ACC-001 (Alice — your account)</option>
            <option value="ACC-002">ACC-002 (Bob — another customer)</option>
            <option value="ACC-003">ACC-003 (Charlie — another customer)</option>
            <option value="ACC-004">ACC-004 (System Admin — internal)</option>
          </select>
        </div>
        <button class="btn btn-primary" onclick="lookupAccount()">🔍 View Account</button>
        <div id="account-result" class="result-box" style="display:none"></div>
      </div>

      <div class="card">
        <div class="card-title">💸 Money Transfer <span class="badge badge-danger">BOLA + No Auth</span></div>
        <div class="form-group">
          <label>From Account</label>
          <input type="text" id="transfer-from" value="ACC-002" placeholder="ACC-002 (Bob's account)" />
        </div>
        <div class="form-group">
          <label>To Account</label>
          <input type="text" id="transfer-to" value="ACC-001" placeholder="ACC-001" />
        </div>
        <div class="form-group">
          <label>Amount ($)</label>
          <input type="number" id="transfer-amount" value="1000" step="0.01" />
        </div>
        <button class="btn btn-danger" onclick="doTransfer()">💸 Execute Transfer</button>
        <div id="transfer-result" class="result-box" style="display:none"></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">🚀 Rate Limit Bypass <span class="badge badge-warn">X-Forwarded-For Spoof</span></div>
        <p style="color:var(--fg2);font-size:12px;margin-bottom:12px">The API uses X-Forwarded-For header for rate limiting. Spoofing this header bypasses the limit.</p>
        <div class="form-group">
          <label>X-Forwarded-For Header</label>
          <input type="text" id="xff-header" value="192.168.1.1" placeholder="Spoofed IP address" />
        </div>
        <button class="btn btn-primary" onclick="testRateLimit()">⚡ Send 20 Rapid Requests</button>
        <div id="rate-result" class="result-box" style="display:none"></div>
      </div>

      <div class="card">
        <div class="card-title">🐛 Debug Endpoint <span class="badge badge-danger">Info Leak</span></div>
        <p style="color:var(--fg2);font-size:12px;margin-bottom:12px">Debug mode exposes stack traces, internal config, and database credentials in error responses.</p>
        <button class="btn btn-danger" onclick="triggerDebug()">💥 Trigger Error</button>
        <button class="btn btn-secondary" onclick="getDebugInfo()" style="margin-left:8px">📋 /debug/config</button>
        <div id="debug-result" class="result-box" style="display:none"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">📋 All Vulnerabilities</div>
      <table>
        <thead><tr><th>Vulnerability</th><th>Endpoint</th><th>Severity</th><th>Type</th></tr></thead>
        <tbody>
          <tr><td>Broken Object-Level Auth</td><td><code>/api/demo-apps/fintech/api/accounts/{id}</code></td><td><span class="vuln-tag vuln-critical">CRITICAL</span></td><td>CWE-639</td></tr>
          <tr><td>Unauthorized Transfer</td><td><code>/api/demo-apps/fintech/api/accounts/{id}/transfer</code></td><td><span class="vuln-tag vuln-critical">CRITICAL</span></td><td>CWE-862</td></tr>
          <tr><td>Rate Limit Bypass</td><td><code>/api/demo-apps/fintech/api/accounts/{id} (via XFF)</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-770</td></tr>
          <tr><td>Debug Info Leak</td><td><code>/api/demo-apps/fintech/api/debug/config</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-209</td></tr>
        </tbody>
      </table>
    </div>

    <script>
      const BASE = '/api/demo-apps/fintech/api';

      async function lookupAccount() {
        const id = document.getElementById('account-id').value;
        const box = document.getElementById('account-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/accounts/' + id);
          const data = await r.json();
          box.className = 'result-box success';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function doTransfer() {
        const from = document.getElementById('transfer-from').value;
        const to = document.getElementById('transfer-to').value;
        const amount = parseFloat(document.getElementById('transfer-amount').value);
        const box = document.getElementById('transfer-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/accounts/' + from + '/transfer', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({to_account: to, amount})
          });
          const data = await r.json();
          box.className = data.success ? 'result-box success' : 'result-box danger';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function testRateLimit() {
        const xff = document.getElementById('xff-header').value;
        const box = document.getElementById('rate-result');
        box.style.display = 'block';
        box.className = 'result-box';
        box.textContent = 'Sending 20 rapid requests...\\n';
        let blocked = 0, passed = 0;
        for (let i = 0; i < 20; i++) {
          try {
            const r = await fetch(BASE + '/accounts/ACC-001', { headers: {'X-Forwarded-For': xff + '.' + i} });
            if (r.status === 429) { blocked++; box.textContent += '❌ Request ' + (i+1) + ': RATE LIMITED (429)\\n'; }
            else { passed++; box.textContent += '✅ Request ' + (i+1) + ': OK (200) — bypassed!\\n'; }
          } catch(e) { box.textContent += '⚠️ Request ' + (i+1) + ': Error\\n'; }
        }
        box.textContent += '\\n📊 Results: ' + passed + ' passed, ' + blocked + ' blocked\\n';
        box.textContent += passed === 20 ? '⚡ EXPLOIT SUCCESS: All requests passed — rate limit fully bypassed via XFF spoofing!' : '🛡️ Some requests were blocked.';
      }

      async function triggerDebug() {
        const box = document.getElementById('debug-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/accounts/INVALID-ID/transfer', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({to_account: 'xxx', amount: -1})
          });
          const data = await r.json();
          box.className = 'result-box danger';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function getDebugInfo() {
        const box = document.getElementById('debug-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/debug/config');
          const data = await r.json();
          box.className = 'result-box danger';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }
    </script>
    """
    return HTMLResponse(_wrap_page(
        "🏦 BankCore FinTech API Gateway",
        "Financial ledger with BOLA, rate-limit bypass, and debug information disclosure vulnerabilities",
        body,
        "fintech",
    ))


@router.get("/fintech/api/accounts/{account_id}")
async def fintech_get_account(
    account_id: str,
    x_forwarded_for: str | None = Header(None, alias="X-Forwarded-For"),
):
    """VULNERABLE: No authorization — any caller can view any account (BOLA — CWE-639).
    Rate limiting uses X-Forwarded-For which is spoofable (CWE-770)."""
    # Intentionally weak rate limiting using spoofable header
    client_ip = x_forwarded_for or "unknown"
    now = time.time()
    _FINTECH_RATE_LIMITS.setdefault(client_ip, [])
    _FINTECH_RATE_LIMITS[client_ip] = [t for t in _FINTECH_RATE_LIMITS[client_ip] if now - t < 60]
    if len(_FINTECH_RATE_LIMITS[client_ip]) > 100:  # Very generous limit — practically no real protection
        return JSONResponse({"error": "Rate limited", "retry_after": 60}, status_code=429)
    _FINTECH_RATE_LIMITS[client_ip].append(now)

    account = _FINTECH_ACCOUNTS.get(account_id)
    if not account:
        return JSONResponse({"error": f"Account '{account_id}' not found"}, status_code=404)
    return {
        "account": account,
        "vulnerability_note": "No authorization check — BOLA allows accessing any account"
    }


class TransferRequest(BaseModel):
    to_account: str
    amount: float


@router.post("/fintech/api/accounts/{account_id}/transfer")
async def fintech_transfer(account_id: str, payload: TransferRequest):
    """VULNERABLE: No auth check — anyone can initiate transfers from any account (CWE-862)."""
    source = _FINTECH_ACCOUNTS.get(account_id)
    dest = _FINTECH_ACCOUNTS.get(payload.to_account)

    if not source:
        # VULNERABLE: Debug info leak in error
        return JSONResponse({
            "success": False,
            "error": f"Source account '{account_id}' not found",
            "debug_info": {
                "db_connection": "postgresql://bankcore_admin:B4nkC0re_S3cret!@db.internal:5432/ledger",
                "redis_url": "redis://:r3d1s_p4ss@cache.internal:6379/0",
                "stack_trace": "at TransferService.execute() in /app/services/transfer.py:142",
                "internal_accounts": list(_FINTECH_ACCOUNTS.keys()),
            },
        }, status_code=200)

    if not dest:
        return JSONResponse({"success": False, "error": f"Destination account '{payload.to_account}' not found"}, status_code=200)

    if payload.amount <= 0:
        return JSONResponse({
            "success": False,
            "error": "Invalid amount",
            "debug_info": {
                "validation_error": "amount must be positive",
                "internal_config": {"max_transfer": 50000, "daily_limit": 100000},
                "db_credentials": "postgresql://bankcore_admin:B4nkC0re_S3cret!@db.internal:5432/ledger",
            }
        }, status_code=200)

    if source["balance"] < payload.amount:
        return JSONResponse({"success": False, "error": "Insufficient funds", "current_balance": source["balance"]}, status_code=200)

    # Execute transfer (in-memory)
    source["balance"] -= payload.amount
    dest["balance"] += payload.amount
    txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    _FINTECH_TRANSFERS.append({
        "id": txn_id, "from": account_id, "to": payload.to_account,
        "amount": payload.amount, "timestamp": time.time(),
    })
    return {
        "success": True,
        "transaction_id": txn_id,
        "from_balance": source["balance"],
        "to_balance": dest["balance"],
        "vulnerability_note": "Transfer executed without authentication or authorization"
    }


@router.get("/fintech/api/debug/config")
async def fintech_debug_config():
    """VULNERABLE: Exposes internal configuration and secrets (CWE-209, CWE-215)."""
    return {
        "app": "BankCore FinTech API Gateway v2.3.1",
        "debug_mode": True,
        "database": {
            "host": "db.internal",
            "port": 5432,
            "name": "ledger",
            "user": "bankcore_admin",
            "password": "B4nkC0re_S3cret!",
            "connection_string": "postgresql://bankcore_admin:B4nkC0re_S3cret!@db.internal:5432/ledger",
        },
        "redis": {
            "url": "redis://:r3d1s_p4ss@cache.internal:6379/0",
            "password": "r3d1s_p4ss",
        },
        "jwt_secret": "super_secret_jwt_key_do_not_share",
        "api_keys": {
            "stripe": "sk_test_fake_demo_key_do_not_use_bankcore",
            "sendgrid": "SG.fakekey123456789",
        },
        "internal_endpoints": [
            "http://auth-service.internal:8001/validate",
            "http://ledger-service.internal:8002/transactions",
            "http://notifications.internal:8003/send",
        ],
        "vulnerability_note": "DEBUG endpoint should never be exposed in production!"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 3: CLOUDSTORE E-COMMERCE PLATFORM
# Vulnerabilities: SSRF, Cookie-based privilege escalation, Unauth report export
# ═══════════════════════════════════════════════════════════════════════════════

_CLOUDSTORE_ORDERS: list[dict] = [
    {"id": "ORD-1001", "customer": "alice@shop.com", "items": ["Laptop Pro 16", "USB-C Hub"], "total": 1849.99, "status": "shipped"},
    {"id": "ORD-1002", "customer": "bob@shop.com", "items": ["Wireless Mouse", "Keyboard"], "total": 129.50, "status": "delivered"},
    {"id": "ORD-1003", "customer": "charlie@shop.com", "items": ["4K Monitor 27\"", "HDMI Cable"], "total": 549.00, "status": "processing"},
    {"id": "ORD-1004", "customer": "internal@cloudstore.com", "items": ["[INTERNAL] Server Rack", "10TB HDD x4"], "total": 12500.00, "status": "internal"},
]


@router.get("/cloudstore", response_class=HTMLResponse)
async def cloudstore_frontend():
    """CloudStore E-Commerce Platform frontend."""
    body = """
    <div class="grid-2">
      <div class="card">
        <div class="card-title">🌐 Image URL Previewer <span class="badge badge-danger">SSRF Vulnerable</span></div>
        <p style="color:var(--fg2);font-size:12px;margin-bottom:12px">The server fetches and previews images from user-supplied URLs. Try internal endpoints!</p>
        <div class="form-group">
          <label>Image / Resource URL</label>
          <input type="text" id="ssrf-url" placeholder="http://169.254.169.254/latest/meta-data/" />
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
          <button class="btn btn-primary" onclick="fetchUrl()">🔍 Fetch URL</button>
          <button class="btn btn-secondary" onclick="document.getElementById('ssrf-url').value='http://169.254.169.254/latest/meta-data/';fetchUrl()">⚡ AWS Metadata</button>
          <button class="btn btn-secondary" onclick="document.getElementById('ssrf-url').value='http://localhost:8000/health';fetchUrl()">⚡ Internal Health</button>
          <button class="btn btn-secondary" onclick="document.getElementById('ssrf-url').value='file:///etc/passwd';fetchUrl()">⚡ File Read</button>
        </div>
        <div id="ssrf-result" class="result-box" style="display:none"></div>
      </div>

      <div class="card">
        <div class="card-title">🍪 Admin Access <span class="badge badge-danger">Cookie Tampering</span></div>
        <p style="color:var(--fg2);font-size:12px;margin-bottom:12px">The application checks a plaintext cookie for admin access. Set it to escalate privileges.</p>
        <div class="form-group">
          <label>Current Cookie: <code id="current-cookie" style="color:var(--warning)">role=customer</code></label>
        </div>
        <div style="display:flex;gap:8px;margin-bottom:12px">
          <button class="btn btn-secondary" onclick="setCookieRole('customer')">👤 Set Customer</button>
          <button class="btn btn-danger" onclick="setCookieRole('admin')">⚡ Escalate to Admin</button>
        </div>
        <button class="btn btn-primary" onclick="checkAdmin()">🔐 Access Admin Panel</button>
        <div id="cookie-result" class="result-box" style="display:none"></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">📊 Order Report Export <span class="badge badge-danger">No Auth Required</span></div>
        <p style="color:var(--fg2);font-size:12px;margin-bottom:12px">Order reports are accessible without any authentication — sensitive customer data exposed.</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-primary" onclick="exportOrders('json')">📋 Export JSON</button>
          <button class="btn btn-secondary" onclick="exportOrders('csv')">📄 Export CSV</button>
        </div>
        <div id="export-result" class="result-box" style="display:none"></div>
      </div>

      <div class="card">
        <div class="card-title">🛒 Order Lookup <span class="badge badge-warn">IDOR</span></div>
        <div class="form-group">
          <label>Order ID</label>
          <select id="order-id">
            <option value="ORD-1001">ORD-1001 (Alice's order)</option>
            <option value="ORD-1002">ORD-1002 (Bob's order)</option>
            <option value="ORD-1003">ORD-1003 (Charlie's order)</option>
            <option value="ORD-1004">ORD-1004 (Internal order)</option>
          </select>
        </div>
        <button class="btn btn-primary" onclick="lookupOrder()">🔍 View Order</button>
        <div id="order-result" class="result-box" style="display:none"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">📋 All Vulnerabilities</div>
      <table>
        <thead><tr><th>Vulnerability</th><th>Endpoint</th><th>Severity</th><th>Type</th></tr></thead>
        <tbody>
          <tr><td>SSRF</td><td><code>/api/demo-apps/cloudstore/api/media/fetch?url=</code></td><td><span class="vuln-tag vuln-critical">CRITICAL</span></td><td>CWE-918</td></tr>
          <tr><td>Privilege Escalation</td><td><code>/api/demo-apps/cloudstore/api/admin/panel (cookie)</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-565</td></tr>
          <tr><td>Unauthenticated Export</td><td><code>/api/demo-apps/cloudstore/api/reports/orders</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-306</td></tr>
          <tr><td>IDOR</td><td><code>/api/demo-apps/cloudstore/api/orders/{id}</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-639</td></tr>
        </tbody>
      </table>
    </div>

    <script>
      const BASE = '/api/demo-apps/cloudstore/api';

      // Initialize cookie
      if (!document.cookie.includes('role=')) document.cookie = 'role=customer; path=/';
      document.getElementById('current-cookie').textContent = 'role=' + (document.cookie.match(/role=([^;]*)/)?.[1] || 'customer');

      async function fetchUrl() {
        const url = document.getElementById('ssrf-url').value;
        const box = document.getElementById('ssrf-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/media/fetch?url=' + encodeURIComponent(url));
          const data = await r.json();
          box.className = data.error ? 'result-box danger' : 'result-box success';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      function setCookieRole(role) {
        document.cookie = 'role=' + role + '; path=/';
        document.getElementById('current-cookie').textContent = 'role=' + role;
        document.getElementById('current-cookie').style.color = role === 'admin' ? '#ff4757' : 'var(--warning)';
      }

      async function checkAdmin() {
        const box = document.getElementById('cookie-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/admin/panel', { credentials: 'include' });
          const data = await r.json();
          box.className = data.access_granted ? 'result-box success' : 'result-box danger';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function exportOrders(format) {
        const box = document.getElementById('export-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/reports/orders?format=' + format);
          const data = await r.json();
          box.className = 'result-box success';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function lookupOrder() {
        const id = document.getElementById('order-id').value;
        const box = document.getElementById('order-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/orders/' + id);
          const data = await r.json();
          box.className = 'result-box success';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }
    </script>
    """
    return HTMLResponse(_wrap_page(
        "🛒 CloudStore E-Commerce Platform",
        "Multi-tier e-commerce platform with SSRF, cookie-based privilege escalation, and unauthenticated data export",
        body,
        "cloudstore",
    ))


@router.get("/cloudstore/api/media/fetch")
async def cloudstore_ssrf(url: str = Query(..., description="URL to fetch — VULNERABLE to SSRF")):
    """VULNERABLE: Server-side request to user-supplied URL (SSRF — CWE-918)."""
    import httpx

    # INTENTIONALLY VULNERABLE — no URL validation, no SSRF protection
    # Simulates fetching an image but allows arbitrary internal requests
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(url)
            content_type = resp.headers.get("content-type", "unknown")
            return {
                "url": url,
                "status_code": resp.status_code,
                "content_type": content_type,
                "content_length": len(resp.content),
                "body_preview": resp.text[:2000] if "text" in content_type or "json" in content_type or "html" in content_type else f"[Binary content: {len(resp.content)} bytes]",
                "headers": dict(resp.headers),
                "vulnerability_note": "SSRF — no URL validation performed. Internal services and cloud metadata are accessible."
            }
    except Exception as e:
        return JSONResponse({
            "error": str(e),
            "url": url,
            "hint": "The URL could not be reached, but the server DID attempt the request (SSRF confirmed)"
        }, status_code=200)


@router.get("/cloudstore/api/admin/panel")
async def cloudstore_admin_panel(role: str | None = Cookie(None)):
    """VULNERABLE: Admin check via client-controlled plaintext cookie (CWE-565)."""
    if role == "admin":
        return {
            "access_granted": True,
            "admin_panel": {
                "total_revenue": 15028.49,
                "total_orders": len(_CLOUDSTORE_ORDERS),
                "internal_api_key": "cs-api-key-ADMIN-7f8e9d0c",
                "database_url": "mongodb://admin:Cl0udSt0re_DB!@mongo.internal:27017/cloudstore",
                "users_table": "cloudstore.users (2,847 records)",
                "payment_processor": "Stripe (sk_live_xxx...)",
            },
            "vulnerability_note": "Admin access granted via client-side cookie — trivially bypassable"
        }
    return {
        "access_granted": False,
        "message": "Access denied. Admin role required.",
        "hint": "Set cookie 'role=admin' to bypass this check"
    }


@router.get("/cloudstore/api/reports/orders")
async def cloudstore_export_orders(format: str = Query("json")):
    """VULNERABLE: No authentication required — exposes all order data (CWE-306)."""
    data = {
        "report_type": "Full Order Export",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_orders": len(_CLOUDSTORE_ORDERS),
        "orders": _CLOUDSTORE_ORDERS,
        "vulnerability_note": "No authentication required to access this sensitive report"
    }
    if format == "csv":
        csv_lines = ["order_id,customer,items,total,status"]
        for o in _CLOUDSTORE_ORDERS:
            csv_lines.append(f"{o['id']},{o['customer']},\"{'; '.join(o['items'])}\",{o['total']},{o['status']}")
        data["csv_content"] = "\n".join(csv_lines)
    return data


@router.get("/cloudstore/api/orders/{order_id}")
async def cloudstore_get_order(order_id: str):
    """VULNERABLE: No authorization — any caller can access any order (IDOR — CWE-639)."""
    for o in _CLOUDSTORE_ORDERS:
        if o["id"] == order_id:
            return {"order": o, "vulnerability_note": "No authorization check — IDOR vulnerability"}
    return JSONResponse({"error": f"Order '{order_id}' not found"}, status_code=404)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 4: DEVOPS TASK PIPELINE WORKER
# Vulnerabilities: Command injection, env variable dump, path traversal
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/devops", response_class=HTMLResponse)
async def devops_frontend():
    """DevOps Task Pipeline Worker frontend."""
    body = """
    <div class="grid-2">
      <div class="card">
        <div class="card-title">🔧 Build Command Executor <span class="badge badge-danger">Command Injection</span></div>
        <p style="color:var(--fg2);font-size:12px;margin-bottom:12px">Execute build commands on the worker agent. The command is passed directly to the OS shell.</p>
        <div class="form-group">
          <label>Build Command</label>
          <input type="text" id="cmd-input" placeholder="echo 'Hello World'" />
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
          <button class="btn btn-danger" onclick="executeCmd()">▶️ Execute</button>
          <button class="btn btn-secondary" onclick="document.getElementById('cmd-input').value='echo Hello && whoami';executeCmd()">⚡ whoami</button>
          <button class="btn btn-secondary" onclick="document.getElementById('cmd-input').value='echo test; dir';executeCmd()">⚡ dir listing</button>
          <button class="btn btn-secondary" onclick="document.getElementById('cmd-input').value='echo %USERNAME% %COMPUTERNAME%';executeCmd()">⚡ sysinfo</button>
        </div>
        <div id="cmd-result" class="result-box" style="display:none"></div>
      </div>

      <div class="card">
        <div class="card-title">🔑 Environment Variables <span class="badge badge-danger">Secret Leak</span></div>
        <p style="color:var(--fg2);font-size:12px;margin-bottom:12px">The /env endpoint dumps all environment variables — potentially exposing API keys and secrets.</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
          <button class="btn btn-danger" onclick="dumpEnv()">💣 Dump All Env Vars</button>
          <button class="btn btn-secondary" onclick="dumpFilteredEnv('SECRET')">🔍 Filter: SECRET</button>
          <button class="btn btn-secondary" onclick="dumpFilteredEnv('KEY')">🔍 Filter: KEY</button>
          <button class="btn btn-secondary" onclick="dumpFilteredEnv('PASSWORD')">🔍 Filter: PASSWORD</button>
        </div>
        <div id="env-result" class="result-box" style="display:none"></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">📂 File Reader <span class="badge badge-danger">Path Traversal</span></div>
        <p style="color:var(--fg2);font-size:12px;margin-bottom:12px">Read build artifacts by filename. No path sanitization allows reading arbitrary files.</p>
        <div class="form-group">
          <label>File Path</label>
          <input type="text" id="file-path" placeholder="build.log or ../../etc/passwd" />
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
          <button class="btn btn-primary" onclick="readFile()">📖 Read File</button>
          <button class="btn btn-secondary" onclick="document.getElementById('file-path').value='../../requirements.txt';readFile()">⚡ requirements.txt</button>
          <button class="btn btn-secondary" onclick="document.getElementById('file-path').value='../../.env';readFile()">⚡ .env file</button>
        </div>
        <div id="file-result" class="result-box" style="display:none"></div>
      </div>

      <div class="card">
        <div class="card-title">📡 Worker Status <span class="badge badge-info">Info Gathering</span></div>
        <button class="btn btn-primary" onclick="getWorkerStatus()">📊 Get Worker Info</button>
        <div id="status-result" class="result-box" style="display:none"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">📋 All Vulnerabilities</div>
      <table>
        <thead><tr><th>Vulnerability</th><th>Endpoint</th><th>Severity</th><th>Type</th></tr></thead>
        <tbody>
          <tr><td>OS Command Injection</td><td><code>/api/demo-apps/devops/api/build/execute</code></td><td><span class="vuln-tag vuln-critical">CRITICAL</span></td><td>CWE-78</td></tr>
          <tr><td>Env Variable Dump</td><td><code>/api/demo-apps/devops/api/env</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-214</td></tr>
          <tr><td>Path Traversal</td><td><code>/api/demo-apps/devops/api/artifacts/{path}</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-22</td></tr>
          <tr><td>System Info Disclosure</td><td><code>/api/demo-apps/devops/api/status</code></td><td><span class="vuln-tag vuln-high">HIGH</span></td><td>CWE-200</td></tr>
        </tbody>
      </table>
    </div>

    <script>
      const BASE = '/api/demo-apps/devops/api';

      async function executeCmd() {
        const cmd = document.getElementById('cmd-input').value;
        const box = document.getElementById('cmd-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/build/execute', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({command: cmd})
          });
          const data = await r.json();
          box.className = data.exit_code === 0 ? 'result-box success' : 'result-box danger';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function dumpEnv() {
        const box = document.getElementById('env-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/env');
          const data = await r.json();
          box.className = 'result-box danger';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function dumpFilteredEnv(filter) {
        const box = document.getElementById('env-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/env?filter=' + filter);
          const data = await r.json();
          box.className = 'result-box danger';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function readFile() {
        const path = document.getElementById('file-path').value;
        const box = document.getElementById('file-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/artifacts/' + encodeURIComponent(path));
          const data = await r.json();
          box.className = data.error ? 'result-box danger' : 'result-box success';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }

      async function getWorkerStatus() {
        const box = document.getElementById('status-result');
        box.style.display = 'block';
        try {
          const r = await fetch(BASE + '/status');
          const data = await r.json();
          box.className = 'result-box success';
          box.textContent = JSON.stringify(data, null, 2);
        } catch(e) { box.className = 'result-box danger'; box.textContent = '❌ ' + e; }
      }
    </script>
    """
    return HTMLResponse(_wrap_page(
        "⚙️ DevOps Task Pipeline Worker",
        "CI/CD job execution agent with command injection, environment secret dumping, and path traversal vulnerabilities",
        body,
        "devops",
    ))


class BuildCommand(BaseModel):
    command: str


@router.post("/devops/api/build/execute")
async def devops_execute_command(payload: BuildCommand):
    """VULNERABLE: Direct OS command execution from user input (CWE-78)."""
    try:
        # INTENTIONALLY VULNERABLE — direct shell execution of user input
        result = subprocess.run(
            payload.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tempfile.gettempdir(),
        )
        return {
            "command": payload.command,
            "exit_code": result.returncode,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000],
            "vulnerability_note": "OS command injection — user input executed directly in shell (CWE-78)"
        }
    except subprocess.TimeoutExpired:
        return {"command": payload.command, "error": "Command timed out (10s limit)", "exit_code": -1}
    except Exception as e:
        return {"command": payload.command, "error": str(e), "exit_code": -1}


@router.get("/devops/api/env")
async def devops_dump_env(filter: str | None = Query(None)):
    """VULNERABLE: Dumps environment variables including secrets (CWE-214)."""
    env_vars = dict(os.environ)

    # Add fake sensitive secrets for demo purposes
    env_vars.update({
        "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
        "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "DATABASE_PASSWORD": "pr0duct10n_db_p4ss!",
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "SLACK_WEBHOOK": "https://hooks.slack.com/services/T00/B00/xxxx",
        "DEPLOY_SECRET": "dp-sec-0x7f3e9a2d1b4c",
    })

    if filter:
        env_vars = {k: v for k, v in env_vars.items() if filter.upper() in k.upper()}

    return {
        "total_variables": len(env_vars),
        "variables": env_vars,
        "vulnerability_note": "All environment variables exposed — secrets, API keys, and credentials leaked (CWE-214)"
    }


@router.get("/devops/api/artifacts/{file_path:path}")
async def devops_read_artifact(file_path: str):
    """VULNERABLE: No path sanitization — allows reading arbitrary files (CWE-22)."""
    # INTENTIONALLY VULNERABLE — no path traversal protection
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, "data", "artifacts", file_path)

    # Resolve path (allows ../ traversal)
    resolved = os.path.abspath(full_path)

    try:
        if os.path.isfile(resolved):
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(10000)
            return {
                "file": file_path,
                "resolved_path": resolved,
                "size": os.path.getsize(resolved),
                "content": content,
                "vulnerability_note": "Path traversal — no sanitization on file_path input (CWE-22)"
            }
        else:
            # Try from CWD as well
            alt_path = os.path.abspath(os.path.join(os.getcwd(), file_path))
            if os.path.isfile(alt_path):
                with open(alt_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(10000)
                return {
                    "file": file_path,
                    "resolved_path": alt_path,
                    "size": os.path.getsize(alt_path),
                    "content": content,
                    "vulnerability_note": "Path traversal — no sanitization on file_path input (CWE-22)"
                }
            return {"error": f"File not found: {file_path}", "attempted_paths": [resolved, alt_path]}
    except Exception as e:
        return {"error": str(e), "file": file_path, "resolved_path": resolved}


@router.get("/devops/api/status")
async def devops_worker_status():
    """VULNERABLE: Exposes detailed system and process information (CWE-200)."""
    import platform
    import sys

    return {
        "worker": {
            "id": f"worker-{uuid.uuid4().hex[:8]}",
            "version": "1.4.2-rc3",
            "uptime_seconds": int(time.time()) % 86400,
            "status": "idle",
        },
        "system": {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": sys.version,
        },
        "capabilities": {
            "shell_access": True,
            "docker_access": True,
            "network_access": "unrestricted",
            "privilege_level": "root-equivalent",
        },
        "recent_builds": [
            {"id": "build-001", "command": "npm run build", "status": "success", "duration": "12s"},
            {"id": "build-002", "command": "docker build -t app .", "status": "success", "duration": "45s"},
            {"id": "build-003", "command": "pytest --cov", "status": "failed", "duration": "8s"},
        ],
        "vulnerability_note": "Detailed system information disclosed without authentication (CWE-200)"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO APPS INDEX
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def demo_apps_index():
    """Landing page for all demo applications."""
    body = """
    <div class="grid-2">
      <a href="/api/demo-apps/juice-shop" style="text-decoration:none">
        <div class="card" style="cursor:pointer">
          <div class="card-title">🍹 OWASP Juice Shop <span class="badge badge-danger">5 Vulns</span></div>
          <p style="color:var(--fg2);font-size:13px;margin-bottom:12px">SQL Injection, Reflected XSS, Auth Bypass, BOLA/IDOR, Weak JWT</p>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span class="badge badge-info">Node.js 20</span>
            <span class="badge badge-info">Express</span>
            <span class="badge badge-info">SQLite</span>
          </div>
        </div>
      </a>
      <a href="/api/demo-apps/fintech" style="text-decoration:none">
        <div class="card" style="cursor:pointer">
          <div class="card-title">🏦 BankCore FinTech <span class="badge badge-danger">4 Vulns</span></div>
          <p style="color:var(--fg2);font-size:13px;margin-bottom:12px">BOLA, Unauthorized Transfers, Rate-Limit Bypass, Debug Info Leak</p>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span class="badge badge-info">Python</span>
            <span class="badge badge-info">FastAPI</span>
            <span class="badge badge-info">Redis</span>
          </div>
        </div>
      </a>
      <a href="/api/demo-apps/cloudstore" style="text-decoration:none">
        <div class="card" style="cursor:pointer">
          <div class="card-title">🛒 CloudStore E-Commerce <span class="badge badge-danger">4 Vulns</span></div>
          <p style="color:var(--fg2);font-size:13px;margin-bottom:12px">SSRF, Cookie-Based Privilege Escalation, Unauth Report Export, IDOR</p>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span class="badge badge-info">Express</span>
            <span class="badge badge-info">Docker Compose</span>
            <span class="badge badge-info">MongoDB</span>
          </div>
        </div>
      </a>
      <a href="/api/demo-apps/devops" style="text-decoration:none">
        <div class="card" style="cursor:pointer">
          <div class="card-title">⚙️ DevOps Worker <span class="badge badge-danger">4 Vulns</span></div>
          <p style="color:var(--fg2);font-size:13px;margin-bottom:12px">OS Command Injection, Env Secret Dump, Path Traversal, Info Disclosure</p>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span class="badge badge-info">Go 1.22</span>
            <span class="badge badge-info">Alpine</span>
            <span class="badge badge-info">Shell</span>
          </div>
        </div>
      </a>
    </div>
    """
    return HTMLResponse(_wrap_page(
        "🎯 Pantheon Demo Vulnerable Applications",
        "4 intentionally vulnerable micro-applications for security testing demonstrations. Each contains real exploitable endpoints.",
        body,
        "",
    ))
