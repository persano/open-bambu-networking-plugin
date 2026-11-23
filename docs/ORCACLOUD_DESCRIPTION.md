Open Bamboo Networking connects your Bambu Lab printer to OrcaSlicer with full cloud print dispatch, remote camera liveview, and AMS slot sync, without requiring closed source vendor libraries or Developer Mode on the printer.

This plugin is an ease-of-use installer for a modified version of the work from https://github.com/ClusterM/open-bamboo-networking. Most of what makes printers talk is that upstream project. The native library embeds a Bambu Lab application client secret so it can automatically fetch the signing certificates needed for cloud and LAN printing, which means this is not a clean-room implementation. If this plugin saves you time, donations to the upstream author are welcome at https://github.com/sponsors/ClusterM.

![Tick the plugin checkbox: menu -> Plugins -> Open Bamboo Networking Plugin](https://api.orcaslicer.com/api/v1/bundles/media/5882a3ef-d5f4-4a8a-9a5a-cd2c4c913bfb/content)

## Enable it: this is where most "it does not work" reports start

Installing from OrcaCloud alone does not switch the plugin on. After installing:

1. Open **Plugins** from the OrcaSlicer menu (the list icon at the top left, see image above) and **tick the checkbox** next to **Open Bamboo Networking Plugin**. If the box stays unticked the library never loads and nothing will connect.
2. In OrcaSlicer, open the new **Open Bamboo** tab in the top navigation bar, click **Install / Update Open Bamboo Library**, and restart OrcaSlicer.
3. On OrcaSlicer 2.5+, open **Edit -> Preferences -> Online** and tick **Enable Bambu Cloud** under **Cloud Providers**. This is a separate checkbox from **Enable Bambu network plug-in** at the bottom of the same page, and until it is ticked the homepage shows no Bambu Cloud login section.
4. Log into your **Bambu Cloud** account on the homepage (not just Orca Cloud).

![Enable Bambu Cloud under Preferences -> Online -> Cloud Providers](https://raw.githubusercontent.com/persano/open-bambu-networking-plugin/main/docs/enable_bambu_cloud.png)

## What it does

- **Cloud print without developer mode.** Jobs are signed and sent directly over official Bambu Cloud, with no Developer Mode and no switch to LAN Only mode.
- **Remote camera liveview.** Live video when you are away from home through TUTK P2P tunnels, with instant stop and resume reconnects.
- **Instant AMS slot sync.** Multi-color AMS slot telemetry and temperatures are restored immediately on connection, keeping sliced filament assignments in sync.
- **In-slicer management tab.** An "Open Bamboo" tab in OrcaSlicer's top bar with real-time status detection and one click installation or rollback.
- **Clean and silent startup.** Compliant with OrcaSlicer's security auditor: no permission popups or socket warnings at launch.
- **Cross platform.** Pre-compiled open source native libraries bundled for Windows (x64 and arm64), Linux (x64 and arm64), and macOS (Apple Silicon and Intel).

## Credits and licensing

The native networking library comes from [ClusterM/open-bamboo-networking](https://github.com/ClusterM/open-bamboo-networking), with patches from [persano/open-bamboo-networking](https://github.com/persano/open-bamboo-networking). It is AGPL-3.0 licensed; the full license text ships inside this plugin package.

## Open source and privacy first

- **Open source native libraries.** Built from open-bamboo-networking with fixes for cloud printing with Developer Mode OFF, remote TUTK P2P camera liveview, and AMS slot sync. Not a clean-room implementation.
- **Local credentials stay local.** Printer access codes, local keys, and authentication tokens stay on your computer.
- **Safe one click restore.** A rollback button restores stock libraries or previous configurations at any time.

## Requirements and compatibility

- **Supported printers:** Bambu Lab P1P / P1S, P2S, A1 / A1 Mini, X1 / X1 Carbon, H2D (all verified from user reports) and X2D (connects and prints, occasional liveview drops under investigation). The H2S runs the same fixes but I have no report from a real unit. X1E is untested rather than known broken, if you run the plugin on one please open an issue with your results.
- **Operating systems:** Windows 10/11 (x64 and arm64), Linux (x64 and arm64), and macOS (Apple Silicon / Intel).
- **OrcaSlicer versions:** v2.3.0+ (manual install only) and v2.5.0+ nightly builds (when plugin support was added).
- **Before reporting "error code 7":** turn **OFF** "Use 3rd Party Print Host" in the printer settings. While it is on, OrcaSlicer sends the job to that host instead of through this plugin (camera and controls still work) and the send fails. If OrcaSlicer asks for a plug-in version like `v02.08.04.99` or reports the plug-in missing, click **Install / Update Open Bamboo Library** once more and restart.

![Open Bamboo Networking installed](https://api.orcaslicer.com/api/v1/bundles/media/56b81240-7a2d-4aaf-b45e-853d360da535/content)

## FAQ and troubleshooting

- **No Bambu Cloud login section on the homepage:** see step 3 under "Enable it" above. It is not the **Enable Bambu network plug-in** checkbox at the bottom of the Online preferences page, and on fresh OrcaSlicer 2.5+ installs the section stays hidden until the box is ticked.
- **Do I need Bambu Studio or a slicer_key.pem?** No to both. The plugin is standalone and bundles its own open source networking libraries, no files need to be copied. Envelope signing is automated in memory, no pem file to extract or place, and since 0.2.24 the library fetches and refreshes the printer app certificate on its own.
- **"MQTT Command verification failed" (HMS 0500-0500-0001-0007):** the printer rejected a signed command. Update this plugin from OrcaCloud, run Install / Update once, restart, and send a test print, since 0.2.24 the signing certificate is fetched and refreshed automatically so a stale certificate is the usual cause. If it appeared right after a firmware update, Bambu's wiki suggests Bambu Studio 01.10.02.64 or later, for this plugin just update to the latest version instead. If it persists, attach `open-bambu-networking.log` from the Open Bamboo tab.
- **Failed to connect to printer / server:** check `block_cloud = 0` in `obn.conf` in your OrcaSlicer configuration folder (`%APPDATA%\OrcaSlicer\obn.conf` on Windows). The default template ships `block_cloud = 1`, which blocks all cloud MQTT and makes the slicer report "Failed to connect"; the installer writes or updates this key automatically, add it by hand if you created the file yourself, then restart. Also make sure you are logged into Bambu Cloud. If your ISP restricts TLS on port 8883, try `lan_tls_skip_verify = 1`. For LAN discovery, allow inbound UDP port 2021 for OrcaSlicer and keep printer and PC on the same subnet.
- **The Developer mode toggle** in OrcaSlicer preferences only unhides experimental slicer settings. It has no effect on printer connectivity or firmware security.

## Reporting problems

Hub comments are a poor place for files. Please open an issue instead: https://github.com/persano/open-bambu-networking-plugin/issues

Include: **plugin version** (Open Bamboo tab), **OrcaSlicer version** (Help -> About, full string with build hash), **operating system**, **printer and firmware** (printer screen, Settings -> General -> Version), **exact error** (full dialog text, `err_code` or HMS code verbatim), and **steps to reproduce**, saying whether the job went through Bambu Cloud, LAN, or the SD card.

To capture the log: close OrcaSlicer, delete `obn.log` from your config folder (the Open Bamboo tab shows the exact path) and add `log_level = debug` to `obn.conf`, start OrcaSlicer and send one short test print, then stop. The easy way: click **Export Report for GitHub** in the Open Bamboo tab, it writes a ready to attach zip to your desktop. For rejected signed commands (84033547, 84033543) include `slicer_cert.pem` too, it is a public certificate and safe to share. **Never attach `slicer_key.pem`.** Files too large for GitHub can go on a file host, paste the link in the issue.

## Disclaimer

This is an independent community project, not affiliated with, endorsed by, or associated with Bambu Lab Inc. The bundled networking library embeds credentials that are not yours, and this plugin automates access to Bambu Lab cloud services. You alone are responsible for ensuring your use complies with the applicable terms and law.

Source code, issue tracking, and pre-compiled packages are on GitHub:

Plugin: https://github.com/persano/open-bambu-networking-plugin
Native Core: https://github.com/persano/open-bamboo-networking
Upstream project: https://github.com/ClusterM/open-bamboo-networking
