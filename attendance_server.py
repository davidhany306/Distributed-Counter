"""
Distributed Attendance Server
=============================
A TCP server that maintains a shared attendance list for multiple clients.
Uses threading.Lock to prevent race conditions when multiple students mark
attendance simultaneously.
"""

import socket
import threading

# ---------------------------------------------------------------------------
# Shared State (protected by Lock)
# ---------------------------------------------------------------------------
attendance_set = set()        # Stores unique student names
clients = []                  # Active client connections for broadcast
attendance_lock = threading.Lock()   # Synchronizes access to shared state


def broadcast(count, exclude_conn=None):
    """
    Send the updated attendance count to all connected clients.
    exclude_conn: optional socket to skip (usually the sender already knows).
    """
    with attendance_lock:
        snapshot = clients.copy()

    message = f"BROADCAST:{count}\n".encode("utf-8")
    dead = []
    for conn in snapshot:
        if conn is exclude_conn:
            continue
        try:
            conn.sendall(message)
        except (BrokenPipeError, ConnectionResetError, OSError):
            dead.append(conn)

    # Clean up disconnected clients
    if dead:
        with attendance_lock:
            for conn in dead:
                if conn in clients:
                    clients.remove(conn)


def handle_client(conn, addr):
    """Handle one client connection in a dedicated thread."""
    print(f"[+] Client connected: {addr}")

    with attendance_lock:
        clients.append(conn)

    try:
        buffer = b""
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data

            # Process complete lines
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                command = line.decode("utf-8").strip()
                process_command(conn, addr, command)

    except ConnectionResetError:
        print(f"[!] Connection reset by {addr}")
    finally:
        with attendance_lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        print(f"[-] Client disconnected: {addr}")


def process_command(conn, addr, command):
    """Parse a client command and perform the appropriate action."""
    global attendance_set

    # Command format: "MARK:<name>" or "GET"
    if command.startswith("MARK:"):
        name = command[5:].strip()

        if not name:
            conn.sendall(b"ERROR:Name cannot be empty\n")
            return

        with attendance_lock:
            if name in attendance_set:
                # Duplicate — reject but still send current count
                count = len(attendance_set)
                response = f"DUPLICATE:{count}\n"
                conn.sendall(response.encode("utf-8"))
                print(f"[*] {addr} tried duplicate attendance: '{name}'")
            else:
                # New student — add and increment counter
                attendance_set.add(name)
                count = len(attendance_set)
                response = f"OK:{count}\n"
                conn.sendall(response.encode("utf-8"))
                print(f"[>] Attendance marked: '{name}' | Total: {count}")
                broadcast(count, exclude_conn=conn)

    elif command == "GET":
        with attendance_lock:
            count = len(attendance_set)
        response = f"OK:{count}\n"
        conn.sendall(response.encode("utf-8"))

    else:
        conn.sendall(b"ERROR:Unknown command\n")


def start_server(host="0.0.0.0", port=5000):
    """Create the listening socket and accept connections forever."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)

    print(f"[SERVER] Attendance Server listening on {host}:{port}")
    print("[SERVER] Press Ctrl+C to stop\n")

    try:
        while True:
            conn, addr = server_socket.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            )
            thread.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()
