# Changelog - Open Bamboo Networking Plugin for OrcaSlicer

All notable changes to the Open Bamboo Networking plugin are documented in this file.

## [0.2.9] - 2026-09-25

### Added
- **Multi-Platform Support**: Added macOS Apple Silicon (`arm64`) pre-compiled clean-room library (`libbambu_networking.dylib`).
- **Hybrid Page + Script Architecture**: Added dedicated "Open Bamboo" tab in OrcaSlicer top bar with interactive GUI dashboard alongside headless script capability.
- **Audit-Clean Execution**: Eliminated `platform` module socket calls to ensure 0 security audit warnings on application launch.
- **OrcaCloud Integration**: Configured OIDC GitHub Actions publishing for OrcaCloud Plugin Hub.

## [0.2.8] - 2026-09-25

### Added
- **Script Capability Transition**: Refactored plugin from persistent top-bar page to native on-demand `script` capability.
- **Custom Icon**: Added modern stylized Open Bamboo panda icon (`icon.png`).
- **One-Click Native Execution**: Clicking **Run** in OrcaSlicer's Plugins dialog automatically detects the operating system, backs up existing binaries, and installs the clean-room library.
- **Interactive Configuration Panel**: Custom configuration tab providing active binary verification, size checking, and 1-click stock restoration.
- **Cross-Platform Binary Bundling**: Includes pre-compiled clean-room binaries for Windows x64 (`bambu_networking.dll`) and Linux x86_64 (`libbambu_networking.so`).

### Verified Hardware Features (Bambu Lab P1S)
- **Cloud Printing Without Developer Mode**: RSA-SHA256 signature envelope and printer public key RSA-PKCS#1 v1.5 encryption (`url_enc`, `param_enc`).
- **Remote Camera Liveview**: Clean-room ThroughTek (TUTK) P2P client with signed `liveview.prepare` authorization (`ttcode_enc`).
- **Instant Reconnect Teardown**: Rapid 5x close packet burst on stream stop, reducing relay reconnect delay from 30–60s to <2s.
- **WAN Relay Keepalive**: Handles relay ping (`0x23 0x05 0x42`) and automatic pong responses for long-running monitoring.
- **Instant AMS Slot Sync**: Proactive `pushall` request upon cloud MQTT connection immediately syncs filament colors and temperatures.
- **Spurious HMS Suppression**: Transparently filters transient `65543` / `84033543` error codes caused by initial unsigned cloud dispatches.
