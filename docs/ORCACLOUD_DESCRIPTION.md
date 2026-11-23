Open Bamboo Networking connects your Bambu Lab printer to OrcaSlicer with full cloud print dispatch, remote camera liveview, and AMS slot sync, without requiring closed source vendor libraries or Developer Mode on the printer.

This plugin is an ease-of-use installer for a modified version of the work from https://github.com/ClusterM/open-bamboo-networking. Most of what makes printers talk is that upstream project. The native library embeds a Bambu Lab application client secret so it can automatically fetch the signing certificates needed for cloud and LAN printing, which means this is not a clean-room implementation. If this plugin saves you time, donations to the upstream author are welcome at https://github.com/sponsors/ClusterM.

![Open Bamboo Networking before installation](https://api.orcaslicer.com/api/v1/bundles/media/5882a3ef-d5f4-4a8a-9a5a-cd2c4c913bfb/content)

## What it does

- **Cloud print without developer mode.** Signs and sends print jobs directly over official Bambu Cloud, with no Developer Mode and no switch to LAN Only mode.
- **Remote camera liveview.** Streams live video when you are away from home through TUTK P2P tunnels, with instant stop and resume reconnects.
- **Instant AMS slot sync.** Restores multi-color AMS slot telemetry and temperatures the moment you connect, keeping sliced filament assignments in sync.
- **In-slicer management tab.** An "Open Bamboo" tab in OrcaSlicer's top bar with real-time status detection and one click installation or rollback.
- **Clean and silent startup.** Fully compliant with OrcaSlicer's security auditor: zero permission popups or socket warnings when OrcaSlicer launches.
- **Cross platform.** Pre-compiled open source native libraries bundled for Windows (x64 and arm64), Linux (x64 and arm64), and macOS (Apple Silicon arm64 and Intel x64).

## Credits and licensing

- The native networking library comes from [ClusterM/open-bamboo-networking](https://github.com/ClusterM/open-bamboo-networking), with patches from [persano/open-bamboo-networking](https://github.com/persano/open-bamboo-networking). It is AGPL-3.0 licensed; the full license text ships inside this plugin package.

## Open source and privacy first

- **Open source native libraries.** Bundles the AGPL-3.0 libraries built from open-bamboo-networking, with the fixes for cloud printing while Developer Mode is OFF, remote TUTK P2P camera liveview, and AMS slot sync. Not a clean-room implementation.
- **Local credentials stay local.** Your printer access codes, local keys, and authentication tokens stay stored on your computer.
- **Safe one click restore.** A complete rollback button restores stock libraries or previous configurations at any time.

## Requirements and compatibility

- **Supported printers:** Bambu Lab P1P / P1S, P2S, A1 / A1 Mini, X1 / X1 Carbon, H2D (all verified from user reports) and X2D (connects and prints, occasional liveview drops under investigation). H2S runs the same fixes but I have no report from a real unit. X1E is untested rather than known broken, if you run it please open an issue with your results.
- **Operating systems:** Windows 10/11 (x64 and arm64), Linux (x64 and arm64), macOS (Apple Silicon arm64 / Intel x64).
- **OrcaSlicer versions:** v2.3.0+ (manual install only) and v2.5.0+ nightly builds (when plugin support was added).
- **Before reporting "error code 7":** turn **OFF** "Use 3rd Party Print Host" in the printer settings, while it is on OrcaSlicer sends the job to that host instead of through this plugin and the send fails. If OrcaSlicer asks for a plug-in version like `v02.08.04.99` or reports the plug-in missing, click **Install / Update Open Bamboo Library** once more and restart.

![Open Bamboo Networking installed](https://api.orcaslicer.com/api/v1/bundles/media/56b81240-7a2d-4aaf-b45e-853d360da535/content)

## How to get started

1. Install this plugin from OrcaCloud.
2. In OrcaSlicer, open the new **Open Bamboo** tab in the top navigation bar.
3. Click **Install / Update Open Bamboo Library**.
4. Restart OrcaSlicer.
5. Open the OrcaSlicer menu (list icon, top left), choose **Plugins**, and **tick the checkbox** next to **Open Bamboo Networking Plugin**. If the box stays unticked the library never loads and nothing connects, this is the step people most often miss.

![Tick the plugin checkbox: Plugins window -> Open Bamboo Networking Plugin](https://api.orcaslicer.com/api/v1/bundles/media/5bdca3e2-6e06-43ef-adb8-58f49aba7af5/content)

6. On OrcaSlicer 2.5+, open **Edit -> Preferences -> Online** and tick **Enable Bambu Cloud** under **Cloud Providers**. Until it is ticked, the homepage shows no Bambu Cloud login section. It is a separate checkbox from **Enable Bambu network plug-in** at the bottom of the same page.

![Enable Bambu Cloud under Preferences -> Online -> Cloud Providers](https://raw.githubusercontent.com/persano/open-bambu-networking-plugin/main/docs/enable_bambu_cloud.png)

7. Log into your **Bambu Cloud** account on the homepage (not just Orca Cloud).

## FAQ & Troubleshooting

- **No Bambu Cloud login section on the homepage:** tick **Enable Bambu Cloud** in **Preferences -> Online -> Cloud Providers** (see the screenshot under "How to get started"). It is not the **Enable Bambu network plug-in** checkbox at the bottom of the same page, and on OrcaSlicer 2.5+ fresh installs the section stays hidden until this box is ticked.
- **Do I need Bambu Studio or a slicer_key.pem?** No to both. The plugin is standalone and bundles its own libraries, no files to copy. Envelope signing is automated in memory, and since 0.2.24 the library fetches and refreshes the printer app certificate on its own. The bundled library does embed a Bambu Lab application client secret to fetch those certificates, so this is not a clean-room implementation.
- **"MQTT Command verification failed" (HMS 0500-0500-0001-0007):** the printer rejected a signed command, usually a stale certificate. Update this plugin from OrcaCloud, run Install / Update once, restart, and send a test print. If it appeared right after a firmware update, Bambu's wiki points at Bambu Studio 01.10.02.64 or later, for this plugin just update to the latest version instead. If it persists, attach `open-bambu-networking.log` from the Open Bamboo tab.
- **OrcaSlicer Developer Mode toggle:** only unhides experimental slicer settings, no effect on printer connectivity or firmware security.
- **Failed to connect to printer / server:** check `block_cloud = 0` in `obn.conf` in your configuration folder (`%APPDATA%\OrcaSlicer\obn.conf` on Windows). The template ships `block_cloud = 1`, which blocks all cloud MQTT and makes the slicer report "Failed to connect"; the installer writes this key, add it by hand if you created the file yourself, then restart. Also log into Bambu Cloud. If your ISP restricts TLS on port 8883 try `lan_tls_skip_verify = 1`. For LAN discovery allow inbound UDP port 2021 and keep printer and PC on the same subnet.

## Reporting problems

Hub comments are a poor place for files. Please open an issue on GitHub instead:

https://github.com/persano/open-bambu-networking-plugin/issues

Include: **plugin version** (Open Bamboo tab), **OrcaSlicer version** (Help -> About, full string with build hash), **operating system**, **printer and firmware** (printer screen, Settings -> General -> Version), **exact error** (dialog text, `err_code` or HMS code verbatim), and **steps to reproduce**, saying whether the job went through Bambu Cloud, LAN, or the SD card.

To capture the log: close OrcaSlicer, delete `obn.log` from your config folder (the Open Bamboo tab shows the exact path) and add `log_level = debug` to `obn.conf`, start OrcaSlicer and send one short test print, then stop. The easy way: click **Export Report for GitHub** in the Open Bamboo tab, it writes a ready to attach zip to your desktop. For rejected signed commands (84033547, 84033543) include `slicer_cert.pem` too, it is a public certificate and safe to share. **Never attach `slicer_key.pem`.** Files too large for GitHub can go on a file host, paste the link in the issue.

## Disclaimer

This is an independent community project, not affiliated with, endorsed by, or associated with Bambu Lab Inc. The bundled networking library embeds credentials that are not yours, and this plugin automates access to Bambu Lab cloud services. You alone are responsible for ensuring your use complies with the applicable terms and law.

Source code, issue tracking, and pre-compiled packages are available on GitHub:

Plugin: https://github.com/persano/open-bambu-networking-plugin
Native Core: https://github.com/persano/open-bamboo-networking
Upstream project: https://github.com/ClusterM/open-bamboo-networking
