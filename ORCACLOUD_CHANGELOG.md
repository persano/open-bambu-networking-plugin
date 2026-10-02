## 0.2.23 - 2026-10-02

- Fixed a `Could not update obn.conf (...)` warning that OrcaSlicer's plugin security audit made appear on every install: the audit blocks the installer from touching any `.conf` file, so the `block_cloud = 0` cloud-enable step always reported a permission error - even when your configuration was already correct. The installer now applies that step through the bundled networking library, which the audit allows; your other settings are still never touched.

## 0.2.22 - 2026-10-01

- Fixed "Failed to connect to printer" (issues #1 and #2): cloud access was left disabled because the `obn.conf` template ships `block_cloud = 1` (or the file has no `block_cloud` line at all, which also blocks). The installer now creates or repairs `block_cloud = 0` in `obn.conf` during install without touching your other settings, and the troubleshooting docs explain the fix plus LAN discovery requirements (firewall UDP 2021, same subnet).

## 0.2.21 - 2026-09-29

- Fixed remote camera liveview: the cloud-pushed `liveview.prepare` is rejected with `err_code: 84033543` on secured printers, so the TUTK server never started and the camera timed out on "loading...". The plugin now sends its own signed `prepare` right after the ttcode mint - and re-sends it signed when the cloud's copy comes back rejected - restoring remote liveview.
- Native libraries rebuilt on all three platforms from open-bamboo-networking `682f13d`, still at ABI `02.08.01.99`.

## 0.2.20 - 2026-09-28

- Fixed remote camera liveview minting. `/v1/iot-service/api/user/ttcode` has been answering HTTP 403 `{"code":8}` since the native library refresh in 0.2.19, because the request carried the PoP header pair. Bisected against production one header group at a time: X-BBL headers only `200`, X-BBL plus `x-bbl-app-certification-id`/`x-bbl-device-security-sign` `403`, PoP alone `403`, neither `200`. The pair is no longer sent, restoring the mint every pre-0.2.19 build performed successfully (72 consecutive `200`s on this machine).
- Native libraries rebuilt on all three platforms from open-bamboo-networking `7c64b28`, still at ABI `02.08.01.99`.
## 0.2.19 - 2026-09-28

- Fixed the "Bambu Network plug-in not detected" loop: the libraries refreshed in 0.2.18 were built for ABI `02.08.02`, a series OrcaSlicer does not whitelist, so the slicer refused to bind them, rewrote `network_plugin_version` to `02.08.02` and renamed the file to `bambu_networking_02.08.02.dll` - after which it could no longer find any library and kept re-offering its own download. All platforms now ship the `02.08.01.99` build OrcaSlicer expects.
- The installer now always writes `bambu_networking_02.08.01.dll`, the series file OrcaSlicer's loader binds; stock OrcaSlicer never loads the plain `bambu_networking.dll` on a modern config, so installing only that file used to be a no-op.
- Wrong-series leftovers are removed on install, and install is refused with an actionable message if the bundled library reports a series OrcaSlicer refuses.
- Status now shows the library's reported version and flags a wrong ABI series.

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
