"""Offline build orchestration. Does not install to SD/NAND or upload inputs."""
from pathlib import Path, PurePosixPath
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib,json,os,re,shutil,struct,subprocess,time,zipfile
import compat_manifest

VERSION='0.1-preview'  # DATA compatibility version; stable B20 payload retained
UI_VERSION='0.2.1-preview-r9.1'
ROM_SHA='bd5b432f304edaf04f92fa853f5e52bd0345474e13983306c26c88cfc53f4136'
TITLE=0x000400000011C400
NRO='rosa-b20-mesa26.nro'
FLAGS=['-O2','-ffp-contract=off','-fno-math-errno','-w',
       '-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-fPIE']
HIDDEN={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}

class BuildError(Exception):pass

class CompatibilityError(BuildError):
    def __init__(self, support_code, message):
        super().__init__(message)
        self.support_code = support_code

def local_path(value):
    # Reject UNC syntax before Path normalization (also in cross-platform tests).
    if str(value).startswith(('\\\\','//')):raise BuildError('Choose a local disk path. Network shares are not supported.')
    p=Path(value).absolute()
    if str(p).startswith(('\\\\','//')):raise BuildError('Choose a local disk path. Network shares are not supported.')
    if os.name=='nt':
        import ctypes
        if ctypes.windll.kernel32.GetDriveTypeW(str(p.anchor))==4:
            raise BuildError('Mapped network drives are not supported. Game files must stay on local storage.')
    resolved=p.resolve()
    if str(resolved).startswith(('\\\\','//')):raise BuildError('Network redirection is not supported.')
    return resolved

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def _sha_range(stream, offset, size):
    """Stream a declared game range: never persist or export game bytes."""
    stream.seek(offset)
    hashed=hashlib.sha256()
    while size:
        chunk=stream.read(min(size,4*1024*1024))
        if not chunk:raise BuildError('Game partition ended unexpectedly.')
        hashed.update(chunk)
        size-=len(chunk)
    return hashed.hexdigest()

