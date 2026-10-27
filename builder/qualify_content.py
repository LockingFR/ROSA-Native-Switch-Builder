"""Independent recursive qualification; never grants owner publication approval."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,io,json,lzma,re,tarfile,zipfile,os,getpass
from PyInstaller.archive.readers import CArchiveReader

def digest(b):return hashlib.sha256(b).hexdigest()
def safe(name):
    p=PurePosixPath(name)
    return not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name

def inspect(folder,output):
    report={'technical_checks_passed':False,'distribution_approved':False,
            'approval_reason':'Owner publication approval is separate and never inferred by this script.',
            'issues':[],'entries':[],'review_findings':[]}
    def check(name,b,scope):
        # PyInstaller stores native Windows paths; ZIP/TAR paths stay strict.
        if scope=='EXE':name=name.replace('\\','/')
        report['entries'].append({'path':name,'scope':scope,'bytes':len(b),'sha256':digest(b)})
        if not safe(name):report['issues'].append('Unsafe entry: '+name)
        markers=[getpass.getuser(),*os.environ.get('ROSA_AUDIT_PRIVATE_MARKERS','').split(';')]
        if any(marker and marker.lower().encode('utf-8') in b.lower() for marker in markers):report['issues'].append('Personal identity: '+name)
        if (b'-----BEGIN '+b'PRIVATE KEY-----') in b or (b'-----BEGIN '+b'RSA PRIVATE KEY-----') in b:report['review_findings'].append('PEM private-key marker: '+name)
        if len(b)>0x104 and b[0x100:0x104] in (b'NCSD',b'NCCH'):report['issues'].append('Game container signature: '+name)
        parts=PurePosixPath(name).parts
        if any(x in ('savedata','save-backup','private-cache') for x in parts):report['issues'].append('Private data path: '+name)
        if PurePosixPath(name).suffix.lower() in ('.3ds','.cia','.cxi','.nsp','.nca','.nro','.keys'):
            report['review_findings'].append('Game-sensitive extension: '+name)
    def zip_members(raw,label):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=z.namelist()
            if len({n.casefold() for n in names})!=len(names):report['issues'].append('Duplicate ZIP entries: '+label)
            if z.testzip():report['issues'].append('ZIP CRC failure: '+label)
            files={n:z.read(n) for n in names}
        for n,b in files.items():check(label+'/'+n,b,label)
        if 'manifest.json' in files:
            m=json.loads(files['manifest.json'])
            if set(files)-{'manifest.json'}!=set(m['files']):report['issues'].append('Manifest set mismatch: '+label)
            for n,r in m['files'].items():
                if n not in files or r!={'bytes':len(files[n]),'sha256':digest(files[n])}:report['issues'].append('Manifest digest mismatch: '+label+'/'+n)
        return files
    data=(folder/'ROSA-Builder.data').read_bytes()
    payload=zip_members(data,'DATA')
    mesa=zip_members(payload['sdk/mesa-switch.zip'],'Mesa')
    with tarfile.open(fileobj=io.BytesIO(mesa['sources/mesa-source.tar.xz']),mode='r:xz') as t:
        seen=set();links=[]
        for m in t:
            if not safe(m.name) or m.name.casefold() in seen:report['issues'].append('Unsafe/duplicate source tar entry: '+m.name)
            seen.add(m.name.casefold())
            if m.isfile():
                with t.extractfile(m) as f:check('MesaSource/'+m.name,f.read(),'MesaSource')
            elif m.issym() or m.islnk():links.append({'path':m.name,'target':m.linkname})
            elif not m.isdir():report['issues'].append('Source tar special entry: '+m.name)
        report['source_tar_links']=links
    exe=CArchiveReader(str(folder/'ROSA-Builder.exe'))
    for name,info in exe.toc.items():
        # PYZ is additionally traversed via its own reader; .pyc modules contain
        # standard library code, not an opaque exception to the inventory.
        try:b=exe.extract(name)
        except Exception as e:report['issues'].append('Unreadable frozen entry: '+name);continue
        check('EXE/'+name,b,'EXE')
        if name.endswith('.zip'):zip_members(b,'EXE/'+name)
        if info[-1]=='z':
            pyz=exe.open_embedded_archive(name)
            for module in pyz.toc:
                b=pyz.extract(module,raw=True);check('PYZ/'+module,b,'PYZ')
    embedded=json.loads(exe.extract('release.json'))
    if digest(data)!=embedded['data_sha256']:report['issues'].append('EXE/DATA binding mismatch')
    report['technical_checks_passed']=not report['issues'] and not report['review_findings']
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('entries','source_tar_links')}))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    try:r=inspect(a.folder,a.output)
    except Exception as error:
        r={'technical_checks_passed':False,'distribution_approved':False,
           'issues':['Inspection did not complete: '+type(error).__name__],
           'review_findings':[]}
        a.output.write_text(json.dumps(r,indent=2),encoding='utf-8')
        print(json.dumps(r))
    raise SystemExit(bool(r['issues'] or r['review_findings']))
