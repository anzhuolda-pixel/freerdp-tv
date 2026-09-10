#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-billion-a9-test6"
BRAND = "BILLION RDP REMOTE"


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
        fail("usage: patch_billion_brand_test6.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found: " + str(studio))

    # Keep the same Android package name so saved profiles/settings remain tied
    # to the same app identity. Only the visible brand and version are changed.
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data,
        "VERSION_NAME=3.31.1-baihong-a9-test5",
        "VERSION_NAME=3.31.1-billion-a9-test6",
        "update Test6 version name")
    data = replace_once(data,
        "VERSION_CODE=331105",
        "VERSION_CODE=331106",
        "update Test6 version code")
    write(props, data)

    app_strings = studio / "aFreeRDP/src/main/res/values/strings.xml"
    data = read(app_strings)
    data = replace_once(data,
        '<string name="app_title" translatable="false">百宏 RDP REMOTE</string>',
        '<string name="app_title" translatable="false">BILLION RDP REMOTE</string>',
        "set BILLION app title")
    write(app_strings, data)

    strings = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(strings)
    data = data.replace("Baihong RDP REMOTE", BRAND)
    write(strings, data)

    zh_strings = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh_strings)
    data = data.replace("百宏 RDP REMOTE", BRAND)
    write(zh_strings, data)

    print("BILLION brand patch applied:", VERSION)
    print("App label:", BRAND)


if __name__ == "__main__":
    main()
