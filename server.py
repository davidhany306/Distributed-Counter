"""
Attendance Server
=================
Handles multiple clients at once using threads.
Stores data in SQLite so nothing is lost on restart.
Enforces capacity limit server-side.
"""

import socket
import threading
import sqlite3
import os
from datetime import datetime

# ── Settings ─────────────────────────────────────────────────────────────────
HOST        = "0.0.0.0"
PORT        = 5000
DB_FILE     = "attendance.db"
CAPACITY    = int(os.environ.get("ATTEND_CAPACITY", "40"))
VALID_GROUPS = {"L1", "L2", "T1-1", "T1-2", "T2-1", "T2-2"}

# One lock shared by all threads so only one writes to the DB at a time
db_lock = threading.Lock()


# ── Database setup ────────────────────────────────────────────────────────────
def init_db():
    """Create the attendance table if it doesn't exist yet."""
    with sqlite3.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                grp   TEXT NOT NULL,
                sid   TEXT NOT NULL,
                name  TEXT NOT NULL,
                date  TEXT NOT NULL
            )
        """)
        # This index makes duplicate checks fast
        con.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_grp_sid_date
            ON attendance (grp, sid, date)
        """)


# ── Database helpers ──────────────────────────────────────────────────────────
def db_count(grp, date):
    """Return how many students are marked for a group on a given date."""
    with sqlite3.connect(DB_FILE) as con:
        row = con.execute(
            "SELECT COUNT(*) FROM attendance WHERE grp=? AND date=?",
            (grp, date)
        ).fetchone()
    return row[0]


def db_mark(grp, sid, name, date):
    """
    Try to insert a new attendance record.
    Returns 'new', 'duplicate', or 'full'.
    """
    with db_lock:
        with sqlite3.connect(DB_FILE) as con:
            # Check capacity first
            count = con.execute(
                "SELECT COUNT(*) FROM attendance WHERE grp=? AND date=?",
                (grp, date)
            ).fetchone()[0]

            if count >= CAPACITY:
                return "full", count

            try:
                con.execute(
                    "INSERT INTO attendance (grp, sid, name, date) VALUES (?,?,?,?)",
                    (grp, sid, name, date)
                )
                # Count again after insert to get the new total
                new_count = con.execute(
                    "SELECT COUNT(*) FROM attendance WHERE grp=? AND date=?",
                    (grp, date)
                ).fetchone()[0]
                return "new", new_count

            except sqlite3.IntegrityError:
                # UNIQUE constraint hit — this student already signed in today
                return "duplicate", count


def db_list(grp, date):
    """Return a list of (name, sid) tuples for a group on a given date."""
    with sqlite3.connect(DB_FILE) as con:
        rows = con.execute(
            "SELECT name, sid FROM attendance WHERE grp=? AND date=? ORDER BY id",
            (grp, date)
        ).fetchall()
    return rows


def db_summary(date):
    """Return a dict of {group: count} for all groups on a given date."""
    with sqlite3.connect(DB_FILE) as con:
        rows = con.execute(
            "SELECT grp, COUNT(*) FROM attendance WHERE date=? GROUP BY grp",
            (date,)
        ).fetchall()
    # Start with zero for every group, then fill in what the DB returned
    summary = {g: 0 for g in VALID_GROUPS}
    for grp, cnt in rows:
        summary[grp] = cnt
    return summary


# ── Per-client networking ─────────────────────────────────────────────────────
def handle_client(conn, addr):
    """
    Each client runs in its own thread.
    We buffer incoming bytes and process one command per newline.
    """
    print(f"[+] Connected: {addr}")
    buffer = b""

    try:
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                break
            buffer += chunk

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                cmd = line.decode("utf-8", errors="replace").strip()
                if cmd:
                    process_command(conn, cmd)

    except (ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
    finally:
        conn.close()
        print(f"[-] Disconnected: {addr}")


def reply(conn, msg):
    """Send a newline-terminated response back to the client."""
    conn.sendall((msg + "\n").encode())


def process_command(conn, cmd):
    """Parse one command and send back the right response."""
    print(f"[CMD] {cmd}")
    today = datetime.now().strftime("%Y-%m-%d")

    # ── MARK:group:student_id:name ──────────────────────────────────────────
    if cmd.startswith("MARK:"):
        parts = cmd.split(":", 3)
        if len(parts) != 4:
            return reply(conn, "ERROR:Bad format — expected MARK:group:id:name")

        _, grp, sid, name = parts
        grp  = grp.strip()
        sid  = sid.strip()
        name = name.strip()

        if grp not in VALID_GROUPS:
            return reply(conn, "ERROR:Unknown group")
        if not sid or not name:
            return reply(conn, "ERROR:ID and name cannot be empty")
        # Basic check: student ID should be digits only
        if not sid.isdigit():
            return reply(conn, "ERROR:Student ID must be numbers only")

        status, count = db_mark(grp, sid, name, today)

        if status == "new":
            print(f"[>] {name} ({sid}) marked in {grp} | Total: {count}")
            reply(conn, f"SUCCESS:{count}")
        elif status == "duplicate":
            reply(conn, f"DUPLICATE:{count}")
        elif status == "full":
            reply(conn, f"FULL:{count}")

    # ── GET:group ───────────────────────────────────────────────────────────
    elif cmd.startswith("GET:"):
        grp = cmd.split(":", 1)[1].strip()
        if grp not in VALID_GROUPS:
            return reply(conn, "ERROR:Unknown group")
        count = db_count(grp, today)
        reply(conn, f"SUCCESS:{count}")

    # ── ADMIN:group:date ────────────────────────────────────────────────────
    elif cmd.startswith("ADMIN:"):
        parts = cmd.split(":", 2)
        if len(parts) != 3:
            return reply(conn, "ERROR:Bad format — expected ADMIN:group:date")
        _, grp, date = parts
        grp  = grp.strip()
        date = date.strip()
        if grp not in VALID_GROUPS:
            return reply(conn, "ERROR:Unknown group")
        rows = db_list(grp, date)
        # Format: "name|id,name|id,..."
        result = ",".join(f"{name}|{sid}" for name, sid in rows)
        reply(conn, f"LIST:{result}")

    # ── SUMMARY:date ────────────────────────────────────────────────────────
    elif cmd.startswith("SUMMARY:"):
        date = cmd.split(":", 1)[1].strip()
        summary = db_summary(date)
        # Format: "L1=5,L2=3,T1-1=12,..."
        result = ",".join(f"{g}={c}" for g, c in sorted(summary.items()))
        reply(conn, f"SUMMARY:{result}")

    else:
        reply(conn, "ERROR:Unknown command")


# ── Start server ──────────────────────────────────────────────────────────────
def start_server():
    init_db()
    print(f"[SERVER] Database: {DB_FILE}")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[SERVER] Listening on {HOST}:{PORT}")
    print(f"[SERVER] Capacity per group: {CAPACITY}")
    print("[SERVER] Press Ctrl+C to stop\n")

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()