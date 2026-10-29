"""Maintainer: derive comparison metadata ONLY from the exact enrolled B20 dump.

Does not enroll variants or change any compatibility hash. Output is exclusive.
"""
import argparse
import pprint
from pathlib import Path
import core


def derive(rom):
    rom=core.local_path(rom)
    before=rom.stat()
    if core.sha(rom)!=core.ROM_SHA:
        raise core.BuildError('Reference digest mismatch; no metadata generated.')
    identity=core.inspect_rom(rom,diagnostics=True)
    if core.sha(rom)!=core.ROM_SHA or (before.st_size,before.st_mtime_ns)!=(rom.stat().st_size,rom.stat().st_mtime_ns):
        raise core.BuildError('Input changed during reference inspection.')
    return identity['diagnostic_profile']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    profile=derive(args.rom)
    with core.local_path(args.output).open('x',encoding='utf-8') as stream:
        stream.write('"""Comparison metadata from the exact SHA-256-verified B20 input; never authorizes acceptance."""\nREFERENCE_DIAGNOSTICS = '+pprint.pformat(profile,sort_dicts=False,width=100)+'\n')
