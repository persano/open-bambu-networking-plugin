# /// script
# requires-python = ">=3.12"
#
# [tool.orcaslicer.plugin]
# name = "Open Bamboo Networking"
# description = "Open source networking plugin for Bambu Lab printers. Enables cloud printing without developer mode, remote camera liveview over the internet, and instant AMS slot synchronization."
# author = "persano"
# version = "0.2.19"
# ///
"""Open Bamboo Networking Plugin for OrcaSlicer.

Provides automated provisioning, real-time GUI management, and status monitoring
for the Open Bamboo Networking library (`bambu_networking.dll` / `libbambu_networking.so`).

Built using clean room native libraries from persano/open-bamboo-networking,
incorporating custom fixes for cloud printing with Developer Mode OFF,
off-LAN ThroughTek (TUTK) camera liveview, and AMS slot sync.

Zero external processes or socket calls are executed on startup, avoiding any security audit prompts.
"""

import os
import sys
import json
import shutil
import hashlib
import re
import orca

# OrcaSlicer binds the network library by its AA.BB.CC series and only accepts the series its
# AVAILABLE_NETWORK_VERSIONS whitelist declares. A library reporting any other series (02.08.02)
# is refused, the configured version ping-pongs, and the slicer keeps re-offering its own
# download with "Bambu Network plug-in not detected". The install series is therefore pinned.
INSTALL_SERIES = "02.08.01"
LEGACY_SERIES = "01.10.01"
VERSION_RE = re.compile(rb"0[12]\.\d{2}\.\d{2}\.\d{2}(?:\.\d{2})?")

def get_os_name():
    if sys.platform.startswith("win"):
        return "Windows"
    elif sys.platform == "darwin":
        return "macOS"
    return "Linux"

def get_lib_prefix_suffix():
    if sys.platform.startswith("win"):
        return "bambu_networking", ".dll"
    elif sys.platform == "darwin":
        return "libbambu_networking", ".dylib"
    else:
        return "libbambu_networking", ".so"

def get_primary_plugin_dir():
    appdata = os.environ.get("APPDATA", "")
    if sys.platform.startswith("win"):
        return os.path.join(appdata, "OrcaSlicer", "plugins")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/OrcaSlicer/plugins")
    else:
        return os.path.expanduser("~/.config/OrcaSlicer/plugins")

def get_all_plugin_dirs():
    """Returns all directories OrcaSlicer checks for networking libraries.
    Includes the primary AppData plugin folder and, for portable or custom builds,
    the executable directory and its resources/plugins folder.
    """
    dirs = []
    primary = get_primary_plugin_dir()
    if primary and primary not in dirs:
        dirs.append(primary)

    prefix, suffix = get_lib_prefix_suffix()
    exe_candidates = []
    if sys.platform.startswith("win"):
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.GetModuleFileNameW(0, buf, 1024)
            if buf.value:
                exe_candidates.append(os.path.dirname(os.path.abspath(buf.value)))
        except Exception:
            pass

    try:
        if sys.executable:
            exe_candidates.append(os.path.dirname(os.path.abspath(sys.executable)))
    except Exception:
        pass

    for exe_dir in exe_candidates:
        if not os.path.isdir(exe_dir):
            continue
        subfolders = [
            exe_dir,
            os.path.join(exe_dir, "plugins"),
            os.path.join(exe_dir, "resources", "plugins"),
        ]
        for cand in subfolders:
            if os.path.isdir(cand) and cand not in dirs:
                dirs.append(cand)

    return dirs

def get_default_target_path():
    primary = get_primary_plugin_dir()
    prefix, suffix = get_lib_prefix_suffix()
    return os.path.join(primary, f"{prefix}{suffix}")

def get_bundled_plugin_path():
    plugin_root = os.path.dirname(os.path.abspath(__file__))
    if sys.platform.startswith("win"):
        return os.path.join(plugin_root, "bin", "win_x64", "bambu_networking.dll")
    elif sys.platform.startswith("linux"):
        return os.path.join(plugin_root, "bin", "linux_x64", "libbambu_networking.so")
    elif sys.platform == "darwin":
        return os.path.join(plugin_root, "bin", "macos_arm64", "libbambu_networking.dylib")
    return ""

def get_sidecar_names():
    """Companion modules OrcaSlicer loads next to the network library.

    A missing BambuSource.dll makes get_bambu_source_entry() return null, which OrcaSlicer
    answers by offering its own network plug-in download - the same loop as a wrong series.
    """
    if sys.platform.startswith("win"):
        return ["BambuSource.dll", "live555.dll"]
    if sys.platform == "darwin":
        return ["libBambuSource.dylib", "liblive555.dylib", "network_plugins.json"]
    return ["libBambuSource.so", "liblive555.so"]

def bundled_sidecar_path(name):
    return os.path.join(os.path.dirname(get_bundled_plugin_path()), name)

