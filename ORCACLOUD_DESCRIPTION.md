Open Bamboo Networking connects your Bambu Lab printer to OrcaSlicer with full cloud print dispatch, remote camera liveview, and AMS slot sync, without requiring closed source vendor libraries or Developer Mode on the printer.

This plugin is an ease-of-use installer for a modified version of the work from https://github.com/ClusterM/open-bamboo-networking. Most of what makes printers talk is that upstream project. The native library embeds a Bambu Lab application client secret so it can automatically fetch the signing certificates needed for cloud/LAN printing, which means this is not a clean-room implementation. If this plugin saves you time, donations to the upstream author are welcome at https://github.com/sponsors/ClusterM.

![Open Bambu Network not Installed](https://api.orcaslicer.com/api/v1/bundles/media/5882a3ef-d5f4-4a8a-9a5a-cd2c4c913bfb/content)

## What it does

- **Cloud print without developer mode.** Automatically signs and sends print jobs directly over official Bambu Cloud without touching Developer Mode or switching your printer to LAN Only mode.
- **Remote camera liveview.** Streams live camera video when you are away from home via TUTK P2P tunnels, with instant stop and resume reconnects.
- **Instant AMS slot sync.** Restores multi-color AMS slot telemetry and temperatures immediately on connection, keeping sliced filament assignments in sync.
- **In-slicer management tab.** Adds an "Open Bamboo" tab right in OrcaSlicer's top bar with real-time status detection and 1 click installation or rollback.
- **Clean and silent startup.** Fully compliant with OrcaSlicer's security auditor: zero permission popups or socket warnings when launching OrcaSlicer.
- **Cross platform.** Pre-compiled open source native libraries bundled for Windows, Linux, and macOS Apple Silicon.

## Credits and licensing

- The native networking library comes from [ClusterM/open-bamboo-networking](https://github.com/ClusterM/open-bamboo-networking), with patches from [persano/open-bamboo-networking](https://github.com/persano/open-bamboo-networking). It is AGPL-3.0 licensed; the full license text ships inside this plugin package.
- The key extraction tooling the embedded secret comes from was written by [mitchcapper](https://github.com/mitchcapper).

## Open source and privacy first

- **Open source native libraries.** Bundles the AGPL-3.0 libraries built from open-bamboo-networking, incorporating fixes for cloud printing with Developer Mode OFF, remote TUTK P2P camera liveview, and AMS slot sync. Not a clean-room implementation, and not presented as one.
- **Local credentials stay local.** Your printer access codes, local keys, and authentication tokens remain stored safely on your computer.
- **Decoupled from core.** The plugin manages networking externally through OrcaSlicer's Python plugin architecture, keeping the main slicer codebase free of legal and licensing encumbrance.
- **Safe 1 click restore.** A complete rollback button lets you restore stock libraries or previous configurations at any time.

## Requirements and compatibility

- **Supported printers:** Bambu Lab P1P / P1S, A1 / A1 Mini, and X1 / X1 Carbon.
- **Operating systems:** Windows 10/11 (x64), Linux (x64), and macOS Apple Silicon (arm64).
- **OrcaSlicer versions:** OrcaSlicer v2.3.0+, v2.4.0 official, and v2.5.0 nightly builds.

![Open Bambu Network Installed](https://api.orcaslicer.com/api/v1/bundles/media/56b81240-7a2d-4aaf-b45e-853d360da535/content)

## How to get started

1. Install this plugin from OrcaCloud.
2. In OrcaSlicer, open the new **Open Bamboo** tab in the top navigation bar.
3. Click **Install / Update Open Bamboo Library**.
4. Restart OrcaSlicer.
5. Log into your **Bambu Cloud** account (on OrcaSlicer 2.5+, make sure you sign into **Bambu Cloud**, not just Orca Cloud).

## FAQ & Troubleshooting

- **Do I need Bambu Studio installed?** No. This plugin is standalone: it bundles its own open source networking libraries. You do not need Bambu Studio installed, and no files need to be copied. It is not a clean-room implementation: the bundled library embeds a Bambu Lab application client secret so it can fetch the required signing certificates automatically.
- **Do I need slicer_key.pem?** No. Cryptographic envelope signing is fully automated in memory. You do not need to extract, generate, or place any slicer_key.pem file. The printer app certificate is provisioned automatically too - since 0.2.24 the bundled library fetches and refreshes it on its own.
- **OrcaSlicer Developer Mode toggle:** The Developer mode toggle in OrcaSlicer preferences only unhides experimental slicer settings. It has no effect on printer connectivity or firmware security.
- **Failed to connect to printer / server:** First check `block_cloud = 0` in `obn.conf` in your OrcaSlicer configuration folder (`%APPDATA%\OrcaSlicer\obn.conf` on Windows). The default `obn.conf` template ships `block_cloud = 1`, which blocks all cloud MQTT - if the log shows `blocked by block_cloud`, the plugin has no path to the printer and the slicer reports "Failed to connect". The installer writes or updates this key automatically; if you created `obn.conf` by hand, add the line yourself and restart OrcaSlicer. Also ensure you are logged into Bambu Cloud. If your network or ISP restricts TLS on port 8883, you can test adding `lan_tls_skip_verify = 1` to `obn.conf`. For LAN discovery issues, allow inbound UDP port 2021 for OrcaSlicer in your firewall and keep the printer and PC on the same subnet.

## Disclaimer

This is an independent community project, not affiliated with, endorsed by, or associated with Bambu Lab Inc. The bundled networking library embeds credentials that are not yours, and this plugin automates access to Bambu Lab cloud services. You alone are responsible for ensuring your use complies with the applicable terms and law.

Source code, issue tracking, and pre-compiled packages are available on GitHub:

Plugin: https://github.com/persano/open-bambu-networking-plugin

Native Core: https://github.com/persano/open-bamboo-networking

Upstream project: https://github.com/ClusterM/open-bamboo-networking
