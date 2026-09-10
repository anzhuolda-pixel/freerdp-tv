#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-billion-a9-test10"

def fail(msg):
    raise SystemExit("PATCH ERROR: " + msg)

def read(path):
    if not path.is_file():
        fail("missing file: " + str(path))
    return path.read_text(encoding="utf-8")

def write(path, data):
    path.write_text(data, encoding="utf-8", newline="\n")

def replace_once(data, old, new, desc):
    c = data.count(old)
    if c != 1:
        fail(f"{desc}: expected 1 match, found {c}")
    return data.replace(old, new, 1)

def main():
    if len(sys.argv) != 2:
        fail("usage: patch_stability_test10.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("Android Studio project not found")

    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-billion-a9-test9", "VERSION_NAME=" + VERSION,
                        "bump version name")
    data = replace_once(data, "VERSION_CODE=331109", "VERSION_CODE=331110",
                        "bump version code")
    data += "\nRELEASE_STORE_FILE=billion-rdp-test.p12\n"
    data += "RELEASE_KEY_ALIAS=billion-rdp\n"
    data += "RELEASE_KEY_PASSWORD=BillionRdpTest10\n"
    data += "RELEASE_STORE_PASSWORD=BillionRdpTest10\n"
    write(props, data)

    gradle = studio / "aFreeRDP" / "build.gradle"
    data = read(gradle)
    data = replace_once(data, 'storeType "jks"', 'storeType "pkcs12"',
                        "switch release signer to PKCS12")
    write(gradle, data)

    manifest = studio / "aFreeRDP" / "src" / "main" / "AndroidManifest.xml"
    data = read(manifest)
    marker = "    <uses-feature android:name=\"android.hardware.touchscreen\" android:required=\"false\" />\n"
    if marker not in data:
        fail("touchscreen optional marker not found")
    optional = marker + (
        "    <uses-feature android:name=\"android.hardware.camera\" android:required=\"false\" />\n"
        "    <uses-feature android:name=\"android.hardware.camera.any\" android:required=\"false\" />\n"
        "    <uses-feature android:name=\"android.hardware.camera.autofocus\" android:required=\"false\" />\n"
        "    <uses-feature android:name=\"android.hardware.microphone\" android:required=\"false\" />\n"
    )
    data = replace_once(data, marker, optional, "mark camera/microphone optional")
    write(manifest, data)

    print("Test10 stability patch applied")
    print("Reproducible test signing + camera/microphone optional + Test9 UX retained")

if __name__ == "__main__":
    main()
