# Home Wi‑Fi Parental Firewall

A Windows-based parental firewall for home networks that helps protect children from adult websites, inappropriate content, ads, trackers, and other harmful online destinations by filtering traffic from devices connected through the home Wi‑Fi hotspot.

This project is designed for parents and guardians who want a practical, local layer of protection on the home network. It lets you monitor network activity, block unwanted domains, cut off internet access to specific devices, and protect connected devices from unsafe or inappropriate content while browsing on the family Wi‑Fi.

## Why this project exists

The goal is simple: keep kids safer online by filtering the home Wi‑Fi before harmful content reaches their devices.

This project helps block:

- Adult websites and explicit content
- Gambling, scam, and unsafe sites
- Advertising and tracking domains
- Harmful or suspicious websites
- Unwanted keywords and unsafe traffic patterns
- Devices that should be disconnected from the internet temporarily

It is meant to act as a family safety tool on a home network, especially when devices connect through a Windows hotspot or local Wi‑Fi access point.

## Features

- Block domains such as adult content, gambling, malware, and harmful websites
- Block ads, trackers, and unwanted traffic sources
- Filter traffic by keyword patterns
- Cut off internet access to individual connected devices
- Live dashboard that shows blocked activity in real time
- Hotspot-aware filtering for devices connected through the home network
- Device-level control for instant network shutdown or restore
- Easy config management through a desktop interface

## How it works

The firewall inspects traffic from devices connected to the hotspot and blocks dangerous or undesired content using several network-layer techniques:

- DNS sinkhole: blocked domains are answered locally instead of resolving to the real site
- TLS SNI reset: HTTPS requests that mention a blocked domain are terminated before the connection completes
- HTTP host inspection: blocked hostnames in plain HTTP traffic are cut off
- Keyword and pattern filtering: suspicious content and unsafe strings can be blocked

This helps stop access to blocked websites and harmful content across the home network before it reaches the user device.

## Project goal

This tool is designed to support a safer online environment for children by giving parents a way to:

- Protect kids from adult sites and explicit content
- Reduce exposure to aggressive ads and unwanted tracking
- Block harmful or suspicious websites
- Manage which devices can access the internet at certain times
- Maintain visibility into network activity through the dashboard

## Requirements

- Windows 10 or Windows 11
- Mobile hotspot enabled on the host PC
- Python 3.8+
- Npcap installed: https://npcap.com/ (choose WinPcap API-compatible mode)
- Run as Administrator

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the project

You can launch it with the provided batch file:

```bash
run_firewall_dashboard.bat
```

Or start it manually:

```bash
python firewall_dashboard.py
```

## Typical usage

1. Turn on Windows Mobile Hotspot.
2. Connect your home devices to that hotspot.
3. Launch the dashboard as Administrator.
4. Start the firewall protection.
5. Add blocked domains or unsafe keywords.
6. Monitor live activity and block harmful sites in real time.
7. Use device-level cut-off controls if a device needs internet access removed immediately.

## Example blocking behavior

If a child tries to visit a blocked site such as a mature content site or a malicious domain:

- The domain is blocked before it loads
- The browser or app fails to reach the site
- The dashboard logs the event and shows the blocked connection

## Dashboard overview

The dashboard includes pages such as:

- Dashboard
- Blocked Sites
- Keywords
- Devices
- Activity Log
- Settings

These sections let you manage rules, review blocked activity, and quickly respond to suspicious behavior on the family network.

## Configuration

The project stores settings in `firewall_config.json`.

```json
{
    "filter_enabled": true,
    "hotspot_filtering_enabled": true,
    "hotspot_subnet": "192.168.137.0/24",
    "blocked_domains": ["example-blocked-site.com"],
    "blocked_ips": [],
    "blocked_keywords": [],
    "allowed_ips": ["127.0.0.1"]
}
```

## Important notes

- Best suited for networks you own or administer.
- This is a local family protection helper, not a replacement for professional-grade network security systems.
- HTTPS content cannot always be fully inspected, but the firewall still blocks many dangerous domains and connections using DNS and SNI-level controls.
- Apps using encrypted DNS may require additional filtering layers, but the dashboard remains useful for monitoring and blocking attempts.

## Disclaimer

This project is for authorized, lawful use on networks you own or manage, such as a home family Wi‑Fi network. It is intended to support parental control and home cybersecurity practices, especially for protecting children from adult content, harmful websites, and malicious online exposure.

## License

This project is provided for educational and personal use. Please review the repository license if one is added later.
