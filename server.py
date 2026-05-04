import socket
import threading
import sqlite3
import os
from datetime import datetime

# ── Settings ─────────────────────────
HOST = "0.0.0.0"
PORT = 5000
DB_FILE = "attendance.db"
CAPACITY = int(os.environ.get("ATTEND_CAPACITY", "40"))
VALID_GROUPS = {"L1", "L2", "T1-1", "T1-2", "T2-1", "T2-2"}

db_lock = threading.Lock()

clients = []
clients_lock = threading.Lock()

# ── Database setup ──────────────────
def init_db():
    with sqlite3.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grp TEXT,
                sid TEXT,
                name TEXT,
                date TEXT
            )
        """)
        con.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_grp_sid_date
            ON attendance (grp, sid, date)
        """)

# ── DB helpers ──────────────────────
def db_count(grp, date):
    with sqlite3.connect(DB_FILE) as con:
        return con.execute(
            "SELECT COUNT(*) FROM attendance WHERE grp=? AND date=?",
            (grp, date)
        ).fetchone()[0]

def db_mark(grp, sid, name, date):
    with db_lock:
        with sqlite3.connect(DB_FILE) as con:
            count = db_count(grp, date)

            if count >= CAPACITY:
                return "full", count

            try:
                con.execute(
                    "INSERT INTO attendance (grp, sid, name, date) VALUES (?,?,?,?)",
                    (grp, sid, name, date)
                )
                return "new", db_count(grp, date)

            except sqlite3.IntegrityError:
                return "duplicate", count

def db_list(grp, date):
    with sqlite3.connect(DB_FILE) as con:
        return con.execute(
            "SELECT name, sid FROM attendance WHERE grp=? AND date=?",
            (grp, date)
        ).fetchall()

def db_summary(date):
    with sqlite3.connect(DB_FILE) as con:
        return con.execute(
            "SELECT grp, COUNT(*) FROM attendance WHERE date=? GROUP BY grp",
            (date,)
        ).fetchall()

# ── Networking ──────────────────────
def reply(conn, msg):
    print(f"[RESPONSE] {msg}")
    conn.sendall((msg + "\n").encode())

def broadcast(msg, exclude=None):
    print(f"[BROADCAST] {msg}")
    with clients_lock:
        for c in clients:
            if c != exclude:
                try:
                    c.sendall((msg + "\n").encode())
                except:
                    pass

def handle_client(conn, addr):
    print(f"[+] Connected: {addr}")

    with clients_lock:
        clients.append(conn)

    buffer = b""

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                cmd = line.decode().strip()
                if cmd:
                    process_command(conn, cmd)

    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)

        conn.close()
        print(f"[-] Disconnected: {addr}")

# ── Command handler ─────────────────
def process_command(conn, cmd):
    print(f"[CMD] {cmd}")
    today = datetime.now().strftime("%Y-%m-%d")

    # MARK attendance
    if cmd.startswith("MARK:"):
        parts = cmd.split(":", 3)
        if len(parts) != 4:
            return reply(conn, "ERROR:Bad format")

        _, grp, sid, name = parts

        if grp not in VALID_GROUPS:
            return reply(conn, "ERROR:Invalid group")

        status, count = db_mark(grp, sid, name, today)

        if status == "new":
            reply(conn, f"SUCCESS:{count}")
            broadcast(f"BROADCAST:{grp}:{count}", exclude=conn)

        elif status == "duplicate":
            reply(conn, f"DUPLICATE:{count}")

        elif status == "full":
            reply(conn, f"FULL:{count}")

    # GET count
    elif cmd.startswith("GET:"):
        grp = cmd.split(":", 1)[1]

        if grp not in VALID_GROUPS:
            return reply(conn, "ERROR:Invalid group")

        count = db_count(grp, today)
        reply(conn, f"SUCCESS:{count}")

    # ADMIN list
    elif cmd.startswith("ADMIN:"):
        try:
            _, grp, date = cmd.split(":", 2)

            if grp not in VALID_GROUPS:
                return reply(conn, "ERROR:Invalid group")

            rows = db_list(grp, date)
            result = ",".join([f"{name}|{sid}" for name, sid in rows])

            reply(conn, f"LIST:{result}")

        except Exception as e:
            reply(conn, f"ERROR:{e}")

    # SUMMARY
    elif cmd.startswith("SUMMARY:"):
        try:
            date = cmd.split(":", 1)[1]
            rows = db_summary(date)

            summary = ",".join([f"{grp}={cnt}" for grp, cnt in rows])
            reply(conn, f"SUMMARY:{summary}")

        except Exception as e:
            reply(conn, f"ERROR:{e}")

    else:
        reply(conn, "ERROR:Unknown command")

# ── Start server ────────────────────
def start_server():
    init_db()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)

    print(f"[SERVER] Listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
