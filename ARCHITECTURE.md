# 🏗️ WiFi Firewall - System Architecture

## 📊 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                     │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         Firewall Dashboard (GUI)                      │ │
│  │         (firewall_dashboard.py)                       │ │
│  │                                                       │ │
│  │  [START] [STOP]  [Interface Selector]               │ │
│  │                                                       │ │
│  │  Tabs:                                               │ │
│  │   • Blocked Domains    • Blocked IPs                │ │
│  │   • Blocked Keywords   • Real-time Logs             │ │
│  │   • Settings & Statistics                           │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CONTROL LAYER                            │
│                                                             │
│  • Start/Stop Firewall                                     │
│  • Thread Management                                       │
│  • Real-time Log Updates                                   │
│  • Configuration Management                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    FIREWALL ENGINE                          │
│                  (wifi_firewall.py)                         │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  WiFiFirewall Class                                   │ │
│  │                                                       │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │  Packet Capture (Scapy)                         │ │ │
│  │  │   • Sniff network traffic                       │ │ │
│  │  │   • Extract packet data                         │ │ │
│  │  └─────────────────────────────────────────────────┘ │ │
│  │                     │                                 │ │
│  │                     ↓                                 │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │  Content Analysis                               │ │ │
│  │  │   • Check sensitive patterns (regex)            │ │ │
│  │  │   • Check blocked domains                       │ │ │
│  │  │   • Check blocked IPs                           │ │ │
│  │  │   • Check blocked keywords                      │ │ │
│  │  └─────────────────────────────────────────────────┘ │ │
│  │                     │                                 │ │
│  │                     ↓                                 │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │  Filtering Decision                             │ │ │
│  │  │   • Allow or Block                              │ │ │
│  │  │   • Log action                                  │ │ │
│  │  │   • Update statistics                           │ │ │
│  │  └─────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                               │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │ Configuration    │    │  Log Files       │             │
│  │                  │    │                  │             │
│  │ firewall_       │    │  firewall.log    │             │
│  │ config.json     │    │                  │             │
│  │                 │    │  • Timestamps    │             │
│  │ • Domains       │    │  • IP addresses  │             │
│  │ • IPs           │    │  • Block reasons │             │
│  │ • Keywords      │    │  • Statistics    │             │
│  │ • Patterns      │    │                  │             │
│  └──────────────────┘    └──────────────────┘             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    NETWORK LAYER                            │
│                                                             │
│         WiFi Network Interface                             │
│         (Monitored by Scapy/Npcap)                         │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow Diagram

```
Network Packet
      │
      ↓
WiFi Interface (Npcap captures)
      │
      ↓
Scapy Packet Sniffer
      │
      ↓
Packet Handler (wifi_firewall.py)
      │
      ├──→ Check IP (blocked/allowed)
      │         │
      │         ↓
      │    BLOCK/ALLOW
      │
      ├──→ Extract Payload
      │         │
      │         ↓
      │    Check Sensitive Patterns (regex)
      │         │
      │         ↓
      │    BLOCK/ALLOW
      │
      ├──→ Check Domain
      │         │
      │         ↓
      │    BLOCK/ALLOW
      │
      └──→ Check Keywords
                │
                ↓
           BLOCK/ALLOW
                │
                ↓
         Log to File
                │
                ↓
    Update Statistics
                │
                ↓
    GUI Displays (real-time refresh)
```

## 🎛️ Component Interaction

### Dashboard → Firewall Engine

```python
# User clicks "START FIREWALL"
dashboard.start_firewall()
    │
    ├──→ Create WiFiFirewall instance
    │    firewall = WiFiFirewall(config_file)
    │
    ├──→ Start in separate thread
    │    thread.start(firewall.start_monitoring)
    │
    └──→ Update UI status
         status: "RUNNING"
```

### Firewall Engine → Dashboard

```python
# Firewall detects blocked packet
firewall.block_packet(packet, reason)
    │
    ├──→ Write to firewall.log
    │
    ├──→ Update blocked_count statistics
    │
    └──→ Dashboard auto-refreshes (every 2 seconds)
         │
         └──→ Read firewall.log
              │
              └──→ Display in log viewer (color-coded)
```

## 🧩 Module Breakdown

### 1. **firewall_dashboard.py**
**Purpose:** GUI interface for user interaction

**Key Classes:**
- `FirewallDashboard`: Main GUI controller

**Key Methods:**
- `start_firewall()`: Initialize and start firewall engine
- `stop_firewall()`: Stop firewall monitoring
- `run_firewall(interface)`: Thread function to run firewall
- `auto_refresh_logs()`: Periodic log update (2s interval)
- `add_domain/ip/keyword()`: Manage blocking rules
- `save_config()`: Persist configuration changes

**UI Components:**
- Control buttons (Start/Stop)
- Network interface selector
- Status indicator
- 5 tabs for different functions
- Real-time log viewer with syntax highlighting

