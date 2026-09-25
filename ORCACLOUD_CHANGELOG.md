## 0.2.17 - 2026-09-25

- Merged upstream fixes for public key caching with atomic certificate persistence.
- Resolved cloud printer connection notification race condition when slicer registers callbacks late.
- Added proactive pushall kickstart on broker connect and subscription for instant AMS slot, temperatures, and job sync.

## 0.2.16 - 2026-09-25

- Zero startup audit prompts: Slicer startup never touches external filesystem paths during UI generation.
- On-demand permission model: Security audit hooks only trigger when user explicitly clicks Check Status, Install, Restore, or Uninstall.
- Removed background file deletions from read-only status checks.
- Streamlined portable directory discovery using exact executable path without scanning unrelated directories.
- Avoided un-persistable file deletion audit hooks by utilizing atomic rename operations for locked libraries.

## 0.2.15 - 2026-09-25

- Added multi-directory detection and synchronization to support portable and standalone OrcaSlicer installations.
- Automatically synchronizes libraries across the executable root, resources/plugins folder, and user AppData folder.
- Synchronized stock restorations and uninstalls across all active slicer locations simultaneously.

## 0.2.14 - 2026-09-25

- Embedded inline IPC bridge in webview HTML to ensure UI buttons always connect to slicer backend.
- Added automatic retry logic for webview message delivery on cold startup.
- Fixed button clicks falling back to static status view when host bridge is initializing.

## 0.2.13 - 2026-09-25

- Fixed WinError 32 (file in use by another process) when installing, restoring stock, or uninstalling while OrcaSlicer is running.
- Added atomic rename-aside mechanism so locked native libraries can be replaced or removed without closing OrcaSlicer first.
- Added cleanup for temporary pending files on startup.

## 0.2.12 - 2026-09-25

- Renamed all UI text, status badges, and action buttons to "Open Bamboo" instead of "Clean Room".
- Added SHA256 cryptographic verification for 100% accurate identification of Open Bamboo vs stock binaries.
- Synchronized versioned native libraries (such as `bambu_networking_02.08.01.dll`) on install, restore stock, and uninstall so OrcaSlicer never loads mismatched binaries.

## 0.2.11 - 2026-09-25

- Fixed library status detection so stock vendor binaries are not falsely identified as clean room libraries.
- Added separate "Restore Stock Backup" action alongside "Uninstall / Remove Library".
- Fixed uninstall logic so active library is removed cleanly rather than restoring backup.

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
