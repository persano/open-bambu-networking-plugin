# Changelog

All notable changes to Open Bamboo Networking are documented in this file.

## 0.2.10 - 2026-09-25

- Fixed an empty wheel RECORD file that prevented OrcaSlicer from installing and activating the plugin.
- Added top_level.txt to wheel dist-info for clean package import resolution.

## 0.2.9 - 2026-09-25

- Added pre-compiled macOS Apple Silicon (arm64) clean room library (libbambu_networking.dylib).
- Added dedicated "Open Bamboo" tab in OrcaSlicer top bar with interactive dashboard and 1 click installer.
- Removed socket calls on startup to ensure zero security audit warnings on application launch.
- Added automated publishing to OrcaCloud Plugin Hub via GitHub Actions OIDC.

## 0.2.8 - 2026-09-25

- Initial release bundling clean room networking libraries for Windows (x64) and Linux (x64).
- Enabled cloud printing without developer mode using automatic slicer key signing.
- Enabled remote camera liveview over the internet via clean room ThroughTek (TUTK) P2P streaming.
- Added instant stream teardown burst on camera stop, cutting reconnect delay to under 2 seconds.
- Added proactive pushall telemetry request on cloud connect to sync AMS slot assignments immediately.
- Filtered transient error codes caused by initial unsigned cloud requests.
