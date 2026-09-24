# Parental Firewall 🛡

Blocks specific websites for **every device connected to your PC's hotspot** — with a modern desktop dashboard for managing rules, watching live activity, and cutting a device's internet off entirely.

## How blocking works

When you add a site (e.g. `instagram.com`) to **Blocked Sites**, the engine blocks it three ways for hotspot clients:

| Layer | Mechanism | Covers |
|-------|-----------|--------|
| DNS sinkhole | Blocked domain queries are answered with `192.168.137.1` (your PC) instead of the real server | All apps that use normal DNS |
| TLS SNI reset | HTTPS ClientHello packets naming a blocked domain get a TCP RST — connection dies instantly | HTTPS sites, even when DNS resolves another way |
| HTTP host reset | Plain HTTP requests with a blocked `Host:` header get a TCP RST | Unencrypted traffic |

Rules apply to devices on the hotspot subnet (`192.168.137.0/24` by default — the standard Windows Mobile Hotspot range). Your own PC's traffic is not filtered.

### Device-level control
On the **Devices** page you can also **cut off ALL internet** for one device (Windows Firewall rule, in+out) and restore it later — useful as a hard kill switch per device.

## Requirements

- Windows 10/11 with Mobile Hotspot (Settings → Network → Mobile hotspot) **on**
- Python 3.8+
- Npcap — https://npcap.com/ (install with "WinPcap API-compatible Mode")
- **Run as Administrator** (packet capture + firewall rules need it)

```
pip install -r requirements.txt
```

## Run it

Double-click `run_firewall_dashboard.bat` (self-elevates to Administrator), or:

```
python firewall_dashboard.py
```

## Using the dashboard

New sidebar layout with six pages:

| Page | What you do there |
|------|-------------------|
| **Dashboard** | Stat cards (blocked sites, keywords, packets blocked, devices), live activity table, and a **Quick Block** box — type a domain, press Enter, done. |
| **Blocked Sites** | Add/remove the domains every hotspot device is blocked from. Subdomains included automatically (`cdn.instagram.com` is covered by `instagram.com`). |
| **Keywords** | Words that get unencrypted traffic cut off. |
| **Devices** | Lists devices connected to the hotspot; cut off / restore internet per device. |
| **Activity Log** | Live color-coded log with clear/export. |
| **Settings** | Toggle content filtering, toggle hotspot-only scoping, save. |

Rule changes apply **live** — no restart needed when protection is running.

## Typical session

1. Turn on Windows Mobile Hotspot.
2. Run the dashboard as Administrator → **START PROTECTION**.
3. Connect your phone to the hotspot.
4. Type `instagram.com` in Quick Block → on the phone, the site/app now fails to load.
5. Watch the Dashboard activity table record the blocks.

## Config (`firewall_config.json`)

```json
{
    "filter_enabled": true,
    "hotspot_filtering_enabled": true,
    "hotspot_subnet": "192.168.137.0/24",
    "blocked_domains": ["chatgpt.com"],
    "blocked_ips": [],
    "blocked_keywords": [],
    "allowed_ips": ["127.0.0.1"]
}
```

- `hotspot_filtering_enabled: false` → filter ALL traffic through the PC, not just hotspot devices.
- `hotspot_subnet` → change if your hotspot uses a different range.

## Honest limitations

- HTTPS **content** (pages inside a connection) can't be read — blocking works at DNS/SNI level, which is how real network blockers do it.
- Apps using encrypted DNS (DoH) bypass the DNS sinkhole, but the TLS SNI layer still catches them.
- QUIC/HTTP3 (UDP 443) isn't intercepted yet; browsers usually fall back to TCP after a failed attempt.
- Requires the hotspot interface; auto-detected by subnet.

**Disclaimer:** For authorized use on networks you own or administer.
