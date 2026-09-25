import os
import zipfile
import hashlib
import base64

VERSION = "0.2.13"
DIST_INFO = f"open_bambu_networking-{VERSION}.dist-info"

METADATA_CONTENT = f"""Metadata-Version: 2.1
Name: open_bambu_networking
Version: {VERSION}
Summary: Open source networking plugin for Bambu Lab printers. Enables cloud printing without developer mode, remote camera liveview over the internet, and instant AMS slot synchronization.
Author: persano
Requires-Python: >=3.12
"""

WHEEL_CONTENT = """Wheel-Version: 1.0
Generator: custom
Root-Is-Purelib: true
Tag: py3-none-any
"""

TOP_LEVEL_CONTENT = "open_bambu_networking\n"

def build_wheel(whl_filename, platform_files):
    """
    whl_filename: output .whl path
    platform_files: dict of {source_path_on_disk: target_path_in_wheel}
    """
    files = {}

    # Common files
    with open("open_bambu_networking.py", "rb") as f:
        code_data = f.read()
    files["open_bambu_networking/__init__.py"] = code_data
    files["open_bambu_networking/open_bambu_networking.py"] = code_data

    if os.path.exists("icon.png"):
        with open("icon.png", "rb") as f:
            files["open_bambu_networking/icon.png"] = f.read()

    if os.path.exists("CHANGELOG.md"):
        with open("CHANGELOG.md", "rb") as f:
            files["open_bambu_networking/CHANGELOG.md"] = f.read()

    if os.path.exists(".install_state.json"):
        with open(".install_state.json", "rb") as f:
            files["open_bambu_networking/.install_state.json"] = f.read()

    # Platform specific binaries
    for src, dst in platform_files.items():
        with open(src, "rb") as f:
            files[dst] = f.read()

    # Dist-info metadata
    files[f"{DIST_INFO}/METADATA"] = METADATA_CONTENT.encode("utf-8")
    files[f"{DIST_INFO}/WHEEL"] = WHEEL_CONTENT.encode("utf-8")
    files[f"{DIST_INFO}/top_level.txt"] = TOP_LEVEL_CONTENT.encode("utf-8")

    # Build RFC 376 / PEP 427 RECORD with sha256 hashes and byte lengths
    record_lines = []
    for arcname, data in files.items():
        digest = hashlib.sha256(data).digest()
        b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        record_lines.append(f"{arcname},sha256={b64},{len(data)}")
    
    # RECORD itself is recorded without hash and length per PEP 376
    record_lines.append(f"{DIST_INFO}/RECORD,,")
    record_bytes = ("\n".join(record_lines) + "\n").encode("utf-8")
    files[f"{DIST_INFO}/RECORD"] = record_bytes

    # Create zip file
    with zipfile.ZipFile(whl_filename, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for arcname, data in files.items():
            z.writestr(arcname, data)

    print(f"Built {whl_filename}: {os.path.getsize(whl_filename):,} bytes (RECORD entries: {len(record_lines)})")

def build_zip():
    zip_filename = "open_bambu_networking_plugin.zip"
    with zipfile.ZipFile(zip_filename, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write("open_bambu_networking.py", "open_bambu_networking.py")
        if os.path.exists("icon.png"):
            z.write("icon.png", "icon.png")
        if os.path.exists(".install_state.json"):
            z.write(".install_state.json", ".install_state.json")
        if os.path.exists("CHANGELOG.md"):
            z.write("CHANGELOG.md", "CHANGELOG.md")
        if os.path.exists("README.md"):
            z.write("README.md", "README.md")
        if os.path.exists("LICENSE"):
            z.write("LICENSE", "LICENSE")

        # Binaries
        for root, _, filenames in os.walk("bin"):
            for fn in filenames:
                full_path = os.path.join(root, fn)
                z.write(full_path, full_path.replace("\\", "/"))

    print(f"Built {zip_filename}: {os.path.getsize(zip_filename):,} bytes")

if __name__ == "__main__":
    # 1. Windows x86_64
    build_wheel(
        "open_bambu_networking_win_x86_64.whl",
        {"bin/win_x64/bambu_networking.dll": "open_bambu_networking/bin/win_x64/bambu_networking.dll"}
    )

    # 2. Linux x86_64
    build_wheel(
        "open_bambu_networking_linux_x86_64.whl",
        {"bin/linux_x64/libbambu_networking.so": "open_bambu_networking/bin/linux_x64/libbambu_networking.so"}
    )

    # 3. macOS arm64
    macos_files = {}
    for fn in os.listdir("bin/macos_arm64"):
        macos_files[f"bin/macos_arm64/{fn}"] = f"open_bambu_networking/bin/macos_arm64/{fn}"
    build_wheel("open_bambu_networking_macosx_arm64.whl", macos_files)

    # 4. Zip for manual installation
    build_zip()
