"""Authenticated, isolated Mesa SDK setup; no system installation or game input."""
from pathlib import Path
import json, os, tempfile
import core

def aarch64_archive(path):
    data=Path(path).read_bytes()
    if not data.startswith(b'!<arch>\n'):raise core.BuildError('Mesa library is not a static ARM64 archive: '+Path(path).name)
    offset=8;objects=0
    while offset<len(data):
        header=data[offset:offset+60]
        try:size=int(header[48:58])
        except ValueError:raise core.BuildError('Invalid Mesa archive header.')
        body=data[offset+60:offset+60+size];name=header[:16].strip()
        if len(header)!=60 or header[58:60]!=b'`\n' or len(body)!=size:raise core.BuildError('Truncated Mesa archive.')
        if name not in (b'/',b'//',b'/SYM64/'):
            if body[:6]!=b'\x7fELF\x02\x01' or body[18:20]!=b'\xb7\x00':
                raise core.BuildError('Mesa archive contains a non-AArch64 object: '+Path(path).name)
            objects+=1
        offset+=60+size+(size%2)
    if not objects:raise core.BuildError('Mesa archive contains no ARM64 objects.')
    return objects

def plan(payload):
    return json.loads((Path(payload)/'mesa-sdk.json').read_text(encoding='utf-8'))

class SDKValidationError(core.BuildError):
    def __init__(self,diagnostic):
        self.diagnostic=diagnostic
        first=next(r for r in diagnostic['files'] if r['status']!='match')
        detail=first['name']+': '+first['status']
        if first.get('actual_sha256'):detail+='; expected SHA-256 '+first['expected_sha256']+'; found '+first['actual_sha256']
        else:detail+='; expected file size '+str(first['expected_bytes'])+' bytes'
        super().__init__('Mesa SDK check failed: '+detail+'. '+diagnostic['resolution_hint'])

def diagnose(root,spec,sdk_only=False):
    """Relative filenames, explicit hashes and architecture; no personal paths."""
    root=core.local_path(root);records=[]
    for name,record in spec['files'].items():
        if sdk_only and not name.startswith(('lib/','include/')):continue
        p=root/name
        row={'name':name,'expected_bytes':record['bytes'],'expected_sha256':record['sha256']}
        if not p.is_file():row['status']='missing'
        else:
            row.update(actual_bytes=p.stat().st_size,actual_sha256=core.sha(p))
            row['status']='match' if row['actual_bytes']==record['bytes'] and row['actual_sha256']==record['sha256'] else 'unrecognized_bytes'
            if name in ('lib/libEGL.a','lib/libglapi.a','lib/libz.a'):
                try:row['aarch64_objects']=aarch64_archive(p)
                except core.BuildError:row['status']='wrong_or_invalid_archive';row['architecture_valid']=False
        records.append(row)
    compatible=all(r['status']=='match' for r in records) and bool(records)
    has_lib=any((root/n).is_file() for n in ('lib/libEGL.a','lib/libglapi.a','lib/libz.a'))
    hint=('Use Automatic Mesa setup to install the authenticated bundled SDK; your current SDK will remain unchanged.' if has_lib else
          'Select the SDK root containing lib/ and include/, or use Automatic Mesa setup. A parent folder can also be selected.')
    return {'schema':1,'compatible':compatible,'files':records,'resolution_hint':hint,'supported_mesa':spec.get('mesa_version','26.2.4'),'target':spec.get('target','AArch64 Horizon static EGL/GLES')}

def resolve_existing(root,spec):
    """Allow common parent selections without relaxing any byte/architecture check."""
    root=core.local_path(root)
    candidates=[root,root/'opt/devkitpro/portlibs/switch',root/'devkitpro/portlibs/switch',root/'portlibs/switch',root/'switch']
    found=[p for p in candidates if (p/'lib/libEGL.a').is_file()]
    for candidate in found:
        report=diagnose(candidate,spec,sdk_only=True)
        if report['compatible']:return candidate
    raise SDKValidationError(diagnose(found[0] if found else root,spec,sdk_only=True))

def validate(root, spec, sdk_only=False):
    root=core.local_path(root)
    report=diagnose(root,spec,sdk_only)
    if not report['compatible']:raise SDKValidationError(report)
    return root

def cache_root(spec):
    base=os.environ.get('LOCALAPPDATA') or str(Path.home()/'.cache')
    return core.local_path(Path(base)/'ROSA-Builder'/'mesa'/spec['sha256'])

def setup(payload, mode='auto', existing=None, archive=None, emit=lambda **e:None, cache=None):
    payload=Path(payload);spec=plan(payload)
    if mode=='existing':
        if not existing:raise core.BuildError('Select an existing Mesa SDK root, or choose Auto setup Mesa SDK.')
        emit(stage='sdk',message='Verifying existing Mesa SDK')
        return resolve_existing(existing,spec)
    if mode not in ('auto','import'):raise core.BuildError('Unknown Mesa SDK mode.')
    selected=core.local_path(archive) if mode=='import' and archive else payload/'sdk/mesa-switch.zip'
    if mode=='import' and not archive:raise core.BuildError('Select the matching ROSA Mesa SDK ZIP archive.')
    # An explicit import must still be authenticated when a valid cache exists.
    if mode=='import' or not (Path(cache) if cache else cache_root(spec)).exists():
        if not selected.is_file() or core.sha(selected)!=spec['sha256']:
            raise core.BuildError('Mesa SDK archive SHA-256 mismatch or archive missing. Restore the matching EXE/DATA pair or import its exact SDK ZIP.')
    dest=core.local_path(cache) if cache else cache_root(spec)
    if dest.exists():
        try:
            result=validate(dest,spec)
            emit(stage='sdk',message='Reusing verified Mesa SDK')
            return result
        except SDKValidationError:
            if cache is not None:raise
            # Preserve a damaged managed cache; prepare a fresh authenticated
            # sibling instead. Never repair the user's manual/system SDK.
            dest=dest.with_name(dest.name+'-recovered-r9')
            emit(stage='sdk',message='Existing managed Mesa cache failed verification; preserving it and using a separate verified recovery cache.')
            if dest.exists():return validate(dest,spec)
    dest.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='mesa-partial-',dir=dest.parent))
    staged=temporary/'sdk'
    emit(stage='sdk',message='Preparing bundled Mesa Switch 26.2.4 SDK')
    core.unpack_payload(selected,staged,spec['sha256'])
    validate(staged,spec)
    try:staged.rename(dest)
    except FileExistsError:return validate(dest,spec)
    emit(stage='sdk',message='Mesa SDK prepared and verified')
    return dest
