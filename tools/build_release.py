"""Build the offline Windows app and validated unsigned MSIX using official SDK tools."""
import argparse
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from spiderpot_upgrade import VERSION
WORK = ROOT.parent / 'build'
OUTPUT = ROOT.parent / 'outputs'
SDK_VERSION = '10.0.28000.2705'


def sdk_tools():
    folder = WORK / 'sdk'
    matches = list(folder.glob('**/x64/makeappx.exe'))
    if not matches:
        WORK.mkdir(parents=True,exist_ok=True)
        archive = WORK / 'windows-sdk-buildtools.nupkg'
        if not archive.exists():
            url = f'https://api.nuget.org/v3-flatcontainer/microsoft.windows.sdk.buildtools/{SDK_VERSION}/microsoft.windows.sdk.buildtools.{SDK_VERSION}.nupkg'
            urllib.request.urlretrieve(url, archive)
        with zipfile.ZipFile(archive) as package:
            package.extractall(folder)
        matches = list(folder.glob('**/x64/makeappx.exe'))
    if not matches:
        raise RuntimeError('Official SDK MakeAppx not found')
    return matches[0]


def licenses(destination):
    destination.mkdir(parents=True,exist_ok=True)
    summaries=[]
    for name in ('Pillow','numpy','opencv-python-headless','pynput','pystray','screeninfo','six','psutil','winrt-runtime','winrt-Windows.Foundation','winrt-Windows.ApplicationModel','typing_extensions','cryptography','cffi','pycparser','qrcode','colorama','miniupnpc'):
        dist=metadata.distribution(name)
        summaries.append(f'{name} {dist.version}\n{dist.metadata.get("Home-page", "")}\nLicense: {dist.metadata.get("License-Expression",dist.metadata.get("License","See bundled license"))}\n')
        for file in dist.files or []:
            if any(part.lower().startswith(('license','copying','notice')) for part in file.parts):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    relative=Path(name)/Path(*file.parts[1:])
                    target=destination/relative
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,target)
    (destination/'INDEX.txt').write_text('\n'.join(summaries),encoding='utf-8')


def manifest(identity):
    def x(key): return escape(identity[key], {'"':'&quot;'})
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
 xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
 xmlns:desktop="http://schemas.microsoft.com/appx/manifest/desktop/windows10"
 xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
 IgnorableNamespaces="uap desktop rescap">
 <Identity Name="{x('name')}" Publisher="{x('publisher')}" Version="{VERSION}.0" ProcessorArchitecture="x64"/>
 <Properties><DisplayName>Spiderpot</DisplayName><PublisherDisplayName>{x('publisher_display_name')}</PublisherDisplayName><Logo>images\\StoreLogo.png</Logo></Properties>
 <Resources><Resource Language="tr-TR"/></Resources>
 <Dependencies><TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.28000.0"/></Dependencies>
 <Applications><Application Id="Spiderpot" Executable="app\\Spiderpot.exe" EntryPoint="Windows.FullTrustApplication">
  <uap:VisualElements DisplayName="Spiderpot" Description="Masaüstü görünüm modları ve isteğe bağlı yerel fotoğraf kaydı" BackgroundColor="transparent" Square150x150Logo="images\\Square150x150Logo.png" Square44x44Logo="images\\Square44x44Logo.png"/>
  <Extensions><desktop:Extension Category="windows.startupTask" Executable="app\\Spiderpot.exe" EntryPoint="Windows.FullTrustApplication"><desktop:StartupTask TaskId="SpiderpotStartup" Enabled="false" DisplayName="Spiderpot"/></desktop:Extension></Extensions>
 </Application></Applications>
 <Capabilities><rescap:Capability Name="runFullTrust"/><DeviceCapability Name="webcam"/></Capabilities>
