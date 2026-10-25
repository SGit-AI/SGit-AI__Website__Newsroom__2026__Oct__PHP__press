#!/usr/bin/env python3
"""Take v1's assets (scripts, styles, images, fonts, components) into the press, to publish them once for every site.

    python3 tools/assets_v1.py --from ../sgit-ai__website__newsroom__2026__oct__php

Copies v1's tracked assets/ at its current, released commit into assets/ here, byte for byte, and records the commit
in assets.json. tools/release.sh then publishes them under /v/<version>/assets/, and the partition cuts the sites only
against a press version whose assets are exactly v1's at the commit it cuts. Until pass two moves the assets' sources
here, v1 is where they are written.
"""
import argparse, json, os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ap = argparse.ArgumentParser(); ap.add_argument('--from', dest='v1', required=True)
v1 = os.path.abspath(ap.parse_args().v1)
if subprocess.run(['git', '-C', v1, 'status', '--porcelain', '--untracked-files=no', '--', 'assets'], capture_output=True, text=True).stdout.strip():
    sys.exit('assets: the v1 clone has uncommitted changes under assets/; take them from a released commit')
files = [f for f in subprocess.run(['git', '-C', v1, 'ls-files', '-z', 'assets'], capture_output=True, check=True).stdout.decode().split('\0') if f]
shutil.rmtree(os.path.join(ROOT, 'assets'), ignore_errors=True)
for f in files:
    os.makedirs(os.path.dirname(os.path.join(ROOT, f)), exist_ok=True)
    shutil.copyfile(os.path.join(v1, f), os.path.join(ROOT, f))
commit = subprocess.run(['git', '-C', v1, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
version = open(os.path.join(v1, 'VERSION'), encoding='utf-8').read().strip()
with open(os.path.join(ROOT, 'assets.json'), 'w', encoding='utf-8', newline='\n') as fh:
    json.dump({'from': {'repository': 'SGit-AI/sgit-ai__website__newsroom__2026__oct__php', 'commit': commit, 'site_version': version}, 'files': len(files)}, fh, indent=1); fh.write('\n')
print(f'assets: {len(files)} files from v1 at {commit[:12]} (site v{version})')