def install_sidecar(name, pdir):
    """Copies a companion module, keeping a .bak of whatever was there before."""
    src = bundled_sidecar_path(name)
    if not os.path.exists(src):
        return
    dst = os.path.join(pdir, name)
    if os.path.exists(dst):
        if get_file_hash(dst) == get_file_hash(src):
            return
        bak = dst + ".bak"
        if not os.path.exists(bak):
            try:
                safe_copy(dst, bak)
            except Exception:
                pass
    safe_copy(src, dst)

def read_reported_version(path):
    """The version string the library answers with for bambu_network_get_version()."""
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return ""
    matches = [m.group(0).decode("ascii") for m in VERSION_RE.finditer(data)]
    if not matches:
        return ""
    for v in matches:
        if v.startswith(INSTALL_SERIES + "."):
            return v
    return matches[0]

def series_of(version):
    parts = version.split(".")
    return ".".join(parts[:3]) if len(parts) >= 3 else ""

def bundled_series_warning():
    """Actionable message when the bundled library reports a series OrcaSlicer refuses."""
    version = read_reported_version(get_bundled_plugin_path())
    if not version:
        return ""
    if series_of(version) in (INSTALL_SERIES, LEGACY_SERIES):
        return ""
    return (
        f"Bundled library reports {version}, but OrcaSlicer only loads the "
        f"{INSTALL_SERIES} series, so installing it leaves the slicer unable to "
        f"detect the plug-in. Rebuild it with -DOBN_VERSION={INSTALL_SERIES}.99."
    )

def read_slicer_config():
    """Reads the OrcaSlicer.conf keys that gate loading of any network library."""
    conf_path = os.path.join(os.path.dirname(get_primary_plugin_dir()), "OrcaSlicer.conf")
    result = {"path": conf_path, "installed_networking": None, "network_plugin_version": ""}
    try:
        with open(conf_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return result

    m = re.search(r'"installed_networking"\s*:\s*(true|false)', text)
    if m:
        result["installed_networking"] = m.group(1) == "true"
    m = re.search(r'"network_plugin_version"\s*:\s*"([^"]*)"', text)
    if m:
        result["network_plugin_version"] = m.group(1)
    return result

def config_warning(conf):
    """OrcaSlicer skips the whole network library load until the plug-in is enabled."""
    if conf["installed_networking"] is False:
        return (
            "OrcaSlicer has the network plug-in disabled, so no library is loaded at all and "
            "the slicer reports it as missing. Enable it under Preferences > Enable Bambu "
            "network plug-in, then restart."
        )
    if conf["installed_networking"] is True and conf["network_plugin_version"] not in ("", INSTALL_SERIES):
        if series_of(conf["network_plugin_version"]) != INSTALL_SERIES:
            return (
                f"OrcaSlicer is configured for network plug-in {conf['network_plugin_version']}, "
                f"which is not the {INSTALL_SERIES} series this build installs. Install once to "
                "let the slicer re-point the configuration."
            )
    return ""

def cleanup_old_files():
    for pdir in get_all_plugin_dirs():
        if not pdir or not os.path.exists(pdir):
            continue
        try:
            for f in os.listdir(pdir):
                if ".old" in f or ".pending_delete" in f:
                    try:
                        os.remove(os.path.join(pdir, f))
                    except Exception:
                        pass
        except Exception:
            pass

def safe_copy(src, dst):
    """Safely copies src to dst, handling Windows locked DLLs by moving the locked file aside first."""
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source file not found: {src}")

    dst_dir = os.path.dirname(dst)
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)

    try:
        shutil.copy2(src, dst)
        return True
    except (PermissionError, OSError) as copy_error:
        first_error = copy_error

    if not os.path.exists(dst):
        # Nothing was locked: the copy itself was refused (read-only folder such as
        # C:\Program Files, antivirus, ...) or the file is not there at all, so there
        # is no file to move aside and renaming it would fail with WinError 2.
        raise OSError(
            f"Cannot create {os.path.basename(dst)} in {dst_dir or os.curdir}: "
            f"{first_error}. The folder is not writable by OrcaSlicer, run "
            "OrcaSlicer as administrator and try again"
        )

    base_old = dst + ".old"
    old_path = base_old
    counter = 1
    while os.path.exists(old_path):
        old_path = f"{base_old}.{counter}"
        counter += 1

    try:
        os.rename(dst, old_path)
    except Exception as e:
        raise OSError(f"Cannot overwrite locked file {os.path.basename(dst)}: {e}")

    try:
        shutil.copy2(src, dst)
    except Exception as e:
        # Put the original file back so a failed write never leaves no library at all.
        try:
            os.rename(old_path, dst)
        except Exception:
            pass
        raise OSError(f"Cannot write {os.path.basename(dst)} after unlocking it: {e}")
    return True

