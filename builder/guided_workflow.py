"""Guided local workflow: authenticated dependency discovery and safe diagnostics.

No raw logs, paths, file names, game bytes, keys or saves enter exported reports.
Discovery never installs globally and never weakens core ROM/SDK validation.
"""
from pathlib import Path, PurePosixPath
import json, os, platform, re, shutil, zipfile, tempfile, sys
import core,compat_manifest,rom_diagnostics

REPORT_SCHEMA=2

def explain(error):
    if isinstance(error,core.CompatibilityError):return str(error)
    if hasattr(error,'diagnostic'):return str(error)
    text=str(error)
    if 'encrypt' in text.lower():return 'Encrypted dump: create your own unencrypted cartridge dump first. The Builder cannot decrypt it or accept keys.'
    if 'revision' in text.lower() or 'executable' in text.lower():return 'This executable is not enrolled for B20. Export the diagnostic hashes; changing the filename or bypassing checks will not make it compatible.'
    if 'Input changed' in text:return 'The input changed while being checked. Close tools writing to it and diagnose the original local file again.'
    if 'SDK' in text or 'devkitPro' in text:return 'Dependency check failed. Keep Automatic setup enabled, or select the exact matching SDK in Advanced settings.'
    if 'Payload' in text or 'DATA' in text or 'integrity' in text.lower():return 'The EXE/DATA pair is missing, modified or mismatched. Restore both files from the same verified download.'
    if 'space' in text.lower():return 'Choose a local drive with at least 8 GiB free.'
    if 'format' in text.lower() or 'CIA' in text:return 'Use your own unencrypted NCSD cartridge dump (.3ds or .cci). CIA and standalone CXI inputs are not supported.'
    return 'The operation stopped safely. Your original game and existing installations were not changed. Export a diagnostic report for support.'

def rom_report(path,allow_code_equivalent=False):
    result={'format':'unknown','encryption':'unknown','status':'unsupported','build_allowed':False}
    try:
        path=core.local_path(path)
        with path.open('rb') as stream:header=stream.read(0x200)
        if header[0x100:0x104]==b'NCSD':result['format']='NCSD'
        elif header[0x100:0x104]==b'NCCH':result['format']='NCCH/CXI'
        elif path.suffix.lower()=='.cia':result['format']='CIA (extension; build unsupported)'
        before=path.stat()
        details=core.inspect_rom(path,hash_partition=True,diagnostics=True)
        digest=core.sha(path)
        after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise core.BuildError('Input changed during inspection.')
        result.update({k:details[k] for k in ('format','encryption','title_id','ncch_sha256','code_sha256','exheader_sha256','code_bytes','remaster_version')})
        result.update(sha256=digest,bytes=after.st_size,input_stable=True)
        result['reference_matches']={'full_file':digest==core.ROM_SHA,'game_partition':details['ncch_sha256']==compat_manifest.REFERENCE_NCCH_SHA256,'executable':details['code_sha256']==compat_manifest.REFERENCE_CODE_SHA256,'exheader':details['exheader_sha256']==compat_manifest.REFERENCE_EXHEADER_SHA256}
        result['reference_hashes']={'full_file':core.ROM_SHA,'game_partition':compat_manifest.REFERENCE_NCCH_SHA256,'executable':compat_manifest.REFERENCE_CODE_SHA256,'exheader':compat_manifest.REFERENCE_EXHEADER_SHA256}
        result['diagnostic_profile']=details['diagnostic_profile']
        result['diagnostic_comparison']=rom_diagnostics.compare(details['diagnostic_profile'],getattr(compat_manifest,'REFERENCE_DIAGNOSTICS',None))
        verdict=core.classify_rom_identity(details,digest,allow_code_equivalent)
        result.update(status=verdict,build_allowed=True)
        result['message']='Compatible input verified. Game data remains local.'
    except (core.BuildError,OSError,ValueError) as error:
        if 'encrypted' in str(error).lower():result['encryption']='encrypted'
        result['message']=explain(error)
        # Export fixed support codes, never arbitrary exception text containing paths.
        result['support_code']=getattr(error,'support_code', 'ENCRYPTED' if result['encryption']=='encrypted' else 'INPUT_UNSUPPORTED')
    return result

def devkit_candidates(explicit=None):
    values=[explicit] if explicit else [os.environ.get('DEVKITPRO'), 'C:/devkitPro',Path(os.environ.get('LOCALAPPDATA',Path.home()/'.cache'))/'ROSA-Builder'/'devkitpro']
    compiler=shutil.which('aarch64-none-elf-gcc.exe')
    if not explicit and compiler:values.append(Path(compiler).parent.parent.parent)
    found=[]
    for value in values:
        if not value:continue
        try:p=core.local_path(value)
        except core.BuildError:continue
        if p not in found:found.append(p)
    return found

