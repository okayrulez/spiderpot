import os
import subprocess
import sys


def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(root_dir, "Assets")
    icon_path = os.path.join(assets_dir, "spider_noir_icon.ico")
    manifest_path = os.path.join(assets_dir, "Spiderpot.exe.manifest")
    payload_path = os.path.join(root_dir, "dist", "Spiderpot_Sistem.exe")

    subprocess.run(
        [sys.executable, os.path.join(root_dir, "Build_System_Exe.py")],
        check=True,
        cwd=root_dir,
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "pyinstaller",
            "pillow",
        ],
        check=True,
    )

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--workpath",
        os.path.join(root_dir, "_build_setup"),
        "--onefile",
        "--noconsole",
        "--name",
        "Spiderpot_Setup",
        f"--manifest={manifest_path}",
        "--add-data",
        f"{assets_dir};Assets",
        "--add-data",
        f"{payload_path};Payload",
    ]
    if os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")
    cmd.append(os.path.join(root_dir, "Spiderpot_Kurulum.py"))

    subprocess.run(cmd, check=True, cwd=root_dir)
    print(os.path.join(root_dir, "dist", "Spiderpot_Setup.exe"))


if __name__ == "__main__":
    main()
