<div align="center">

<picture>
  <img alt="Open Bamboo logo" src="resources/images/icon.png" width="128" height="128">
</picture>

# Open Bamboo Networking Plugin for OrcaSlicer

[![Release](https://img.shields.io/badge/release-v0.2.38-blue.svg)](https://github.com/persano/open-bambu-networking-plugin/releases)
[![License: GPL v3 (installer) / AGPL v3 (native libs)](https://img.shields.io/badge/License-GPLv3%20%2F%20AGPLv3-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![OrcaCloud](https://img.shields.io/badge/OrcaCloud-Plugin%20Hub-teal.svg)](https://cloud.orcaslicer.com/app/plugins/shared-plugins/5d35283e-0378-474d-8d3a-6d8f718fddeb)
[![OrcaSlicer](https://img.shields.io/badge/OrcaSlicer-v2.3%2B%20%7C%20v2.4%20%7C%20v2.5%20nightly-orange.svg)](https://github.com/OrcaSlicer/OrcaSlicer)

<p>An open source networking plugin for OrcaSlicer. It enables cloud printing without developer mode, remote camera liveview over the internet, and AMS slot sync on Bambu Lab printers, without any closed source binaries for the main OrcaSlicer project to redistribute.</p>

</div>

---

## Attribution

This plugin is an ease-of-use installer for a modified version of the masterful work from [ClusterM/open-bamboo-networking](https://github.com/ClusterM/open-bamboo-networking). Most of what makes printers talk is that project, not this repository. The native library embeds a Bambu Lab application client secret so it can automatically fetch the signing certificates required for cloud/LAN mode, which is why the shipped binaries are not a clean-room implementation. Donations to the upstream author are welcome at [GitHub Sponsors](https://github.com/sponsors/ClusterM) or via the [upstream support section](https://github.com/ClusterM/open-bamboo-networking#support-the-developer-and-the-project).

Licensing: this repository's installer code is GPL-3.0 ([LICENSE](LICENSE)). The bundled native binaries are AGPL-3.0 works from the projects above; the full AGPL text ships in this repository and inside every package as [LICENSE.AGPL](LICENSE.AGPL), and [NOTICE](NOTICE) records the exact source revision each binary is built from.

## Why this exists

OrcaSlicer cannot legally distribute Bambu Lab's closed source networking library (`bambu_networking.dll` / `libbambu_networking.so`) due to licensing and GPL constraints.

Without this library:
- **Cloud printing is blocked**: You have to switch your printer to Developer Mode or LAN Only mode, which disables Bambu Handy push notifications and remote printing.
- **Remote camera feeds do not work**: Camera streams from outside your home network require ThroughTek (TUTK) P2P negotiation, which standard open source builds lack.
- **AMS multi-material slots desync**: Multi-color sliced plates can lose their filament mapping when sent over the cloud.

Rather than trying to bundle closed source binaries into OrcaSlicer or asking people to copy DLLs by hand, this plugin packages the open source native binaries built from [persano/open-bamboo-networking](https://github.com/persano/open-bamboo-networking), a fork of [ClusterM/open-bamboo-networking](https://github.com/ClusterM/open-bamboo-networking), into OrcaSlicer's Python plugin system. It incorporates critical patches for cloud liveview remote camera streaming over TUTK P2P, AMS pushall slot sync, and certificate fallback. It gives you a dedicated management tab inside OrcaSlicer to set up or restore the library in 1 click.

---

## Core Native Library & Fixes

While [ClusterM/open-bamboo-networking](https://github.com/ClusterM/open-bamboo-networking) created the initial open source implementation, it lacked support for recent secure Bambu firmware with Developer Mode OFF, off-LAN camera streaming, and multi-color AMS slot synchronization.

The native fixes that enable this plugin to function were developed by **persano (me)** in [`persano/open-bamboo-networking`](https://github.com/persano/open-bamboo-networking):

- **Cloud Printing Without Developer Mode**: Slicer RSA envelope signing and printer RSA PKCS#1 v1.5 field encryption (`url_enc`, `param_enc`), preventing printer rejection error `84033543` (`HMS 0500-0500-0001-0007`) on cloud dispatch.
- **Off-LAN Remote Camera Liveview**: Signed `liveview.prepare` negotiation, `ttcode_enc` encryption, and ThroughTek (TUTK) P2P tunnel handshake for streaming camera feeds outside the local network.
- **Instant AMS Slot Synchronization**: MQTT `pushall` telemetry trigger on subscribe to restore filament mapping and temperatures immediately on connect.
- **Certificate Cache & Disk Fallback**: Resilient printer public key acquisition with negative caching and TTL.

The pre-compiled binaries distributed inside this plugin (`bambu_networking.dll`, `libbambu_networking.so`, `libbambu_networking.dylib`) are built directly from these enhancements.

---

## Features

- **Cloud print without developer mode**: Uses automatic key signing so you can send cloud prints normally.
- **Remote camera liveview**: Streams live camera video when you are away from home via TUTK P2P tunnels.
- **AMS slot sync**: Keeps multi-color filament slots mapped properly on cloud dispatch.
- **In-slicer interface**: Adds an "Open Bamboo" tab right in OrcaSlicer with live library status and 1 click install or rollback.
- **Clean startup**: No security prompts or permission alerts when opening OrcaSlicer.
- **Cross platform**: Pre-compiled libraries included for Windows (x64), Linux (x64), and macOS (Apple Silicon arm64).

---

## Installation

### Method 1: OrcaCloud Plugin Hub (Recommended)
1. Subscribe on the [OrcaCloud Plugin Page](https://cloud.orcaslicer.com/app/plugins/shared-plugins/5d35283e-0378-474d-8d3a-6d8f718fddeb).
2. In OrcaSlicer, open **Help** -> **Plugins** (or **File** -> **Plugins**) and click **Refresh**.
3. Enable **Open Bamboo Networking**.
4. Restart OrcaSlicer.

### Method 2: Manual zip install
1. Download `open_bambu_networking_plugin.zip` from the [Releases](https://github.com/persano/open-bambu-networking-plugin/releases/latest) page.
2. Unpack the zip into your OrcaSlicer plugins folder:
   - **Windows**: `%APPDATA%\OrcaSlicer\orca_plugins\open_bambu_networking\`
   - **Linux**: `~/.config/OrcaSlicer/orca_plugins/open_bambu_networking/`
   - **macOS**: `~/Library/Application Support/OrcaSlicer/orca_plugins/open_bambu_networking/`
3. Launch OrcaSlicer.
4. Click the new **Open Bamboo** tab in the top navigation bar.
5. Click **Install / Update Open Bamboo Library**.
6. Restart OrcaSlicer.
7. Log into your **Bambu Cloud** account (on OrcaSlicer 2.5+, be sure you log into **Bambu Cloud**, not only Orca Cloud).

---

## Compatibility

### Supported Printers
- Bambu Lab P1P / P1S
- Bambu Lab A1 / A1 Mini
- Bambu Lab X1 / X1 Carbon

### Operating Systems
- Windows 10 and 11 (x64) - Tested and verified
- Linux (x64) - Library included
- macOS Apple Silicon (arm64) - Library included

### OrcaSlicer Versions
- OrcaSlicer 2.3.0 and newer
- OrcaSlicer 2.4.0 official
- OrcaSlicer 2.5.0 nightly builds

---

## FAQ & Troubleshooting

- **Do I need Bambu Studio installed?** No. This plugin is standalone: it bundles its own open source networking libraries (`bambu_networking.dll` / `libbambu_networking.so`). You do not need Bambu Studio installed, and no files need to be copied. It is not a clean-room implementation: the bundled library embeds a Bambu Lab application client secret (recovered from a running Bambu Studio process) so it can fetch the required signing certificates automatically.
- **Do I need `slicer_key.pem`?** No. Cryptographic envelope signing and field encryption are fully automated in memory. You do not need to extract, generate, or place any `slicer_key.pem` file. The printer app certificate is provisioned the same way: since 0.2.24 the bundled library fetches `slicer_cert.pem` / `slicer_crl.pem` / `slicer_key.pem` itself when a secured printer is detected, refreshes them whenever Bambu rotates the certificate, and leaves hand-placed copies untouched.
- **OrcaSlicer Developer Mode toggle:** The Developer mode toggle in OrcaSlicer preferences only unhides experimental slicing settings. It has no effect on printer connectivity or firmware security.
- **Failed to connect to the printer / server:** First check `block_cloud = 0` in `obn.conf` (located at `%APPDATA%\OrcaSlicer\obn.conf` on Windows or `~/.config/OrcaSlicer/obn.conf` on Linux). The default `obn.conf` template ships `block_cloud = 1`, which blocks **all** cloud MQTT — if `obn.log` shows `bambu_network_connect_server: blocked by block_cloud` or `send_message: cloud fallback blocked`, the plugin has no path to the printer at all and the slicer reports "Failed to connect". The installer writes or updates this key automatically; if you created `obn.conf` by hand, add the line yourself and restart OrcaSlicer. Also ensure you are logged into Bambu Cloud. If the printer is on your LAN but never appears in `obn.log` as `ssdp: printer seen`, allow inbound UDP port 2021 for OrcaSlicer in your firewall and make sure the printer and PC share the same subnet (no guest/AP isolation or separate VLANs). If an ISP, firewall, or antivirus inspects or blocks TLS on port 8883, you can test bypassing TLS validation by setting `lan_tls_skip_verify = 1` in `obn.conf`. To generate diagnostic logs, add `log_level = debug` to `obn.conf` and inspect `obn.log` (the installer already enables `log_to_file = 1`, and the plugin's status page shows the exact `obn.log` path).
- **Remote camera or cloud print fails with HTTP 403 on macOS or Linux:** Since 0.2.33 the plugin reports the platform of the signing certificate it holds, which is what Bambu's cloud compares, so this fixes itself on update. The signing certificate the bundled library fetches automatically is the Windows one on every operating system. If you placed your own `slicer_cert.pem` by hand and it is a Linux certificate, and the cloud still rejects the calls, set `cloud_os_type = linux` in `obn.conf`, restart OrcaSlicer and upload the print again. Windows hosts need no change, and LAN connections ignore this key.

---


## How it works under the hood

1. **Python plugin (`open_bambu_networking.py`)**:
   Uses `orca.pages` to display an embedded UI panel in OrcaSlicer through the `window.orca` bridge, and `orca.script` for background tasks.
2. **Native library**:
   Bundles the pre-compiled `open-bamboo-networking` binaries built from the [persano/open-bamboo-networking](https://github.com/persano/open-bamboo-networking) fork (`bambu_networking.dll`, `libbambu_networking.so`, `libbambu_networking.dylib`). It implements OrcaSlicer's `BBLNetworkPlugin` C interface, incorporating custom fixes for ThroughTek TUTK P2P camera liveview, MQTT pushall on subscribe for AMS multi-color slot sync, and certificate store fallbacks.

---

## Credits and Architecture

- **[ClusterM](https://github.com/ClusterM)** and contributors to [`open-bamboo-networking`](https://github.com/ClusterM/open-bamboo-networking) for creating the open source implementation this plugin is built on, including the `tools/extract_key_from_dump.py` extraction tooling. If this plugin saves you time, that is their work first: consider [sponsoring them](https://github.com/sponsors/ClusterM).
- **[persano](https://github.com/persano) (me)** for developing the cloud liveview ThroughTek TUTK P2P camera streaming patches, AMS pushall sync fixes, certificate fallbacks, and the OrcaSlicer Python plugin integration in [`persano/open-bamboo-networking`](https://github.com/persano/open-bamboo-networking).
- **[SoftFever](https://github.com/SoftFever)** and the OrcaSlicer team for building OrcaSlicer and the Python plugin framework.

---

## Disclaimer

This is an independent community project. It is not affiliated with, endorsed by, or associated with Bambu Lab Inc. All product names and brand names belong to their respective owners.

The bundled networking library embeds credentials that are not yours, and this plugin automates access to Bambu Lab cloud services. You alone are responsible for ensuring your use complies with the applicable terms and law.