def inspect_rom(path, hash_partition=True, diagnostics=False):
    """Read explicit NCSD/NCCH/ExeFS boundaries; no hardcoded region inference."""
    path=local_path(path)
    if path.suffix.lower() not in ('.3ds','.cci'):raise BuildError('Select an unencrypted NCSD cartridge dump (.3ds or .cci). CIA installation packages and CXI executables are not supported.')
    size_total=path.stat().st_size if path.is_file() else 0
    if size_total<0x400:raise BuildError('The selected dump is missing or truncated.')
    with path.open('rb') as f:
        header=f.read(0x200)
        if header[0x100:0x104]!=b'NCSD':raise BuildError('The file is not the tested NCSD cartridge format.')
        offset=struct.unpack_from('<I',header,0x120)[0]*512
        part_size=struct.unpack_from('<I',header,0x124)[0]*512
        if offset<512 or offset+0x600>size_total:raise BuildError('Invalid cartridge partition bounds.')
        f.seek(offset);ncch=f.read(0x200)
        if ncch[0x100:0x104]!=b'NCCH':raise BuildError('Missing executable partition header.')
        if struct.unpack_from('<Q',ncch,0x118)[0]!=TITLE:raise BuildError('This is not the supported Omega Ruby title (000400000011C400).')
        if ncch[0x18F]&4==0:raise BuildError('The input is encrypted. No decryption or key handling is provided.')
        ncch_size=struct.unpack_from('<I',ncch,0x104)[0]*512
        if ncch_size<0x600 or ncch_size>4*1024**3 or offset+ncch_size>size_total or (part_size and ncch_size>part_size):
            raise BuildError('Invalid NCCH partition length; ROM may be truncated or unsupported.')
        exefs=struct.unpack_from('<I',ncch,0x1A0)[0]*512
        exefs_size=struct.unpack_from('<I',ncch,0x1A4)[0]*512
        if exefs<0x200 or exefs_size<0x200 or exefs+exefs_size>ncch_size:
            raise BuildError('The executable filesystem is truncated.')
        exheader_size=struct.unpack_from('<I',ncch,0x180)[0]
        if exheader_size<0x200 or exheader_size>0x800 or 0x200+exheader_size>ncch_size:
            raise BuildError('Unsupported or missing executable header.')
        if exefs<0x200+exheader_size:
            raise BuildError('Executable filesystem overlaps the executable header.')
        exheader_digest=_sha_range(f,offset+0x200,exheader_size)
        f.seek(offset+0x20e);remaster_version=struct.unpack('<H',f.read(2))[0]
        f.seek(offset+exefs);exe_header=f.read(0x200)
        if len(exe_header)!=0x200:raise BuildError('Executable filesystem header truncated.')
        code=[]
        for i in range(10):
            rec=exe_header[i*16:(i+1)*16]
            if rec[:8].split(b'\0',1)[0]==b'.code':
                pos, length=struct.unpack_from('<II',rec,8)
                if length==0 or pos+length>exefs_size-0x200:
                    raise BuildError('Invalid .code executable section bounds.')
                code.append((pos,length))
        if len(code)!=1:raise BuildError('No unique .code executable section in ExeFS.')
        code_pos,code_len=code[0]
        code_digest=_sha_range(f,offset+exefs+0x200+code_pos,code_len)
        ncch_digest=_sha_range(f,offset,ncch_size) if hash_partition else None
        profile = None
        if diagnostics:
            import rom_diagnostics
            f.seek(offset+0x200)
            ex_raw=f.read(exheader_size)
            noncode=[]
            occupied=[(code_pos,code_pos+code_len)]
            for i in range(10):
                rec=exe_header[i*16:(i+1)*16]
                if not rec[:8].strip(b'\0') or rec[:8].split(b'\0',1)[0]==b'.code':continue
                pos,length=struct.unpack_from('<II',rec,8)
                if pos+length>exefs_size-0x200 or any(pos<end and start<pos+length for start,end in occupied):
                    raise BuildError('Invalid or overlapping ExeFS resource bounds.')
                occupied.append((pos,pos+length))
                # Hash the record too: names/order/layout never leave the machine.
                noncode.append(hashlib.sha256(rec).hexdigest()+_sha_range(f,offset+exefs+0x200+pos,length))
            romfs,romfs_size=(struct.unpack_from('<I',ncch,p)[0]*512 for p in (0x1b0,0x1b4))
            if romfs_size and (romfs<0x200+exheader_size or romfs+romfs_size>ncch_size
                               or (romfs<exefs+exefs_size and exefs<romfs+romfs_size)):
                raise BuildError('Invalid or overlapping RomFS resource bounds.')
            profile={'exheader':rom_diagnostics.exheader_profile(ex_raw), 'resources':{
                'romfs_bytes':romfs_size,
                'romfs_sha256':_sha_range(f,offset+romfs,romfs_size) if romfs_size else None,
                'exefs_noncode_sha256':hashlib.sha256(''.join(noncode).encode('ascii')).hexdigest(),
                'exefs_header_sha256':hashlib.sha256(exe_header).hexdigest(),
                'ncch_header_sha256':hashlib.sha256(ncch).hexdigest()}}
    result={'title_id':f'{TITLE:016X}', 'ncch_sha256':ncch_digest,
            'code_sha256':code_digest,'exheader_sha256':exheader_digest,
            'code_bytes':code_len,'ncch_bytes':ncch_size,'remaster_version':remaster_version,'format':'NCSD','encryption':'unencrypted'}
    if profile is not None:result['diagnostic_profile']=profile
    return result

def classify_rom_identity(identity,digest,allow_code_equivalent=False):
    if digest==ROM_SHA:
        compatibility='exact-B20-reference'
    else:
        # Never accept an alternate ROM until a maintainer has locally
        # enrolled an *exact SHA-256-matching* reference input.
        expected_partition=compat_manifest.REFERENCE_NCCH_SHA256
        expected_code=compat_manifest.REFERENCE_CODE_SHA256
        expected_exheader=compat_manifest.REFERENCE_EXHEADER_SHA256
        if not all(re.fullmatch(r'[a-f0-9]{64}',x or '') for x in (expected_partition,expected_code,expected_exheader)):
            raise BuildError('Only the full-file B20 reference is currently enrolled. Maintainer must bind a verified reference before distributing this hotfix.')
        if identity['ncch_sha256']==expected_partition:
            compatibility='identical-game-partition'
        elif identity['code_sha256']==expected_code and identity['exheader_sha256']==expected_exheader:
            if not allow_code_equivalent:
                raise CompatibilityError('RESOURCES_NOT_VALIDATED', 'Game code and exheader match, but the partition differs; resource compatibility is unvalidated. Enable the experimental code-equivalent option only if you accept unvalidated resource compatibility.')
            compatibility='EXPERIMENTAL-code-equivalent-unvalidated-resources'
        else:
            if identity['code_sha256']==expected_code:
                raise CompatibilityError('EXHEADER_NOT_ENROLLED', 'Stored game code matches B20, but the exheader differs and is not enrolled. Memory layout, compression, execution settings and capabilities require review. Export the R9.1 diagnostic; compatibility is not demonstrated.')
            raise CompatibilityError('CODE_NOT_ENROLLED', 'Unsupported executable: stored game code differs from B20. This code revision is not enrolled. Export the diagnostic, never the ROM.')
    return compatibility


