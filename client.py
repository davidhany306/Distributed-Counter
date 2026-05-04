import socket
import sys

def send_command(host, port, command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall((command + "\n").encode())

            reply = b""
            while b"\n" not in reply:
                chunk = s.recv(1024)
                if not chunk:
                    break
                reply += chunk

            reply = reply.decode().strip()

            if reply.startswith("SUCCESS:"):
                print(f"OK → {reply}")
            elif reply.startswith("BROADCAST:"):
                print(f"BROADCAST → {reply}")
            else:
                print(reply)

    except Exception as e:
        print(e)

if __name__ == "__main__":
    send_command("127.0.0.1", 5000, "GET:L1")
