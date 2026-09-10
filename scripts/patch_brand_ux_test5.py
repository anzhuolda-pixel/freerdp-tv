#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-baihong-a9-test5"


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


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_brand_ux_test5.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found: " + str(studio))

    # ------------------------------------------------------------------
    # 1. Version metadata
    # ------------------------------------------------------------------
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data,
        "VERSION_NAME=3.31.1-adaptive-a9-test4",
        "VERSION_NAME=3.31.1-baihong-a9-test5",
        "update Test5 version name")
    data = replace_once(data,
        "VERSION_CODE=331104",
        "VERSION_CODE=331105",
        "update Test5 version code")
    write(props, data)

    # ------------------------------------------------------------------
    # 2. Baihong app identity. Keep package name unchanged so upgrades from
    #    Test4 retain saved profiles and settings.
    # ------------------------------------------------------------------
    app_strings = studio / "aFreeRDP/src/main/res/values/strings.xml"
    data = read(app_strings)
    data = replace_once(data,
        '<string name="app_title" translatable="false">FreeRDP Remote</string>',
        '<string name="app_title" translatable="false">百宏 RDP REMOTE</string>',
        "set Baihong app title")
    write(app_strings, data)

    manifest = studio / "aFreeRDP/src/main/AndroidManifest.xml"
    data = read(manifest)
    data = replace_once(data,
        '        android:icon="@mipmap/ic_launcher"\n        android:label="aFreeRDP"',
        '        android:icon="@drawable/ic_baihong_rdp"\n        android:label="@string/app_title"',
        "set Baihong icon and application label")
    # The receiver only needs system boot broadcasts. Keeping it non-exported
    # prevents other apps from explicitly invoking it.
    data = replace_once(data,
        '            android:name="com.freerdp.afreerdp.TvBootReceiver"\n            android:enabled="true"\n            android:exported="true">',
        '            android:name="com.freerdp.afreerdp.TvBootReceiver"\n            android:enabled="true"\n            android:exported="false">',
        "harden boot receiver")
    write(manifest, data)

    # Simple vector identity: red tile + monitor + two-way RDP arrow.
    # VectorDrawable works on the whole supported range (Android 9+), avoiding
    # density-specific launcher PNG issues on OEM TV firmware.
    icon = '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#B5121B"
        android:pathData="M14,4H94C99.52,4 104,8.48 104,14V94C104,99.52 99.52,104 94,104H14C8.48,104 4,99.52 4,94V14C4,8.48 8.48,4 14,4Z" />
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M23,25H85C88.31,25 91,27.69 91,31V68C91,71.31 88.31,74 85,74H23C19.69,74 17,71.31 17,68V31C17,27.69 19.69,25 23,25ZM25,33V66H83V33Z" />
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M43,80H65V86H75V92H33V86H43Z" />
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M30,49L42,39V45H54V51H42V57ZM78,49L66,39V45H54V51H66V57Z" />
</vector>
'''
    write(studio / "aFreeRDP/src/main/res/drawable/ic_baihong_rdp.xml", icon)

    # ------------------------------------------------------------------
    # 3. Auto-connect safety / UX fixes.
    #    - do not reconnect after Activity recreation/rotation
    #    - cancel a pending delayed auto-connect when user leaves Home
    #    - cancel it when user manually chooses a profile
    #    - ensure the launch only happens while Home is foreground
    # ------------------------------------------------------------------
    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    data = replace_once(data,
        '\tprivate ExternalDisplayManager externalDisplayManager;\n',
        '\tprivate ExternalDisplayManager externalDisplayManager;\n\tprivate boolean autoConnectScheduled = false;\n',
        "add auto-connect state")
    data = replace_once(data,
        '\t\tmaybeTvAutoConnect(caller);\n',
        '\t\tif (savedInstanceState == null)\n\t\t\tmaybeTvAutoConnect(caller);\n',
        "avoid reconnect after Activity recreation")
    data = replace_once(data,
        '\t\t\t\t\texternalDisplayManager.launchSessionWithDisplayPicker(refStr);\n',
        '\t\t\t\t\tautoConnectScheduled = false;\n\t\t\t\t\texternalDisplayManager.launchSessionWithDisplayPicker(refStr);\n',
        "cancel pending auto-connect on manual connection")

    old_method = '''\tprivate void maybeTvAutoConnect(Intent caller)
\t{
\t\tif (caller != null && Intent.ACTION_VIEW.equals(caller.getAction())) return;
\t\tif (!ApplicationSettingsActivity.getTvAutoConnectEnabled(this)) return;
\t\tfinal String refStr = ApplicationSettingsActivity.getTvAutoConnectTarget(this);
\t\tif (refStr == null || refStr.isEmpty()) return;
\t\tfinal int delayMs = ApplicationSettingsActivity.getTvAutoConnectDelayMs(this);
\t\tbinding.getRoot().postDelayed(() -> {
\t\t\tif (isFinishing() || isDestroyed()) return;
\t\t\tLog.i(TAG, "TV auto-connect target: " + refStr);
\t\t\texternalDisplayManager.launchSessionWithDisplayPicker(refStr);
\t\t}, delayMs);
\t}

