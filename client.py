import socket   ## library to connect to server 


def send_command(host, port, command):  ##(ip address, port number, command to send) 
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: ## create a socket object  (af_inet for ipv4, sock_stream for tcp)
            s.connect((host, port)) ## connect to the server using the provided host and port
            s.sendall((command + "\n").encode()) ## send the command to the server fe 25rha /n, encoding it to bytes and adding a newline character

            reply = b""  ## variable of bytes 
            while b"\n" not in reply:
                chunk = s.recv(1024)
                if not chunk:
                    break
                reply += chunk

            reply = reply.decode().strip()  ## bytes to string again and remove any leading/trailing whitespace

            if reply.startswith("SUCCESS:"):
                print(f"OK → {reply}")
            elif reply.startswith("BROADCAST:"):
                print(f"BROADCAST → {reply}")
            else:
                print(reply)

    except Exception as e:
        print(e)

def main():
    host = "127.0.0.1"
    port = 5000

    lectures = ["L1", "L2"]
    tutorials = ["T1-1", "T1-2", "T2-1", "T2-2"]

    while True:
        print("\n===== MENU =====")
        print("1. Get Lecture")
        print("2. Get Tutorial")
        print("5. Reset")
        print("6. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            print("Available Lectures:", lectures)
            lec = input("Choose Lecture: ")

            if lec not in lectures:
                print("Invalid Lecture ❌")
                continue

            command = f"GET:{lec}"

        elif choice == "2":
            print("Available Tutorials:", tutorials)
            tut = input("Choose Tutorial: ")

            if tut not in tutorials:
                print("Invalid Tutorial ❌")
                continue

            command = f"GET:{tut}"

        elif choice == "5":
            command = "RESET"

        elif choice == "6":
            print("Goodbye 👋")
            break

        else:
            print("Invalid choice ❌")
            continue

        send_command(host, port, command)


if __name__ == "__main__":
    main()