def safe_remove(target):
    """Safely removes target, handling Windows locked DLLs by renaming aside so OrcaSlicer will not load it."""
    if not os.path.exists(target):
        return True

    base_del = target + ".pending_delete"
    del_path = base_del
    counter = 1
    while os.path.exists(del_path):
        del_path = f"{base_del}.{counter}"
        counter += 1

    try:
        os.rename(target, del_path)
        return True
    except Exception:
        pass

    try:
        os.remove(target)
        return True
    except Exception as e:
        raise OSError(f"Cannot remove file {os.path.basename(target)}: {e}")

def get_file_hash(path):
    if not path or not os.path.exists(path) or not os.path.isfile(path):
        return ""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

def get_active_target_path():
    """Returns the library file path that OrcaSlicer actually binds on startup."""
    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"

    for pdir in get_all_plugin_dirs():
        if not os.path.exists(pdir):
            continue

        # The series file is the one resolve_library_path() binds first, so it wins over any
        # other versioned copy a previous run may have left behind.
        series_f = os.path.join(pdir, f"{prefix}_{INSTALL_SERIES}{suffix}")
        if os.path.exists(series_f):
            return series_f

        candidates = []
        try:
            for f in os.listdir(pdir):
                if f.startswith(versioned_prefix) and f.endswith(suffix):
                    if not f.endswith(".bak") and not f.endswith(".vendor_backup") and ".old" not in f and ".pending_delete" not in f:
                        candidates.append(os.path.join(pdir, f))
        except Exception:
            pass

        if candidates:
            candidates.sort(reverse=True)
            return candidates[0]

        default_f = os.path.join(pdir, f"{prefix}{suffix}")
        if os.path.exists(default_f):
            return default_f

    return get_default_target_path()

def get_status_dict():
    active_target = get_active_target_path()
    default_target = get_default_target_path()
    bundled = get_bundled_plugin_path()

    display_target = active_target if os.path.exists(active_target) else default_target
    display_exists = os.path.exists(display_target)

    bundled_exists = os.path.exists(bundled)
    bundled_hash = get_file_hash(bundled)

    # Check if ANY active library across all plugin directories is Open Bamboo
    is_open_bamboo = False
    prefix, suffix = get_lib_prefix_suffix()
    for pdir in get_all_plugin_dirs():
        if not os.path.exists(pdir):
            continue
        try:
            for f in os.listdir(pdir):
                if (f.startswith(prefix) and f.endswith(suffix)) and not f.endswith(".bak") and not f.endswith(".vendor_backup") and ".old" not in f and ".pending_delete" not in f:
                    if get_file_hash(os.path.join(pdir, f)) == bundled_hash:
                        is_open_bamboo = True
                        break
        except Exception:
            pass
        if is_open_bamboo:
            break

    target_size = os.path.getsize(display_target) if display_exists else 0
    bundled_size = os.path.getsize(bundled) if bundled_exists else 0

    backup_exists = False
    for pdir in get_all_plugin_dirs():
        if os.path.exists(pdir):
            try:
                for f in os.listdir(pdir):
                    if f.endswith(".bak") and prefix in f:
                        backup_exists = True
                        break
            except Exception:
                pass
        if backup_exists:
            break

    active_version = read_reported_version(display_target) if display_exists else ""
    warning = ""
    if active_version and series_of(active_version) not in (INSTALL_SERIES, LEGACY_SERIES):
        warning = (
            f"Installed library reports {active_version}, but OrcaSlicer only loads the "
            f"{INSTALL_SERIES} series. It will keep reporting the plug-in as missing until "
            f"the {INSTALL_SERIES} build is installed."
        )
    if not warning:
        warning = bundled_series_warning()

    conf = read_slicer_config()
    conf_warning = config_warning(conf)

    return {
        "target_path": display_target,
        "target_exists": display_exists,
        "backup_exists": backup_exists,
        "bundled_exists": bundled_exists,
        "is_open_bamboo": is_open_bamboo,
        "reported_version": active_version,
        "series_warning": warning,
        "config_warning": conf_warning,
        "installed_networking": conf["installed_networking"],
        "config_version": conf["network_plugin_version"],
        "target_size_kb": round(target_size / 1024, 1),
        "bundled_size_kb": round(bundled_size / 1024, 1),
        "os": get_os_name(),
        "arch": "x64" if sys.maxsize > 2**32 else "x86"
    }