'''
    new_method = '''\tprivate void maybeTvAutoConnect(Intent caller)
\t{
\t\tif (autoConnectScheduled) return;
\t\tif (caller != null && Intent.ACTION_VIEW.equals(caller.getAction())) return;
\t\tif (!ApplicationSettingsActivity.getTvAutoConnectEnabled(this)) return;
\t\tfinal String refStr = ApplicationSettingsActivity.getTvAutoConnectTarget(this);
\t\tif (refStr == null || refStr.isEmpty()) return;
\t\tfinal int delayMs = ApplicationSettingsActivity.getTvAutoConnectDelayMs(this);
\t\tautoConnectScheduled = true;
\t\tbinding.getRoot().postDelayed(() -> {
\t\t\tif (!autoConnectScheduled) return;
\t\t\tautoConnectScheduled = false;
\t\t\tif (isFinishing() || isDestroyed()) return;
\t\t\tif (!getLifecycle().getCurrentState().isAtLeast(androidx.lifecycle.Lifecycle.State.RESUMED))
\t\t\t{
\t\t\t\tLog.i(TAG, "Auto-connect skipped: HomeActivity is not foreground");
\t\t\t\treturn;
\t\t\t}
\t\t\tLog.i(TAG, "Auto-connect target: " + refStr);
\t\t\texternalDisplayManager.launchSessionWithDisplayPicker(refStr);
\t\t}, Math.max(delayMs, 250));
\t}

'''
    data = replace_once(data, old_method, new_method, "harden auto-connect scheduling")

    resume_anchor = '''\t@Override protected void onResume()
\t{
'''
    pause_method = '''\t@Override protected void onPause()
\t{
\t\tautoConnectScheduled = false;
\t\tsuper.onPause();
\t}

'''
    data = replace_once(data, resume_anchor, pause_method + resume_anchor,
                        "cancel pending auto-connect when Home leaves foreground")
    write(home, data)

    # ------------------------------------------------------------------
    # 4. Settings UX: wording is device-neutral and the clear action is
    #    disabled when no auto-connect target exists.
    # ------------------------------------------------------------------
    appsettings = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/ApplicationSettingsActivity.java"
    data = read(appsettings)
    data = replace_once(data,
        '''\t\t\tif (clear != null)
\t\t\t{
\t\t\t\tclear.setOnPreferenceClickListener(pref -> {
\t\t\t\t\tclearTvAutoConnectTarget(requireContext());
''',
        '''\t\t\tif (clear != null)
\t\t\t{
\t\t\t\tclear.setEnabled(!getTvAutoConnectTarget(requireContext()).isEmpty());
\t\t\t\tclear.setOnPreferenceClickListener(pref -> {
\t\t\t\t\tclearTvAutoConnectTarget(requireContext());
\t\t\t\t\tpref.setEnabled(false);
''',
        "disable empty clear-target action")
    write(appsettings, data)

    strings = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(strings)
    replacements = {
        '<string name="settings_tv_start_on_boot">Start app after TV boot</string>':
            '<string name="settings_tv_start_on_boot">Start app after device boot</string>',
        '<string name="settings_tv_start_on_boot_summary">Open FreeRDP TV after Android boots. Automatic connection is controlled separately.</string>':
            '<string name="settings_tv_start_on_boot_summary">Open Baihong RDP REMOTE after Android boots. Automatic connection is controlled separately.</string>',
        '<string name="adaptive_first_run_title">FreeRDP Remote is ready</string>':
            '<string name="adaptive_first_run_title">Baihong RDP REMOTE is ready</string>'
    }
    for old, new in replacements.items():
        data = replace_once(data, old, new, "update English brand/wording")
    write(strings, data)

    zh_strings = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh_strings)
    replacements = {
        '<string name="settings_tv_start_on_boot">电视开机自动启动 APP</string>':
            '<string name="settings_tv_start_on_boot">设备开机自动启动 APP</string>',
        '<string name="settings_tv_start_on_boot_summary">开启后 Android 开机完成自动打开 FreeRDP TV；是否自动进入服务器由下面选项单独控制。</string>':
            '<string name="settings_tv_start_on_boot_summary">开启后 Android 开机完成自动打开百宏 RDP REMOTE；是否自动进入服务器由下面选项单独控制。</string>',
        '<string name="adaptive_first_run_title">FreeRDP Remote 已准备好</string>':
            '<string name="adaptive_first_run_title">百宏 RDP REMOTE 已准备好</string>'
    }
    for old, new in replacements.items():
        data = replace_once(data, old, new, "update Chinese brand/wording")
    write(zh_strings, data)

    print("Brand/UX patch applied:", VERSION)
    print("App: 百宏 RDP REMOTE")
    print("Fixes: system app label + vector icon + safe auto-connect + generic boot wording")


if __name__ == "__main__":
    main()
