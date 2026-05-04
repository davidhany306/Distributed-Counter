# Distributed Systems Project

## Overview

This project demonstrates two distributed systems built with Python, showcasing client-server architectures, thread synchronization, and real-time updates:

1. **Distributed Counter System**: A shared counter that multiple clients can increment, decrement, reset, or query over TCP.
2. **Distributed Attendance System**: A system for tracking student attendance with unique name registration and real-time count broadcasting.

Both systems use threading and locks to handle concurrent access safely, preventing race conditions.

## Features

- **Thread-Safe Operations**: Uses `threading.Lock` to synchronize access to shared state.
- **Real-Time Broadcasting**: Servers broadcast updates to all connected clients for live synchronization.
- **Multiple Client Types**: Console clients, GUI clients (Tkinter), and a web interface (Streamlit).
- **TCP-Based Communication**: Reliable socket connections for client-server interaction.
- **Concurrency Testing**: Designed to handle multiple simultaneous connections.

## Requirements

- Python 3.7 or higher
- `streamlit` library (install with `pip install streamlit`)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd distributed-systems-project
   ```

2. Install dependencies:
   ```bash
   pip install streamlit
   ```

## Usage

### Distributed Counter System

#### Components
- `server.py`: TCP server managing the shared counter.
- `client.py`: Console-based client for manual testing.
- `client_gui.py`: Tkinter GUI client with buttons and live display.

#### Running the Counter System

1. **Start the server**:
   ```bash
   python server.py
   ```
   Output:
   ```
   [SERVER] Listening on 0.0.0.0:5000
   [SERVER] Press Ctrl+C to stop
   ```

2. **Run clients** (in separate terminals):
   - Console client:
     ```bash
     python client.py
     ```
     Type commands: `INCREMENT`, `DECREMENT`, `RESET`, `GET`, or `quit`.
     Or run directly: `python client.py INCREMENT`

   - GUI client:
     ```bash
     python client_gui.py
     ```
     A window appears with buttons and a live counter label.

3. **Test concurrency**: Open multiple clients and perform operations simultaneously. The lock ensures correctness.

#### How Synchronization Works

Python threads share memory. Without locks, concurrent `INCREMENT` operations can cause race conditions:

```
Thread A reads counter = 5
Thread B reads counter = 5
Thread A writes counter = 6
Thread B writes counter = 6  # Lost increment!
```

`threading.Lock` solves this by making operations atomic:

```python
counter_lock = threading.Lock()
with counter_lock:
    counter += 1
```

### Distributed Attendance System

#### Components
- `attendance_server.py`: TCP server managing the attendance set.
- `attendance_client_gui.py`: Tkinter GUI for marking attendance.
- `app.py`: Streamlit web interface for attendance management.

#### Running the Attendance System

1. **Start the attendance server**:
   ```bash
   python attendance_server.py
   ```

2. **Run clients** (in separate terminals):
   - GUI client:
     ```bash
     python attendance_client_gui.py
     ```
     Enter name and click "Mark Attendance".

   - Web interface:
     ```bash
     streamlit run app.py
     ```
     Access at http://localhost:8501 for admin features like viewing/exporting attendance.

#### Features
- Unique name registration (no duplicates).
- Real-time count updates via broadcasting.
- Web app for administrative tasks (login required).

## Architecture

Both systems follow a similar pattern:
- **Server**: Listens on TCP port, spawns threads per client, uses locks for shared state.
- **Clients**: Connect via sockets, send commands, receive responses and broadcasts.
- **Broadcasting**: Servers notify all clients of state changes for synchronization.

## Code Structure

| File | Description |
|------|-------------|
| `server.py` | Counter server with lock and broadcasting |
| `client.py` | Counter console client |
| `client_gui.py` | Counter GUI client |
| `attendance_server.py` | Attendance server |
| `attendance_client_gui.py` | Attendance GUI client |
| `app.py` | Streamlit web app for attendance |

## FAQ

**Q: What happens with concurrent operations?**  
A: Locks serialize updates, ensuring no data loss.

**Q: Why threading?**  
A: Prevents blocking on slow clients; each connection gets its own thread.

**Q: Can the counter/attendance persist?**  
A: Currently in-memory only. Extend with file/database storage.

**Q: How to add more operations?**  
A: Modify server handlers and client commands.

## Contributing

Feel free to extend with persistence, authentication, or more features!

## License

MIT License
