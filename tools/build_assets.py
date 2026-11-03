"""Generate Spiderpot's code-defined red circular mark; no third-party imagery."""
from pathlib import Path
import math
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from spiderpot_support import circular_icon


def main():
    assets = ROOT / 'Assets'
    logo = circular_icon(1024)
    logo.save(assets / 'spiderpot-logo.png')
    logo.save(assets / 'spiderpot.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    logo.save(ROOT / 'app_icon.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    circular_icon(256, active=True).save(assets / 'spiderpot-active.png')
    # Same silhouette is used by the EXE, configuration wizard, Store and tray.
    store = ROOT / 'store' / 'images'
    store.mkdir(parents=True, exist_ok=True)
    for name, size in [('Square44x44Logo',44),('Square150x150Logo',150),('StoreLogo',50),('StoreTile',300)]:
        circular_icon(size).save(store / (name+'.png'))
    width, height = 1920, 1080
    wallpaper = Image.new('RGB', (width,height), '#10151d')
    draw = ImageDraw.Draw(wallpaper)
    for radius in range(900, 70, -80):
        draw.ellipse((width/2-radius,height/2-radius,width/2+radius,height/2+radius), outline='#242a35',width=2)
    for spoke in range(16):
        angle=spoke*math.tau/16
        draw.line((width/2,height/2,width/2+math.cos(angle)*1200,height/2+math.sin(angle)*1200),fill='#242a35',width=2)
    badge=circular_icon(330)
    wallpaper.paste(badge,((width-330)//2,(height-330)//2),badge)
    wallpaper.save(assets / 'spiderpot-wallpaper.jpg',quality=95)
    print('Generated original circular icon, multi-size ICO, Store logos and wallpaper.')


if __name__ == '__main__':
    main()
