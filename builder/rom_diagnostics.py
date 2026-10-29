"""Read-only metadata fingerprints. Never an enrollment or acceptance mechanism."""
import hashlib
import re
import struct

# Offsets relative to the SCI/ACI exheader, as consumed by the B20 loader.
FIELDS = {
    'sci_flags': (0x0d, 'B'), 'remaster_version': (0x0e, 'H'),
    'stack_bytes': (0x1c, 'I'), 'bss_bytes': (0x3c, 'I'),
    'savedata_bytes': (0x1c0, 'Q'), 'jump_id': (0x1c8, 'Q'),
    'program_id': (0x200, 'Q'), 'core_version': (0x208, 'I'),
    'system_flags_1': (0x20c, 'B'), 'system_flags_2': (0x20d, 'B'),
    'execution_flags': (0x20e, 'B'), 'thread_priority': (0x20f, 'B'),
    'resource_limit_category': (0x36f, 'B'),
}
for _name, _offset in (('text', 0x10), ('rodata', 0x20), ('data', 0x30)):
    for _part, _delta in (('address', 0), ('pages', 4), ('bytes', 8)):
        FIELDS[_name+'_'+_part] = (_offset+_delta, 'I')
# Preserve tagged descriptors as numeric metadata instead of guessing unknown
# tags. A reviewer can examine SVC masks, handle limits, memory type and maps.
for _index in range(28):
    FIELDS[f'kernel_descriptor_{_index:02d}'] = (0x370+4*_index, 'I')

# Together these cover every declared byte, including reserved/unknown fields.
BLOCKS = {
    'sci_layout': (0, 0x40), 'dependencies': (0x40, 0x1c0),
    'system_info': (0x1c0, 0x200), 'local_execution': (0x200, 0x210),
    'resource_limits': (0x210, 0x230), 'storage_access': (0x230, 0x250),
    'service_access': (0x250, 0x360), 'local_reserved': (0x360, 0x370),
    'kernel_capabilities': (0x370, 0x3f0), 'arm9_access': (0x3f0, 0x400),
    'access_descriptor': (0x400, 0x800),
}
RESOURCES = ('romfs_sha256', 'exefs_noncode_sha256', 'exefs_header_sha256',
             'ncch_header_sha256')


def exheader_profile(raw):
    fields = {name: struct.unpack_from('<'+kind, raw, offset)[0]
              for name, (offset, kind) in FIELDS.items()
              if offset+struct.calcsize(kind) <= len(raw)}
    blocks = {name: hashlib.sha256(raw[start:min(end, len(raw))]).hexdigest()
              for name, (start, end) in BLOCKS.items() if start < len(raw)}
    return {'bytes': len(raw), 'fields': fields, 'blocks': blocks}


def safe_profile(profile):
    """Reconstruct the export schema; no arbitrary nested strings or keys."""
    def number(value):
        return type(value) is int and 0 <= value < 2**64
    def digest(value):
        return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value)
    ex = profile.get('exheader', {})
    resources = profile.get('resources', {})
    return {
        'exheader': {
            'bytes': ex.get('bytes') if number(ex.get('bytes')) else None,
            'fields': {k: v for k, v in ex.get('fields', {}).items()
                       if k in FIELDS and number(v)},
            'blocks': {k: v for k, v in ex.get('blocks', {}).items()
                       if k in BLOCKS and digest(v)},
        },
        'resources': {k: v for k, v in resources.items()
                      if (k in RESOURCES and (v is None or digest(v)))
                      or (k == 'romfs_bytes' and number(v))},
    }


def compare(profile, reference):
    """A partition mismatch alone does not establish resource differences."""
    actual = safe_profile(profile)
    expected = safe_profile(reference or {})
    def matches(left, right, keys):
        return {k: left[k] == right[k] if k in left and k in right else None
                for k in keys}
    return {
        'exheader_size': matches({k:v for k,v in actual['exheader'].items() if v is not None},
                                {k:v for k,v in expected['exheader'].items() if v is not None}, ('bytes',)),
        'exheader_fields': matches(actual['exheader']['fields'], expected['exheader']['fields'], FIELDS),
        'exheader_blocks': matches(actual['exheader']['blocks'], expected['exheader']['blocks'], BLOCKS),
        'resources': matches(actual['resources'], expected['resources'], (*RESOURCES, 'romfs_bytes')),
    }
