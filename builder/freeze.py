"""Freeze the private GUI; never uploads or creates a GitHub release."""
from pathlib import Path
import hashlib,json,subprocess,os
root=Path(__file__).resolve().parents[1]
out=root/'build'/os.environ.get('ROSA_PREVIEW_FOLDER','preview-0.1')
python=Path(os.environ.get('ROSA_FREEZE_PYTHON', 'C:/rosa_tools/builder-python-20261021/Scripts/python.exe'))
if not python.is_file():raise RuntimeError('Missing pinned Windows Python environment. Set ROSA_FREEZE_PYTHON to the correct python.exe.')
try:subprocess.run([str(python),'-c','import PyInstaller,zstandard,sdk'],cwd=root/'builder',check=True,capture_output=True,text=True)
except subprocess.CalledProcessError as exc:raise RuntimeError('Build Python must have PyInstaller and zstandard installed; no executable was built.') from exc
spec=root/'build/ROSA-Builder.spec'
release=json.loads((root/'builder/release.json').read_text(encoding='utf-8'))
data=out/'ROSA-Builder.data'
if not data.is_file() or hashlib.sha256(data.read_bytes()).hexdigest()!=release['data_sha256']:
    raise RuntimeError('New DATA is missing or mismatched: repackage and verify before freezing R8 EXE.')
spec.write_text('''import os
a = Analysis([APP], pathex=[BUILDER], binaries=[], datas=[(RELEASE, '.')],
             hiddenimports=['sdk','zstandard'], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[])
# Windows 10/11 provide their own API-set/UCRT system DLLs. Do not copy DLLs
# from this developer machine's Windows directory into a distribution.
windows_root = os.path.normcase(os.path.abspath(os.environ['WINDIR'])) + os.sep
a.binaries = [b for b in a.binaries if not os.path.normcase(os.path.abspath(b[1])).startswith(windows_root)
              and not b[0].lower().startswith('api-ms-') and b[0].lower() != 'ucrtbase.dll']
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='ROSA-Builder',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, uac_admin=False)
'''.replace('APP',repr(str(root/'builder/app.py'))).replace('BUILDER',repr(str(root/'builder'))).replace('RELEASE',repr(str(root/'builder/release.json'))))
subprocess.run([str(python),'-m','PyInstaller','--noconfirm','--clean',
               '--distpath',str(out),'--workpath',str(root/'build/pyinstaller'),str(spec)],check=True)
lines=[]
for name in ('ROSA-Builder.exe','ROSA-Builder.data'):
    with (out/name).open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    lines.append(digest+'  '+name)
(out/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
