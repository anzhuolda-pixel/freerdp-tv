#!/usr/bin/env python3
import re
import sys
from pathlib import Path

VERSION = "3.31.1-baihong-a9-test15"
VERSION_CODE = "331115"


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


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_konka_compat_test15.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    # Version only. Keep package id and stable Test10+ signing identity.
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-baihong-a9-test14",
                        "VERSION_NAME=" + VERSION, "update Test15 version")
    data = replace_once(data, "VERSION_CODE=331114", "VERSION_CODE=" + VERSION_CODE,
                        "update Test15 version code")
    write(props, data)

    # ------------------------------------------------------------------
    # Test14 introduced startup-only HomeBinding fields/status logic. Some OEM
    # TV frameworks are unusually fragile during first Activity inflation.
    # Return HomeActivity to the already field-tested Test13/Test12 structure:
    # only the RecyclerView is bound at startup. Branding and TV row focus remain.
    # ------------------------------------------------------------------
    home_xml = studio / "freeRDPCore/src/main/res/layout/home.xml"
    write(home_xml, '''<?xml version="1.0" encoding="utf-8"?>
<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#F4F6F8"
    android:fitsSystemWindows="true">

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/recyclerViewBookmarks"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:paddingTop="10dp"
        android:paddingBottom="16dp"
        android:clipToPadding="false" />
</RelativeLayout>
''')

    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    data = data.replace("import android.view.View;\n", "")
    data = replace_once(data,
                        '\t\tDeviceMode.maybeShowFirstRunGuide(this);\n\t\tconfigureBaihongHome();\n',
                        '\t\tDeviceMode.maybeShowFirstRunGuide(this);\n',
                        "remove Test14 startup HomeBinding hook")

    method_start = data.find('\tprivate void configureBaihongHome()\n')
    resume_start = data.find('\t@Override protected void onResume()\n', method_start)
    if method_start < 0 or resume_start < 0:
        fail("Test14 Home status methods not found")
    data = data[:method_start] + data[resume_start:]
    data = data.replace('\t\tupdateBaihongAutoConnectStatus();\n', '')
    write(home, data)

    # ------------------------------------------------------------------
    # Replace Test14 SeekBarPreference/new integer key with the known-good
    # ListPreference/string storage path used by Test3-Test13. The installer can
    # still define startup delay, now with 10 choices up to 120 seconds.
    # This avoids OEM Preference/SeekBar quirks and avoids mixed-type prefs.
    # ------------------------------------------------------------------
    tv_xml = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    data = read(tv_xml)
    seek = '''        <SeekBarPreference
            android:key="tv.auto_connect_delay_seconds_v2"
            android:defaultValue="10"
            android:title="@string/settings_tv_connect_delay"
            android:summary="@string/settings_tv_connect_delay_summary"
            android:max="120"
            app:min="0"
            app:seekBarIncrement="1"
            app:showSeekBarValue="true"
            app:adjustable="true" />'''
    listpref = '''        <ListPreference
            android:key="tv.auto_connect_delay"
            android:defaultValue="10"
            android:title="@string/settings_tv_connect_delay"
            android:summary="@string/settings_tv_connect_delay_summary"
            android:entries="@array/tv_connect_delay_compat_entries"
            android:entryValues="@array/tv_connect_delay_compat_values"
            app:useSimpleSummaryProvider="true" />'''
    data = replace_once(data, seek, listpref, "replace SeekBar delay with OEM-safe ListPreference")
    write(tv_xml, data)

    appsettings = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/ApplicationSettingsActivity.java"
    data = read(appsettings)
    data = replace_once(data,
                        '\t\t\tmigrateTvAutoConnectDelay(requireContext());\n\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);\n',
                        '\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);\n',
                        "remove Test14 delay migration during settings inflation")

    method_start = data.find('\tpublic static void migrateTvAutoConnectDelay(Context context)\n')
    method_end_marker = '\tpublic static void setTvAutoConnectTarget(Context context, String ref, String label)\n'
    method_end = data.find(method_end_marker, method_start)
    if method_start < 0 or method_end < 0:
        fail("Test14 delay helper block not found")
    compat_delay = '''\tpublic static int getTvAutoConnectDelaySeconds(Context context)
\t{
\t\tString raw = get(context).getString("tv.auto_connect_delay", "10");
\t\ttry
\t\t{
\t\t\tint seconds = Integer.parseInt(raw);
\t\t\tif (seconds < 0) seconds = 0;
\t\t\tif (seconds > 120) seconds = 120;
\t\t\treturn seconds;
\t\t}
\t\tcatch (Exception ignored)
\t\t{
\t\t\treturn 10;
\t\t}
\t}

\tpublic static int getTvAutoConnectDelayMs(Context context)
\t{
\t\treturn getTvAutoConnectDelaySeconds(context) * 1000;
\t}

'''
    data = data[:method_start] + compat_delay + data[method_end:]
    write(appsettings, data)

    # Add OEM-safe predefined delay choices. Values are strings, matching the
    # long-standing ListPreference storage used by previous working builds.
    for rel in ["freeRDPCore/src/main/res/values/strings.xml",
                "freeRDPCore/src/main/res/values-zh/strings.xml"]:
        path = studio / rel
        data = read(path)
        if 'name="tv_connect_delay_compat_entries"' not in data:
            zh = "values-zh" in rel
            entries = ["立即", "5 秒", "10 秒（推荐）", "15 秒", "20 秒", "30 秒", "45 秒", "60 秒", "90 秒", "120 秒"] if zh else ["Immediately", "5 seconds", "10 seconds (recommended)", "15 seconds", "20 seconds", "30 seconds", "45 seconds", "60 seconds", "90 seconds", "120 seconds"]
            block = '    <string-array name="tv_connect_delay_compat_entries">\n' + ''.join(f'        <item>{x}</item>\n' for x in entries) + '    </string-array>\n'
            block += '    <string-array name="tv_connect_delay_compat_values" translatable="false">\n' + ''.join(f'        <item>{x}</item>\n' for x in [0,5,10,15,20,30,45,60,90,120]) + '    </string-array>\n'
            pos = data.rfind("</resources>")
            data = data[:pos] + block + data[pos:]
        if "values-zh" in rel:
            data = set_string(data, "settings_tv_connect_delay", "软件启动后延时自动连接")
            data = set_string(data, "settings_tv_connect_delay_summary", "请选择 0～120 秒。电视随开机启动建议 10～30 秒，让 Android 和网络先稳定。")
        else:
            data = set_string(data, "settings_tv_connect_delay", "Startup auto-connect delay")
            data = set_string(data, "settings_tv_connect_delay_summary", "Choose 0–120 seconds. 10–30 seconds is recommended when the TV starts with power-on.")
        write(path, data)

    print("Test15 Konka compatibility hotfix applied:", VERSION)
    print("Home startup returned to stable RecyclerView-only binding")
    print("Auto-connect delay retained using OEM-safe ListPreference string storage")
    print("Visible brand remains 百宏RDP; Test11-13 TV/display/localization features retained")


if __name__ == "__main__":
    main()