def do_install():
    cleanup_old_files()

    bundled = get_bundled_plugin_path()
    if not os.path.exists(bundled):
        return False, f"Bundled Open Bamboo library not found at: {bundled}"

    series_warning = bundled_series_warning()
    if series_warning:
        return False, series_warning

    bundled_hash = get_file_hash(bundled)
    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"

    installed_targets = []
    conflicting_removed = []
    failures = []
    plugin_dirs = get_all_plugin_dirs()

    for pdir in plugin_dirs:
        try:
            os.makedirs(pdir, exist_ok=True)
        except Exception as e:
            failures.append((pdir, str(e)))
            continue
        default_target = os.path.join(pdir, f"{prefix}{suffix}")
        series_target = os.path.join(pdir, f"{prefix}_{INSTALL_SERIES}{suffix}")
        targets_to_update = {default_target, series_target}

        try:
            for f in os.listdir(pdir):
                if (f.startswith(versioned_prefix) and f.endswith(suffix)) or f == os.path.basename(default_target):
                    if not f.endswith(".bak") and not f.endswith(".vendor_backup") and ".old" not in f and ".pending_delete" not in f:
                        targets_to_update.add(os.path.join(pdir, f))
        except Exception:
            pass

        for t in sorted(targets_to_update):
            if os.path.exists(t):
                t_hash = get_file_hash(t)
                if t_hash == bundled_hash:
                    installed_targets.append(t)
                    continue
                bak = t + ".bak"
                if not os.path.exists(bak):
                    try:
                        safe_copy(t, bak)
                    except Exception:
                        pass
            try:
                safe_copy(bundled, t)
                installed_targets.append(t)
            except Exception as e:
                failures.append((t, str(e)))

        # OrcaSlicer resolves the library by series, so a leftover 02.08.02 build is never the
        # one that binds - it only keeps the configured version pointed at a series the slicer
        # refuses, which is what makes it report the plug-in as missing over and over.
        try:
            for f in os.listdir(pdir):
                if not (f.startswith(versioned_prefix) and f.endswith(suffix)):
                    continue
                if f.endswith(".bak") or f.endswith(".vendor_backup") or ".old" in f or ".pending_delete" in f:
                    continue
                series = f[len(versioned_prefix):-len(suffix)]
                if series.startswith("02.08.") and not series.startswith(INSTALL_SERIES):
                    try:
                        safe_remove(os.path.join(pdir, f))
                        conflicting_removed.append(f)
                    except Exception:
                        pass
        except Exception:
            pass

        for name in get_sidecar_names():
            try:
                install_sidecar(name, pdir)
            except Exception:
                pass

    if not installed_targets:
        detail = "; ".join(f"{t}: {e}" for t, e in failures[:3]) or "unknown error"
        return False, f"Failed to install: {detail}"

    cleanup_note = ""
    if conflicting_removed:
        cleanup_note = " Removed unsupported-series leftover(s): " + ", ".join(sorted(set(conflicting_removed))) + "."

    conf_note = ""
    if read_slicer_config()["installed_networking"] is False:
        conf_note = (
            " OrcaSlicer still has the network plug-in disabled, so it will keep reporting it "
            "missing: enable Preferences > Enable Bambu network plug-in, then restart."
        )

    if failures:
        failed_dirs = sorted({t if t in plugin_dirs else os.path.dirname(t) for t, _ in failures})
        detail = "; ".join(f"{t}: {e}" for t, e in failures[:2])
        return True, (
            f"Open Bamboo library installed to {len(installed_targets)} location(s), "
            f"but not to {', '.join(failed_dirs)} ({detail}). Restart OrcaSlicer; if the "
            "library is not picked up, start OrcaSlicer as administrator and install again."
            + cleanup_note + conf_note
        )

    return True, (
        "Open Bamboo library installed successfully "
        f"({INSTALL_SERIES} series). Please restart OrcaSlicer." + cleanup_note + conf_note
    )

def do_uninstall():
    cleanup_old_files()

    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"
    removed = []

    for pdir in get_all_plugin_dirs():
        if not os.path.exists(pdir):
            continue
        default_target = os.path.join(pdir, f"{prefix}{suffix}")
        if os.path.exists(default_target):
            try:
                safe_remove(default_target)
                removed.append(os.path.basename(default_target))
            except Exception:
                pass

        try:
            for f in os.listdir(pdir):
                if f.startswith(versioned_prefix) and f.endswith(suffix):
                    if not f.endswith(".bak") and not f.endswith(".vendor_backup") and ".old" not in f and ".pending_delete" not in f:
                        vf = os.path.join(pdir, f)
                        try:
                            safe_remove(vf)
                            removed.append(f)
                        except Exception:
                            pass
        except Exception:
            pass

        for name in get_sidecar_names():
            extra = os.path.join(pdir, name)
            if not os.path.exists(extra):
                continue
            # Only take away what this plugin put there; a vendored copy belongs to OrcaSlicer.
            bundled_sidecar = bundled_sidecar_path(name)
            if os.path.exists(bundled_sidecar) and get_file_hash(extra) != get_file_hash(bundled_sidecar):
                continue
            try:
                safe_remove(extra)
                removed.append(name)
            except Exception:
                pass

    if not removed:
        return False, "No active library files found to remove."

    return True, "Open Bamboo library removed successfully! Please restart OrcaSlicer."

