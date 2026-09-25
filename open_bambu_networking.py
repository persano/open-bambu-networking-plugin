# /// script
# requires-python = ">=3.12"
#
# [tool.orcaslicer.plugin]
# name = "Open Bamboo Networking"
# description = "Open source networking plugin for Bambu Lab printers. Enables cloud printing without developer mode, remote camera liveview over the internet, and instant AMS slot synchronization."
# author = "persano"
# version = "0.2.14"
# ///
"""Open Bamboo Networking Plugin for OrcaSlicer.

Provides automated provisioning, real-time GUI management, and status monitoring
for the Open Bamboo Networking library (`bambu_networking.dll` / `libbambu_networking.so`).

Zero external processes or socket calls are executed on startup, avoiding any security audit prompts.
"""

import os
import sys
import json
import shutil
import hashlib
import orca

def get_os_name():
    if sys.platform.startswith("win"):
        return "Windows"
    elif sys.platform == "darwin":
        return "macOS"
    return "Linux"

def get_plugin_dir():
    appdata = os.environ.get("APPDATA", "")
    if sys.platform.startswith("win"):
        return os.path.join(appdata, "OrcaSlicer", "plugins")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/OrcaSlicer/plugins")
    else:  # Linux
        return os.path.expanduser("~/.config/OrcaSlicer/plugins")

def get_lib_prefix_suffix():
    if sys.platform.startswith("win"):
        return "bambu_networking", ".dll"
    elif sys.platform == "darwin":
        return "libbambu_networking", ".dylib"
    else:
        return "libbambu_networking", ".so"

def get_default_target_path():
    pdir = get_plugin_dir()
    prefix, suffix = get_lib_prefix_suffix()
    return os.path.join(pdir, f"{prefix}{suffix}")

def get_bundled_plugin_path():
    plugin_root = os.path.dirname(os.path.abspath(__file__))
    if sys.platform.startswith("win"):
        return os.path.join(plugin_root, "bin", "win_x64", "bambu_networking.dll")
    elif sys.platform.startswith("linux"):
        return os.path.join(plugin_root, "bin", "linux_x64", "libbambu_networking.so")
    elif sys.platform == "darwin":
        return os.path.join(plugin_root, "bin", "macos_arm64", "libbambu_networking.dylib")
    return ""

def cleanup_old_files():
    pdir = get_plugin_dir()
    if not os.path.exists(pdir):
        return
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
    except (PermissionError, OSError):
        pass

    base_old = dst + ".old"
    old_path = base_old
    counter = 1
    while os.path.exists(old_path):
        try:
            os.remove(old_path)
            break
        except Exception:
            old_path = f"{base_old}.{counter}"
            counter += 1

    try:
        os.rename(dst, old_path)
    except Exception as e:
        raise OSError(f"Cannot overwrite locked file {os.path.basename(dst)}: {e}")

    shutil.copy2(src, dst)

    try:
        os.remove(old_path)
    except Exception:
        pass
    return True

def safe_remove(target):
    """Safely removes target, handling Windows locked DLLs by renaming aside so OrcaSlicer will not load it."""
    if not os.path.exists(target):
        return True

    try:
        os.remove(target)
        return True
    except (PermissionError, OSError):
        pass

    base_del = target + ".pending_delete"
    del_path = base_del
    counter = 1
    while os.path.exists(del_path):
        try:
            os.remove(del_path)
            break
        except Exception:
            del_path = f"{base_del}.{counter}"
            counter += 1

    try:
        os.rename(target, del_path)
    except Exception as e:
        raise OSError(f"Cannot remove locked file {os.path.basename(target)}: {e}")

    try:
        os.remove(del_path)
    except Exception:
        pass
    return True

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
    """Returns the library file path that OrcaSlicer actually binds on startup.
    OrcaSlicer prioritizes versioned libraries (e.g. bambu_networking_02.08.01.dll)
    over unversioned bambu_networking.dll.
    """
    pdir = get_plugin_dir()
    if not os.path.exists(pdir):
        return get_default_target_path()

    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"
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

    return get_default_target_path()

def get_status_dict():
    cleanup_old_files()

    active_target = get_active_target_path()
    default_target = get_default_target_path()
    bundled = get_bundled_plugin_path()
    pdir = get_plugin_dir()

    display_target = active_target if os.path.exists(active_target) else default_target
    display_exists = os.path.exists(display_target)

    bundled_exists = os.path.exists(bundled)
    bundled_hash = get_file_hash(bundled)
    target_hash = get_file_hash(display_target) if display_exists else ""

    is_open_bamboo = bool(display_exists and bundled_exists and (target_hash == bundled_hash))

    target_size = os.path.getsize(display_target) if display_exists else 0
    bundled_size = os.path.getsize(bundled) if bundled_exists else 0

    backup_exists = False
    if os.path.exists(pdir):
        try:
            for f in os.listdir(pdir):
                if f.endswith(".bak"):
                    backup_exists = True
                    break
        except Exception:
            pass

    return {
        "target_path": display_target,
        "target_exists": display_exists,
        "backup_exists": backup_exists,
        "bundled_exists": bundled_exists,
        "is_open_bamboo": is_open_bamboo,
        "target_size_kb": round(target_size / 1024, 1),
        "bundled_size_kb": round(bundled_size / 1024, 1),
        "os": get_os_name(),
        "arch": "x64" if sys.maxsize > 2**32 else "x86"
    }

