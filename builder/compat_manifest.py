"""Locally enrolled B20 code identity. Hashes only, never game data."""
REFERENCE_NCCH_SHA256 = '7d2eb6ec0a241e055b295101d310328db58289ee53d84a78737d0ee452ea8d41'
REFERENCE_CODE_SHA256 = '7046fdd23c28858856cea14b359b69caca68742fb21acaa49f737ca610fa9bd5'
REFERENCE_EXHEADER_SHA256 = '63c5eeddc891be395bf24b1882448f2bc4b50ee7e4deb8e6be75b70cc2eb67a3'

# Diagnostic comparison only. Classification above never consults this profile.
from reference_profile import REFERENCE_DIAGNOSTICS