def do_restore_stock():
    cleanup_old_files()

    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"
    bundled = get_bundled_plugin_path()
    bundled_hash = get_file_hash(bundled)

    # First, locate any master stock backup across all plugin directories
    master_stock = ""
    for pdir in get_all_plugin_dirs():
        if not os.path.exists(pdir):
            continue
        try:
            for f in os.listdir(pdir):
                if f.endswith(".bak") and prefix in f:
                    full_f = os.path.join(pdir, f)
                    if get_file_hash(full_f) != bundled_hash:
                        master_stock = full_f
                        break
        except Exception:
            pass
        if master_stock:
            break

    if not master_stock:
        return False, "No stock backup (.bak) files found to restore."

    restored_files = []

    for pdir in get_all_plugin_dirs():
        if not os.path.exists(pdir):
            continue
        default_target = os.path.join(pdir, f"{prefix}{suffix}")

        # Restore direct backups in this directory
        try:
            for f in os.listdir(pdir):
                if f.endswith(".bak") and prefix in f:
                    bak = os.path.join(pdir, f)
                    orig = bak[:-4]
                    try:
                        safe_copy(bak, orig)
                        restored_files.append(os.path.basename(orig))
                    except Exception:
                        pass
        except Exception:
            pass

        # If any file in this directory still matches Open Bamboo, overwrite with master stock
        try:
            for f in os.listdir(pdir):
                if (f.startswith(prefix) and f.endswith(suffix)) and not f.endswith(".bak") and not f.endswith(".vendor_backup") and ".old" not in f and ".pending_delete" not in f:
                    full_f = os.path.join(pdir, f)
                    if get_file_hash(full_f) == bundled_hash:
                        try:
                            safe_copy(master_stock, full_f)
                            restored_files.append(f)
                        except Exception:
                            safe_remove(full_f)
        except Exception:
            pass

        # Companion modules are restored from their own backup, or dropped when we are the
        # ones who placed them and no vendor copy was kept.
        for name in get_sidecar_names():
            cur = os.path.join(pdir, name)
            bak = cur + ".bak"
            if os.path.exists(bak):
                try:
                    safe_copy(bak, cur)
                    restored_files.append(name)
                except Exception:
                    pass
                continue
            bundled_sidecar = bundled_sidecar_path(name)
            if os.path.exists(cur) and os.path.exists(bundled_sidecar) \
                    and get_file_hash(cur) == get_file_hash(bundled_sidecar):
                try:
                    safe_remove(cur)
                    restored_files.append(name)
                except Exception:
                    pass

    return True, f"Restored original stock library ({', '.join(set(restored_files))})! Please restart OrcaSlicer."


class OpenBambuPage(orca.pages.PagesPluginCapabilityBase):
    """Main interactive page capability providing tab UI and management dashboard."""

    def get_name(self):
        return "Open Bamboo"

    def get_icon(self):
        plugin_root = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(plugin_root, "icon.png")
        if os.path.exists(icon_path):
            return icon_path
        return ""

    def on_message(self, message):
        try:
            data = message if isinstance(message, dict) else json.loads(message)
        except Exception:
            data = {"action": str(message)}

        action = data.get("action", "")
        reply = {"action": action, "success": True, "message": ""}

        if action == "install":
            success, msg = do_install()
            reply["success"] = success
            reply["message"] = msg
            try:
                orca.host.ui.message(msg, "Open Bamboo Networking", buttons="ok", icon="info" if success else "error")
            except Exception:
                pass
        elif action == "uninstall":
            success, msg = do_uninstall()
            reply["success"] = success
            reply["message"] = msg
            try:
                orca.host.ui.message(msg, "Open Bamboo Networking", buttons="ok", icon="info" if success else "error")
            except Exception:
                pass
        elif action == "restore_stock":
            success, msg = do_restore_stock()
            reply["success"] = success
            reply["message"] = msg
            try:
                orca.host.ui.message(msg, "Open Bamboo Networking", buttons="ok", icon="info" if success else "error")
            except Exception:
                pass
        elif action == "get_status":
            reply["message"] = "Status refreshed."

        reply["status"] = get_status_dict()
        try:
            self.post_message(reply)
        except Exception:
            pass

    def get_ui(self):
        default_status = {
            "target_path": "",
            "target_exists": False,
            "backup_exists": True,
            "bundled_exists": False,
            "is_open_bamboo": False,
            "reported_version": "",
            "series_warning": "",
            "config_warning": "",
            "installed_networking": None,
            "config_version": "",
            "target_size_kb": 0,
            "bundled_size_kb": 0,
            "os": get_os_name(),
            "arch": "x64" if sys.maxsize > 2**32 else "x86",
            "initial": True
        }
        status_json = json.dumps(default_status)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open Bamboo Networking</title>