def do_install():
    cleanup_old_files()

    pdir = get_plugin_dir()
    bundled = get_bundled_plugin_path()

    if not os.path.exists(bundled):
        return False, f"Bundled Open Bamboo library not found at: {bundled}"

    os.makedirs(pdir, exist_ok=True)
    bundled_hash = get_file_hash(bundled)

    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"
    default_target = get_default_target_path()

    targets_to_update = {default_target}

    try:
        for f in os.listdir(pdir):
            if (f.startswith(versioned_prefix) and f.endswith(suffix)) or f == os.path.basename(default_target):
                if not f.endswith(".bak") and not f.endswith(".vendor_backup") and ".old" not in f and ".pending_delete" not in f:
                    targets_to_update.add(os.path.join(pdir, f))
    except Exception:
        pass

    for t in targets_to_update:
        if os.path.exists(t):
            t_hash = get_file_hash(t)
            if t_hash != bundled_hash:
                bak = t + ".bak"
                if not os.path.exists(bak):
                    try:
                        safe_copy(t, bak)
                    except Exception:
                        pass

    for t in targets_to_update:
        try:
            safe_copy(bundled, t)
        except Exception as e:
            return False, f"Failed to install to {os.path.basename(t)}: {e}"

    if sys.platform == "darwin":
        bundled_dir = os.path.dirname(bundled)
        for fname in ["libBambuSource.dylib", "liblive555.dylib", "network_plugins.json"]:
            src_f = os.path.join(bundled_dir, fname)
            if os.path.exists(src_f):
                try:
                    safe_copy(src_f, os.path.join(pdir, fname))
                except Exception:
                    pass

    return True, "Open Bamboo library installed successfully! Please restart OrcaSlicer."

def do_uninstall():
    cleanup_old_files()

    pdir = get_plugin_dir()
    if not os.path.exists(pdir):
        return False, "No active library files found to remove."

    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"
    default_target = get_default_target_path()

    removed = []

    if os.path.exists(default_target):
        try:
            safe_remove(default_target)
            removed.append(os.path.basename(default_target))
        except Exception as e:
            return False, f"Failed to remove {os.path.basename(default_target)}: {e}."

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

    if sys.platform == "darwin":
        for fname in ["libBambuSource.dylib", "liblive555.dylib", "network_plugins.json"]:
            extra = os.path.join(pdir, fname)
            if os.path.exists(extra):
                try:
                    safe_remove(extra)
                except Exception:
                    pass

    if not removed:
        return False, "No active library files found to remove."

    return True, "Open Bamboo library removed successfully! Please restart OrcaSlicer."

def do_restore_stock():
    cleanup_old_files()

    pdir = get_plugin_dir()
    if not os.path.exists(pdir):
        return False, "Plugin directory not found."

    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"
    default_target = get_default_target_path()
    bundled = get_bundled_plugin_path()
    bundled_hash = get_file_hash(bundled)

    backups = []
    try:
        for f in os.listdir(pdir):
            if f.endswith(".bak") and (prefix in f):
                backups.append(os.path.join(pdir, f))
    except Exception:
        pass

    if not backups:
        return False, "No stock backup (.bak) files found to restore."

    restored_files = []
    for bak in backups:
        orig = bak[:-4]
        try:
            safe_copy(bak, orig)
            restored_files.append(os.path.basename(orig))
        except Exception as e:
            return False, f"Failed to restore {os.path.basename(orig)}: {e}"

    stock_source = default_target if (os.path.exists(default_target) and get_file_hash(default_target) != bundled_hash) else ""
    try:
        for f in os.listdir(pdir):
            if f.startswith(versioned_prefix) and f.endswith(suffix):
                if not f.endswith(".bak") and not f.endswith(".vendor_backup") and ".old" not in f and ".pending_delete" not in f:
                    vf = os.path.join(pdir, f)
                    if get_file_hash(vf) == bundled_hash:
                        if stock_source:
                            safe_copy(stock_source, vf)
                        else:
                            safe_remove(vf)
    except Exception:
        pass

    return True, f"Restored original stock library ({', '.join(restored_files)})! Please restart OrcaSlicer."


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
        status = get_status_dict()
        status_json = json.dumps(status)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open Bamboo Networking</title>
<script>
(function() {
  if (window.orca) return;
  var handlers = [];
  function send(data) {
    var payload = JSON.stringify({
      channel: 'orca', kind: 'message', data: (data === undefined ? null : data)
    });
    if (window.wx && typeof window.wx.postMessage === 'function') {
      window.wx.postMessage(payload);
      return true;
    }
    if (window.chrome && window.chrome.webview && typeof window.chrome.webview.postMessage === 'function') {
      window.chrome.webview.postMessage(payload);
      return true;
    }
    return false;
  }
  window.orca = {
    postMessage: function(data) {
      if (!send(data)) {
        var attempts = 0;
        var timer = setInterval(function() {
          attempts++;
          if (send(data) || attempts > 60) clearInterval(timer);
        }, 50);
      }
    },
    onMessage: function(callback) {
      if (typeof callback === 'function') handlers.push(callback);
    }
  };
  window.__orcaDispatch = function(payload) {
    var data = payload ? payload.data : null;
    for (var i = 0; i < handlers.length; i++) {
      try { handlers[i](data); } catch(e) {}
    }
  };
})();
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
    const platformText = document.getElementById("platformText");

    currentTargetPath = s.target_path || "";
    targetPath.textContent = currentTargetPath || "-";
    platformText.textContent = (s.os || "") + " " + (s.arch || "");

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
    showAlert("Processing " + action + "...", true);

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
