"""
Distributed Counter Client (GUI)
================================
A Tkinter GUI that connects to the counter server.
- Buttons for Increment, Decrement, Reset
- A label showing the current counter value
- Background thread listens for broadcast updates
"""

import socket
import threading
import tkinter as tk
from tkinter import messagebox


class CounterClientGUI:
    def __init__(self, master, host, port):
        self.master = master
        self.host = host
        self.port = port
        self.sock = None
        self.lock = threading.Lock()
        self.connected = False

        master.title("Distributed Counter")
        master.geometry("300x220")
        master.resizable(False, False)

        # --- GUI Widgets ---
        tk.Label(master, text="Distributed Counter", font=("Helvetica", 16, "bold")).pack(pady=10)

        self.value_label = tk.Label(master, text="?", font=("Helvetica", 32))
        self.value_label.pack(pady=5)

        btn_frame = tk.Frame(master)
        btn_frame.pack(pady=10)

        self.inc_btn = tk.Button(btn_frame, text="+ Increment", width=10, command=self.increment)
        self.inc_btn.grid(row=0, column=0, padx=5)

        self.dec_btn = tk.Button(btn_frame, text="- Decrement", width=10, command=self.decrement)
        self.dec_btn.grid(row=0, column=1, padx=5)

        self.reset_btn = tk.Button(btn_frame, text="Reset", width=10, command=self.reset)
        self.reset_btn.grid(row=1, column=0, columnspan=2, pady=5)

        self.status = tk.Label(master, text="Connecting...", fg="blue")
        self.status.pack(pady=5)

        # --- Connection & Listener ---
        self.connect()

    def connect(self):
        """Establish the TCP connection and start the broadcast listener."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            self.status.config(text="Connected", fg="green")

            # Fetch current value once
            self.send_command("GET")

            # Start background thread to listen for BROADCAST messages
            listener = threading.Thread(target=self.listen, daemon=True)
            listener.start()
        except Exception as e:
            self.status.config(text=f"Connection failed: {e}", fg="red")
            self.disable_buttons()

    def send_command(self, command):
        """Send a command and optionally read a direct response."""
        if not self.connected:
            return
        try:
            self.sock.sendall(command.encode("utf-8"))
        except OSError as e:
            self.status.config(text=f"Error: {e}", fg="red")
            self.connected = False
            self.disable_buttons()

    def listen(self):
        """Background thread: continuously receive data from the server."""
        buffer = b""
        while self.connected:
            try:
                chunk = self.sock.recv(1024)
                if not chunk:
                    break
                buffer += chunk

                # Process complete lines
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self.process_message(line.decode("utf-8").strip())
            except OSError:
                break

        # Connection lost
        self.connected = False
        self.master.after(0, lambda: self.status.config(text="Disconnected", fg="red"))
        self.master.after(0, self.disable_buttons)

    def process_message(self, msg):
        """Parse server messages and update the GUI."""
        # We use after() so Tkinter updates happen on the main thread
        if msg.startswith("OK:") or msg.startswith("BROADCAST:"):
            try:
                value = msg.split(":", 1)[1]
                self.master.after(0, lambda v=value: self.value_label.config(text=v))
            except IndexError:
                pass
        elif msg.startswith("ERROR"):
            self.master.after(0, lambda m=msg: self.status.config(text=m, fg="red"))

    def increment(self):
        self.send_command("INCREMENT")

    def decrement(self):
        self.send_command("DECREMENT")

    def reset(self):
        if messagebox.askyesno("Confirm", "Reset counter to 0?"):
            self.send_command("RESET")

    def disable_buttons(self):
        self.inc_btn.config(state=tk.DISABLED)
        self.dec_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = CounterClientGUI(root, "127.0.0.1", 5000)
    root.mainloop()


if __name__ == "__main__":
    main()
