#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-tv-a9-test2"

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
        fail("%s: expected 1 match, found %d" % (desc, count))
    return data.replace(old, new, 1)

def insert_before_last(data, marker, addition, desc):
    pos = data.rfind(marker)
    if pos < 0:
        fail(desc + ": marker not found")
    return data[:pos] + addition + data[pos:]

def main():
    if len(sys.argv) != 2:
        fail("usage: patch_freerdp_tv.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found: " + str(studio))

    release_properties = '''COMPILE_API=37
TARGET_API=28
MIN_API=28
TOOLS_VERSION=37.0.0
NDK_VERSION=29.0.13113456
CMAKE_VERSION=4.1.2
SPLIT_ENABLED=false
BUILD_UNIVERSAL=true
SPLIT_ARCHITECTURES=armeabi-v7a;arm64-v8a
ABI_FILTERS=armeabi-v7a;arm64-v8a
CMAKE_ARGUMENTS=-DWITH_FFMPEG=OFF;-DWITH_OPENH264=OFF;-DWITH_OPUS=OFF;-DWITH_WEBP=OFF;-DWITH_JPEG=OFF;-DWITH_PNG=OFF;-DWITH_CJSON=OFF;-DWITH_OPENSSL=ON
VERSION_NAME=3.31.1-tv-a9-test2
VERSION_CODE=331102
'''
    write(studio / "release.properties", release_properties)

    session = studio / "freeRDPCore" / "src" / "main" / "java" / "com" / "freerdp" / "freerdpcore" / "presentation" / "SessionActivity.java"
    data = read(session)
    old = "getWindow().setNavigationBarContrastEnforced(false);"
    new = '''if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
            getWindow().setNavigationBarContrastEnforced(false);'''
    data = replace_once(data, old, new, "guard API29 navigation-bar contrast call")
    write(session, data)

    exp_xml = studio / "freeRDPCore" / "src" / "main" / "res" / "xml" / "settings_app_experimental.xml"
    data = read(exp_xml)
    keypos = data.find('android:key="@string/preference_key_experimental_remoteapp"')
    if keypos < 0:
        fail("RemoteApp experimental preference key not found")
    start = data.rfind("<SwitchPreferenceCompat", 0, keypos)
    end = data.find("/>", keypos)
    if start < 0 or end < 0:
        fail("RemoteApp preference block not found")
    end += 2
    block = data[start:end]
    if 'android:defaultValue="false"' in block:
        block = block.replace('android:defaultValue="false"', 'android:defaultValue="true"', 1)
        data = data[:start] + block + data[end:]
        write(exp_xml, data)

    tv_settings_xml = '''<?xml version="1.0" encoding="utf-8"?>
<PreferenceScreen xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">

    <SwitchPreferenceCompat
        android:key="tv.auto_connect_last"
        android:defaultValue="false"
        android:title="@string/settings_tv_auto_connect"
        android:summary="@string/settings_tv_auto_connect_summary" />

    <SwitchPreferenceCompat
        android:key="tv.start_on_boot"
        android:defaultValue="false"
        android:title="@string/settings_tv_start_on_boot"
        android:summary="@string/settings_tv_start_on_boot_summary" />

    <ListPreference
        android:key="tv.auto_connect_delay"
        android:defaultValue="3"
        android:title="@string/settings_tv_connect_delay"
        android:entries="@array/tv_connect_delay_entries"
        android:entryValues="@array/tv_connect_delay_values"
        app:useSimpleSummaryProvider="true" />

</PreferenceScreen>
'''
    write(studio / "freeRDPCore" / "src" / "main" / "res" / "xml" / "settings_app_tv.xml", tv_settings_xml)

    headers = studio / "freeRDPCore" / "src" / "main" / "res" / "xml" / "settings_app_headers.xml"
    data = read(headers)
    anchor = '''    <Preference
        android:icon="@drawable/ic_computer"
        android:key="settings.client"
        android:title="@string/settings_cat_client"
        app:fragment="com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity$ClientFragment" />
'''
    addition = anchor + '''
    <Preference
        android:icon="@drawable/ic_tune"
        android:key="settings.tv"
        android:title="@string/settings_cat_tv"
        app:fragment="com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity$TvFragment" />
'''
    data = replace_once(data, anchor, addition, "add TV settings header")
    write(headers, data)

    appsettings = studio / "freeRDPCore" / "src" / "main" / "java" / "com" / "freerdp" / "freerdpcore" / "presentation" / "ApplicationSettingsActivity.java"
    data = read(appsettings)

    power_fragment = '''\tpublic static class PowerFragment extends PreferenceFragmentCompat
\t{
\t\t@Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey)
\t\t{
\t\t\tsetPreferencesFromResource(R.xml.settings_app_power, rootKey);
\t\t}
\t}

\t// -------------------------------------------------------------------------
'''
    tv_fragment = power_fragment + '''
\tpublic static class TvFragment extends PreferenceFragmentCompat
\t{
\t\t@Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey)
\t\t{
\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);
\t\t}
\t}

\t// -------------------------------------------------------------------------
'''
    data = replace_once(data, power_fragment, tv_fragment, "add TvFragment")

    defaults = '''\t\tPreferenceManager.setDefaultValues(appContext, R.xml.settings_app_power, false);
'''
    data = replace_once(data, defaults, defaults + '''\t\tPreferenceManager.setDefaultValues(appContext, R.xml.settings_app_tv, false);
''', "initialize TV preference defaults")

    helper_anchor = '''\tpublic static int getDisconnectTimeout(Context context)
\t{
'''
    helpers = '''\tpublic static boolean getTvAutoConnect(Context context)
\t{
\t\treturn get(context).getBoolean("tv.auto_connect_last", false);
\t}

\tpublic static boolean getTvStartOnBoot(Context context)
\t{
\t\treturn get(context).getBoolean("tv.start_on_boot", false);
\t}

\tpublic static int getTvAutoConnectDelayMs(Context context)
\t{
\t\tString raw = get(context).getString("tv.auto_connect_delay", "3");
\t\ttry
\t\t{
\t\t\tint seconds = Integer.parseInt(raw);
\t\t\tif (seconds < 0)
\t\t\t\tseconds = 0;
\t\t\tif (seconds > 30)
\t\t\t\tseconds = 30;
\t\t\treturn seconds * 1000;
\t\t}
\t\tcatch (NumberFormatException e)
\t\t{
\t\t\treturn 3000;
\t\t}
\t}

\tpublic static void setTvLastConnection(Context context, String connectionReference)
\t{
\t\tif (connectionReference == null)
\t\t\treturn;
\t\tget(context).edit().putString("tv.last_connection_ref", connectionReference).apply();
\t}

\tpublic static String getTvLastConnection(Context context)
\t{
\t\treturn get(context).getString("tv.last_connection_ref", "");
\t}

''' + helper_anchor
    data = replace_once(data, helper_anchor, helpers, "add TV preference helper methods")
    write(appsettings, data)

    home = studio / "freeRDPCore" / "src" / "main" / "java" / "com" / "freerdp" / "freerdpcore" / "presentation" / "HomeActivity.java"
    data = read(home)
    click = '''\t\t\t\t\texternalDisplayManager.launchSessionWithDisplayPicker(refStr);
'''
    click_new = '''\t\t\t\t\tApplicationSettingsActivity.setTvLastConnection(HomeActivity.this, refStr);
\t\t\t\t\texternalDisplayManager.launchSessionWithDisplayPicker(refStr);
'''
    data = replace_once(data, click, click_new, "remember last manually launched connection")

    call_anchor = '''\t\tgetOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
'''
    call_new = '''\t\tmaybeTvAutoConnect(caller);

''' + call_anchor
    data = replace_once(data, call_anchor, call_new, "invoke TV auto-connect")

    method_anchor = '''\t@Override protected void onResume()
\t{
'''
    method = '''\tprivate void maybeTvAutoConnect(Intent caller)
\t{
\t\tif (caller != null && Intent.ACTION_VIEW.equals(caller.getAction()))
\t\t\treturn;
\t\tif (!ApplicationSettingsActivity.getTvAutoConnect(this))
\t\t\treturn;

\t\tfinal String refStr = ApplicationSettingsActivity.getTvLastConnection(this);
\t\tif (refStr == null || refStr.isEmpty())
\t\t\treturn;

\t\tfinal int delayMs = ApplicationSettingsActivity.getTvAutoConnectDelayMs(this);
\t\tbinding.getRoot().postDelayed(() -> {
\t\t\tif (isFinishing() || isDestroyed())
\t\t\t\treturn;
\t\t\tLog.i(TAG, "TV auto-connect: " + refStr);
\t\t\texternalDisplayManager.launchSessionWithDisplayPicker(refStr);
\t\t}, delayMs);
\t}

''' + method_anchor
    data = replace_once(data, method_anchor, method, "add TV auto-connect method")
    write(home, data)

    receiver = '''package com.freerdp.afreerdp;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity;
import com.freerdp.freerdpcore.presentation.HomeActivity;

public class TvBootReceiver extends BroadcastReceiver
{
    private static final String TAG = "TvBootReceiver";

    @Override public void onReceive(Context context, Intent intent)
    {
        if (intent == null || !Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction()))
            return;
        if (!ApplicationSettingsActivity.getTvStartOnBoot(context))
            return;

        Log.i(TAG, "Boot completed: launching FreeRDP TV");
        Intent launch = new Intent(context, HomeActivity.class);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        launch.putExtra("tv.boot_launch", true);
        context.startActivity(launch);
    }
}
'''
    write(studio / "aFreeRDP" / "src" / "main" / "java" / "com" / "freerdp" / "afreerdp" / "TvBootReceiver.java", receiver)

    manifest = studio / "aFreeRDP" / "src" / "main" / "AndroidManifest.xml"
    data = read(manifest)
    marker = '''    android:installLocation="auto">
'''
    features = '''    android:installLocation="auto">

    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-feature android:name="android.software.leanback" android:required="false" />
    <uses-feature android:name="android.hardware.touchscreen" android:required="false" />
'''
    data = replace_once(data, marker, features, "add TV features and boot permission")

    launcher = '''                <category android:name="android.intent.category.LAUNCHER" />
'''
    launcher_new = launcher + '''                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />
'''
    data = replace_once(data, launcher, launcher_new, "add TV launcher category")

    home_activity = '''            android:name="com.freerdp.freerdpcore.presentation.HomeActivity"
'''
    data = replace_once(data, home_activity, home_activity + '''            android:screenOrientation="landscape"
''', "lock home screen landscape")

    provider_anchor = '''        <provider
            android:name="androidx.core.content.FileProvider"
'''
    receiver_manifest = '''        <receiver
            android:name="com.freerdp.afreerdp.TvBootReceiver"
            android:enabled="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
            </intent-filter>
        </receiver>

''' + provider_anchor
    data = replace_once(data, provider_anchor, receiver_manifest, "register boot receiver")
    write(manifest, data)

    core_manifest = studio / "freeRDPCore" / "src" / "main" / "AndroidManifest.xml"
    data = read(core_manifest)
    session_name = '''android:name=".presentation.SessionActivity"'''
    if 'android:screenOrientation="landscape"' not in data:
        data = replace_once(data, session_name, session_name + '\n            android:screenOrientation="landscape"', "lock SessionActivity landscape")
    write(core_manifest, data)

    strings = studio / "freeRDPCore" / "src" / "main" / "res" / "values" / "strings.xml"
    data = read(strings)
    en = '''
    <string name="settings_cat_tv">TV / Automatic connection</string>
    <string name="settings_tv_auto_connect">Auto-connect last server</string>
    <string name="settings_tv_auto_connect_summary">On the next app launch, automatically open the last manually used RDP or RemoteApp connection.</string>
    <string name="settings_tv_start_on_boot">Start after TV boot</string>
    <string name="settings_tv_start_on_boot_summary">Open FreeRDP TV after Android finishes booting. Enable Auto-connect last server to enter RDP automatically.</string>
    <string name="settings_tv_connect_delay">Auto-connect delay</string>
    <string-array name="tv_connect_delay_entries">
        <item>Immediately</item>
        <item>3 seconds</item>
        <item>5 seconds</item>
        <item>10 seconds</item>
        <item>15 seconds</item>
    </string-array>
    <string-array name="tv_connect_delay_values">
        <item>0</item>
        <item>3</item>
        <item>5</item>
        <item>10</item>
        <item>15</item>
    </string-array>
'''
    data = insert_before_last(data, "</resources>", en, "add English TV strings")
    write(strings, data)

    zh_strings = studio / "freeRDPCore" / "src" / "main" / "res" / "values-zh" / "strings.xml"
    data = read(zh_strings)
    zh = '''
    <string name="settings_cat_tv">电视与自动连接</string>
    <string name="settings_tv_auto_connect">启动时自动连接上次服务器</string>
    <string name="settings_tv_auto_connect_summary">下次打开 APP 时，自动进入上一次手动打开的 RDP 或 RemoteApp 连接。</string>
    <string name="settings_tv_start_on_boot">电视开机自动启动</string>
    <string name="settings_tv_start_on_boot_summary">Android 开机完成后自动打开 FreeRDP TV；同时开启自动连接即可开机后自动进入服务器。</string>
    <string name="settings_tv_connect_delay">自动连接延时</string>
    <string-array name="tv_connect_delay_entries">
        <item>立即</item>
        <item>3 秒</item>
        <item>5 秒</item>
        <item>10 秒</item>
        <item>15 秒</item>
    </string-array>
    <string-array name="tv_connect_delay_values">
        <item>0</item>
        <item>3</item>
        <item>5</item>
        <item>10</item>
        <item>15</item>
    </string-array>
'''
    data = insert_before_last(data, "</resources>", zh, "add Chinese TV strings")
    write(zh_strings, data)

    app_strings = studio / "aFreeRDP" / "src" / "main" / "res" / "values" / "strings.xml"
    data = read(app_strings)
    data = replace_once(data, '<string name="app_title" translatable="false">aFreeRDP</string>', '<string name="app_title" translatable="false">FreeRDP TV</string>', "set app title")
    write(app_strings, data)

    print("FreeRDP TV patch applied:", VERSION)
    print("Android 9 / ARM32+ARM64 / RDP+RemoteApp / auto-connect / boot autostart")

if __name__ == "__main__":
    main()
