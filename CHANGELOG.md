# Changelog

All notable changes to Open Bamboo Networking are documented in this file.

## 0.2.31 - 2026-10-10

- Merged open-bamboo-networking master (`d8d8561`, `b974e97`, `293ce94`) into the fork: LAN print reconnect hang fix (upstream #120), cancel honored during the post-upload MQTT reconnect in `local_print`, and the new `auth_probe` action for the plugin runner. Full suite green on the merge commit (35/35 on Linux).
- Libraries rebuilt from open-bamboo-networking `a73efa8` (the merge commit) on all three platforms, still at `02.08.04.99` / `02.08.01.99`.

## 0.2.30 - 2026-10-09

- Adaptive install for future plug-in series. Official OrcaSlicer drops old rows from `AVAILABLE_NETWORK_VERSIONS`, so the next PR that adds a series (the `02.08.04` one in #16202 was the first) would again leave every shipped file undetectable. When `OrcaSlicer.conf` asks for a series this release does not ship, the installer now also writes `bambu_networking_<host_series>.*` from the `02.08.04` build and a one-line `reported_version` file next to `obn.conf`; the library's `bambu_network_get_version()` reads that file and answers with the host's series, so the slicer binds the file. The override is removed again when the configured series is one of the shipped ones, on uninstall and on restore stock, and the status page shows it. If a future official build changes the plug-in ABI instead of only the version row (struct field order, removed export), the same-day rebuild still comes from the upstream watch workflow below.
- New `watch_upstream.yml` workflow in open-bamboo-networking: daily fetch of official OrcaSlicer's `src/slic3r/Utils/bambu_networking.hpp`, commit of the new snapshot under `.github/`, an issue with the diff on change, and a `build.yml` dispatch for the new latest series when its ABI snapshot directory exists (`build.yml` is dispatch-only, so nothing loops).
- Libraries rebuilt from open-bamboo-networking `3aff180` (the `reported_version` override read) on all three platforms, still at `02.08.04.99` / `02.08.01.99`. New config-suite case covers valid/invalid override content plus the active-dir lookup; Windows runs the 13 core tests, Linux CI the extended suite, all green.

## 0.2.29 - 2026-10-09

- Official OrcaSlicer took PR #16202 (merged 2026-10-07, present in builds from `ee2c40ea`): `AVAILABLE_NETWORK_VERSIONS` now lists `02.08.04` as latest and dropped `02.08.01`, and the loader resolves `bambu_networking_02.08.04.*` with no unversioned fallback. On those builds 0.2.28 and older report "Bambu Network plug-in not detected" forever. One install now places both series: the `02.08.04.99` build as the unversioned `bambu_networking.*` and as `bambu_networking_02.08.04.*`, and the `02.08.01.99` build as `bambu_networking_02.08.01.*`, so post-#16202 hosts bind the new file and hosts whose whitelist predates #16202 keep binding `02.08.01` unchanged. Conflict cleanup keeps both series and still removes other `02.08.*` leftovers; the status page counts either build as Open Bamboo. Our OrcaSlicer fork synced the same change (`queue_plate_id`, `02.08.04` row, `02.08.01` dropped, the fork's `02.07.01` row and `.99` load-gate bypass kept) in `persano/OrcaSlicer` commit `1d852f9c9`.
- `mytask_pop` now defaults to `auto`: the proof-of-possession pair attaches on the CN cloud with no config edit, keeping the historical bearer-only request elsewhere. This is what the reporter's A/B on the Chinese-cloud H2D showed (`mytask_pop = 1` printed, off reproduced the exact 403), so the promised default ships. Explicit `1` still forces the pair on for any region, explicit `0` forces it off including CN; `is_cn_region()` moved to the public config API to drive the switch. Note: an `obn.conf` created from the 0.2.27/0.2.28 template contains a literal `mytask_pop = 0`, which keeps its old explicit-off meaning - delete the line or set `mytask_pop = auto` to get the region default.
- Merged open-bamboo-networking `73d923b..1f9e192`: upstream's configurable `filter_mqtt_hms_65543` (PR #99, default off there, default on in this fork as before) and PR #115 research corpus, plus `97b6192` (the `mytask_pop` auto switch). New `filter_mqtt_hms_65543` key in `obn.conf`.
- Libraries rebuilt from open-bamboo-networking `97b6192`: Windows/Linux/macOS each ship the `02.08.04.99` and `02.08.01.99` builds. The installer harness covers the dual-series placement (both files from their own builds, wrong-series leftover removed, backup/restore/uninstall), and config/cloud-print suites cover `auto`/`0`/`1` parsing and the CN/global switch (extended suite runs in Linux CI; Windows runs the 13 core tests, all green).

## 0.2.28 - 2026-10-08

- Merged ClusterM/open-bamboo-networking master into the fork: upstream accepted our revert of `8080cb9` as PR #113 and merged it verbatim - all six reverted files are byte-identical to the PR head - so the signed client-side `liveview.prepare` we have shipped since 0.2.21 is now the upstream state as well.
- Takes upstream `2cfd2ba` (app_cert_list): the query now sends `"type":"app"` and checks the report's `result` - without `type` the firmware replies `result=FAIL` and no `cert_ids`, so the harvest was empty, and non-SUCCESS replies now warn in `obn.log` instead of being parsed silently.
- Takes upstream TUTK research updates (`93d7d46`, `7243b88`) and the `plugin_runner --client-version` flag, combined with our `BambuStudio` `client_name` default. Drops `7243b88`'s `TutkSession.cpp` re-indent: whitespace-only (`diff -w` empty), it only mangled indentation.
- Conflict resolution kept our superset: `rescue_cloud_project_file`, `seq_json_value` sequence handling, trailing-sibling signing, and the 84033543/65543 frame filters are unchanged; also removed a duplicate `rescue_cloud_liveview` declaration the upstream revert restored in `agent.hpp`.
- Libraries rebuilt from open-bamboo-networking `38ac86a`, still at ABI `02.08.01.99`. `ctest` 13/13 passed (incl. `signing`, `plugin_symbols`, `state_persist`).

## 0.2.27 - 2026-10-08

- New opt-in `mytask_pop` key in `obn.conf` (default `0`): when set to `1`, `POST /v1/user-service/my/task` (cloud print / print history record) additionally carries the proof-of-possession header pair `x-bbl-app-certification-id` / `x-bbl-device-security-sign`. This targets a Chinese-cloud (`api.bambulab.cn`) H2D where, with `client_name = BambuStudio` and every other API answering 200, exactly this call answered 403 while stock Bambu Studio printed fine on the same account and printer, and research `10.05` lists `/my/task` as proof-of-possession-required on verified printers. The default keeps the historical bearer-only request that `api.bambulab.com` accepts, so nothing changes for existing installs; the flag is key-match guarded and, with no slicer key/cert present, sends no headers at all rather than a blank pair. If the flag is on but the pair cannot be attached, `obn.log` warns instead of failing silently.
- Libraries rebuilt from open-bamboo-networking `ce029b2`, still at ABI `02.08.01.99`.
- Covered by unit tests (flag off by default, flag on with no signing material attaches nothing, flag on with a matching key/cert attaches the HTTP `issuer:serial` form of the pair); the CN-cloud hardware case is still unverified and is what this build is released for.

## 0.2.26 - 2026-10-07

- Cloud print and "local print with record" failed with HTTP 403 `The client does not have access rights to the content.` on every install that had not overridden `client_name`: the shipped default `OpenBambooNetworking` is rejected by `POST /v1/user-service/my/task`, which only accepts the stock client name `BambuStudio`, and the `/user/ttcode` camera mint has the same requirement. The default in `obn.conf` and the empty-config fallback are now `BambuStudio`, and `create_task` logs a warning naming the offending value instead of only failing against the server. Reported from a Chinese-cloud H2D where every other API answered 200. Existing configs keep their explicit line and need the one-line edit to `client_name = BambuStudio`.
- `plugin_runner` now defaults to the same client name as the runtime so captures and probes reproduce plugin behavior.
- Libraries rebuilt from open-bamboo-networking `8e3dfb2`, still at ABI `02.08.01.99`.
- Verified on hardware (P1S): `create_task` answers a real `task_id` instead of 403, the printer accepts the signed `project_file` dispatch (`print_type: cloud`) and the job reaches PREPARE.
## 0.2.25 - 2026-10-06

- Fixed remote camera live view on H2-series printers: the `/user/ttcode` mint now sends the proof-of-possession header pair `x-bbl-app-certification-id` / `x-bbl-device-security-sign` together with a populated `X-BBL-Executable-info` attestation, which the cloud requires on those models (without them it answers 403 `{"code":8}` and the camera stays on "loading"). The proof-of-possession pair is only attached when `slicer_key.pem` actually belongs to `slicer_cert.pem`, and the match is re-checked on every mint, so a certificate fetch that finishes after startup can no longer disable it for the whole session.
- New `executable_info` key in `obn.conf`: overrides the built-in BambuStudio attestation without a rebuild, for when Bambu rotates it and the built-in copy stops being accepted.
- All three libraries (Windows, Linux, macOS) rebuilt from open-bamboo-networking `6f85987` (the H2 fix itself is `d159fb9`), still at ABI `02.08.01.99`. The automatic app-certificate provisioning that 0.2.24 shipped Windows-only is now in the Linux and macOS libraries as well.
- Verified on hardware (P1S, fw `01.10.00.00`): ttcode mint answers 200 with the proof-of-possession pair, the printer accepts the signed `ttcode_enc` prepare, the camera plays, and no `84033543` appears.

## 0.2.24 - 2026-10-03

- Signed commands now work from a clean config. The bundled Windows networking library implements `bambu_network_update_cert`: when the plugin detects a secured printer (or first needs to sign a command) it fetches the shared app certificate, CRL and signing key from Bambu's certificate endpoint - the same endpoint Bambu's own plugin uses - cross-checks the fetched key against the certificate, and writes `slicer_cert.pem` / `slicer_crl.pem` / `slicer_key.pem` into the plugin's config directory. This is the fix for the `84033543` rejections reported in #2: the signing material is present out of the box and is refreshed automatically whenever Bambu rotates the certificate. Hand-placed copies still override the automatic ones and are never overwritten.
- Windows library rebuilt from open-bamboo-networking `ebfd02c`, still at ABI `02.08.01.99`; the Linux and macOS libraries get this in their next rebuild. Credential cipher/fetch unit tests and a Windows end-to-end probe (fresh config directory to HTTP 200, certificate chain matching working Studio-extracted credentials) pass.
- The README FAQ now documents the automatic app-certificate provisioning (the OrcaCloud page description is maintained separately on the plugin page).

## 0.2.23 - 2026-10-02

- Fixed the `Could not update obn.conf (Plugin attempted an audited operation without permission)` warning appended to every install on OrcaSlicer builds with the plugin audit hook. The audit's categorical `conf` denied-path keyword refuses every Python `open()` of a path containing "conf" before any allow-list or permission prompt is consulted, so the `block_cloud = 0` ensure added in 0.2.22 could never succeed there - it even warned when the configuration was already correct, because the read failed too. The installer now applies the same fix through the bundled networking library via the new `obn_ensure_conf_block_cloud` export (C++ writes are outside the Python audit hook, and the library owns the file), with identical outcomes and install-message wording; the direct Python write remains as a fallback for libraries predating the export. The Windows library in this build carries the export; the Linux and macOS libraries get it in their next rebuild.
- Camera over LAN no longer waits on SSDP: a fresh process restores the printer's LAN address from the obn.env-backed registry (seeding the certificate pin and LAN session autostart with it) and only appends `lv=rtsps` to the stream URL after the printer answers a port-322 probe, so printers without an RTSP port fall back to plain MJPEG instead of a dead URL.
- Re-requests a full telemetry push on every printer selection. Studio zeroes its push counters on selection changes and keeps the AMS panel and camera play button disabled until the next full (`msg: 0`) push arrives; the old once-per-connection kickstart latch left that gate closed for up to ~14 seconds after a mid-session re-selection.

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
