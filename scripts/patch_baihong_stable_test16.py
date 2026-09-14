#!/usr/bin/env python3
import re
import sys
from pathlib import Path

VERSION = "3.31.1-baihong-a9-test16"
VERSION_CODE = "331116"
BRAND = "百宏RDP"


def fail(msg):
    raise SystemExit("PATCH ERROR: " + msg)


def read(path):
    if not path.is_file():
        fail("missing file: " + str(path))
    return path.read_text(encoding="utf-8")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8", newline="\n")


def replace_once(data, old, new, desc):
    count = data.count(old)
    if count != 1:
        fail(f"{desc}: expected 1 match, found {count}")
    return data.replace(old, new, 1)


def set_string(data, name, value):
    pattern = re.compile(r'<string\s+name="' + re.escape(name) + r'"(?:\s+[^>]*)?>.*?</string>')
    repl = f'<string name="{name}">{value}</string>'
    if pattern.search(data):
        return pattern.sub(repl, data, count=1)
    pos = data.rfind("</resources>")
    if pos < 0:
        fail("strings.xml missing </resources>")
    return data[:pos] + "    " + repl + "\n" + data[pos:]


def replace_array(data, name, items):
    pattern = re.compile(r'<string-array\s+name="' + re.escape(name) + r'"(?:\s+[^>]*)?>.*?</string-array>', re.S)
    if not pattern.search(data):
        fail("missing string-array: " + name)
    body = [f'<string-array name="{name}">']
    body.extend(f'        <item>{item}</item>' for item in items)
    body.append('    </string-array>')
    return pattern.sub("\n".join(body), data, count=1)


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_baihong_stable_test16.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    # Test16 rebases directly on the field-tested Test13 startup/UI structure.
    # Test14/Test15 Home layout, HomeBinding, SeekBar and startup-status UI are
    # deliberately excluded because the Konka TV reports white-screen crashes.
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-billion-a9-test13",
                        "VERSION_NAME=" + VERSION, "update Test16 version")
    data = replace_once(data, "VERSION_CODE=331113", "VERSION_CODE=" + VERSION_CODE,
                        "update Test16 version code")
    write(props, data)

    # Visible product name only; keep package id and stable Test10+ signer.
    app_strings = studio / "aFreeRDP/src/main/res/values/strings.xml"
    data = read(app_strings)
    data = replace_once(data,
                        '<string name="app_title" translatable="false">BILLION RDP REMOTE</string>',
                        '<string name="app_title" translatable="false">百宏RDP</string>',
                        "rename app label")
    write(app_strings, data)

    en_path = studio / "freeRDPCore/src/main/res/values/strings.xml"
    zh_path = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    for path in (en_path, zh_path):
        data = read(path)
        data = data.replace("BILLION RDP REMOTE", BRAND)
        data = data.replace("Baihong RDP REMOTE", BRAND)
        data = data.replace("百宏 RDP REMOTE", BRAND)
        if path == zh_path:
            data = set_string(data, "settings_tv_connect_delay", "软件启动后自动连接延时")
        else:
            data = set_string(data, "settings_tv_connect_delay", "Startup auto-connect delay")
        write(path, data)

    # Preserve the old string-valued ListPreference used successfully by Test3-13.
    # Only expand the selectable delay range; do not introduce a SeekBar/int pref.
    en = read(en_path)
    en = replace_array(en, "tv_connect_delay_entries",
                       ["Immediately", "5 seconds", "10 seconds (recommended)", "15 seconds",
                        "20 seconds", "30 seconds", "45 seconds", "60 seconds", "90 seconds", "120 seconds"])
    en = replace_array(en, "tv_connect_delay_values",
                       ["0", "5", "10", "15", "20", "30", "45", "60", "90", "120"])
    write(en_path, en)

    zh = read(zh_path)
    zh = replace_array(zh, "tv_connect_delay_entries",
                       ["立即", "5 秒", "10 秒（推荐）", "15 秒", "20 秒", "30 秒", "45 秒", "60 秒", "90 秒", "120 秒"])
    write(zh_path, zh)

    tv_xml = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    data = read(tv_xml)
    key = 'android:key="tv.auto_connect_delay"'
    pos = data.find(key)
    if pos < 0:
        fail("stable tv.auto_connect_delay preference not found")
    start = data.rfind("<ListPreference", 0, pos)
    end = data.find("/>", pos)
    if start < 0 or end < 0:
        fail("stable delay ListPreference block not found")
    end += 2
    block = data[start:end]
    block = block.replace('android:defaultValue="5"', 'android:defaultValue="10"', 1)
    data = data[:start] + block + data[end:]
    write(tv_xml, data)

    appsettings = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/ApplicationSettingsActivity.java"
    data = read(appsettings)
    old = '''\tpublic static int getTvAutoConnectDelayMs(Context context)\n\t{\n\t\tString raw = get(context).getString("tv.auto_connect_delay", "5");\n\t\ttry\n\t\t{\n\t\t\tint seconds = Integer.parseInt(raw);\n\t\t\tif (seconds < 0) seconds = 0;\n\t\t\tif (seconds > 30) seconds = 30;\n\t\t\treturn seconds * 1000;\n\t\t}\n\t\tcatch (NumberFormatException e)\n\t\t{\n\t\t\treturn 5000;\n\t\t}\n\t}\n'''
    new = '''\tpublic static int getTvAutoConnectDelayMs(Context context)\n\t{\n\t\tString raw = get(context).getString("tv.auto_connect_delay", "10");\n\t\ttry\n\t\t{\n\t\t\tint seconds = Integer.parseInt(raw);\n\t\t\tif (seconds < 0) seconds = 0;\n\t\t\tif (seconds > 120) seconds = 120;\n\t\t\treturn seconds * 1000;\n\t\t}\n\t\tcatch (NumberFormatException e)\n\t\t{\n\t\t\treturn 10000;\n\t\t}\n\t}\n'''
    data = replace_once(data, old, new, "extend stable startup delay to 120 seconds")
    write(appsettings, data)

    # Guardrails: ensure none of the Test14/Test15-only startup UI is present.
    home = read(studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java")
    home_xml = read(studio / "freeRDPCore/src/main/res/layout/home.xml")
    forbidden = ["configureBaihongHome", "updateBaihongAutoConnectStatus", "tvHomeHint", "tvHomeTitle", "autoConnectStatus"]
    for token in forbidden:
        if token in home or token in home_xml:
            fail("unstable Test14/Test15 startup UI leaked into Test16: " + token)
    if "SeekBarPreference" in read(tv_xml):
        fail("unstable SeekBarPreference leaked into Test16")

    print("Test16 stable Konka rebase applied:", VERSION)
    print("Base UI: Test13; branding: 百宏RDP; startup delay: stable ListPreference 0..120 seconds")


if __name__ == "__main__":
    main()
