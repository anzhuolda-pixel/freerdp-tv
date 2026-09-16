#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

src = Path('scripts/build_konka_test20.sh').read_text(encoding='utf-8')

def rep(old, new, desc):
    global src
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'Test21 build wrapper patch failed for {desc}: expected 1, got {count}')
    src = src.replace(old, new, 1)

rep(
    'patch_konka_win7_defaults_test20.py generate_test_signing.py; do',
    'patch_konka_win7_defaults_test20.py patch_auto_reconnect_test21.py generate_test_signing.py; do',
    'py_compile list')
rep(
    'python3 scripts/patch_konka_win7_defaults_test20.py upstream\n',
    'python3 scripts/patch_konka_win7_defaults_test20.py upstream\npython3 scripts/patch_auto_reconnect_test21.py upstream\n',
    'patch execution')
rep(
    'grep -F "VERSION_NAME=3.31.1-baihong-konka32-api28-test20" "$STUDIO/release.properties"',
    'grep -F "VERSION_NAME=3.31.1-baihong-konka32-api28-test21" "$STUDIO/release.properties"',
    'version gate')
rep(
    'OUT="$GITHUB_WORKSPACE/output/BAIHONG-RDP-3.31.1-Android9-KONKA32-Test20.apk"',
    'OUT="$GITHUB_WORKSPACE/output/BAIHONG-RDP-3.31.1-Android9-KONKA32-Test21.apk"',
    'apk output name')
rep(
    "grep -Fq \"versionName='3.31.1-baihong-konka32-api28-test20'\" \"$GITHUB_WORKSPACE/output/APK_BADGING.txt\"",
    "grep -Fq \"versionName='3.31.1-baihong-konka32-api28-test21'\" \"$GITHUB_WORKSPACE/output/APK_BADGING.txt\"",
    'badging gate')
rep(
    '百宏RDP Test20 - Konka Android 9 / Win7 RDP compatibility defaults',
    '百宏RDP Test21 - Konka Android 9 / Win7 defaults / resilient auto reconnect',
    'build info title')
rep(
    'Existing saved profiles are preserved and not overwritten\n',
    'Existing saved profiles are preserved and not overwritten\nTransient network/server disconnect: automatic reconnect with 3/5/10/20/30 second backoff, then 30 seconds indefinitely\nAndroid network restoration callback accelerates reconnect when link returns\nAuthentication/account failures stop automatic retries and retain the normal error dialog\n',
    'build info reconnect notes')

Path('/tmp/build_konka_test21.sh').write_text(src, encoding='utf-8', newline='\n')
PY

chmod +x /tmp/build_konka_test21.sh
bash /tmp/build_konka_test21.sh
