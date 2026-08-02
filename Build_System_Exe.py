import os
import subprocess
import sys


def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(root_dir, "Assets")
    core_script = os.path.join(assets_dir, "Spiderpot_Core.py")
    wallpaper_path = os.path.join(assets_dir, "spider_noir.jpg")
    icon_path = os.path.join(assets_dir, "spider_noir_icon.ico")
    manifest_path = os.path.join(assets_dir, "Spiderpot.exe.manifest")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "pyinstaller",
            "opencv-python",
            "pynput",
            "pillow",
            "pystray",
            "screeninfo",
        ],
        check=True,
    )

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--workpath",
        os.path.join(root_dir, "_build_system"),
        "--onefile",
        "--noconsole",
        "--name",
        "Spiderpot_Sistem",
        f"--manifest={manifest_path}",
        "--add-data",
        f"{wallpaper_path};.",
    ]
    if os.path.isfile(icon_path):
        command.append(f"--icon={icon_path}")
    command.append(core_script)

    subprocess.run(command, check=True, cwd=root_dir)
    print(os.path.join(root_dir, "dist", "Spiderpot_Sistem.exe"))


if __name__ == "__main__":
    main()
