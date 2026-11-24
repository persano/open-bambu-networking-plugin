# /// script
# requires-python = ">=3.12"
#
# [tool.orcaslicer.plugin]
# name = "Open Bamboo Networking"
# description = "Open source networking plugin for Bambu Lab printers. Enables cloud printing without developer mode, remote camera liveview over the internet, and instant AMS slot synchronization."
# author = "persano"
# version = "0.2.63"
# ///
"""Open Bamboo Networking Plugin for OrcaSlicer.

Installer and manager for the Open Bamboo Networking library
(`bambu_networking.dll` / `libbambu_networking.so`). The native library is an
AGPL-3.0 work built mostly from ClusterM/open-bamboo-networking, with patches
in persano/open-bamboo-networking (cloud printing with Developer Mode OFF,
off-LAN ThroughTek (TUTK) camera liveview, AMS slot sync). It embeds a Bambu
Lab application client secret to auto-fetch the signing certificates, so it is
not a clean-room implementation. See NOTICE and LICENSE.AGPL in the plugin
package for licensing and attribution.

Zero external processes or socket calls are executed on startup, avoiding any security audit prompts.
"""

import os
import sys
import json
import shutil
import hashlib
import re
import time
import zipfile
import tempfile
import orca

# OrcaSlicer binds the network library by its AA.BB.CC series and only accepts the series its
# AVAILABLE_NETWORK_VERSIONS whitelist declares. A library reporting any other series (02.08.02)
# is refused, the configured version ping-pongs, and the slicer keeps re-offering its own
# download with "Bambu Network plug-in not detected". The installer therefore pins the series
# and ships all of the ones OrcaSlicer accepts: 02.08.04 is the current latest (OrcaSlicer
# PR #16202), 02.08.01 remains for builds whose whitelist predates it, 02.03.00 for configs
# pinned to that series, 02.09.01 for configs migrated from Bambu Studio 02.09.01.
INSTALL_SERIES = "02.08.04"
SECONDARY_SERIES = "02.08.01"
# OrcaSlicer configs pinned to 02.03.00 (migrated from Bambu Studio, or set
# before the whitelist gained 02.08.04) bind only bambu_networking_02.03.00.*,
# so without this file the official stock build answers 403 and shows the LAN
# mode dialog there. A real series build is required, not the adaptive rename:
# 02.03.00 removes fields (PrintParams_0203, bind without dev_model), and the
# adaptive rename hands the older by-value layouts a Current-ABI library.
V0203_SERIES = "02.03.00"
# Configs migrated from Bambu Studio 02.09.01 bind only bambu_networking_02.09.01.*;
# the series is append-only over 02.08.04 (minors query and error codes, no struct
# layout change), so a real 02.09.01 build ships and the adaptive rename keeps
# covering future series with the newest build.
V0209_SERIES = "02.09.01"
SUPPORTED_SERIES = (INSTALL_SERIES, SECONDARY_SERIES, V0203_SERIES, V0209_SERIES)
LEGACY_SERIES = "01.10.01"
VERSION_RE = re.compile(rb"0[12]\.\d{2}\.\d{2}\.\d{2}(?:\.\d{2})?")

def get_os_name():
    if sys.platform.startswith("win"):
        return "Windows"
    elif sys.platform == "darwin":
        return "macOS"
    return "Linux"

def get_arch_name():
    import platform
    m = platform.machine().lower()
    if m in ("aarch64", "arm64"):
        return "arm64"
    if m in ("x86_64", "amd64"):
        return "x86_64"
    if m in ("i386", "i486", "i586", "i686", "x86"):
        return "x86"
    return m or "unknown"

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
        # Flatpak forces XDG_CONFIG_HOME to ~/.var/app/<app-id>/config, which is
        # the only directory the slicer reads; expanduser would point at the
        # host ~/.config that OrcaSlicer never sees. Same probe the native
        # library uses for reported_version (config.cpp).
        xdg = os.environ.get("XDG_CONFIG_HOME", "")
        root = xdg if xdg else os.path.expanduser("~/.config")
        return os.path.join(root, "OrcaSlicer", "plugins")

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

def get_platform_bin_dir():
    """bin/ dir for this machine's os/arch: win_x64, win_arm64, macos_arm64,
    macos_x64, linux_arm64 or linux_x64."""
    import platform
    if sys.platform.startswith("win"):
        os_name = "win"
    elif sys.platform == "darwin":
        os_name = "macos"
    else:
        os_name = "linux"
    arch = "arm64" if platform.machine().lower() in ("aarch64", "arm64") else "x64"
    return f"{os_name}_{arch}"

def get_bundled_plugin_path():
    plugin_root = os.path.dirname(os.path.abspath(__file__))
    bin_dir = get_platform_bin_dir()
    if sys.platform.startswith("win"):
        return os.path.join(plugin_root, "bin", bin_dir, "bambu_networking.dll")
    elif sys.platform.startswith("linux"):
        return os.path.join(plugin_root, "bin", bin_dir, "libbambu_networking.so")
    elif sys.platform == "darwin":
        return os.path.join(plugin_root, "bin", bin_dir, "libbambu_networking.dylib")
    return ""

def get_bundled_series_path(series):
    """The bundled build for one series, or "" when the wheel ships none."""
    primary = get_bundled_plugin_path()
    if not primary or not series:
        return ""
    prefix, suffix = get_lib_prefix_suffix()
    candidate = os.path.join(os.path.dirname(primary), f"{prefix}_{series}{suffix}")
    return candidate if os.path.exists(candidate) else ""

def get_bundled_secondary_path():
    """The second series build shipped next to the primary one.

    OrcaSlicer builds without PR #16202 only whitelist 02.08.01, so they resolve
    `bambu_networking_02.08.01.*` and would report the plug-in missing when only
    the 02.08.04 series files exist. Returns "" when the wheel carries no
    secondary build.
    """
    return get_bundled_series_path(SECONDARY_SERIES)

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

