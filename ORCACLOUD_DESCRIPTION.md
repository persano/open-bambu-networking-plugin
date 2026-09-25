Open Bamboo Networking connects your Bambu Lab printer to OrcaSlicer with full cloud print dispatch, remote camera liveview, and AMS slot sync, without requiring closed source vendor libraries or Developer Mode on the printer.

![Open Bambu Network not Installed](https://api.orcaslicer.com/api/v1/bundles/media/5a098184-b7bd-4fbd-8031-a6c6aff8ca99/content?expires=1790358429&signature=qi1l3CmC_62buxalYt90ifxo6Nd72_p-hZuWn8LVqkg)

## What it does

- **Cloud print without developer mode.** Automatically signs and sends print jobs directly over official Bambu Cloud without touching Developer Mode or switching your printer to LAN Only mode.
- **Remote camera liveview.** Streams live camera video when you are away from home via clean room ThroughTek (TUTK) P2P tunnels, with instant stop and resume reconnects.
- **Instant AMS slot sync.** Restores multi-color AMS slot telemetry and temperatures immediately on connection, keeping sliced filament assignments in sync.
- **In-slicer management tab.** Adds an "Open Bamboo" tab right in OrcaSlicer's top bar with real-time status detection and 1 click installation or rollback.
- **Clean and silent startup.** Fully compliant with OrcaSlicer's security auditor: zero permission popups or socket warnings when launching OrcaSlicer.
- **Cross platform.** Pre-compiled clean room native libraries bundled for Windows, Linux, and macOS Apple Silicon.

## Clean room and privacy first

- **Zero proprietary vendor blobs.** Bundles clean room open source libraries built from persano/open-bamboo-networking (enhanced fork of ClusterM's project with cloud camera and AMS sync fixes).
- **Local credentials stay local.** Your printer access codes, local keys, and authentication tokens remain stored safely on your computer.
- **Decoupled from core.** The plugin manages networking externally through OrcaSlicer's Python plugin architecture, keeping the main slicer codebase free of legal and licensing encumbrance.
- **Safe 1 click restore.** A complete rollback button lets you restore stock libraries or previous configurations at any time.

## Requirements and compatibility

- **Supported printers:** Bambu Lab P1P / P1S, A1 / A1 Mini, and X1 / X1 Carbon.
- **Operating systems:** Windows 10/11 (x64), Linux (x64), and macOS Apple Silicon (arm64).
- **OrcaSlicer versions:** OrcaSlicer v2.3.0+, v2.4.0 official, and v2.5.0 nightly builds.

![Open Bambu Network Installed](https://api.orcaslicer.com/api/v1/bundles/media/5de8526d-5539-4059-8cca-f672f741c6a7/content?expires=1790358429&signature=CNbvTqPZSmyaCLwtHTSnxgIKZs8dvLsEc4OFUu-Hkb0)

## How to get started

1. Install this plugin from OrcaCloud.
2. In OrcaSlicer, open the new **Open Bamboo** tab in the top navigation bar.
3. Click **Install / Update Open Bamboo Library**.
4. Restart OrcaSlicer.
5. Log into your Bambu account in the top-right corner to print and stream video normally.

Source code, issue tracking, and pre-compiled packages are available on GitHub:
Plugin: https://github.com/persano/open-bambu-networking-plugin
Native Core: https://github.com/persano/open-bamboo-networking