### 2. **wifi_firewall.py**
**Purpose:** Core firewall engine and packet processing

**Key Classes:**
- `WiFiFirewall`: Main firewall engine

**Key Methods:**
- `start_monitoring(interface)`: Begin packet capture
- `packet_handler(packet)`: Process each packet
- `check_sensitive_content(payload)`: Regex pattern matching
- `check_blocked_domain(payload)`: Domain filtering
- `block_packet(packet, reason)`: Log and block action
- `load_config()`: Read firewall rules
- `print_statistics()`: Display blocking stats

**Detection Mechanisms:**
- Regex pattern matching for sensitive data
- String matching for domains/keywords
- IP address filtering
- HTTP layer inspection

### 3. **firewall_config.json**
**Purpose:** Persistent configuration storage

**Structure:**
```json
{
  "filter_enabled": boolean,
  "sensitive_patterns": [regex_strings],
  "blocked_domains": [domain_strings],
  "blocked_ips": [ip_strings],
  "blocked_keywords": [keyword_strings],
  "allowed_ips": [ip_strings]
}
```

## 🔐 Security Features

### Multi-Layer Detection

1. **IP Layer:**
   - Check source/destination IPs
   - Block blacklisted addresses
   - Whitelist trusted IPs

2. **Payload Layer:**
   - Inspect packet content
   - Regex pattern matching
   - Keyword detection

3. **HTTP Layer:**
   - Extract HTTP requests
   - Check Host headers
   - Inspect URLs

### Pattern Matching

```
Credit Cards:  \b\d{16}\b
SSN:           \b\d{3}-\d{2}-\d{4}\b
Emails:        \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b
Passwords:     \bpassword\s*[:=]\s*\S+\b
API Keys:      \bapi[_-]?key\s*[:=]\s*\S+\b
Tokens:        \btoken\s*[:=]\s*\S+\b
```

## 📡 Threading Model

```
Main Thread (GUI)
    │
    ├──→ UI Event Loop (tkinter mainloop)
    │
    ├──→ Auto-refresh Timer (every 2s)
    │    │
    │    └──→ refresh_logs()
    │         update_runtime_stats()
    │
    └──→ Firewall Thread (daemon)
         │
         └──→ packet capture loop
              │
              └──→ for each packet:
                   packet_handler()
```

## 💾 File I/O Operations

### Configuration Flow

```
Startup:
  load_config() → Read firewall_config.json
      │
      └──→ Parse JSON
           │
           └──→ Store in memory

User Changes:
  add_domain() → Update in-memory config
      │
      └──→ save_config() → Write to firewall_config.json
```

### Logging Flow

```
Packet Blocked:
  block_packet()
      │
      ├──→ Format log message
      │    (timestamp + level + message)
      │
      └──→ Append to firewall.log
           │
           └──→ Dashboard reads (auto-refresh)
                │
                └──→ Display in log viewer
```

## 🎨 UI Update Cycle

```
Dashboard Running:
    │
    └──→ Every 2 seconds:
         │
         ├──→ Check if firewall is running
         │
         ├──→ Read firewall.log
         │    │
         │    └──→ Compare with current display
         │         │
         │         └──→ Update if changed
         │
         ├──→ Update runtime statistics
         │    │
         │    └──→ Total packets blocked
         │         Firewall status
         │
         └──→ Auto-scroll logs (if enabled)
```

## 🔧 Extension Points

### Adding New Detection Rules

1. **Edit firewall_config.json:**
   - Add to `sensitive_patterns`
   - Add to `blocked_keywords`

2. **Modify wifi_firewall.py:**
   - Add new `check_*()` method
   - Call from `packet_handler()`

### Adding New UI Features

1. **Edit firewall_dashboard.py:**
   - Add new tab: `setup_*_tab()`
   - Add new controls
   - Connect to firewall methods

## 🚀 Performance Considerations

### Optimization Strategies

1. **Regex Compilation:**
   - Pre-compile patterns at startup
   - Reuse compiled regex objects

2. **Threading:**
   - Run packet capture in separate thread
   - Prevent UI blocking

3. **Log Buffering:**
   - Batch write log entries
   - Reduce file I/O overhead

4. **Selective Filtering:**
   - Skip whitelisted IPs early
   - Filter by protocol/port

## 📈 Scalability

**Current Limitations:**
- Single-threaded packet processing
- In-memory statistics only
- File-based logging

**Scaling Options:**
- Multi-threaded packet processing
- Database for logs/statistics
- Distributed filtering
- Web-based dashboard

## 🎯 Integration Summary

**Connected Components:**

✅ **GUI ↔ Firewall Engine**: Full integration via threading  
✅ **Configuration ↔ Both**: Shared JSON config file  
✅ **Logging ↔ Dashboard**: Real-time log display  
✅ **Statistics ↔ Dashboard**: Live stats updating  
✅ **User Actions ↔ Firewall**: Start/stop/configure  

**The system is fully integrated and operational!** 🛡️