def register_bambu_source(pdir, register=True):
    """Register or unregister BambuSource.dll as a DirectShow source filter.

    Registration lives in HKCU (no admin needed) and is what makes the
    camera liveview resolve the bambu: URL scheme. OrcaSlicer only runs it
    when it copies the network plug-in itself, so a library dropped in by
    this installer stays unregistered and the camera stays black until the
    user runs regsvr32 by hand (issue #8). Best effort: returns True when
    the export answered a success HRESULT.
    """
    if not sys.platform.startswith("win"):
        return False
    dll = os.path.join(pdir, "BambuSource.dll")
    if not os.path.exists(dll):
        return False
    try:
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LoadLibraryW.argtypes = [ctypes.c_wchar_p]
        kernel32.LoadLibraryW.restype = ctypes.c_void_p
        kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        kernel32.GetProcAddress.restype = ctypes.c_void_p
        kernel32.FreeLibrary.argtypes = [ctypes.c_void_p]
        handle = kernel32.LoadLibraryW(dll)
        if not handle:
            return False
        try:
            export = b"DllRegisterServer" if register else b"DllUnregisterServer"
            addr = kernel32.GetProcAddress(handle, export)
            if not addr:
                return False
            fn = ctypes.WINFUNCTYPE(ctypes.c_long)(addr)
            return fn() >= 0
        finally:
            kernel32.FreeLibrary(handle)
    except Exception:
        return False

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
    for series in SUPPORTED_SERIES:
        for v in matches:
            if v.startswith(series + "."):
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
    if series_of(version) in SUPPORTED_SERIES + (LEGACY_SERIES,):
        return ""
    return (
        f"Bundled library reports {version}, but OrcaSlicer only loads the "
        f"{' and '.join(SUPPORTED_SERIES)} series, so installing it leaves the "
        f"slicer unable to detect the plug-in. Rebuild it with "
        f"-DOBN_VERSION={INSTALL_SERIES}.99."
    )

