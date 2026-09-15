#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def fail(msg):
    raise SystemExit("PATCH ERROR: " + msg)


def read(path):
    if not path.is_file():
        fail("missing file: " + str(path))
    return path.read_text(encoding="utf-8")


def write(path, data):
    path.write_text(data, encoding="utf-8", newline="\n")


def replace_once(data, old, new, desc):
    count = data.count(old)
    if count != 1:
        fail(f"{desc}: expected 1 match, found {count}")
    return data.replace(old, new, 1)


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_konka_win7_defaults_test20.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"

    # Version metadata.
    props = studio / "release.properties"
    data = read(props)
    data = re.sub(r'^VERSION_NAME=.*$', 'VERSION_NAME=3.31.1-baihong-konka32-api28-test20', data, count=1, flags=re.M)
    data = re.sub(r'^VERSION_CODE=.*$', 'VERSION_CODE=331120', data, count=1, flags=re.M)
    write(props, data)

    # Test20 keeps the proven Test19 Android 9 runtime baseline and changes only
    # the defaults used for newly-created / quick-connect profiles.
    #
    # Old Windows 7 RDP hosts often have NLA/TLS disabled or use legacy crypto.
    # FreeRDP maps security=1 to /sec:rdp and tlsSecLevel=0 to
    # /tls:seclevel:0 (OpenSSL security level 0 = allow legacy algorithms).
    # Existing saved profiles are not overwritten.
    bookmark = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/domain/BookmarkBase.java"
    data = read(bookmark)
    data = replace_once(data, 'private int security = 0;', 'private int security = 1;', 'default security to RDP')
    data = replace_once(data, 'private int tlsSecLevel = -1;', 'private int tlsSecLevel = 0;', 'default TLS security level to allow all')
    data = replace_once(
        data,
        'advancedSettings.setTlsSecLevel(sharedPrefs.getInt(keyTlsSecLevel, -1));',
        'advancedSettings.setTlsSecLevel(sharedPrefs.getInt(keyTlsSecLevel, 0));',
        'quick-connect TLS security fallback')
    data = replace_once(
        data,
        'advancedSettings.setSecurity(sharedPrefs.getInt(keySecurity, 0));',
        'advancedSettings.setSecurity(sharedPrefs.getInt(keySecurity, 1));',
        'quick-connect security fallback')
    write(bookmark, data)

    # Verify that the defaults now match the settings that were proven on the
    # user's Windows 7 host, while leaving TLS minimum version at its upstream
    # default (-1 / use default setting).
    data = read(bookmark)
    if 'private int security = 1;' not in data:
        fail('RDP security default missing')
    if 'private int tlsSecLevel = 0;' not in data:
        fail('TLS security level 0 default missing')
    if 'private int tlsMinLevel = -1;' not in data:
        fail('TLS minimum version default was unexpectedly changed')

    print('Test20 patch applied: default security=RDP, TLS security level=0 (allow all)')


if __name__ == '__main__':
    main()