<script>
(function() {{
  if (window.orca) return;
  var handlers = [];
  function send(data) {{
    var payload = JSON.stringify({{
      channel: 'orca', kind: 'message', data: (data === undefined ? null : data)
    }});
    if (window.wx && typeof window.wx.postMessage === 'function') {{
      window.wx.postMessage(payload);
      return true;
    }}
    if (window.chrome && window.chrome.webview && typeof window.chrome.webview.postMessage === 'function') {{
      window.chrome.webview.postMessage(payload);
      return true;
    }}
    return false;
  }}
  window.orca = {{
    postMessage: function(data) {{
      if (!send(data)) {{
        var attempts = 0;
        var timer = setInterval(function() {{
          attempts++;
          if (send(data) || attempts > 60) clearInterval(timer);
        }}, 50);
      }}
    }},
    onMessage: function(callback) {{
      if (typeof callback === 'function') handlers.push(callback);
    }}
  }};
  window.__orcaDispatch = function(payload) {{
    var data = payload ? payload.data : null;
    for (var i = 0; i < handlers.length; i++) {{
      try {{ handlers[i](data); }} catch(e) {{}}
    }}
  }};
}})();
</script>
<style>
  :root {{
    --bg: #1e1e1e;
    --card-bg: #252526;
    --card-border: #3c3c3c;
    --text-primary: #f0f0f0;
    --text-secondary: #9d9d9d;
    --accent: #009688;
    --accent-hover: #00796b;
    --danger: #d32f2f;
    --danger-hover: #b71c1c;
    --success: #388e3c;
    --warning: #f57c00;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background-color: var(--bg);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    margin: 0;
    padding: 24px;
    font-size: 14px;
    line-height: 1.5;
  }}
  .container {{
    max-width: 820px;
    margin: 0 auto;
  }}
  .header {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--card-border);
    margin-bottom: 24px;
  }}
  .header-logo {{
    font-size: 42px;
    line-height: 1;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4));
  }}
  .header-title h1 {{
    margin: 0;
    font-size: 22px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.3px;
  }}
  .header-title p {{
    margin: 4px 0 0 0;
    font-size: 13px;
    color: var(--text-secondary);
  }}
  .badge {{
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-left: 8px;
    vertical-align: middle;
  }}
  .badge-success {{ background: #1b5e20; color: #a5d6a7; border: 1px solid #2e7d32; }}
  .badge-warning {{ background: #e65100; color: #ffcc80; border: 1px solid #ef6c00; }}
  .badge-inactive {{ background: #424242; color: #bdbdbd; border: 1px solid #616161; }}

  .card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }}
  .card h3 {{
    margin-top: 0;
    margin-bottom: 14px;
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
  }}
  .meta-grid {{
    display: grid;
    grid-template-columns: 140px 1fr;
    gap: 8px 12px;
    font-size: 13px;
  }}
  .meta-key {{
    color: var(--text-secondary);
  }}
  .meta-val {{
    color: #e0e0e0;
    font-family: Consolas, monospace;
    word-break: break-all;
  }}

  .btn-group {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 20px;
  }}
  button.btn {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    transition: background 0.15s, transform 0.05s;
    user-select: none;
  }}
  button.btn:active {{
    transform: scale(0.98);
  }}
  .btn-primary {{
    background: var(--accent);
    color: #ffffff;
  }}
  .btn-primary:hover {{
    background: var(--accent-hover);
  }}
  .btn-secondary {{
    background: #333333;
    color: #e0e0e0;
    border: 1px solid #4a4a4a !important;
  }}
  .btn-secondary:hover {{
    background: #444444;
  }}
  .btn-danger {{
    background: #4a1515;
    color: #ff8a80;
    border: 1px solid #7f1d1d !important;
  }}
  .btn-danger:hover {{
    background: var(--danger);
    color: #ffffff;
  }}

  .alert {{
    padding: 12px 16px;
    border-radius: 6px;
    margin-bottom: 20px;
    font-size: 13px;
    display: none;
  }}
  .alert-success {{
    background: rgba(46, 125, 50, 0.2);
    border: 1px solid #2e7d32;
    color: #c8e6c9;
  }}
  .alert-error {{
    background: rgba(183, 28, 28, 0.2);
    border: 1px solid #b71c1c;
    color: #ffcdd2;
  }}

  .feature-list {{
    list-style: none;
    padding: 0;
    margin: 0;
  }}
  .feature-list li {{
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }}
  .feature-list li:last-child {{
    border-bottom: none;
  }}
  .feature-icon {{
    color: var(--accent);
    font-weight: bold;
    flex-shrink: 0;
  }}
  .feature-title {{
    font-weight: 600;
    color: #fff;
  }}
  .feature-desc {{
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
  }}

  .steps {{
    counter-reset: step-counter;
    list-style: none;
    padding: 0;
    margin: 0;
  }}
  .steps li {{
    counter-increment: step-counter;
    position: relative;
    padding-left: 32px;
    margin-bottom: 12px;
    font-size: 13px;
  }}
  .steps li::before {{
    content: counter(step-counter);
    position: absolute;
    left: 0;
    top: 0;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    font-weight: bold;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="header-logo">🐼</div>
    <div class="header-title">
      <h1>Open Bamboo Networking <span id="statusBadge" class="badge badge-inactive">Loading...</span></h1>
      <p>Open Source Networking Plugin for Bambu Lab Printers</p>
    </div>
  </div>

  <div id="alertBox" class="alert"></div>

  <div class="card">
    <h3>📦 Library Status & Controls</h3>
    <div class="meta-grid">
      <div class="meta-key">Status:</div>
      <div id="statusText" class="meta-val">Reading...</div>

      <div class="meta-key">Active Path:</div>
      <div id="targetPath" class="meta-val">-</div>

      <div class="meta-key">File Size:</div>
      <div id="targetSize" class="meta-val">-</div>

      <div class="meta-key">Reported Version:</div>
      <div id="reportedVersion" class="meta-val">-</div>

      <div class="meta-key">Platform:</div>
      <div id="platformText" class="meta-val">-</div>
    </div>

    <div class="btn-group">
      <button class="btn btn-secondary" onclick="sendAction('get_status')">
        <span>🔍</span> <span>Check Status</span>
      </button>
      <button class="btn btn-primary" onclick="sendAction('install')">
        <span>🚀</span> <span>Install / Update Open Bamboo Library</span>
      </button>
      <button class="btn btn-secondary" id="btnRestoreStock" onclick="sendAction('restore_stock')">
        <span>🔄</span> <span>Restore Stock Backup</span>
      </button>
      <button class="btn btn-danger" onclick="sendAction('uninstall')">
        <span>🗑️</span> <span>Uninstall / Remove Library</span>
      </button>
      <button class="btn btn-secondary" onclick="copyPath()">
        <span>📋</span> <span>Copy Path</span>
      </button>
    </div>
  </div>

  <div class="card">
    <h3>✨ Verified Capabilities</h3>
    <ul class="feature-list">
      <li>
        <span class="feature-icon">✔</span>
        <div>
          <div class="feature-title">Cloud Printing without Developer Mode</div>
          <div class="feature-desc">Print and send slices over Bambu Cloud without touching Developer Mode or LAN Mode. Slicer key signing fully automated.</div>
        </div>
      </li>
      <li>
        <span class="feature-icon">✔</span>
        <div>
          <div class="feature-title">Remote Camera Liveview</div>
          <div class="feature-desc">Clean room ThroughTek (TUTK) P2P video streaming over off-LAN internet connections.</div>
        </div>
      </li>
      <li>
        <span class="feature-icon">✔</span>
        <div>
          <div class="feature-title">Instant AMS Slot Synchronization</div>
          <div class="feature-desc">Automatic pushall recovery ensures multi-filament AMS slots stay updated in real time.</div>
        </div>
      </li>
      <li>
        <span class="feature-icon">✔</span>
        <div>
          <div class="feature-title">100% Open Source & Legal</div>
          <div class="feature-desc">Zero proprietary blobs. Built on open protocol specifications with full legal safety.</div>
        </div>
      </li>
    </ul>
  </div>

  <div class="card">
    <h3>🚀 Quick Start Guide</h3>
    <ol class="steps">
      <li>Click <strong>Install / Update Open Bamboo Library</strong> above.</li>
      <li><strong>Restart OrcaSlicer</strong> completely so the native engine binds the library.</li>
      <li>Sign in to your Bambu Cloud account in the top-right corner. All printers will appear in the Device tab with live camera feeds and instant cloud printing!</li>
    </ol>
  </div>
</div>

<script>
  let initialStatus = {status_json};
  let currentTargetPath = "";

  function updateStatus(s) {{
    if (!s) return;
    const badge = document.getElementById("statusBadge");
    const statusText = document.getElementById("statusText");
    const targetPath = document.getElementById("targetPath");
    const targetSize = document.getElementById("targetSize");
    const reportedVersion = document.getElementById("reportedVersion");
    const platformText = document.getElementById("platformText");

    currentTargetPath = s.target_path || "";
    targetPath.textContent = currentTargetPath || "-";
    platformText.textContent = (s.os || "") + " " + (s.arch || "");

    if (s.initial) {{
      badge.className = "badge badge-inactive";
      badge.textContent = "Standby";
      statusText.innerHTML = "<span style='color:var(--text-secondary);'>Ready. Click <b>Check Status</b> or <b>Install</b> to inspect/manage library.</span>";
      targetSize.textContent = "-";
      reportedVersion.textContent = "-";
      return;
    }}

    reportedVersion.textContent = s.reported_version || "-";

    if (s.is_open_bamboo) {{
      badge.className = "badge badge-success";
      badge.textContent = "Active (Open Bamboo)";
      statusText.innerHTML = "<span style='color:#66bb6a; font-weight:600;'>Open Bamboo Library Active & Ready (" + s.target_size_kb + " KB)</span>";
      targetSize.textContent = s.target_size_kb + " KB";
    }} else if (s.target_exists) {{
      badge.className = "badge badge-warning";
      badge.textContent = "Stock Bambu Active";
      statusText.innerHTML = "<span style='color:#ffa726; font-weight:600;'>Stock Bambu Library Active (" + s.target_size_kb + " KB)</span>";
      targetSize.textContent = s.target_size_kb + " KB";
    }} else {{
      badge.className = "badge badge-inactive";
      badge.textContent = "Not Installed";
      statusText.innerHTML = "<span style='color:#ef5350; font-weight:600;'>Not Installed (Click Install below)</span>";
      targetSize.textContent = "0 KB";
    }}

    if (s.series_warning) {{
      badge.className = "badge badge-warning";
      badge.textContent = "Wrong ABI Series";
      statusText.innerHTML = "<span style='color:#ef5350; font-weight:600;'>" + s.series_warning + "</span>";
    }} else if (s.config_warning) {{
      badge.className = "badge badge-warning";
      badge.textContent = "Plug-in Disabled";
      statusText.innerHTML = "<span style='color:#ef5350; font-weight:600;'>" + s.config_warning + "</span>";
    }}

    const btnRestore = document.getElementById("btnRestoreStock");
    if (btnRestore) {{
      btnRestore.style.display = s.backup_exists ? "inline-flex" : "none";
    }}
  }}

  function showAlert(msg, isSuccess) {{
    const box = document.getElementById("alertBox");
    box.style.display = "block";
    box.className = isSuccess ? "alert alert-success" : "alert alert-error";
    box.textContent = msg;
  }}

  function sendAction(action) {{
    if (action === "get_status") {{
      showAlert("Checking library status...", true);
    }} else {{
      showAlert("Processing " + action + "...", true);
    }}

    function trySend(attempts) {{
      var payload = JSON.stringify({{
        channel: 'orca', kind: 'message', data: {{ action: action }}
      }});
      if (window.orca && typeof window.orca.postMessage === "function") {{
        window.orca.postMessage({{ action: action }});
        return;
      }}
      if (window.wx && typeof window.wx.postMessage === "function") {{
        window.wx.postMessage(payload);
        return;
      }}
      if (window.chrome && window.chrome.webview && typeof window.chrome.webview.postMessage === "function") {{
        window.chrome.webview.postMessage(payload);
        return;
      }}
      if (attempts < 40) {{
        setTimeout(function() {{ trySend(attempts + 1); }}, 50);
      }} else {{
        showAlert("Failed to contact slicer host. Please restart OrcaSlicer and retry.", false);
      }}
    }}

    trySend(0);
  }}

  function copyPath() {{
    if (currentTargetPath) {{
      navigator.clipboard.writeText(currentTargetPath).then(() => {{
        showAlert("Copied path to clipboard: " + currentTargetPath, true);
      }}).catch(() => {{
        showAlert("Path: " + currentTargetPath, true);
      }});
    }}
  }}

  window.addEventListener("DOMContentLoaded", () => {{
    updateStatus(initialStatus);

    if (window.orca && typeof window.orca.onMessage === "function") {{
      window.orca.onMessage((msg) => {{
        try {{
          const data = typeof msg === "string" ? JSON.parse(msg) : msg;
          if (data && data.status) {{
            updateStatus(data.status);
          }}
          if (data && data.message) {{
            showAlert(data.message, data.success !== false);
          }}
        }} catch (e) {{
          console.error("Message parse error:", e);
        }}
      }});
    }}
  }});
</script>
</body>
</html>
"""


class OpenBambuScript(orca.script.ScriptPluginCapabilityBase):
    """Headless script capability for batch or scripted installation."""

    def get_name(self):
        return "Open Bamboo Installer"

    def execute(self):
        success, msg = do_install()
        try:
            orca.host.ui.message(msg, "Open Bamboo Networking", buttons="ok", icon="info" if success else "error")
        except Exception:
            pass

        if success:
            return orca.ExecutionResult.success(msg)
        else:
            return orca.ExecutionResult.failure(orca.PluginResult.RecoverableError, msg)


@orca.plugin
class OpenBambuPlugin(orca.base):
    """Main plugin entry point registering both GUI Page and Headless Script."""

    def register_capabilities(self):
        orca.register_capability(OpenBambuPage)
        orca.register_capability(OpenBambuScript)
