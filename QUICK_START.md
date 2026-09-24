# 🚀 Quick Start — WiFi Firewall (Hotspot Site Blocker)

## One-time setup

1. `pip install -r requirements.txt`
2. Install **Npcap** → https://npcap.com/ (keep "WinPcap API-compatible Mode" checked)

## Every time

1. Turn on **Windows Mobile Hotspot** (Settings → Network & internet → Mobile hotspot).
2. Double-click **`run_firewall_dashboard.bat`** (it self-elevates to Administrator).
3. Click **▶ START PROTECTION** in the sidebar.

## Block a site for all hotspot devices

- **Fastest way:** Dashboard page → *QUICK BLOCK* box → type `example.com` → Enter.
- Or open **Blocked Sites** page → type the domain → **＋ ADD**.

Devices on your hotspot can no longer open that site (DNS + HTTPS + HTTP are all covered). Subdomains are included automatically. Changes apply **live** — no restart.

## Cut off one device completely

**Devices** page → pick the device IP → **✂ CUT OFF INTERNET**.
Restore it with **✔ RESTORE INTERNET**.

## Watch it work

- **Dashboard** → stat cards + live activity table (who tried what, when).
- **Activity Log** → full color-coded history, exportable.

## Stop

Sidebar → **■ STOP PROTECTION**. Per-device cutoffs are cleaned up automatically when the engine stops.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Failed to start" | Run as Administrator; make sure Npcap is installed. |
| No devices listed | Hotspot must be ON with at least one device connected; wait 15 s (auto-refresh) or hit REFRESH. |
| Site not blocked on phone | Check the domain spelling (no `https://`, just `example.com`); app might need restart on the phone. |
| Blocking my own PC | Settings → keep "Only filter devices on this PC's hotspot" checked. |
| Wrong subnet | Edit `hotspot_subnet` in `firewall_config.json`. |
