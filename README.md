# PortPier - TCP Port Mapping Tool

A lightweight Python-based TCP port mapping / NAT traversal tool that exposes local services to the public internet.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()
[![GitHub Stars](https://img.shields.io/github/stars/FatFatYoung/PortPier.svg)](https://github.com/FatFatYoung/PortPier/stargazers)

## ✨ Features

### Server
- 🖥️ Visual management UI (tkinter GUI)
- 👥 Multiple concurrent client connections
- 🔐 Client authentication (username/password)
- 📊 Real-time connection logs
- 🔥 Firewall log viewer
- 🛡️ IP allowlist / blocklist access control
- ⚙️ Flexible port mapping rule configuration
- 🌐 **English/Chinese bilingual support** (one-click switch)

### Client
- 🖥️ Visual configuration UI
- 🔄 Automatic reconnection
- 📝 Real-time connection logs
- 🔐 Password protection
- 💾 Persistent configuration
- 🌐 **English/Chinese bilingual support** (one-click switch)

## 📁 Project Structure

```
PortPier/
├── README.md                        # Project overview (changelog / architecture / FAQ)
├── LICENSE                          # MIT License
├── THIRD_PARTY_NOTICES.md           # Third-party open-source component notices
├── .gitignore
├── server/                          # Server (GUI edition)
│   ├── gui_server.py                # GUI management UI (recommended)
│   ├── common.py                    # Shared protocol module (codec / packet cap / logging)
│   ├── i18n.py                      # Internationalization module
│   ├── build.bat                    # Packaging script
│   ├── config.example.json          # Sample config (TLS / trusted_proxies / max_packet_size)
│   └── legacy/                      # Legacy web console (reference only)
│       ├── server.py
│       └── common.py
└── client/                          # Client (GUI edition)
    ├── gui_client.py                # GUI client (recommended)
    ├── common.py                    # Shared protocol module (same as server)
    ├── i18n.py                      # Internationalization module
    ├── build.bat                    # Packaging script
    ├── client_config.example.json   # Sample connection config
    ├── client_rules.example.json    # Sample mapping rules
    └── legacy/                      # Legacy command-line client (reference only)
        ├── client.py
        └── common.py
```

## 🚀 Quick Start

### Option 1: Prebuilt EXE (recommended)

1. Download the latest release from [Releases](https://github.com/FatFatYoung/PortPier/releases)
2. Extract and double-click `portpier_server.exe` or `portpier_client.exe`
3. **No Python installation required**

### Option 2: Run from Source

#### Requirements
- Python 3.10+
- Windows 10/11

#### Run the Server
```bash
cd server
python gui_server.py
```

#### Run the Client
```bash
cd client
python gui_client.py
```

## 🖥️ Server Deployment

### 1. Start the Server

Double-click `portpier_server.exe` to start the server.

### 2. Log In

- Default username: `admin`
- Default password: `admin`

### 3. Configure the Server

In the "System Settings" tab:

1. **Control port**: the port clients connect to (default 8024)
2. **Global default port range**: the ports clients are allowed to map

### 4. Configure the Firewall

If the server has a firewall, open the required ports:

```powershell
New-NetFirewallRule -DisplayName "PortPier" -Direction Inbound -Protocol TCP -LocalPort 8024,10000-20000 -Action Allow
```

## 📖 Usage

### Server Configuration

1. **Start the server** - double-click `portpier_server.exe`
2. **Default credentials** - admin / admin
3. **Configure the listen port** - default 8024
4. **Add clients** - in the "Client Management" tab

### Client Configuration

1. **Start the client** - double-click `portpier_client.exe`
2. **Default password** - admin
3. **Configure the server** - click "Settings" and fill in the server information
4. **Add mapping rules** - click "Rules" to add port mappings
5. **Connect to the server** - click "Connect"

### Language Switching

Click the language button in the top-right corner of the UI to switch between Chinese and English. The language setting is saved automatically.

## ❓ FAQ

### Q: Connection fails?

- Check that the server address and port are correct
- Check that the server firewall has the ports open
- Check that the token is correct

### Q: Port mapping not working?

- Check that the local service is running
- Check that the remote port is within the allowed range

### Q: Connection drops?

The client reconnects automatically; just wait.

## 🛡️ Security

- All passwords are stored with PBKDF2 hashing
- IP allowlist / blocklist access control
- TCP Keepalive to prevent connection timeouts
- Optional TLS (`tls_enabled`) protecting credentials and tunnel data
- Client tokens are stored only as PBKDF2 hashes; legacy plaintext entries are purged on load
- `X-Forwarded-For` / `X-Real-Ip` are only honored from sources listed in `trusted_proxies`, preventing IP-list bypass via header spoofing
- Per-packet length cap plus a bounded stream queue, preventing memory exhaustion via malicious oversized length declarations

**TLS configuration (config.json on both ends):**

- Server: `tls_enabled: true` plus `tls_certfile` / `tls_keyfile` (PEM); refuses to start when the certificate is missing, never falls back to plaintext
- Client: `tls_enabled: true` plus optional `tls_ca_file` (leave empty to use the system CA); `tls_insecure_skip_verify: true` explicitly skips verification (encrypted but unauthenticated)
- Reverse-proxy deployment: list proxy IPs/CIDR/ranges in `trusted_proxies`; only XFF headers from those sources are trusted; empty means never trust
- `max_packet_size`: upper bound for declared per-packet length (bytes, default 1048576 = 1 MiB; oversized packets disconnect); configurable in both config.json files

## 🏗️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          Internet                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                            Server                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Control     │  │ Mapped 1    │  │ Mapped 2    │   ...    │
│  │ (8024)      │  │ (80)        │  │ (443)       │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│                    ┌─────▼─────┐                             │
│                    │ Client    │                             │
│                    │ Handler   │                             │
│                    └───────────┘                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ TCP connection
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                            Client                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Local Svc 1 │  │ Local Svc 2 │  │ Local Svc 3 │   ...    │
│  │ (80)        │  │ (443)       │  │ (22)        │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│                    ┌─────▼─────┐                             │
│                    │ Proxy     │                             │
│                    │ Client    │                             │
│                    └───────────┘                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Local Network                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Web         │  │ HTTPS       │  │ SSH         │   ...    │
│  │ (80)        │  │ (443)       │  │ (22)        │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

#### 1. Client Connection Flow

```
   Client                     Server
   │                          │
   │  1. TCP connect          │
   │ ────────────────────────>│
   │                          │
   │  2. Send client_id       │
   │ ────────────────────────>│
   │                          │
   │  3. Send token           │
   │ ────────────────────────>│
   │                          │
   │  4. Auth result          │
   │ <────────────────────────│
   │                          │
   │  5. Send rules           │
   │ ────────────────────────>│
   │                          │
   │  6. Keepalive heartbeat  │
   │ <───────────────────────>│
```

#### 2. Data Forwarding Flow

```
 Visitor              Server                Client                Local Service
 │                      │                     │                     │
 │  1. HTTP request     │                     │                     │
 │ ────────────────────>│                     │                     │
 │                      │                     │                     │
 │                      │  2. Assign stream_id│                     │
 │                      │ ───────────────────>│                     │
 │                      │                     │                     │
 │  3. Forward data     │                     │                     │
 │ ────────────────────>│ ───────────────────>│ ───────────────────>│
 │                      │                     │                     │
 │  4. Return response  │                     │                     │
 │ <────────────────────│ <───────────────────│ <───────────────────│
 │                      │                     │                     │
```

### Core Components

#### Server Components

1. **GUI Server** (`gui_server.py`)
   - tkinter visual management UI
   - Client management
   - Rule configuration
   - Log viewer
   - Firewall logs
   - IP access control

2. **Protocol Handler** (`common.py`)
   - Packet encoding/decoding
   - Flow control
   - Heartbeat mechanism

3. **Client Handler**
   - Client connection management
   - Authentication
   - Rule synchronization
   - Data forwarding

#### Client Components

1. **GUI Client** (`gui_client.py`)
   - tkinter visual configuration UI
   - Server configuration
   - Rule management
   - Log viewer

2. **Proxy Client**
   - Local port listening
   - Data forwarding
   - Automatic reconnection

### Protocol Format

#### Packet Format

```
+──────────────+──────────────+──────────────+
│ Length (4B)  │ stream_id    │ Payload      │
│              │ (4B)         │ (variable)   │
+──────────────+──────────────+──────────────+
```

#### stream_id Meaning

| stream_id | Meaning |
|-----------|---------|
| 0 | Control message (heartbeat, rule operations) |
| > 0 | Data stream (maps to a specific connection) |

#### Control Message Format

```json
{
  "action": "add|remove|pong",
  "public_port": 80,
  "target_host": "127.0.0.1",
  "target_port": 8080
}
```

### Security Mechanisms

#### 1. Authentication

- The client sends client_id and token on connect
- The server verifies that the token matches
- Tokens are stored with PBKDF2 hashing

#### 2. IP Access Control

- Allowlist/blocklist for client connection IPs
- Allowlist/blocklist for visitor IPs
- Supports CIDR, IP ranges, and wildcard formats

#### 3. Password Protection

- The client GUI requires a password to log in
- Passwords are stored with PBKDF2 hashing
- Password change supported

### Performance Optimizations

#### 1. Async Architecture

- Asynchronous I/O implemented with Python asyncio
- High-concurrency connection support

#### 2. Buffer Optimization

- Read buffer: 64KB
- Write buffer: 64KB
- Fewer system calls

#### 3. TCP Keepalive

- TCP Keepalive enabled to prevent connection timeouts
- Parameters: 60s idle, 15s interval, 5 retries

### Extensibility

#### 1. Adding a New Transport Protocol

Extend the encode/decode functions in `common.py`.

#### 2. Adding a New Authentication Method

Modify the authentication logic in the server's `handle_client`.

#### 3. Adding New Access Control

Add a new check function on the server side; see `is_ip_allowed` for reference.

## 📝 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project follows [Semantic Versioning](https://semver.org/lang/en.html).

### [Unreleased]

#### Security
- 🔒 **Memory exhaustion protection** - declared packet length is capped at 1 MiB; the stream queue is now a bounded queue
- 🔒 **Plaintext token removal** - `allowed_clients.json` no longer stores plaintext tokens; legacy plaintext entries are purged on load
- 🔒 **XFF spoofing protection** - `X-Forwarded-For` / `X-Real-Ip` are only honored from sources listed in `trusted_proxies`
- 🔒 **TLS encryption** - optional TLS for the control channel and tunnel data (server certificate/key, client CA verification)

#### Fixed
- 🐛 Fixed gui_client.py failing to start due to an import of the relocated common module
- 🐛 Fixed a NameError caused by a missing `logging` import on the authentication-failure path

### [1.2.0] - 2026-05-10

#### Changed
- ✨ **Smoother language switching** - the UI rebuild now carries over the runtime log
  - Fixes the previous loss of logs after switching language
  - Server: the main log and firewall logs (blocked/allowed) are refreshed while keeping history
  - Client: the connection log transitions smoothly instead of being cleared

#### Technical
- 🔧 **UI state management convention** - introduced the "Save-Destroy-Rebuild-Restore" pattern
- 🔧 **ScrolledText state handling** - fixed the silent failure when inserting history text in read-only mode

### [1.1.0] - 2026-05-08

#### Added
- 🌐 **English/Chinese bilingual support** - full UI internationalization
  - Both server and client support Chinese/English switching
  - The language button shows the target language
  - The UI rebuilds immediately after switching
  - The language setting is saved automatically
- 📝 **Localized log messages** - all connection logs support Chinese and English

#### Fixed
- 🐛 Fixed the language button display logic
- 🐛 Fixed scrolling on the server settings page
- 🐛 Fixed the config file path issue on first run
- 🐛 Fixed the double-window issue at startup

### [1.0.0] - 2026-05-04

#### Added
- ✨ Server-side visual management UI (tkinter GUI)
- ✨ Client-side visual configuration UI
- ✨ Multiple concurrent client connections
- ✨ Client authentication
- ✨ Real-time connection logs
- ✨ Firewall log viewer
- ✨ IP allowlist/blocklist access control
- ✨ Automatic reconnection
- ✨ Single-file EXE packaging

#### Technical Highlights
- Async architecture based on Python asyncio
- TCP Keepalive to prevent connection timeouts
- 64KB buffers for faster transfers
- CIDR, IP range, and wildcard IP formats

## 🆚 Comparison with Similar Tools

| Feature | PortPier | frp | ngrok | natpass |
|---------|----------|-----|-------|---------|
| **Language** | Python | Go | Go | Go |
| **GUI** | ✅ | ❌ | ❌ | ❌ |
| **English/Chinese UI** | ✅ | ❌ | ✅ | ❌ |
| **Learning curve** | ⭐ Easy | ⭐⭐ Medium | ⭐ Easy | ⭐⭐⭐ Complex |
| **Target users** | Beginners / Windows | Developers | Developers | Ops |
| **Self-hosted** | ✅ | ✅ | ❌ | ✅ |

## 🤝 Contributing

Thank you for your interest in PortPier! Here is how you can contribute.

### 🐛 Report Bugs

1. Make sure the bug has not already been reported in [Issues](https://github.com/FatFatYoung/PortPier/issues)
2. Open a new Issue including:
   - A clear title and description
   - Steps to reproduce
   - Expected and actual behavior
   - System environment information

### 💡 Suggest Features

Open a new Issue in [Issues](https://github.com/FatFatYoung/PortPier/issues) and label it `enhancement`.

### 🔧 Submit Code

1. Fork this repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push the branch: `git push origin feature/your-feature`
5. Open a Pull Request

#### Code Style

- Use Python 3.10+ syntax
- Follow PEP 8
- Add necessary comments
- Make sure the code runs correctly

### 📝 Improve Documentation

- Fix typos
- Supplement usage instructions
- Add sample code

### 📧 Contact

If you have any questions, reach out via:
- Opening an [Issue](https://github.com/FatFatYoung/PortPier/issues)
- Email: fafafat@qq.com

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

For third-party open-source component notices, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## 📧 Contact

- GitHub: [@FatFatYoung](https://github.com/FatFatYoung)
- Email: fafafat@qq.com

---

⭐ If you find this project helpful, please give it a Star!