</Package>'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--identity', type=Path)
    parser.add_argument('--mail-url', help='Public HTTPS URL for the optional email service')
    parser.add_argument('--skip-exe',action='store_true')
    args=parser.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    WORK.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,str(ROOT/'tools/build_assets.py')],cwd=ROOT,check=True)
    if not args.skip_exe:
        cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--noconsole','--name','Spiderpot',
             '--distpath',str(WORK/'dist'),'--workpath',str(WORK/'pyinstaller'),'--specpath',str(WORK),
             '--icon',str(ROOT/'Assets/spiderpot.ico'),
             '--collect-submodules','pynput.keyboard','--collect-submodules','pynput.mouse',
             '--collect-submodules','winrt','--hidden-import','pystray._win32']
        for source,dest in [('Assets/spiderpot.ico','Assets'),('Assets/spiderpot-logo.png','Assets'),
                            ('Assets/spider_noir.jpg','Assets'),
                            ('Assets/spiderpot-wallpaper.jpg','Assets'),('store/privacy-tr.txt','store')]:
            cmd.extend(['--add-data',str(ROOT/source)+';'+dest])
        if args.mail_url:
            from spiderpot_mail import MailClient
            client = MailClient(args.mail_url)
            if not client.url.startswith('https://'):
                parser.error('--mail-url must use HTTPS')
            url_file = WORK / 'mail-url.txt'
            url_file.write_text(client.url, encoding='utf-8')
            cmd.extend(['--add-data', str(url_file) + ';store'])
        cmd.append(str(ROOT/'Spiderpot.py'))
        with (WORK/'pyinstaller.log').open('w',encoding='utf-8') as log:
            subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    app=WORK/'dist/Spiderpot'
    licenses(app/'_internal/store/third-party')
    shutil.copy2(sys.base_prefix+'/LICENSE.txt',app/'_internal/store/third-party/Python-LICENSE.txt')
    portable=OUTPUT/f'Spiderpot-{VERSION}-x64-Portable.zip'
    with zipfile.ZipFile(portable,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in app.rglob('*'):
            if file.is_file(): archive.write(file,'Spiderpot/'+str(file.relative_to(app)))
    identity=json.loads(args.identity.read_text(encoding='utf-8-sig')) if args.identity else {
        'name':'OkayDedeoglu.Spiderpot.Dev','publisher':'CN=Spiderpot Development','publisher_display_name':'Okay Dedeoğlu'}
    stage=WORK/('stage-store' if args.identity else 'stage-development')
    shutil.copytree(app,stage/'app',dirs_exist_ok=True)
    shutil.copytree(ROOT/'store/images',stage/'images',dirs_exist_ok=True)
    (stage/'AppxManifest.xml').write_text(manifest(identity),encoding='utf-8')
    package=OUTPUT/(f'Spiderpot-{VERSION}-x64-Store.msix' if args.identity else f'Spiderpot-{VERSION}-x64-Development.msix')
    tool=sdk_tools()
    with (WORK/'makeappx.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(tool),'pack','/d',str(stage),'/p',str(package),'/o'],stdout=log,stderr=subprocess.STDOUT,check=True)
    # The installer carries the identical offline app ZIP and upgrades all known names.
    installer_work=WORK/'installer'
    installer_work.mkdir(exist_ok=True)
    shutil.copy2(portable,installer_work/'payload.zip')
    setup_name=f'Spiderpot-{VERSION}-Setup'
    setup_cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--noconsole',
               '--name',setup_name,'--distpath',str(OUTPUT),'--workpath',str(installer_work/'build'),
               '--specpath',str(installer_work),'--paths',str(ROOT),
               '--icon',str(ROOT/'Assets/spiderpot.ico'),
               '--add-data',str(installer_work/'payload.zip')+';.',str(ROOT/'tools/installer_entry.py')]
    with (WORK/'installer-build.log').open('w',encoding='utf-8') as log:
        subprocess.run(setup_cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    summary={'version':VERSION,'identity':identity,'store_identity_confirmed':bool(args.identity),
             'portable':str(portable),'installer':str(OUTPUT/(setup_name+'.exe')),'msix':str(package),'signed':False,
             'note':'Development identity must never be submitted as the reserved Store product.'}
    (OUTPUT/'Spiderpot-build.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__': main()
