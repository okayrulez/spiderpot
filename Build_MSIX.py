import argparse
import html
import json
import os
import shutil
import subprocess
import sys

from PIL import Image


SDK_BIN = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64"


def xml_escape(value):
    return html.escape(str(value), quote=True)


def render_manifest(template, identity):
    replacements = {
        "IDENTITY_NAME": identity["identity_name"],
        "PUBLISHER": identity["publisher"],
        "VERSION": identity["version"],
        "ARCHITECTURE": identity["architecture"],
        "DISPLAY_NAME": identity["display_name"],
        "PUBLISHER_DISPLAY_NAME": identity["publisher_display_name"],
        "DESCRIPTION": identity["description"],
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", xml_escape(value))
    return template


def square_logo(source, destination, size):
    with Image.open(source) as image:
        image = image.convert("RGBA")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
        canvas.save(destination, "PNG")


def wide_logo(source, destination):
    width, height = 310, 150
    with Image.open(source) as image:
        image = image.convert("RGBA")
        image.thumbnail((130, 130), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (width, height), (16, 17, 20, 255))
        canvas.alpha_composite(image, ((width - image.width) // 2, (height - image.height) // 2))
        canvas.save(destination, "PNG")


def main():
    parser = argparse.ArgumentParser(description="Spiderpot MSIX paketini üretir.")
    parser.add_argument(
        "--allow-placeholder",
        action="store_true",
        help="Yalnızca yerel teknik test için geçici Store kimliğiyle paket üret.",
    )
    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.abspath(__file__))
    store_dir = os.path.join(root_dir, "Store")
    layout_dir = os.path.join(root_dir, "_msix_layout")
    dist_dir = os.path.join(root_dir, "dist")

    with open(os.path.join(store_dir, "store_identity.json"), encoding="utf-8") as identity_file:
        identity = json.load(identity_file)

    has_placeholder_identity = (
        "placeholder" in identity["identity_name"].lower()
        or identity["publisher"] == "CN=Spiderpot Development"
    )
    if has_placeholder_identity and not args.allow_placeholder:
        raise SystemExit(
            "Store/store_identity.json hâlâ geçici kimlik içeriyor. "
            "Partner Center Product identity değerlerini girin. Yalnızca yerel "
            "teknik ön paket için --allow-placeholder kullanabilirsiniz."
        )
    if has_placeholder_identity:
        print("UYARI: Geçici Store kimliğiyle yalnızca teknik ön paket üretiliyor.")

    subprocess.run(
        [sys.executable, os.path.join(root_dir, "Build_System_Exe.py")],
        check=True,
        cwd=root_dir,
    )
    subprocess.run(
        [sys.executable, os.path.join(root_dir, "Build_Settings_Exe.py")],
        check=True,
        cwd=root_dir,
    )

    if os.path.isdir(layout_dir):
        shutil.rmtree(layout_dir)
    assets_output = os.path.join(layout_dir, "Assets")
    os.makedirs(assets_output, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    shutil.copy2(
        os.path.join(dist_dir, "Spiderpot_Sistem.exe"),
        os.path.join(layout_dir, "Spiderpot_Sistem.exe"),
    )
    shutil.copy2(
        os.path.join(dist_dir, "Spiderpot_Ayarlar.exe"),
        os.path.join(layout_dir, "Spiderpot_Ayarlar.exe"),
    )

    icon_source = os.path.join(root_dir, "Assets", "spider_noir_icon.png")
    square_logo(icon_source, os.path.join(assets_output, "Square44x44Logo.png"), 44)
    square_logo(icon_source, os.path.join(assets_output, "Square150x150Logo.png"), 150)
    square_logo(icon_source, os.path.join(assets_output, "StoreLogo.png"), 50)
    wide_logo(icon_source, os.path.join(assets_output, "Wide310x150Logo.png"))

    with open(
        os.path.join(store_dir, "AppxManifest.template.xml"),
        encoding="utf-8",
    ) as template_file:
        manifest = render_manifest(template_file.read(), identity)
    with open(os.path.join(layout_dir, "AppxManifest.xml"), "w", encoding="utf-8") as manifest_file:
        manifest_file.write(manifest)

    package_name = (
        f"Spiderpot_{identity['version']}_{identity['architecture']}_unsigned.msix"
    )
    package_path = os.path.join(dist_dir, package_name)
    if os.path.isfile(package_path):
        os.remove(package_path)

    makeappx = os.path.join(SDK_BIN, "makeappx.exe")
    subprocess.run(
        [makeappx, "pack", "/d", layout_dir, "/p", package_path, "/o"],
        check=True,
        cwd=root_dir,
    )

    # MakeAppx validates the manifest and payload while packing. Unpacking the
    # completed file as a second check also catches a damaged package archive.
    verify_dir = os.path.join(root_dir, "_msix_verify")
    if os.path.isdir(verify_dir):
        shutil.rmtree(verify_dir)
    subprocess.run(
        [makeappx, "unpack", "/p", package_path, "/d", verify_dir, "/o"],
        check=True,
        cwd=root_dir,
    )
    expected_files = (
        "AppxManifest.xml",
        "Spiderpot_Sistem.exe",
        "Spiderpot_Ayarlar.exe",
    )
    missing_files = [
        name for name in expected_files if not os.path.isfile(os.path.join(verify_dir, name))
    ]
    if missing_files:
        raise RuntimeError("MSIX doğrulaması başarısız. Eksik: " + ", ".join(missing_files))
    shutil.rmtree(verify_dir)
    print(package_path)


if __name__ == "__main__":
    main()
