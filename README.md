<div align="center">

<picture>
  <img alt="Open Bamboo logo" src="resources/images/icon.png" width="128" height="128">
</picture>

# Open Bamboo Networking Plugin for OrcaSlicer

[![Release](https://img.shields.io/badge/release-v0.2.9-blue.svg)](https://github.com/persano/open-bambu-networking-plugin/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![OrcaCloud](https://img.shields.io/badge/OrcaCloud-Plugin%20Hub-teal.svg)](https://cloud.orcaslicer.com/app/plugins/shared-plugins/5d35283e-0378-474d-8d3a-6d8f718fddeb)
[![OrcaSlicer](https://img.shields.io/badge/OrcaSlicer-v2.3%2B%20%7C%20v2.4%20%7C%20v2.5%20nightly-orange.svg)](https://github.com/OrcaSlicer/OrcaSlicer)

<p>An open source networking plugin for OrcaSlicer. It enables cloud printing without developer mode, remote camera liveview over the internet, and AMS slot sync on Bambu Lab printers, without any closed source binaries or legal issues for the main OrcaSlicer project.</p>

</div>

---

## Why this exists

OrcaSlicer cannot legally distribute Bambu Lab's closed source networking library (`bambu_networking.dll` / `libbambu_networking.so`) due to licensing and GPL constraints.

Without this library:
- **Cloud printing is blocked**: You have to switch your printer to Developer Mode or LAN Only mode, which disables Bambu Handy push notifications and remote printing.
- **Remote camera feeds do not work**: Camera streams from outside your home network require ThroughTek (TUTK) P2P negotiation, which standard open source builds lack.
- **AMS multi-material slots desync**: Multi-color sliced plates can lose their filament mapping when sent over the cloud.

Rather than trying to bundle closed source binaries into OrcaSlicer or asking people to copy DLLs by hand, this plugin packages the clean room open source code from [open-bamboo-networking](https://github.com/ClusterM/open-bamboo-networking) into OrcaSlicer's Python plugin system. It gives you a dedicated management tab inside OrcaSlicer to set up or restore the library in 1 click.

---

## Features

- **Cloud print without developer mode**: Uses automatic key signing so you can send cloud prints normally.
- **Remote camera liveview**: Streams live camera video when you are away from home via clean room TUTK P2P tunnels.
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

## How it works under the hood

1. **Python plugin (`open_bambu_networking.py`)**:
   Uses `orca.pages` to display an embedded UI panel in OrcaSlicer through the `window.orca` bridge, and `orca.script` for background tasks.
2. **Clean room native library**:
   Bundles the open source `open-bamboo-networking` binaries (`bambu_networking.dll`, `libbambu_networking.so`, `libbambu_networking.dylib`). It implements OrcaSlicer's `BBLNetworkPlugin` C interface, handling signature handshakes, MQTT communications, and P2P video streaming.

---

## Credits

- **[ClusterM](https://github.com/ClusterM)** and contributors to [`open-bamboo-networking`](https://github.com/ClusterM/open-bamboo-networking) for reverse engineering the protocol into clean room open source code.
- **[SoftFever](https://github.com/SoftFever)** and the OrcaSlicer team for building OrcaSlicer and the Python plugin framework.

---

## Disclaimer

This is an independent community project. It is not affiliated with, endorsed by, or associated with Bambu Lab Inc. All product names and brand names belong to their respective owners.