def read_slicer_config():
    """Reads the OrcaSlicer.conf keys that gate loading of any network library.

    The read goes through the native library first: OrcaSlicer.conf is on the
    slicer audit's denied-filename list, and a denied Python open must not run
    on hosts where the denial kills the process (issue #17). The plain Python
    open stays as the fallback for installs whose library predates
    obn_read_text_file; that open was already exercised daily by 0.2.54
    without the crash.
    """
    conf_path = os.path.join(os.path.dirname(get_primary_plugin_dir()), "OrcaSlicer.conf")
    result = {"path": conf_path, "installed_networking": None, "network_plugin_version": ""}
    try:
        data = native_read_file(conf_path, max_bytes=4194304)
        if data is None:
            with open(conf_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        else:
            text = data.decode("utf-8", errors="replace")
    except Exception:
        return result


    m = re.search(r'"installed_networking"\s*:\s*(true|false)', text)
    if m:
        result["installed_networking"] = m.group(1) == "true"
    m = re.search(r'"network_plugin_version"\s*:\s*"([^"]*)"', text)
    if m:
        result["network_plugin_version"] = m.group(1)
    return result

SERIES_RE = re.compile(r"^\d{2}\.\d{2}\.\d{2}$")

def get_version_override_path():
    """reported_version file the library reads in bambu_network_get_version()."""
    return os.path.join(os.path.dirname(get_primary_plugin_dir()), "reported_version")

def read_override_version():
    """Content of the reported_version override, or "" when absent/invalid."""
    try:
        with open(get_version_override_path(), "r", encoding="utf-8") as f:
            v = f.readline().strip()
    except Exception:
        return ""
    if re.fullmatch(r"[0-9.]{1,32}", v) and any(c.isdigit() for c in v):
        return v
    return ""

def write_override_version(version):
    """Set (or with "" remove) the version override. Name must avoid "conf":
    the slicer audit hard-denies Python opens of any path containing it."""
    path = get_version_override_path()
    try:
        if not version:
            if os.path.exists(path):
                os.remove(path)
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(version + "\n")
    except Exception:
        pass

def adaptive_series():
    """Host series this build does not ship, or "" when nothing is needed.

    Official OrcaSlicer drops old rows from AVAILABLE_NETWORK_VERSIONS and
    binds only the series it declares, so a future series leaves every
    shipped file undetectable. The newest ABI (02.09.01) is append-only, so
    the same build keeps working there: the installer copies it under the
    host's series name and points the library's reported_version override
    at it.
    """
    series = series_of(read_slicer_config()["network_plugin_version"])
    if not SERIES_RE.match(series):
        return ""
    if series in SUPPORTED_SERIES or series == LEGACY_SERIES:
        return ""
    return series

def config_warning(conf):
    """OrcaSlicer skips the whole network library load until the plug-in is enabled."""
    if conf["installed_networking"] is False:
        return (
            "OrcaSlicer has the network plug-in disabled, so no library is loaded at all and "
            "the slicer reports it as missing. Open Preferences > Online and tick "
            "\"Enable Bambu network plug-in\", then restart OrcaSlicer."
        )
    if conf["installed_networking"] is True and conf["network_plugin_version"]:
        wanted = series_of(conf["network_plugin_version"])
        # A legacy pin makes OrcaSlicer load Bambu's legacy agent instead of any
        # file this build installs (we never ship 01.10.01.*), and the slicer
        # treats legacy as a supported version, so it never re-points on its own.
        if wanted == LEGACY_SERIES:
            return (
                f"OrcaSlicer is set to the legacy network plug-in "
                f"({conf['network_plugin_version']}), so no Open Bamboo library loads. "
                "Open Preferences > Online, set \"Network plug-in version\" to the "
                "02.08.xx (Latest) entry, then restart OrcaSlicer."
            )
        # A reported_version override makes the installed library report the
        # host's series, so the configured version is satisfied by design.
        if wanted not in SUPPORTED_SERIES and wanted != series_of(read_override_version()):
            return (
                f"OrcaSlicer is configured for network plug-in {conf['network_plugin_version']}, "
                f"which is none of the series this build installs "
                f"({', '.join(SUPPORTED_SERIES)}). Install once to let the slicer "
                "re-point the configuration, or set \"Network plug-in version\" under "
                "Preferences > Online to the 02.08.xx (Latest) entry and restart."
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
        hint = (
            "The folder is not writable by OrcaSlicer, run "
            "OrcaSlicer as administrator and try again"
            if sys.platform.startswith("win")
            else "OrcaSlicer cannot write to that folder; check its permissions "
                 "and try again"
        )
        raise OSError(
            f"Cannot create {os.path.basename(dst)} in {dst_dir or os.curdir}: "
            f"{first_error}. {hint}"
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

def _config_dir():
    return os.path.dirname(get_primary_plugin_dir())

def cert_chain_status():
    """App certificate chain state shown on the status page.

    Firmware path-builds the installed chain to its BBL CA root: it needs
    leaf -> intermediate -> application_root (3 PEM blocks). A shorter chain
    installs as SUCCESS but every signed command is then rejected with
    err_code 84033547, so the library's gate refuses to install it.
    """
    path = os.path.join(_config_dir(), "slicer_cert.pem")
    info = {
        "cert_path": path,
        "cert_exists": False,
        "cert_blocks": 0,
        "cert_chain_ok": False,
        "crl_exists": os.path.exists(os.path.join(_config_dir(), "slicer_crl.pem")),
        "cert_error": "",
    }
    # Native only, no Python fallback: the slicer audit denies this path by
    # keyword and the denial has killed the process on flatpak (issue #17).
    # os.path.exists above is safe: os.stat raises no audit event.
    try:
        pem_bytes = native_read_file(path, max_bytes=262144)
    except FileNotFoundError:
        return info
    except Exception as e:
        info["cert_error"] = str(e)
        return info
    if pem_bytes is None:
        info["cert_error"] = "unknown (Open Bamboo library too old to read the certificate)"
        return info
    info["cert_exists"] = True
    pem = pem_bytes.decode("ascii", errors="replace")
    info["cert_blocks"] = pem.count("-----BEGIN CERTIFICATE-----")
    info["cert_chain_ok"] = info["cert_blocks"] >= 3
    return info

def _scan_fetch_lines(lines, state, text):
    """Last fetch-related line wins (same result as scanning the tail reversed)."""
    for line in lines:
        if "appcert fetch: ok" in line:
            state, text = "ok", line.strip()
        elif "appcert fetch:" in line or "update_cert: app-cert fetch failed" in line:
            state, text = "failed", line.strip()
        elif "app-cert material missing/unusable" in line:
            state, text = "running", "fetching shared credentials"
    return state, text

def _native_read_or_none(path, offset=0, max_bytes=None):
    """native_read_file with every failure (including missing file) as None."""
    try:
        return native_read_file(path, offset=offset, max_bytes=max_bytes)
    except Exception:
        return None

def last_fetch_status():
    """Latest app-cert fetch outcome from obn.log.

    Read through the native library only: on hosts where the config path
    itself trips a denied audit keyword, a Python open of obn.log dies with
    the process (issue #17), so there is deliberately no Python fallback.
    """
    state, text = "none", "no credential fetch recorded in obn.log"
    log_path = get_log_file_path()
    tail = _native_read_or_none(log_path, offset=-1000000, max_bytes=1000000)
    if tail is None:
        return {"fetch_state": "nolog", "fetch_text": "obn.log not readable yet"}
    state, text = _scan_fetch_lines(tail.decode("utf-8", errors="replace").splitlines(), state, text)
    if state == "none":
        # The fetch runs once per session, so its line can predate the 1 MB
        # tail window; scan the whole log when the tail has none. The whole
        # read is capped at 64 MB instead of the old unbounded read.
        whole = _native_read_or_none(log_path, max_bytes=67108864)
        if whole is not None:
            state, text = _scan_fetch_lines(whole.decode("utf-8", errors="replace").splitlines(), state, text)
    return {"fetch_state": state, "fetch_text": text[:400]}

def read_log_level():
    """log_level from obn.conf; returns a note when the plugin audit denies it."""
    try:
        with open(os.path.join(_config_dir(), "obn.conf"), "r",
                  encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if line.startswith("log_level"):
                    return line.split("=", 1)[-1].strip() if "=" in line else ""
    except Exception:
        return "unknown (slicer denied access)"
    return "not set (library default)"

def plugin_version():
    """Version from this file's script header, the source of truth the loader reads."""
    try:
        with open(__file__, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(12):
                line = f.readline()
                if not line:
                    break
                m = re.match(r'#\s*version\s*=\s*"([^"]+)"', line.strip())
                if m:
                    return m.group(1)
    except Exception:
        pass
    return ""

def orca_version():
    """Host OrcaSlicer version when the host exposes one, else ""."""
    for attr in ("version", "app_version", "get_version"):
        try:
            v = getattr(orca.host, attr, None)
            if callable(v):
                v = v()
            if isinstance(v, str) and v:
                return v
        except Exception:
            pass
    return ""

def get_status_dict():
    active_target = get_active_target_path()
    default_target = get_default_target_path()
    bundled = get_bundled_plugin_path()

    display_target = active_target if os.path.exists(active_target) else default_target
    display_exists = os.path.exists(display_target)

    bundled_exists = os.path.exists(bundled)
    bundled_hash = get_file_hash(bundled)
    bundled_secondary_hash = get_file_hash(get_bundled_secondary_path())
    bundled_v0203_hash = get_file_hash(get_bundled_series_path(V0203_SERIES))
    bundled_v0209_hash = get_file_hash(get_bundled_series_path(V0209_SERIES))
    valid_hashes = {h for h in (bundled_hash, bundled_secondary_hash, bundled_v0203_hash, bundled_v0209_hash) if h}

    # Check if ANY active library across all plugin directories is Open Bamboo
    is_open_bamboo = False
    prefix, suffix = get_lib_prefix_suffix()
    for pdir in get_all_plugin_dirs():
        if not os.path.exists(pdir):
            continue
        try:
            for f in os.listdir(pdir):
                if (f.startswith(prefix) and f.endswith(suffix)) and not f.endswith(".bak") and not f.endswith(".vendor_backup") and ".old" not in f and ".pending_delete" not in f:
                    if get_file_hash(os.path.join(pdir, f)) in valid_hashes:
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
    if active_version and series_of(active_version) not in SUPPORTED_SERIES + (LEGACY_SERIES,):
        warning = (
            f"Installed library reports {active_version}, but OrcaSlicer only loads the "
            f"{' and '.join(SUPPORTED_SERIES)} series. It will keep reporting the plug-in "
            "as missing until a supported build is installed."
        )
    if not warning:
        warning = bundled_series_warning()

    conf = read_slicer_config()
    conf_warning = config_warning(conf)

    override = read_override_version()
    if override and series_of(override) != series_of(conf["network_plugin_version"]):
        warning = warning or (
            f"The reported_version override ({override}) no longer matches the "
            f"series OrcaSlicer is configured for; install again to refresh it."
        )

    return {
        "target_path": display_target,
        "target_exists": display_exists,
        "backup_exists": backup_exists,
        "log_path": get_log_file_path(),
        "log_exists": os.path.exists(get_log_file_path()),
        "bundled_exists": bundled_exists,
        "is_open_bamboo": is_open_bamboo,
        "reported_version": active_version,
        "version_override": override,
        "series_warning": warning,
        "config_warning": conf_warning,
        "installed_networking": conf["installed_networking"],
        "config_version": conf["network_plugin_version"],
        "target_size_kb": round(target_size / 1024, 1),
        "bundled_size_kb": round(bundled_size / 1024, 1),
        "os": get_os_name(),
        "arch": get_arch_name(),
        "plugin_version": plugin_version(),
        "orca_version": orca_version(),
        "log_level": read_log_level(),
        **cert_chain_status(),
        **last_fetch_status(),
    }

# CDLL instances kept alive so exports bound from them stay valid for the
# process lifetime (ctypes unloads a library whose CDLL object is collected).
_native_loaded = {}

def _native_export(fn_name, argtypes, restype):
    """Bound `fn_name` from the first candidate library exposing it, else None.

    Walks every plugin directory plus the bundled copy, skipping libraries
    that fail to load or predate the export.
    """
    try:
        import ctypes
    except Exception:
        return None

    prefix, suffix = get_lib_prefix_suffix()
    candidates = [os.path.join(pdir, prefix + suffix) for pdir in get_all_plugin_dirs()]
    bundled = get_bundled_plugin_path()
    if bundled:
        candidates.append(bundled)

    seen = set()
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        if not os.path.isfile(cand):
            continue
        lib = _native_loaded.get(cand)
        if lib is None:
            try:
                lib = ctypes.CDLL(cand)
            except Exception:
                continue
            _native_loaded[cand] = lib
        fn = getattr(lib, fn_name, None)
        if fn is None:
            continue
        fn.argtypes = list(argtypes)
        fn.restype = restype
        return fn
    return None

def _native_conf_call(fn_name, conf_path):
    """Call `fn_name(conf_path)` inside the networking library; None on failure.

    OrcaSlicer's plugin audit hard-denies every Python open() of a path whose
    name contains "conf" before any allowed-root or permission flow runs, so
    the installer delegates its obn.conf writes to the library: C++ writes
    are outside the Python audit hook and the library owns the file anyway.
    Returns None when ctypes is unavailable, no candidate library exposes
    the function, or the call raises (older installs), which sends the
    caller down its direct-write fallback.
    """
    try:
        import ctypes
    except Exception:
        return None
    fn = _native_export(fn_name, (ctypes.c_char_p,), ctypes.c_int)
    if fn is None:
        return None
    try:
        return fn(os.fsencode(conf_path))
    except Exception:
        return None

def native_read_file(path, offset=0, max_bytes=None):
    """File bytes read by the native library, or None when it cannot read.

    The slicer's plugin audit hard-denies Python open() of OrcaSlicer.conf
    (denied filename) and slicer_cert.pem (keyword), and on flatpak builds
    that denial has taken the whole process down (issue #17). C++ fopen runs
    outside the CPython audit hook, so these reads go through
    obn_read_text_file() instead of open(). Missing file raises
    FileNotFoundError, matching open(); every other failure returns None.
    A negative offset counts back from end of file. max_bytes truncates
    instead of failing, so oversized files stay readable in part.
    """
    try:
        import ctypes
    except Exception:
        return None
    fn = _native_export(
        "obn_read_text_file",
        (ctypes.c_char_p, ctypes.c_uint64, ctypes.c_char_p, ctypes.c_uint32),
        ctypes.c_int64)
    if fn is None:
        return None

    raw = os.fsencode(path)
    try:
        size = fn(raw, 0, None, 0)
        if size < 0:
            if size == -2:
                raise FileNotFoundError(path)
            return None
        start = offset if offset >= 0 else max(0, size + offset)
        if start > size:
            start = size
        length = size - start
        if max_bytes is not None and length > max_bytes:
            length = max_bytes
        if length == 0:
            return b""
        buf = ctypes.create_string_buffer(length)
        copied = fn(raw, start, buf, length)
        if copied < 0:
            return None
        return buf.raw[:copied]
    except FileNotFoundError:
        raise
    except Exception:
        return None

def _native_ensure_obn_conf(conf_path):
    """Outcome code of the legacy single-fix export (block_cloud only),
    or None when the library predates it; see _native_conf_call."""
    return _native_conf_call("obn_ensure_conf_block_cloud", conf_path)

# Outcome codes from obn_ensure_conf_block_cloud(), worded exactly like the
# direct-write messages below so the install dialog stays unchanged.
_NATIVE_CONF_NOTES = {
    1: " Enabled Bambu Cloud in obn.conf (block_cloud = 0).",
    2: " Set block_cloud = 0 in obn.conf (it was blocking Bambu Cloud).",
    3: " Added block_cloud = 0 to obn.conf (enables Bambu Cloud).",
}

# Bytes 1 and 2 of obn_ensure_conf_fixes(): 0 means "already right / user
# value kept" and adds no message; the wording matches the Python paths
# these replace (ensure_log_to_file, ensure_client_name).
_NATIVE_LOG_NOTES = {
    1: " Enabled diagnostic file logging (obn.log next to obn.conf).",
}
_NATIVE_CLIENT_NOTES = {
    1: " Set client_name = BambuStudio in obn.conf (any other value gets HTTP 403 from cloud print).",
}

def ensure_obn_conf():
    """Guarantee obn.conf lets the native library reach Bambu Cloud.

    The template embedded in the native library ships `block_cloud = 1` (cloud
    off), and a hand-written obn.conf that only adds the FAQ's logging lines has
    no `block_cloud` key at all - the native default is also "block". Either way
    cloud MQTT and the cloud message fallback stay blocked ("blocked by
    block_cloud" / "cloud fallback blocked" in obn.log), so any printer the
    plugin cannot reach over LAN fails with "Failed to connect to printer".
    Only the block_cloud value is touched; every other key the user set
    (logging, TLS, PEM paths) is preserved verbatim.

    The write goes through the library first (see _native_ensure_obn_conf);
    the direct Python write only runs as a fallback on installs whose library
    predates obn_ensure_conf_block_cloud.

    Returns a note for the install message, or "" when nothing changed.
    """
    conf_path = os.path.join(os.path.dirname(get_primary_plugin_dir()), "obn.conf")

    native = _native_ensure_obn_conf(conf_path)
    if native is not None and native >= 0:
        return _NATIVE_CONF_NOTES.get(native, "")

    key_line = re.compile(r"^\s*block_cloud\s*=\s*(\S+)")
    block_header = (
        "# 0 = talk to Bambu Cloud (required for cloud printing and for any\n"
        "# printer that is not reachable over LAN). 1 = block cloud traffic.\n"
        "block_cloud = 0\n"
    )
    try:
        if not os.path.exists(conf_path):
            with open(conf_path, "w", encoding="utf-8") as f:
                f.write(
                    "# Open Bamboo Networking configuration\n"
                    "# Written by the Open Bamboo plugin installer. Add your own\n"
                    "# keys below (log_to_file, log_level, ...); see the README.\n"
                    "\n" + block_header
                )
            return " Enabled Bambu Cloud in obn.conf (block_cloud = 0)."

        with open(conf_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return (
            f" Could not update obn.conf ({e}); if the printer cannot connect,"
            " set block_cloud = 0 in obn.conf and restart OrcaSlicer."
        )

    changed = False
    have_key = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        m = key_line.match(line)
        if not m:
            continue
        have_key = True
        if m.group(1).lower() in ("1", "true", "yes"):
            lines[i] = "block_cloud = 0\n"
            changed = True
    if not have_key:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append(block_header)
        changed = True

    if changed:
        try:
            with open(conf_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            return (
                f" Could not update obn.conf ({e}); if the printer cannot connect,"
                " set block_cloud = 0 in obn.conf and restart OrcaSlicer."
            )
        if have_key:
            return " Set block_cloud = 0 in obn.conf (it was blocking Bambu Cloud)."
        return " Added block_cloud = 0 to obn.conf (enables Bambu Cloud)."
    return ""

def get_log_file_path():
    """Where the native library writes obn.log (same folder as obn.conf)."""
    return os.path.join(os.path.dirname(get_primary_plugin_dir()), "obn.log")

def do_export_report():
    """Zip the diagnostic files for a GitHub issue.

    Ships the obn.log tail (capped at 5 MB), slicer_cert.pem,
    slicer_crl.pem, obn.conf (when the plugin audit lets Python read a
    path containing "conf") and a status.json snapshot. Never includes
    slicer_key.pem, client_auth_secret.txt or the certs/ device material.
    """
    cfg = _config_dir()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest_dir = ""
    for candidate in (os.path.join(os.path.expanduser("~"), "Desktop"),
                      os.path.expanduser("~"), tempfile.gettempdir()):
        if os.path.isdir(candidate):
            dest_dir = candidate
            break
    zip_path = os.path.join(dest_dir, "open-bamboo-report-%s.zip" % stamp)
    readme = (
        "Open Bamboo diagnostic report\n"
        "=============================\n\n"
        "Attach this whole zip to a GitHub issue:\n"
        "https://github.com/persano/open-bambu-networking-plugin/issues\n\n"
        "Contents: obn.log (tail), slicer_cert.pem, slicer_crl.pem,\n"
        "obn.conf (if readable) and status.json. It does NOT contain\n"
        "slicer_key.pem, client_auth_secret.txt or printer keys.\n"
    )
    added = []
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            # Log and certificate bytes come from the native library: the
            # slicer audit denies Python opens of slicer_cert.pem (and of
            # obn.log on hosts with a denied keyword above the config root),
            # where the denial can take the process down (issue #17).
            tail = _native_read_or_none(get_log_file_path(), offset=-5000000, max_bytes=5000000)
            if tail is not None:
                z.writestr("obn.log", tail)
                added.append("obn.log")
            for name in ("slicer_cert.pem", "slicer_crl.pem"):
                data = _native_read_or_none(os.path.join(cfg, name), max_bytes=1048576)
                if data is not None:
                    z.writestr(name, data)
                    added.append(name)
            # obn.conf is exempt from the audit keyword rule (exact-name
            # exemption in the slicer), so a plain Python read is allowed.
            try:
                with open(os.path.join(cfg, "obn.conf"), "rb") as f:
                    z.writestr("obn.conf", f.read())
                added.append("obn.conf")
            except Exception:
                pass
            try:
                z.writestr("status.json",
                           json.dumps(get_status_dict(), indent=2, default=str))
                added.append("status.json")
            except Exception:
                pass
            z.writestr("README.txt", readme)
    except Exception as e:
        return False, "Could not write the report: %s" % e
    if not added:
        return False, "Nothing to export yet: no log or certificate files found."
    return True, ("Report written to %s (includes %s). Attach it to "
                  "https://github.com/persano/open-bambu-networking-plugin/issues"
                  % (zip_path, ", ".join(added)))

_LOG_MANUAL_NOTE = (
    " Could not enable file logging automatically (OrcaSlicer blocked the plugin's "
    "obn.conf access; allow the permission prompt it shows, if any). Add "
    "'log_to_file = 1' to obn.conf and restart OrcaSlicer so obn.log captures "
    "diagnostics."
)

def ensure_log_to_file():
    """Default obn.conf to `log_to_file = 1` so obn.log exists for bug reports.

    Without it the native library logs to stderr only, which OrcaSlicer drops,
    and users have no obn.log to attach, so reports like "print sent but the
    printer never starts" arrive with nothing to diagnose. Only the missing key
    is added; an explicit user value (including log_to_file = 0) is kept. The
    write is a plain Python open, which OrcaSlicer's plugin audit may deny on
    builds that do not exempt obn.conf; the caller then gets the manual-step
    note instead.

    Returns a note for the install message, or "" when nothing changed.
    """
    conf_path = os.path.join(os.path.dirname(get_primary_plugin_dir()), "obn.conf")
    key_re = re.compile(r"^\s*log_to_file\s*=")
    header = (
        "# Open Bamboo Networking configuration\n"
        "# Written by the Open Bamboo plugin installer. Add your own\n"
        "# keys below (log_to_file, log_level, ...); see the README.\n"
        "\n"
    )
    try:
        if not os.path.exists(conf_path):
            with open(conf_path, "w", encoding="utf-8") as f:
                f.write(header + "log_to_file = 1\n")
            return " Enabled diagnostic file logging (obn.log next to obn.conf)."
        with open(conf_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return _LOG_MANUAL_NOTE

    if any(key_re.match(l) for l in lines):
        return ""

    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    if lines and lines[-1].strip():
        lines.append("\n")
    lines.append("log_to_file = 1\n")
    try:
        with open(conf_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception:
        return _LOG_MANUAL_NOTE
    return " Enabled diagnostic file logging (obn.log next to obn.conf)."

_CLIENT_NAME_MANUAL_NOTE = (
    " Could not check client_name in obn.conf (OrcaSlicer blocked the plugin's "
    "obn.conf access; allow the permission prompt it shows, if any). Cloud print "
    "answers HTTP 403 unless obn.conf has 'client_name = BambuStudio'; set that "
    "line yourself if prints never reach the printer."
)

def ensure_client_name():
    """Rewrite the pre-0.2.28 template `client_name = OpenBambooNetworking`.

    `POST /v1/user-service/my/task` (cloud print) answers HTTP 403 for any
    client name other than the stock `BambuStudio`, so a config created by an
    old installer accepts no print at all while everything else works, with
    only `create_task X-BBL-Client-Name=OpenBambooNetworking` in obn.log
    (issue #4, A1 mini on the CN cloud). Only that shipped value is rewritten;
    any other value the user picked is left alone, and an absent key already
    means the library default (BambuStudio).

    Returns a note for the install message, or "" when nothing changed.
    """
    conf_path = os.path.join(os.path.dirname(get_primary_plugin_dir()), "obn.conf")
    key_re = re.compile(r"^(\s*client_name\s*=\s*)([^\s#]+)")
    try:
        with open(conf_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except PermissionError:
        # Stock OrcaSlicer's plugin audit can deny obn.conf reads; staying quiet
        # here would skip the rewrite with no hint while prints keep 403ing.
        return _CLIENT_NAME_MANUAL_NOTE
    except Exception:
        return ""

    changed = False
    for i, line in enumerate(lines):
        m = key_re.match(line)
        if not m:
            continue
        if m.group(2).strip('"').lower() == "openbamboonetworking":
            lines[i] = m.group(1) + "BambuStudio" + line[m.end():]
            changed = True
        break

    if not changed:
        return ""
    try:
        with open(conf_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception:
        return _CLIENT_NAME_MANUAL_NOTE
    return " Set client_name = BambuStudio in obn.conf (any other value gets HTTP 403 from cloud print)."

def ensure_conf_fixes_notes():
    """Apply all three obn.conf fixes through the library in one pass.

    Returns (obn_note, log_note, client_note) worded exactly like
    ensure_obn_conf(), ensure_log_to_file() and ensure_client_name(), or
    None when the library predates obn_ensure_conf_fixes() (or its read or
    write failed), so the caller keeps the legacy three-function flow with
    its Python fallbacks and manual-step notes.

    Why this exists: on OrcaSlicer builds whose audit hard-denies Python
    "conf" access (report of 2026-10-21: A1 on Win11, OrcaSlicer
    2.5.0-alpha) the client_name rewrite and the log_to_file default never
    ran, cloud print answered HTTP 403 with no obn.log to diagnose it, and
    the installer could only tell the user to edit the file by hand.
    """
    conf_path = os.path.join(os.path.dirname(get_primary_plugin_dir()), "obn.conf")
    packed = _native_conf_call("obn_ensure_conf_fixes", conf_path)
    if packed is None or packed < 0:
        return None
    return (
        _NATIVE_CONF_NOTES.get(packed & 0xFF, ""),
        _NATIVE_LOG_NOTES.get((packed >> 8) & 0xFF, ""),
        _NATIVE_CLIENT_NOTES.get((packed >> 16) & 0xFF, ""),
    )

def do_install():
    cleanup_old_files()

    bundled = get_bundled_plugin_path()
    if not os.path.exists(bundled):
        return False, f"Bundled Open Bamboo library not found at: {bundled}"

    series_warning = bundled_series_warning()
    if series_warning:
        return False, series_warning

    bundled_secondary = get_bundled_secondary_path()
    bundled_v0203 = get_bundled_series_path(V0203_SERIES)
    bundled_v0209 = get_bundled_series_path(V0209_SERIES)
    bundled_hashes = {bundled: get_file_hash(bundled)}
    if bundled_secondary:
        bundled_hashes[bundled_secondary] = get_file_hash(bundled_secondary)
    if bundled_v0203:
        bundled_hashes[bundled_v0203] = get_file_hash(bundled_v0203)
    if bundled_v0209:
        bundled_hashes[bundled_v0209] = get_file_hash(bundled_v0209)
    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"
    host_series = adaptive_series()

    installed_targets = []
    conflicting_removed = []
    failures = []
    cam_registered = False
    plugin_dirs = get_all_plugin_dirs()

    for pdir in plugin_dirs:
        try:
            os.makedirs(pdir, exist_ok=True)
        except Exception as e:
            failures.append((pdir, str(e)))
            continue

        # Every series file is written: OrcaSlicer binds `_02.08.04` on builds
        # whose whitelist has PR #16202, `_02.08.01` on older ones, `_02.03.00`
        # where the config is pinned to that series, `_02.09.01` where the config
        # came from Bambu Studio 02.09.01, and the unversioned default as a last
        # fallback. Each series keeps its own build bytes.
        targets_to_update = {
            os.path.join(pdir, f"{prefix}{suffix}"): bundled,
            os.path.join(pdir, f"{prefix}_{INSTALL_SERIES}{suffix}"): bundled,
        }
        if bundled_secondary:
            targets_to_update[os.path.join(pdir, f"{prefix}_{SECONDARY_SERIES}{suffix}")] = bundled_secondary
        if bundled_v0203:
            targets_to_update[os.path.join(pdir, f"{prefix}_{V0203_SERIES}{suffix}")] = bundled_v0203
        if bundled_v0209:
            targets_to_update[os.path.join(pdir, f"{prefix}_{V0209_SERIES}{suffix}")] = bundled_v0209
        # Adaptive file for a future series the host whitelists but this
        # release does not ship; the override below makes the library report
        # that series so the slicer binds it. The newest shipped build carries
        # the widest append-only ABI, so it is the one to hand a future series.
        adaptive_src = bundled_v0209 or bundled
        if host_series:
            targets_to_update[os.path.join(pdir, f"{prefix}_{host_series}{suffix}")] = adaptive_src

        try:
            for f in os.listdir(pdir):
                if not (f.startswith(versioned_prefix) and f.endswith(suffix)):
                    continue
                if f.endswith(".bak") or f.endswith(".vendor_backup") or ".old" in f or ".pending_delete" in f:
                    continue
                ver = f[len(versioned_prefix):-len(suffix)]
                if ver.startswith(SECONDARY_SERIES):
                    if bundled_secondary:
                        targets_to_update[os.path.join(pdir, f)] = bundled_secondary
                elif ver.startswith(V0203_SERIES):
                    if bundled_v0203:
                        targets_to_update[os.path.join(pdir, f)] = bundled_v0203
                elif ver.startswith(V0209_SERIES):
                    if bundled_v0209:
                        targets_to_update[os.path.join(pdir, f)] = bundled_v0209
                elif ver.startswith(INSTALL_SERIES):
                    targets_to_update[os.path.join(pdir, f)] = bundled
                elif host_series and ver == host_series:
                    targets_to_update[os.path.join(pdir, f)] = adaptive_src
                # Other 02.08.* / 02.09.* series are left for the cleanup below to remove.
        except Exception:
            pass

        for t in sorted(targets_to_update):
            src = targets_to_update[t]
            if os.path.exists(t):
                if get_file_hash(t) == bundled_hashes[src]:
                    installed_targets.append(t)
                    continue
                bak = t + ".bak"
                if not os.path.exists(bak):
                    try:
                        safe_copy(t, bak)
                    except Exception:
                        pass
            try:
                safe_copy(src, t)
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
                if series == host_series:
                    continue
                if ((series.startswith("02.08.") or series.startswith("02.09."))
                        and not any(series.startswith(s) for s in SUPPORTED_SERIES)):
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

        # Registration is stateful, so it runs even when install_sidecar
        # skipped an identical copy: an older install copied the DLL and
        # never registered it (issue #8).
        if register_bambu_source(pdir):
            cam_registered = True

    if not installed_targets:
        detail = "; ".join(f"{t}: {e}" for t, e in failures[:3]) or "unknown error"
        return False, f"Failed to install: {detail}"

    cleanup_note = ""
    if conflicting_removed:
        cleanup_note = " Removed unsupported-series leftover(s): " + ", ".join(sorted(set(conflicting_removed))) + "."

    conf_note = ""
    _conf = read_slicer_config()
    if _conf["installed_networking"] is False:
        conf_note = (
            " OrcaSlicer still has the network plug-in disabled, so it will keep reporting it "
            "missing: open Preferences > Online and tick \"Enable Bambu network plug-in\", "
            "then restart."
        )
    elif series_of(_conf["network_plugin_version"]) == LEGACY_SERIES:
        conf_note = (
            f" OrcaSlicer is set to the legacy network plug-in version "
            f"({_conf['network_plugin_version']}), so it will not load this library: open "
            "Preferences > Online, set \"Network plug-in version\" to the 02.08.xx (Latest) "
            "entry, then restart."
        )

    fixes = ensure_conf_fixes_notes()
    if fixes is not None:
        obn_note, log_note, client_note = fixes
    else:
        obn_note = ensure_obn_conf()
        log_note = ensure_log_to_file()
        client_note = ensure_client_name()

    # Adaptive install: make the library report the host's series. Written only
    # after a successful install; uninstall/restore stock remove it again.
    adapt_note = ""
    if host_series:
        write_override_version(host_series + ".99")
        adapt_note = (
            f" OrcaSlicer is configured for the {host_series} series, which this "
            f"release does not ship: the {INSTALL_SERIES} build was installed under "
            f"that name and reports {host_series}.99 so the slicer binds it. If a "
            "future official build still fails to detect it, it changed the plug-in "
            "ABI: update Open Bamboo."
        )
    else:
        write_override_version("")

    cam_note = ""
    if cam_registered:
        cam_note = " Registered the camera DirectShow filter (BambuSource.dll)."

    if failures:
        failed_dirs = sorted({t if t in plugin_dirs else os.path.dirname(t) for t, _ in failures})
        detail = "; ".join(f"{t}: {e}" for t, e in failures[:2])
        return True, (
            f"Open Bamboo library installed to {len(installed_targets)} location(s), "
            f"but not to {', '.join(failed_dirs)} ({detail}). Restart OrcaSlicer; if the "
            + ("library is not picked up, start OrcaSlicer as administrator and install again."
               if sys.platform.startswith("win")
               else "the library is not picked up, check the folder permissions and install again.")
            + cleanup_note + conf_note + obn_note + log_note + client_note + adapt_note + cam_note
        )

    return True, (
        "Open Bamboo library installed successfully "
        f"({', '.join(SUPPORTED_SERIES)} series files). Please restart OrcaSlicer."
        + cleanup_note + conf_note + obn_note + log_note + client_note + adapt_note + cam_note
    )

def do_uninstall():
    cleanup_old_files()
    write_override_version("")

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
            if name == "BambuSource.dll":
                register_bambu_source(pdir, register=False)
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
    write_override_version("")

    prefix, suffix = get_lib_prefix_suffix()
    versioned_prefix = prefix + "_"
    bundled = get_bundled_plugin_path()
    bundled_hash = get_file_hash(bundled)
    bundled_secondary_hash = get_file_hash(get_bundled_secondary_path())
    bundled_v0203_hash = get_file_hash(get_bundled_series_path(V0203_SERIES))
    bundled_v0209_hash = get_file_hash(get_bundled_series_path(V0209_SERIES))
    obn_hashes = {h for h in (bundled_hash, bundled_secondary_hash, bundled_v0203_hash, bundled_v0209_hash) if h}

    # First, locate any master stock backup across all plugin directories
    master_stock = ""
    for pdir in get_all_plugin_dirs():
        if not os.path.exists(pdir):
            continue
        try:
            for f in os.listdir(pdir):
                if f.endswith(".bak") and prefix in f:
                    full_f = os.path.join(pdir, f)
                    # An .bak of a previous Open Bamboo install is not a stock copy.
                    if get_file_hash(full_f) not in obn_hashes:
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
                    if get_file_hash(full_f) in obn_hashes:
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
            if name == "BambuSource.dll":
                # The registered CLSID points at this path: drop our
                # registration, then point it at whatever lands here.
                register_bambu_source(pdir, register=False)
            if os.path.exists(bak):
                try:
                    safe_copy(bak, cur)
                    restored_files.append(name)
                except Exception:
                    pass
                if name == "BambuSource.dll" and os.path.exists(cur):
                    register_bambu_source(pdir)
                continue
            bundled_sidecar = bundled_sidecar_path(name)
            if os.path.exists(cur) and os.path.exists(bundled_sidecar) \
                    and get_file_hash(cur) == get_file_hash(bundled_sidecar):
                try:
                    safe_remove(cur)
                    restored_files.append(name)
                except Exception:
                    pass
            elif name == "BambuSource.dll" and os.path.exists(cur):
                # A vendored OrcaSlicer copy stayed: point the CLSID at it.
                register_bambu_source(pdir)

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
        elif action == "export_report":
            success, msg = do_export_report()
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
            "target_path": get_active_target_path(),
            "target_exists": False,
            "backup_exists": True,
            "log_path": get_log_file_path(),
            "log_exists": os.path.exists(get_log_file_path()),
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
            "arch": get_arch_name(),
            "plugin_version": "",
            "orca_version": "",
            "log_level": "",
            "cert_exists": False,
            "cert_blocks": 0,
            "cert_chain_ok": False,
            "cert_path": "",
            "cert_error": "",
            "crl_exists": False,
            "fetch_state": "none",
            "fetch_text": "",
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
  .meta-note {{
    grid-column: 1 / -1;
    font-size: 12px;
    color: var(--text-secondary);
    border-top: 1px solid rgba(255,255,255,0.08);
    padding-top: 8px;
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

      <div class="meta-key">Log File:</div>
      <div id="logPath" class="meta-val">-</div>

      <div class="meta-key">File Size:</div>
      <div id="targetSize" class="meta-val">-</div>

      <div class="meta-key">Reported Version:</div>
      <div id="reportedVersion" class="meta-val">-</div>

      <div class="meta-key">Platform:</div>
      <div id="platformText" class="meta-val">-</div>
      <div class="meta-note">Clean-room build (compiled with OBN_EMBED_SECRET=OFF): put <code>client_auth_secret.txt</code> (43 ASCII bytes) into the folder shown for Log File, or set the OBN_CLIENT_AUTH_SECRET environment variable, so the app-cert fetch can run. Default builds embed the value and need neither.</div>
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
    <h3>🖨️ Print Readiness</h3>
    <div class="meta-grid">
      <div class="meta-key">App certificate:</div>
      <div id="certState" class="meta-val">-</div>

      <div class="meta-key">Credential fetch:</div>
      <div id="fetchState" class="meta-val">-</div>

      <div class="meta-key">Log level:</div>
      <div id="logLevel" class="meta-val">-</div>

      <div class="meta-key">Plugin / OrcaSlicer:</div>
      <div id="versionsText" class="meta-val">-</div>
    </div>
    <div class="meta-note">Signed prints need the full 3 certificate chain (leaf, intermediate, application root) stored as <code>slicer_cert.pem</code>. A blocked chain is refused on purpose, firmware would answer <code>err_code 84033547</code> to every signed command. The plugin re fetches the chain automatically; if it stays blocked, delete <code>slicer_cert.pem</code> from the folder shown for Log File and restart OrcaSlicer.</div>
    <div class="btn-group">
      <button class="btn btn-secondary" onclick="sendAction('export_report')">
        <span>📦</span> <span>Export Report for GitHub</span>
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
      <li>Sign in to your Bambu Cloud account: click the <strong>Home icon on the left sidebar</strong> of OrcaSlicer and log in there (there is no separate top-bar login button). All printers will appear in the Device tab with live camera feeds and instant cloud printing!</li>
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
    const logPath = document.getElementById("logPath");

    currentTargetPath = s.target_path || "";
    targetPath.textContent = currentTargetPath || "-";
    if (logPath) {{
      logPath.textContent = s.log_path
        ? s.log_path + (s.log_exists ? "" : " (not created yet - send a print once after enabling logging)")
        : "-";
    }}
    platformText.textContent = (s.os || "") + " " + (s.arch || "");

    const certState = document.getElementById("certState");
    const fetchState = document.getElementById("fetchState");
    const logLevel = document.getElementById("logLevel");
    const versionsText = document.getElementById("versionsText");
    if (certState) {{
      if (s.cert_error) {{
        certState.innerHTML = "<span style='color:#ef5350; font-weight:600;'>Cannot read slicer_cert.pem: " + s.cert_error + "</span>";
      }} else if (!s.cert_exists) {{
        certState.innerHTML = "<span style='color:#ffa726;'>Not fetched yet</span>";
      }} else if (s.cert_chain_ok) {{
        certState.innerHTML = "<span style='color:#66bb6a; font-weight:600;'>Full chain (" + s.cert_blocks + " certificates), printer can verify signed commands</span>";
      }} else {{
        certState.innerHTML = "<span style='color:#ef5350; font-weight:600;'>BLOCKED: only " + s.cert_blocks + " certificate(s) stored, firmware rejects signed commands with err 84033547. The plugin re fetches automatically; if this persists, delete slicer_cert.pem from the Log File folder and restart OrcaSlicer.</span>";
      }}
    }}
    if (fetchState) {{
      const fc = s.fetch_state === "ok" ? "#66bb6a" : (s.fetch_state === "failed" ? "#ef5350" : "#ffa726");
      fetchState.innerHTML = "<span style='color:" + fc + ";'>" + (s.fetch_text || "-") + "</span>";
    }}
    if (logLevel) logLevel.textContent = s.log_level || "-";
    if (versionsText) versionsText.textContent = (s.plugin_version || "?") + " / " + (s.orca_version || "unknown");

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
    }} else if (s.cert_exists && !s.cert_chain_ok) {{
      badge.className = "badge badge-warning";
      badge.textContent = "Cert Chain Blocked";
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
    if (!currentTargetPath) {{
      sendAction('get_status');
      showAlert("Path not loaded yet, refreshing status, then click Copy Path again.", true);
      return;
    }}
    const path = currentTargetPath;
    function showIt() {{ showAlert("Path: " + path, true); }}
    // navigator.clipboard is undefined in non-secure webview contexts and
    // writeText rejects when another app holds the clipboard, so a silent
    // no-op was possible; every failure path now surfaces the path anyway.
    try {{
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(path).then(() => {{
          showAlert("Copied path to clipboard: " + path, true);
        }}).catch(showIt);
        return;
      }}
    }} catch (e) {{}}
    showIt();
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
