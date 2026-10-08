"""C tracker - consent-based live location sharing (Flask + SQLite).

Run locally:  pip install -r requirements.txt && python app.py
Everyone must tick the consent boxes and press Start themselves.
Only the latest position is stored, and it is deleted on Stop/Leave.
"""
import os
import secrets
import sqlite3
import time

from flask import Flask, g, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "ctracker.db")
MAX_AGE = 24 * 3600  # drop locations older than 24h


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS members(
              token TEXT PRIMARY KEY, name TEXT, grp TEXT, consent_at REAL);
            CREATE TABLE IF NOT EXISTS locations(
              token TEXT PRIMARY KEY, lat REAL, lon REAL, acc REAL, t REAL);
            """
        )


init_db()


def member():
    token = request.headers.get("X-Token", "")
    row = db().execute("SELECT * FROM members WHERE token=?", (token,)).fetchone()
    return row


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/join")
def join():
    d = request.get_json(force=True, silent=True) or {}
    name = (d.get("name") or "").strip()[:30]
    code = (d.get("code") or "").strip().upper()
    if not name:
        return jsonify(error="Enter your name."), 400
    if d.get("consent") is not True:
        return jsonify(error="Consent is required to join."), 400
    conn = db()
    if code:
        if not conn.execute("SELECT 1 FROM members WHERE grp=?", (code,)).fetchone():
            return jsonify(error="Group code not found."), 404
    else:
        code = secrets.token_hex(3).upper()
    token = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO members VALUES(?,?,?,?)", (token, name, code, time.time())
    )
    conn.commit()
    return jsonify(token=token, code=code, name=name)


@app.post("/api/location")
def location():
    m = member()
    if not m:
        return jsonify(error="Unknown member."), 401
    d = request.get_json(force=True, silent=True) or {}
    try:
        lat, lon = float(d["lat"]), float(d["lon"])
        acc = float(d.get("acc") or 0)
    except (KeyError, ValueError, TypeError):
        return jsonify(error="Bad location."), 400
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify(error="Bad location."), 400
    conn = db()
    conn.execute(
        "REPLACE INTO locations VALUES(?,?,?,?,?)",
        (m["token"], lat, lon, acc, time.time()),
    )
    conn.commit()
    return jsonify(ok=True)


@app.post("/api/stop")
def stop():
    m = member()
    if m:
        conn = db()
        conn.execute("DELETE FROM locations WHERE token=?", (m["token"],))
        conn.commit()
    return jsonify(ok=True)


@app.post("/api/leave")
def leave():
    m = member()
    if m:
        conn = db()
        conn.execute("DELETE FROM locations WHERE token=?", (m["token"],))
        conn.execute("DELETE FROM members WHERE token=?", (m["token"],))
        conn.commit()
    return jsonify(ok=True)


@app.get("/api/members")
def members():
    m = member()
    if not m:
        return jsonify(error="Unknown member."), 401
    conn = db()
    conn.execute("DELETE FROM locations WHERE t<?", (time.time() - MAX_AGE,))
    conn.commit()
    rows = conn.execute(
        """SELECT m.token, m.name, l.lat, l.lon, l.acc, l.t FROM members m
           JOIN locations l ON l.token=m.token WHERE m.grp=?""",
        (m["grp"],),
    ).fetchall()
    out = [
        dict(name=r["name"], me=r["token"] == m["token"], lat=r["lat"],
             lon=r["lon"], acc=r["acc"], t=r["t"] * 1000)
        for r in rows
    ]
    return jsonify(code=m["grp"], members=out)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
