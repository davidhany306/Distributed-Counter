"""
Distributed Attendance Client (GUI)
====================================
A Tkinter GUI that connects to the attendance server.
- Input field for student name
- Mark Attendance button
- Live label showing total attendees
- Background thread listens for broadcast updates
"""

import socket
import threading
import tkinter as tk
from tkinter import messagebox


class AttendanceClientGUI:
    def __init__(self, master, host, port):
        self.master = master
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False

        master.title("Attendance System")
        master.geometry("340x260")
        master.resizable(False, False)

        # --- GUI Widgets ---
        tk.Label(master, text="Attendance System", font=("Helvetica", 18, "bold")).pack(pady=15)

        # Name entry
        tk.Label(master, text="Enter your name:", font=("Helvetica", 11)).pack()
        self.name_entry = tk.Entry(master, font=("Helvetica", 12), justify="center", width=25)
        self.name_entry.pack(pady=5)
        self.name_entry.focus()

        # Mark button
        self.mark_btn = tk.Button(
            master, text="Mark Attendance", font=("Helvetica", 11, "bold"),
            bg="#4CAF50", fg="white", width=18, height=1,
            command=self.mark_attendance
        )
        self.mark_btn.pack(pady=10)

        # Bind Enter key to the button
        master.bind("<Return>", lambda event: self.mark_attendance())

        # Total attendees label
        self.count_label = tk.Label(
            master, text="Total Attendees: --",
            font=("Helvetica", 14)
        )
        self.count_label.pack(pady=5)

        # Status message
        self.status_label = tk.Label(
            master, text="Connecting...", font=("Helvetica", 10), fg="blue"
        )
        self.status_label.pack(pady=5)

        # --- Connection & Listener ---
        self.connect()

    def connect(self):
        """Establish TCP connection and start the background listener."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            self.status_label.config(text="Connected. Enter your name.", fg="green")

            # Fetch initial count
            self.send_command("GET")

            # Start background thread to listen for broadcasts
            listener = threading.Thread(target=self.listen, daemon=True)
            listener.start()
        except Exception as e:
            self.status_label.config(text=f"Connection failed: {e}", fg="red")
            self.disable_ui()

    def send_command(self, command):
        """Send a text command to the server."""
        if not self.connected:
            return
        try:
            self.sock.sendall(command.encode("utf-8"))
        except OSError as e:
            self.status_label.config(text=f"Error: {e}", fg="red")
            self.connected = False
            self.disable_ui()

    def mark_attendance(self):
        """Read the name entry and send MARK command."""
        name = self.name_entry.get().strip()
        if not name:
            self.status_label.config(text="Please enter your name", fg="orange")
            return

        self.status_label.config(text="Sending...", fg="blue")
        self.send_command(f"MARK:{name}")

    def listen(self):
        """Background thread: continuously read data from the server."""
        buffer = b""
        while self.connected:
            try:
                chunk = self.sock.recv(1024)
                if not chunk:
                    break
                buffer += chunk

                # Extract complete lines
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self.process_message(line.decode("utf-8").strip())
            except OSError:
                break

        self.connected = False
        self.master.after(0, lambda: self.status_label.config(
            text="Disconnected from server", fg="red"))
        self.master.after(0, self.disable_ui)

    def process_message(self, msg):
        """Handle server messages and update the GUI on the main thread."""
        if msg.startswith("OK:"):
            count = msg.split(":", 1)[1]
            self.master.after(0, lambda c=count: self.count_label.config(
                text=f"Total Attendees: {c}"))
            self.master.after(0, lambda: self.status_label.config(
                text="Marked successfully", fg="green"))
            self.master.after(0, lambda: self.name_entry.delete(0, tk.END))

        elif msg.startswith("DUPLICATE:"):
            count = msg.split(":", 1)[1]
            self.master.after(0, lambda c=count: self.count_label.config(
                text=f"Total Attendees: {c}"))
            self.master.after(0, lambda: self.status_label.config(
                text="You already marked attendance", fg="orange"))

        elif msg.startswith("BROADCAST:"):
            count = msg.split(":", 1)[1]
            self.master.after(0, lambda c=count: self.count_label.config(
                text=f"Total Attendees: {c}"))

        elif msg.startswith("ERROR:"):
            self.master.after(0, lambda m=msg: self.status_label.config(
                text=m, fg="red"))

    def disable_ui(self):
        """Disable interactive widgets when disconnected."""
        self.name_entry.config(state=tk.DISABLED)
        self.mark_btn.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = AttendanceClientGUI(root, "127.0.0.1", 5000)
    root.mainloop()


if __name__ == "__main__":
    main()
