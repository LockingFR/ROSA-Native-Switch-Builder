"""Prepare an allowlisted beta only after the frozen EXE's complete build.

No GitHub operation is performed. The content auditor never grants human
approval; the owner explicitly requested a beta release on October 27, 2026.
Private build outputs are read for verification and never included.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, zipfile
from verify_full_build import verify

EXE_SHA='88d1a8bdd843ea559ed1c311a9ff9f9e7414c024766799f8bb15995b07ac2ac0'
DATA_SHA='55f225cfd9e03ca4b39997749dfa0610a9c8c67a837b77dcefcb9c1a44fd088d'
NRO_SHA='47c7215f90ca9d4a3954875038e8701c2cf300c64ec1e640a63a6a6574773fd3'
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def prepare(candidate,output):
    if output.exists() or output.with_suffix('.zip').exists():raise FileExistsError('Existing release artifacts preserved')
    launch=json.loads((ROOT/'build/r9-frozen-full-launch.json').read_text(encoding='utf-8-sig'))
    if sha(Path(launch['exe']))!=EXE_SHA:raise ValueError('Frozen build EXE identity changed')
    events=[json.loads(line) for line in Path(launch['report']).read_text(encoding='utf-8').splitlines()]
    if not events or events[-1]['stage']!='complete' or any(e['stage']=='error' for e in events):raise ValueError('Frozen EXE did not complete its full build')
    full=Path(launch['output']);proof=verify(full)
    result=json.loads((full/'build-result.json').read_text(encoding='utf-8'))
    if proof['nro_sha256']!=NRO_SHA or result['payload_sha256']!=DATA_SHA:raise ValueError('Frozen output differs from the qualified reference')
    audit=json.loads((ROOT/'build/content-audit-r9-final.json').read_text(encoding='utf-8'))
    if not audit['technical_checks_passed'] or audit['issues'] or audit['review_findings']:raise ValueError('Content audit is not clear')
    rom=json.loads((ROOT/'build/release-r9-frozen-rom.jsonl').read_text(encoding='utf-8'))
    sdk=json.loads((ROOT/'build/release-r9-frozen-sdk.jsonl').read_text(encoding='utf-8'))
    if not rom['diagnostic']['build_allowed'] or not all(rom['diagnostic']['reference_matches'].values()) or not sdk['sdk']['compatible']:raise ValueError('Frozen diagnostics failed')
    for record in (rom,sdk):
        if record['package']['exe_sha256']!=EXE_SHA or not record['package']['matching_pair']:raise ValueError('Diagnostic used another EXE/DATA pair')
    for name,digest in [('ROSA-Builder.exe',EXE_SHA),('ROSA-Builder.data',DATA_SHA)]:
        if sha(candidate/name)!=digest:raise ValueError('Candidate differs from the tested pair')
    output.mkdir(parents=True)
    for name in ('ROSA-Builder.exe','ROSA-Builder.data'):shutil.copyfile(candidate/name,output/name)
    for source,dest in [('INSTALL-R9.md','INSTALL.md'),('MESA-AND-ROM-DIAGNOSTICS.md','MESA-AND-ROM-DIAGNOSTICS.md'),('CHANGELOG-R9.md','CHANGELOG.md')]:shutil.copyfile(ROOT/'builder/public'/source,output/dest)
    shutil.copyfile(candidate/'THIRD-PARTY-NOTICES.txt',output/'THIRD-PARTY-NOTICES.txt')
    qualification={'release':'v0.2.0-beta','builder_identity':'0.2.0-preview-r9','date':'2026-10-27','technical_content_audit_passed':True,'source_tests_passed':42,'final_frozen_exe_full_build_executed':True,'frozen_exe_full_build':proof,'frozen_rom_and_sdk_diagnostics_passed':True,'frozen_diagnostic_reports_generated':True,'gui_export_allowlist_source_tests_passed':True,'gui_export_button_driven_by_automation':False,'macos_wine_validated':False,'clean_machine_r9_full_build_validated':False,'switch_execution_validated':False,'reference_nro_identical':True,'exe_sha256':EXE_SHA,'data_sha256':DATA_SHA,'publication_authorization':'Explicit owner request of 2026-10-27, conditional on successful Windows checks.','automated_audit_distribution_approved':audit['distribution_approved'],'approval_field_note':'The content auditor never grants human publication approval; its field is unchanged.'}
    (output/'QUALIFICATION.json').write_text(json.dumps(qualification,indent=2)+'\n',encoding='utf-8')
    names=('ROSA-Builder.exe','ROSA-Builder.data','INSTALL.md','MESA-AND-ROM-DIAGNOSTICS.md','CHANGELOG.md','THIRD-PARTY-NOTICES.txt','QUALIFICATION.json')
    checksums=''.join(sha(output/name)+'  '+name+'\n' for name in names)
    (output/'SHA256SUMS.txt').write_text(checksums,encoding='ascii')
    archive=output.with_suffix('.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as zipped:
        for name in (*names,'SHA256SUMS.txt'):zipped.write(output/name,name)
    with zipfile.ZipFile(archive) as zipped:
        if set(zipped.namelist())!=set((*names,'SHA256SUMS.txt')) or zipped.testzip():raise ValueError('ZIP integrity/allowlist failed')
        for name in names:
            if hashlib.sha256(zipped.read(name)).hexdigest()!=sha(output/name):raise ValueError('ZIP member digest mismatch')
    external=archive.parent/'SHA256SUMS-R9.txt'
    if external.exists():raise FileExistsError('Existing checksum file preserved')
    external.write_text(sha(archive)+'  '+archive.name+'\n'+checksums,encoding='ascii')
    return {'archive':str(archive),'sha256':sha(archive),'files':8,'frozen_full_build_verified':True,'public_release_created':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(prepare(a.candidate,a.output),indent=2))