def validate_rom(path,allow_code_equivalent=False):
    path=local_path(path)
    identity=inspect_rom(path,hash_partition=False)
    digest=sha(path)
    if digest!=ROM_SHA:
        identity['ncch_sha256']=inspect_rom(path,hash_partition=True)['ncch_sha256']
    compatibility=classify_rom_identity(identity,digest,allow_code_equivalent)
    return {'sha256':digest,'bytes':path.stat().st_size,'title_id':identity['title_id'],
            'revision':compatibility,'game_code_sha256':identity['code_sha256']}

def check_tools(devkit,mesa):
    devkit=local_path(devkit);mesa=local_path(mesa)
    tools={name:devkit/sub for name,sub in {
        'cc':'devkitA64/bin/aarch64-none-elf-gcc.exe',
        'ar':'devkitA64/bin/aarch64-none-elf-ar.exe',
        'elf2nro':'tools/bin/elf2nro.exe','nacptool':'tools/bin/nacptool.exe'}.items()}
    for name,p in tools.items():
        if not p.is_file():raise BuildError(f'Missing {name}. Select an official devkitPro installation.')
    for p in [devkit/'libnx/lib/libnx.a',devkit/'libnx/switch.specs',
              mesa/'lib/libEGL.a',mesa/'lib/libglapi.a',mesa/'lib/libz.a']:
        if not p.is_file():raise BuildError('Missing SDK file: '+p.name+'. Enable automatic devkitPro and Mesa setup, or select the matching complete SDK roots.')
    return tools

