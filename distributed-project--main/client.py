"""
Distributed Counter Client (Console)
====================================
A simple TCP client that connects to the counter server.
Supports INCREMENT, DECREMENT, RESET, and GET commands.
"""

import socket
import sys


def send_command(host, port, command):
    """
    Connect to the server, send a command, and print the response.
    Commands: INCREMENT | DECREMENT | RESET | GET
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(command.encode("utf-8"))

            # Wait for the server's reply
            reply = b""
            while b"\n" not in reply:
                chunk = s.recv(1024)
                if not chunk:
                    break
                reply += chunk

            reply = reply.decode("utf-8").strip()
            if reply.startswith("OK:"):
                print(f"Server says: counter is now {reply.split(':')[1]}")
            elif reply.startswith("BROADCAST:"):
                print(f"Broadcast: counter is now {reply.split(':')[1]}")
            else:
                print(f"Server says: {reply}")
    except ConnectionRefusedError:
        print("[ERROR] Could not connect to server. Is it running?")
    except Exception as e:
        print(f"[ERROR] {e}")


def interactive_client(host, port):
    """Run an interactive loop where the user types commands."""
    print("Distributed Counter Client")
    print("Commands: INCREMENT | DECREMENT | RESET | GET | quit")
    print("-" * 40)

    while True:
        try:
            cmd = input("> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if cmd == "QUIT" or cmd == "":
            print("Goodbye!")
            break

        if cmd in ("INCREMENT", "DECREMENT", "RESET", "GET"):
            send_command(host, port, cmd)
        else:
            print("Unknown command. Use INCREMENT, DECREMENT, RESET, GET, or quit.")


if __name__ == "__main__":
    # Default connection settings
    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 5000

    # Optional command-line usage: python client.py INCREMENT
    if len(sys.argv) == 2:
        send_command(SERVER_HOST, SERVER_PORT, sys.argv[1].upper())
    else:
        interactive_client(SERVER_HOST, SERVER_PORT)
