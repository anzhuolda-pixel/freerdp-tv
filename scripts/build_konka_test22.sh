#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

src = Path('scripts/build_konka_test20.sh').read_text(encoding='utf-8')

def rep(old, new, desc):
    global src
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'Test22 build wrapper patch failed for {desc}: expected 1, got {count}')
    src = src.replace(old, new, 1)

rep(
    'patch_konka_win7_defaults_test20.py generate_test_signing.py; do',
    'patch_konka_win7_defaults_test20.py patch_auto_reconnect_test21.py patch_status_ui_test22.py patch_session_diag_test22.py generate_test_signing.py; do',
    'py_compile list')
rep(
    'python3 scripts/patch_konka_win7_defaults_test20.py upstream\n',
    'python3 scripts/patch_konka_win7_defaults_test20.py upstream\n'
    'python3 scripts/patch_auto_reconnect_test21.py upstream\n'
    'python3 scripts/patch_status_ui_test22.py upstream\n'
    'python3 scripts/patch_session_diag_test22.py upstream\n',
    'patch execution')
rep(
    'grep -F "VERSION_NAME=3.31.1-baihong-konka32-api28-test20" "$STUDIO/release.properties"',
    'grep -F "VERSION_NAME=3.31.1-baihong-konka32-api28-test22" "$STUDIO/release.properties"',
    'version gate')
rep(
    'OUT="$GITHUB_WORKSPACE/output/BAIHONG-RDP-3.31.1-Android9-KONKA32-Test20.apk"',
    'OUT="$GITHUB_WORKSPACE/output/BAIHONG-RDP-3.31.1-Android9-KONKA32-Test22.apk"',
    'apk output name')
rep(
    "grep -Fq \"versionName='3.31.1-baihong-konka32-api28-test20'\" \"$GITHUB_WORKSPACE/output/APK_BADGING.txt\"",
    "grep -Fq \"versionName='3.31.1-baihong-konka32-api28-test22'\" \"$GITHUB_WORKSPACE/output/APK_BADGING.txt\"",
    'badging gate')
rep(
    '百宏RDP Test20 - Konka Android 9 / Win7 RDP compatibility defaults',
    '百宏RDP Test22 - server status / connection logs / reachability-gated reconnect',
    'build info title')
rep(
    'Existing saved profiles are preserved and not overwritten\n',
    'Existing saved profiles are preserved and not overwritten\n'
    'Home server cards: RDP TCP-port reachability + Ping secondary signal + measured latency\n'
    'Ping failure alone does not mark a server offline when the configured RDP port is reachable\n'
    'Local connection/network event log: default retention 3 days; configurable 3/7/14/30/90/180/365 days\n'
    'Unexpected session disconnect and sustained TCP latency are recorded locally\n'
    'Reconnect gate: while the target RDP port is down, only lightweight reachability probes run; no repeated FreeRDP handshakes\n'
    'When the RDP port returns, FreeRDP automatic reconnect resumes\n',
    'build info Test22 notes')

Path('/tmp/build_konka_test22_base.sh').write_text(src, encoding='utf-8', newline='\n')
PY

chmod +x /tmp/build_konka_test22_base.sh
bash /tmp/build_konka_test22_base.sh
