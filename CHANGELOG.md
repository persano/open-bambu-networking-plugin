# Changelog

All notable changes to Open Bamboo Networking are documented in this file.

## 0.2.22 - 2026-10-01

- Fixed "Failed to connect to printer" reported in #1 and #2: the `obn.conf` template embedded in the native library ships `block_cloud = 1`, and a hand-written `obn.conf` containing only the FAQ's logging lines has no `block_cloud` key at all (the native default is also "block"). Either way cloud MQTT and the cloud message fallback stay disabled - `bambu_network_connect_server: blocked by block_cloud` / `send_message: cloud fallback blocked` in `obn.log` - so any printer the plugin cannot reach over LAN can never connect. The installer now creates `obn.conf` with `block_cloud = 0` when the file is missing, adds the key when it is absent, and flips an explicit `block_cloud = 1` back to `0`, preserving every other user setting (logging, TLS, PEM paths); the install message reports what changed.
- Troubleshooting docs (README FAQ and OrcaCloud description) now lead with the `block_cloud = 0` check, document the `blocked by block_cloud` log signature, and add inbound UDP 2021 / same-subnet guidance for LAN discovery.

## 0.2.21 - 2026-09-29

- Restored client-side signed `liveview.prepare` (revert of upstream `8080cb9`, reported as ClusterM/open-bamboo-networking#112). The cloud-pushed `prepare` that replaced it is rejected with `err_code: 84033543` on secured firmware - reproduced 10/10 on a P1S at `01.10.00.00` with Option B credentials loaded - so `ipcam.tutk_server` never reaches `enable`, `wait_tutk_ready` times out, and the remote liveview dies in TUTK rendezvous. The plugin now publishes a signed `prepare` immediately after the ttcode mint, re-publishes a signed copy when the cloud's dispatch comes back rejected (`rescue_cloud_liveview`), and signs `liveview`/`prepare` frames again (`would_sign` / `signable_root_key`).
- Native libraries rebuilt on all three platforms from open-bamboo-networking `682f13d`, still at ABI `02.08.01.99`.
## 0.2.20 - 2026-09-28

- Fixed remote camera liveview minting. `/v1/iot-service/api/user/ttcode` has been answering HTTP 403 `{"code":8}` since the native library refresh in 0.2.19, because the request carried the PoP header pair. Bisected against production one header group at a time: X-BBL headers only `200`, X-BBL plus `x-bbl-app-certification-id`/`x-bbl-device-security-sign` `403`, PoP alone `403`, neither `200`. The pair is no longer sent, restoring the mint every pre-0.2.19 build performed successfully (72 consecutive `200`s on this machine).
- Native libraries rebuilt on all three platforms from open-bamboo-networking `7c64b28`, still at ABI `02.08.01.99`.
## 0.2.19 - 2026-09-28

- Fixed the "Bambu Network plug-in not detected. Click here to install it." loop reported by @orca_49fddabcc2. The libraries refreshed in 0.2.18 were built for ABI `02.08.02`, a series OrcaSlicer does not whitelist, so the slicer refused to bind them, rewrote `network_plugin_version` to `02.08.02` and renamed the file to `bambu_networking_02.08.02.dll` - after which it could no longer find any library and kept re-offering its own download. All platforms now ship the `02.08.01.99` build OrcaSlicer's `SLIC3R_VERSION 02.08.01.55` expects.
- The installer now always writes `bambu_networking_02.08.01.dll`, the series file `resolve_library_path()` binds. Stock OrcaSlicer never loads the plain `bambu_networking.dll` on a modern config, so installing only that file used to be a no-op.
- Leftover `bambu_networking_02.08.0x.dll` files from a wrong-series build are removed on install instead of lingering and poisoning the configured version, and the success message lists what was cleaned up.
- Install is refused with an actionable message when the bundled library reports a series OrcaSlicer refuses, rather than silently installing a library the slicer cannot detect.
- Status now shows the library's reported version and flags a wrong ABI series, so a bad build is visible before the slicer ever complains.

## 0.2.18 - 2026-09-28

- Fixed the reported install failure `Cannot overwrite locked file bambu_networking.dll: [WinError 2] The system cannot find the file specified`: the installer no longer renames a library that is not there, so a read-only folder such as `C:\Program Files\OrcaSlicer` now reports the real cause (no write permission) with an administrator hint instead of a bogus missing-file error.
- A folder that needs administrator rights no longer aborts the whole install: every writable OrcaSlicer location is still updated and the result message lists the skipped ones.
- Targets that already carry the bundled library are left in place instead of being rewritten, and stale `.old` / `.pending_delete` leftovers are swept from every plugin folder.
- Updated native libraries for Windows (x64), Linux (x64) and macOS (Apple Silicon) to the latest network core: TUTK file transfer, storage browser fix, cloud MQTT TLS verification on Windows, and the upstream #102 / #103 input hardening round.

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
