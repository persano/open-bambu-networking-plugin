# 🐼 Open Bamboo Networking Plugin for OrcaSlicer

[![Release](https://img.shields.io/badge/release-v0.2.8-blue.svg)](https://github.com/persano/open-bambu-networking-plugin/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)]()
[![OrcaSlicer](https://img.shields.io/badge/OrcaSlicer-v2.3%2B%20%7C%20v2.4%20%7C%20v2.5%20nightly-orange.svg)](https://github.com/OrcaSlicer/OrcaSlicer)

Clean-room open-source networking plugin for OrcaSlicer. Enables **Cloud Printing without Developer Mode**, **Remote Camera Liveview** over off-LAN internet, and **Instant AMS Slot Synchronization** for Bambu Lab 3D printers—with zero proprietary binaries or legal burden on OrcaSlicer core.

---

## 💡 Why This Was Created

### The Problem
Upstream OrcaSlicer cannot legally distribute Bambu Lab's proprietary closed-source networking library (`bambu_networking.dll` / `libbambu_networking.so`) due to GPL compliance and commercial licensing restrictions. 

Without this library:
1. **Cloud Printing is blocked**: Users are forced to enable "Developer Mode" or switch their printer to "LAN Only Mode", sacrificing mobile app notifications and cloud connectivity.
2. **Remote Camera Liveview is unavailable**: Off-LAN camera feeds rely on ThroughTek (TUTK) P2P protocol negotiation, which is missing from vanilla open-source builds.
3. **AMS Multi-Filament Telemetry stalls**: Sliced multi-color prints frequently desync filament slots on cloud dispatch.

### The Solution
Instead of forcing proprietary blobs into OrcaSlicer or requiring manual DLL replacements, I created this **native Python plugin**:
- Built on top of OrcaSlicer's new Python plugin framework (`orca.pages` & `orca.script`).
- Provisions the clean-room reverse-engineered open-source networking library ([`open-bamboo-networking`](https://github.com/ClusterM/open-bamboo-networking)).
- Provides an **interactive management tab** directly inside OrcaSlicer with real-time status and 1-click installation.
- Fully decouples networking from OrcaSlicer core, protecting maintainers and the community from legal liability.

---

## ✨ Features & What It Resolves

| Feature | Without Plugin | With Open Bamboo Plugin |
| :--- | :--- | :--- |
| **Cloud Printing** | Requires Developer Mode / LAN Only Mode | **Cloud Print without Developer Mode** (Automated slicer-key signing) |
| **Camera Liveview** | Disabled or LAN-only | **Remote Liveview** via clean-room ThroughTek (TUTK) P2P streaming |
| **AMS Slot Sync** | Telemetry stalls & desync | **Instant pushall telemetry recovery** for multi-material slots |
| **User Experience** | Manual DLL copying or command lines | **Interactive tab in OrcaSlicer** with 1-click Install & Restore |
| **Security Auditing** | Noisy permission prompts | **Zero audit warnings** (clean `sys.platform` implementation) |
| **Legal Status** | Closed-source proprietary binary | **100% Clean-Room Open-Source** (GPL / LGPL) |

---

## 🖥️ User Interface Inside OrcaSlicer

Once installed, OrcaSlicer displays a dedicated **Open Bamboo** tab in the main top navigation bar:

- **📦 Live Status Card**: Real-time detection of active library, file path, size, and system architecture.
- **🔍 Check Current Status**: One-click non-intrusive status refresh.
- **🚀 Install / Update Clean-Room Library**: 1-click provisioning of the clean-room library into `%APPDATA%\OrcaSlicer\plugins\`.
- **🔄 Restore Stock / Uninstall**: Safely roll back to stock or previous backup.
- **📋 Copy Library Path**: Quickly copy path to clipboard without spawning external processes.

---

## 📥 Installation

### Method 1: OrcaCloud Plugin Hub (Recommended)
1. In OrcaSlicer, open **Help** → **Plugins**.
2. Search for **Open Bamboo Networking**.
3. Click **Install**.
4. Restart OrcaSlicer.

> *Note: Submission to OrcaCloud is currently in progress. While awaiting review, use Method 2 below.*

### Method 2: Manual Zip Installation
1. Download [`open_bambu_networking_plugin.zip`](https://github.com/persano/open-bambu-networking-plugin/releases/latest) from the Releases page.
2. Extract the archive into your OrcaSlicer plugins directory:
   - **Windows**: `%APPDATA%\OrcaSlicer\orca_plugins\open_bambu_networking\`
   - **Linux**: `~/.config/OrcaSlicer/orca_plugins/open_bambu_networking/`
3. Launch OrcaSlicer.
4. Click the new **Open Bamboo** tab in the top navigation bar.
5. Click **Install / Update Open Bamboo Library**.
6. Restart OrcaSlicer.

---

## 🖨️ Hardware & Compatibility

### Supported Printers
- Bambu Lab **P1P** / **P1S**
- Bambu Lab **A1** / **A1 Mini**
- Bambu Lab **X1** / **X1 Carbon**

### Operating Systems
- **Windows**: Windows 10 / 11 (x64) - Fully tested & verified
- **Linux**: Ubuntu 22.04+, Fedora, Arch (x64) - Binary bundled
- **macOS**: Apple Silicon & Intel - In progress

### OrcaSlicer Versions
- OrcaSlicer v2.3.0 and newer
- OrcaSlicer v2.4.0 official
- OrcaSlicer v2.5.0 nightly / development builds

---

## 🔧 How It Works Under the Hood

1. **Python Plugin Host (`open_bambu_networking.py`)**:
   - Implements `orca.pages.PagesPluginCapabilityBase` to render a native WebPanel inside OrcaSlicer's notebook.
   - Communicates bidirectionally via the `window.orca` JavaScript bridge.
   - Implements `orca.script.ScriptPluginCapabilityBase` for headless / automated execution.
2. **Clean-Room Native Engine**:
   - The plugin bundles `bambu_networking.dll` / `libbambu_networking.so` compiled from the clean-room `open-bamboo-networking` implementation.
   - It hooks into OrcaSlicer's native C ABI (`BBLNetworkPlugin`).
   - When printing to cloud, it handles RSA/AES signature handshakes, MQTT state machines, and P2P ThroughTek camera tunnels.

---

## 🤝 Acknowledgements & Credits

- **[ClusterM](https://github.com/ClusterM)** and all contributors to [`open-bamboo-networking`](https://github.com/ClusterM/open-bamboo-networking) for the clean-room reverse-engineering work.
- **[SoftFever](https://github.com/SoftFever)** and the **OrcaSlicer team** for building an incredible slicer and the extensible Python plugin system.

---

## ⚖️ Disclaimer

This is an independent community project. It is **not** affiliated with, endorsed by, or associated with Bambu Lab Inc. All product names, logos, and brands are property of their respective owners.