def unpack_payload(data,dest,expected):
    data=local_path(data)
    if not re.fullmatch('[a-f0-9]{64}',expected) or sha(data)!=expected:raise BuildError('ROSA-Builder.data does not match this executable. Restore the matching official pair.')
    dest=Path(dest)
    if dest.exists():raise BuildError('Payload destination exists; preserved.')
    with zipfile.ZipFile(data) as z:
        infos=z.infolist();seen=set();total=0
        if len(infos)>10000:raise BuildError('Package contains too many entries.')
        for i in infos:
            p=PurePosixPath(i.filename)
            parts=p.parts
            if (not parts or p.is_absolute() or '\\' in i.filename or ':' in i.filename
                or '..' in parts or any(x.endswith((' ','.')) for x in parts)
                or any(re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?',x) for x in parts)
                or i.filename.casefold() in seen or i.is_dir()
                or (i.external_attr>>16)&0o170000==0o120000):raise BuildError('Unsafe package entry rejected.')
            seen.add(i.filename.casefold());total+=i.file_size
            if total>2*1024**3 or i.file_size>1024**3:raise BuildError('Package exceeds safety limits.')
        try:manifest=json.loads(z.read('manifest.json'))
        except (KeyError,ValueError):raise BuildError('Package manifest is missing or invalid.')
        if manifest.get('schema')!=1 or manifest.get('builder_version')!=VERSION:raise BuildError('Incompatible package version.')
        entries=manifest.get('files',{})
        if set(entries)!={i.filename for i in infos if i.filename!='manifest.json'}:raise BuildError('Package contents do not match its manifest.')
        dest.mkdir(parents=True)
        for i in infos:
            target=dest.joinpath(*PurePosixPath(i.filename).parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256();written=0
            with z.open(i) as src,target.open('xb') as out:
                while block:=src.read(1024*1024):out.write(block);h.update(block);written+=len(block)
            if i.filename!='manifest.json' and (entries[i.filename].get('bytes')!=written or entries[i.filename].get('sha256')!=h.hexdigest()):raise BuildError('Package file integrity failure.')
    return manifest

def redact(text,paths):
    for path,label in sorted(paths,key=lambda p:len(str(p[0])),reverse=True):
        for s in {str(path),str(path).replace('\\','/')}:
            text=re.sub(re.escape(s),lambda _:label,text,flags=re.I)
    return re.sub(r'(?i)(C:[\\/]Users[\\/])[^\\/\s"\']+',r'\1<user>',text)

def isolated_env(output,devkit):
    env=dict(os.environ)
    private=str(Path(output)/'private-cache')
    env.update(APPDATA=private,LOCALAPPDATA=private,XDG_CACHE_HOME=private,
               XDG_DATA_HOME=private,ZAKURO_CLEAN_RECOMPILE='1',DEVKITPRO=Path(devkit).as_posix())
    return env

def run(command,log,paths,env=None):
    result=subprocess.run([str(x) for x in command],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,**HIDDEN)
    text=result.stdout.decode('utf-8',errors='replace')
    with Path(log).open('a',encoding='utf-8') as out:out.write(redact(text,paths))
    if result.returncode:raise BuildError('A build tool failed. Open the technical log for details; your input and existing installation are unchanged.')
    return text

def build(rom,output,devkit,mesa,data,expected,emit=lambda **event:None,jobs=2,font=None,managed_sdk=False,allow_code_equivalent=False,mesa_mode="existing",mesa_archive=None):
    start=time.monotonic();output=local_path(output);rom=local_path(rom)
    if output.exists():raise BuildError('Choose a new empty output folder. Existing files will never be replaced.')
    if output==rom.parent or output in rom.parents:raise BuildError('Output must not contain the original input.')
    if output.parent.is_symlink():raise BuildError('Output parent must not be a symbolic link.')
    if not output.parent.exists():raise BuildError('Choose an existing parent folder for the output.')
    if shutil.disk_usage(output.parent).free<8*1024**3:raise BuildError('At least 8 GiB of free space is required.')
    if not 1<=jobs<=4:raise BuildError('Use 1 to 4 compiler jobs.')
    emit(stage='validate',message='Checking your personal dump',done=0,total=1)
    if not managed_sdk and not devkit:raise BuildError('Select an existing devkitPro SDK, or enable automatic devkitPro setup.')
    if mesa_mode=='existing' and not mesa:raise BuildError('Select the existing Mesa SDK root, or choose Auto setup Mesa SDK.')
    identity=validate_rom(rom,allow_code_equivalent=allow_code_equivalent)
    if mesa_mode=='existing':
        mesa=local_path(mesa)
        if not managed_sdk:
            devkit=local_path(devkit)
    output.mkdir();log=output/'build.log'
    payload=output/'payload';manifest=unpack_payload(data,payload,expected)
    if (payload/'mesa-sdk.json').is_file():
        import mesa_sdk
        mesa=mesa_sdk.setup(payload,mesa_mode,existing=mesa,archive=mesa_archive,emit=emit)
    elif mesa_mode!='existing':raise BuildError('This DATA does not contain automatic Mesa setup. Restore the matching R8.2 pair.')
    import sdk
    if managed_sdk:
        # Validate Mesa prior to downloading ~110 MB of SDK packages.
        sdk.verify_mesa_files(payload,mesa)
        # The pinned plan is authenticated by the DATA file SHA-256. A failure
        # retains the staging folder, and cannot touch installed devkitPro.
        devkit, _ = sdk.prepare(payload,output/'managed-sdk',emit,mesa_root=mesa)
        tools=check_tools(devkit,mesa)
    else:
        import sdk
        sdk.verify_sdk_files(payload,devkit,mesa)
        tools=check_tools(devkit,mesa)
    paths=[(rom,'<personal-dump>'),(output,'<workspace>'),(devkit,'<devkitPro>'),(mesa,'<Mesa-SDK>')]
    # Exact SDK bytes are part of compatibility, not merely a version label.
    # Verify again in managed mode after promoting the staged SDK.
    if managed_sdk:sdk.verify_sdk_files(payload,devkit,mesa)
    if font:
        font=local_path(font)
        if font.stat().st_size>16*1024**2:raise BuildError('Shared font exceeds the supported size.')
        with font.open('rb') as f:f.seek(0x80);magic=f.read(4)
        if magic not in (b'CFNT',b'CFNU'):raise BuildError('The selected shared font is not a supported CFNT dump.')
        paths.append((font,'<personal-font>'))
    env=isolated_env(output,devkit)
    emit(stage='generate',message='Generating ARM11-to-C code locally',done=0,total=1)
    code=output/'code'
    run([payload/'tools/rosa-codegen.exe',rom,code,payload/'overrides'],log,paths,env)
    sources=(code/'sources.txt').read_text().splitlines()
    if not sources:raise BuildError('No compilation units generated.')
    for name in sources:
        p=(code/name).resolve()
        if not p.is_relative_to(code) or p.suffix!='.c' or not p.is_file():raise BuildError('Invalid generated compilation manifest.')
    def compile_one(name):
        p=code/name
        run([tools['cc'],*FLAGS,'-I',code,'-c',p,'-o',p.with_suffix('.o')],log,paths)
        with p.with_suffix('.o').open('rb') as f:h=f.read(20)
        if h[:4]!=b'\x7fELF' or h[4:6]!=b'\x02\x01' or struct.unpack_from('<H',h,18)[0]!=183:raise BuildError('Compiler output is not a little-endian ARM64 object.')
        return p.with_suffix('.o')
    objects=[]
    emit(stage='compile',message='Compiling native ARM64 code',done=0,total=len(sources))
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        tasks=[pool.submit(compile_one,name) for name in sources]
        try:
            for task in as_completed(tasks):
                objects.append(task.result())
                emit(stage='compile',message='Compiling native ARM64 code',done=len(objects),total=len(sources))
        except Exception:
            for task in tasks:task.cancel()
            raise
    rsp=output/'archive.rsp'
    rsp.write_text('\n'.join('"'+str(x).replace('\\','/')+'"' for x in sorted(objects)))
    archive=code/'librecomp.a'
    run([tools['ar'],'rcs',archive,'@'+str(rsp)],log,paths)
    emit(stage='link',message='Linking B20 runtime and your local game code',done=0,total=1)
    elf=output/'rosa-b20.elf'
    run([tools['cc'],'-B'+str(Path(devkit)/'libnx'),'-specs=switch.specs',
         '-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-fPIE',
         '-Wl,-u,fcntl','-Wl,--wrap=pthread_key_create,--wrap=pthread_key_delete,--wrap=pthread_getspecific,--wrap=pthread_setspecific',
         '-Wl,--gc-sections','-o',elf,payload/'entry.c',
         '-L'+str(Path(devkit)/'libnx/lib'),'-L'+str(Path(mesa)/'lib'),
         '-Wl,--start-group',payload/'runtime/librosa_runtime.a',
         '-Wl,--whole-archive',archive,'-Wl,--no-whole-archive',
         '-lEGL','-lglapi','-lz','-lstdc++','-lnx','-lm','-lc','-lgcc','-Wl,--end-group'],log,paths,env)
    emit(stage='stage',message='Preparing a new SD folder; existing saves are untouched',done=0,total=1)
    sd=output/'sd.partial';rosa=sd/'switch/rosa';rosa.mkdir(parents=True)
    run([tools['elf2nro'],elf,rosa/NRO,'--nacp='+str(payload/'identity.nacp')],log,paths)
    if (rosa/NRO).stat().st_size<1024:raise BuildError('Unexpected NRO output size.')
    for p in (payload/'sd-template').rglob('*'):
        if p.is_file():
            dest=sd/p.relative_to(payload/'sd-template');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    emit(stage='copy',message='Copying your dump into the local SD output',done=0,total=identity['bytes'])
    target=rosa/'game.3ds';copied=0
    with rom.open('rb') as src,target.open('xb') as dest:
        while block:=src.read(8*1024**2):
            dest.write(block);copied+=len(block);emit(stage='copy',message='Copying personal game data',done=copied,total=identity['bytes'])
    if sha(target)!=identity['sha256']:raise BuildError('Game-data copy verification failed.')
    if font:
        dest=rosa/'data/sysdata/shared_font.bin';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(font,dest)
        if sha(dest)!=sha(font):raise BuildError('Font copy verification failed.')
    result={'builder':UI_VERSION,'runtime':'B20 static-runtime prototype','input':identity,
            'nro_sha256':sha(rosa/NRO),'native_archive_sha256':sha(archive),
            'seconds':time.monotonic()-start,'compilation_units':len(sources),
            'console_validated':False,'clean_windows_validated':False,
            'font_supplied':bool(font),'payload_sha256':expected}
    (output/'build-result.json').write_text(json.dumps(result,indent=2))
    sd.rename(output/'sd')
    emit(stage='complete',message='PC build complete. Console validation is still required.',done=1,total=1)
    return result
