import os
import subprocess
import sys


def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(root_dir, "Assets")
    icon_path = os.path.join(assets_dir, "spider_noir_icon.ico")
    wallpaper_path = os.path.join(assets_dir, "spider_noir.jpg")
    manifest_path = os.path.join(assets_dir, "Spiderpot.exe.manifest")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "pyinstaller",
            "pillow",
            "opencv-python",
        ],
        check=True,
    )

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--workpath",
        os.path.join(root_dir, "_build_settings"),
        "--onefile",
        "--noconsole",
        "--name",
        "Spiderpot_Ayarlar",
        f"--manifest={manifest_path}",
        "--add-data",
        f"{wallpaper_path};Assets",
    ]
    if os.path.isfile(icon_path):
        command.append(f"--icon={icon_path}")
    command.append(os.path.join(root_dir, "Spiderpot_Ayarlar.py"))

    subprocess.run(command, check=True, cwd=root_dir)
    print(os.path.join(root_dir, "dist", "Spiderpot_Ayarlar.exe"))


if __name__ == "__main__":
    main()