def choose_dependencies(data,expected,explicit=None,force_managed=False,emit=lambda **e:None):
    """Select only hash-matching existing tools, else use the pinned installer.

    Mesa stays on its existing verified automatic setup/cache path. The later
    build validates every SDK file again before compiling the user's code.
    """
    data=core.local_path(data)
    if core.sha(data)!=expected:raise core.BuildError('EXE/DATA integrity mismatch.')
    with zipfile.ZipFile(data) as archive:
        info=archive.getinfo('manifest.json')
        if info.file_size>2*1024**2:raise core.BuildError('SDK inventory too large.')
        manifest=json.loads(archive.read(info))
    required={n:r for n,r in manifest['sdk_files'].items() if r['root']=='devkitpro'}
    if not required:raise core.BuildError('Missing pinned SDK inventory.')
    for name,record in required.items():
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or not re.fullmatch('[a-f0-9]{64}',record['sha256']):raise core.BuildError('Invalid SDK inventory.')
    if not force_managed:
        for candidate in devkit_candidates(explicit):
            if all((candidate/n).is_file() and core.sha(candidate/n)==record['sha256'] for n,record in required.items()):
                emit(stage='sdk',message='Compatible installed devkitPro detected and hash-verified; Mesa setup remains automatic.')
                return candidate,False
        if explicit:raise core.BuildError('Selected devkitPro SDK differs from the pinned SDK. Choose Automatic setup.')
    emit(stage='sdk',message='Using isolated automatic devkitPro setup with verified official downloads; system installations stay unchanged.')
    return None,True

def sdk_report(data,expected,mode='auto',existing=None,archive=None):
    import mesa_sdk
    with tempfile.TemporaryDirectory(prefix='rosa-sdk-diagnostic-') as temp:
        payload=Path(temp)/'payload'
        core.unpack_payload(data,payload,expected)
        root=mesa_sdk.setup(payload,mode,existing=existing,archive=archive)
        return mesa_sdk.diagnose(root,mesa_sdk.plan(payload),sdk_only=(mode=='existing'))

def package_report(data=None):
    resource=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'release.json'
    release=json.loads(resource.read_text())
    expected=release['data_sha256']
    if data is None:data=Path(sys.executable if getattr(sys,'frozen',False) else __file__).parent/'ROSA-Builder.data'
    actual=core.sha(data) if Path(data).is_file() else None
    result={'builder':release['version'],'expected_data_sha256':expected,'actual_data_sha256':actual,'matching_pair':actual==expected}
    if getattr(sys,'frozen',False):result['exe_sha256']=core.sha(sys.executable)
    return result

def environment_report():
    return {'builder':core.UI_VERSION,'payload_compatibility':core.VERSION,'host_os':platform.system(),'host_arch':platform.machine(),
            'wine_environment_detected':bool(os.environ.get('WINEPREFIX') or os.environ.get('WINELOADERNOEXEC')),
            'macos_or_wine_validated':False,'installed_devkit_detected':any((p/'devkitA64/bin/aarch64-none-elf-gcc.exe').is_file() for p in devkit_candidates()),
            'game_data_uploaded':False}

def export_report(destination,rom=None,events=(),result=None,sdk=None):
    """Build reports from allowlists, not redacted raw logs or arbitrary inputs."""
    destination=core.local_path(destination)
    body={'schema':REPORT_SCHEMA,'package':package_report(),'environment':environment_report(),'privacy':{'game_bytes':False,'paths':False,'raw_logs':False,'saves':False,'keys':False},'events':[]}
    if rom:
        allowed=('format','encryption','status','build_allowed','title_id','code_sha256','exheader_sha256','code_bytes','remaster_version','sha256','bytes','support_code','ncch_sha256','input_stable','reference_matches','reference_hashes')
        body['game']={k:rom[k] for k in allowed if k in rom}
        if 'diagnostic_profile' in rom:
            profile=rom_diagnostics.safe_profile(rom['diagnostic_profile'])
            body['game']['diagnostic_profile']=profile
            body['game']['diagnostic_comparison']=rom_diagnostics.compare(profile,getattr(compat_manifest,'REFERENCE_DIAGNOSTICS',None))
    for event in events:
        safe={k:event[k] for k in ('done','total') if type(event.get(k)) in (int,float)}
        if event.get('stage') in ('validate','generate','compile','link','sdk','stage','copy','complete','error','checked','diagnosed'):safe['stage']=event['stage']
        if safe:body['events'].append(safe)
    if result:
        allowed=('builder','runtime','nro_sha256','native_archive_sha256','seconds','compilation_units','console_validated','clean_windows_validated','font_supplied','payload_sha256')
        body['build']={k:result[k] for k in allowed if k in result}
    if sdk:
        body['sdk']={k:sdk[k] for k in ('schema','compatible','files','resolution_hint','supported_mesa','target') if k in sdk}
    # Exclusive creation prevents overwriting existing reports or personal files.
    with destination.open('x',encoding='utf-8') as stream:json.dump(body,stream,indent=2)
    return body
