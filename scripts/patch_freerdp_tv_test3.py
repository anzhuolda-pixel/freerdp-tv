#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-tv-a9-test3"


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


def insert_before_last(data, marker, addition, desc):
    pos = data.rfind(marker)
    if pos < 0:
        fail(desc + ": marker not found")
    return data[:pos] + addition + data[pos:]


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_freerdp_tv_test3.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found: " + str(studio))

    write(studio / "release.properties", """COMPILE_API=37
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
VERSION_NAME=3.31.1-tv-a9-test3
VERSION_CODE=331103
""")

    session = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionActivity.java"
    data = read(session)
    data = replace_once(data, "getWindow().setNavigationBarContrastEnforced(false);", "if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)\n            getWindow().setNavigationBarContrastEnforced(false);", "guard API29 navigation-bar contrast call")
    write(session, data)

    exp_xml = studio / "freeRDPCore/src/main/res/xml/settings_app_experimental.xml"
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

    write(studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml", """<?xml version="1.0" encoding="utf-8"?>
<PreferenceScreen xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">
    <SwitchPreferenceCompat
        android:key="tv.start_on_boot"
        android:defaultValue="false"
        android:title="@string/settings_tv_start_on_boot"
        android:summary="@string/settings_tv_start_on_boot_summary" />
    <SwitchPreferenceCompat
        android:key="tv.auto_connect_enabled"
        android:defaultValue="false"
        android:title="@string/settings_tv_auto_connect"
        android:summary="@string/settings_tv_auto_connect_summary" />
    <Preference
        android:key="tv.auto_connect_target_display"
        android:title="@string/settings_tv_auto_target"
        android:summary="@string/settings_tv_auto_target_none"
        android:selectable="false" />
    <Preference
        android:key="tv.clear_auto_connect_target"
        android:title="@string/settings_tv_clear_auto_target"
        android:summary="@string/settings_tv_clear_auto_target_summary" />
    <ListPreference
        android:key="tv.auto_connect_delay"
        android:defaultValue="5"
        android:title="@string/settings_tv_connect_delay"
        android:entries="@array/tv_connect_delay_entries"
        android:entryValues="@array/tv_connect_delay_values"
        app:useSimpleSummaryProvider="true" />
</PreferenceScreen>
""")

    headers = studio / "freeRDPCore/src/main/res/xml/settings_app_headers.xml"
    data = read(headers)
    anchor = '''    <Preference
        android:icon="@drawable/ic_computer"
        android:key="settings.client"
        android:title="@string/settings_cat_client"
        app:fragment="com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity$ClientFragment" />
'''
    data = replace_once(data, anchor, anchor + '''
    <Preference
        android:icon="@drawable/ic_tune"
        android:key="settings.tv"
        android:title="@string/settings_cat_tv"
        app:fragment="com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity$TvFragment" />
''', "add TV settings header")
    write(headers, data)

    appsettings = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/ApplicationSettingsActivity.java"
    data = read(appsettings)
    power = '''\tpublic static class PowerFragment extends PreferenceFragmentCompat
\t{
\t\t@Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey)
\t\t{
\t\t\tsetPreferencesFromResource(R.xml.settings_app_power, rootKey);
\t\t}
\t}

\t// -------------------------------------------------------------------------
'''
    tv = power + '''
\tpublic static class TvFragment extends PreferenceFragmentCompat
\t{
\t\t@Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey)
\t\t{
\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);
\t\t\tPreference target = findPreference("tv.auto_connect_target_display");
\t\t\tif (target != null)
\t\t\t{
\t\t\t\tString label = getTvAutoConnectTargetLabel(requireContext());
\t\t\t\ttarget.setSummary(label.isEmpty() ? getString(R.string.settings_tv_auto_target_none) : label);
\t\t\t}
\t\t\tPreference clear = findPreference("tv.clear_auto_connect_target");
\t\t\tif (clear != null)
\t\t\t{
\t\t\t\tclear.setOnPreferenceClickListener(pref -> {
\t\t\t\t\tclearTvAutoConnectTarget(requireContext());
\t\t\t\t\tPreference display = findPreference("tv.auto_connect_target_display");
\t\t\t\t\tif (display != null)
\t\t\t\t\t\tdisplay.setSummary(R.string.settings_tv_auto_target_none);
\t\t\t\t\tToast.makeText(requireContext(), R.string.settings_tv_auto_target_cleared, Toast.LENGTH_SHORT).show();
\t\t\t\t\treturn true;
\t\t\t\t});
\t\t\t}
\t\t}
\t}

\t// -------------------------------------------------------------------------
'''
    data = replace_once(data, power, tv, "add TvFragment")
    defaults = '\t\tPreferenceManager.setDefaultValues(appContext, R.xml.settings_app_power, false);\n'
    data = replace_once(data, defaults, defaults + '\t\tPreferenceManager.setDefaultValues(appContext, R.xml.settings_app_tv, false);\n', "initialize TV defaults")
    helper_anchor = '''\tpublic static int getDisconnectTimeout(Context context)
\t{
'''
    helpers = '''\tpublic static boolean getTvAutoConnectEnabled(Context context)
\t{
\t\treturn get(context).getBoolean("tv.auto_connect_enabled", false);
\t}

\tpublic static boolean getTvStartOnBoot(Context context)
\t{
\t\treturn get(context).getBoolean("tv.start_on_boot", false);
\t}

\tpublic static int getTvAutoConnectDelayMs(Context context)
\t{
\t\tString raw = get(context).getString("tv.auto_connect_delay", "5");
\t\ttry
\t\t{
\t\t\tint seconds = Integer.parseInt(raw);
\t\t\tif (seconds < 0) seconds = 0;
\t\t\tif (seconds > 30) seconds = 30;
\t\t\treturn seconds * 1000;
\t\t}
\t\tcatch (NumberFormatException e)
\t\t{
\t\t\treturn 5000;
\t\t}
\t}

\tpublic static void setTvAutoConnectTarget(Context context, String ref, String label)
\t{
\t\tif (ref == null || ref.isEmpty()) return;
\t\tget(context).edit()
\t\t    .putString("tv.auto_connect_target_ref", ref)
\t\t    .putString("tv.auto_connect_target_label", label == null ? "" : label)
\t\t    .putBoolean("tv.auto_connect_enabled", true)
\t\t    .apply();
\t}

\tpublic static String getTvAutoConnectTarget(Context context)
\t{
\t\treturn get(context).getString("tv.auto_connect_target_ref", "");
\t}

\tpublic static String getTvAutoConnectTargetLabel(Context context)
\t{
\t\treturn get(context).getString("tv.auto_connect_target_label", "");
\t}

\tpublic static void clearTvAutoConnectTarget(Context context)
\t{
\t\tget(context).edit()
\t\t    .remove("tv.auto_connect_target_ref")
\t\t    .remove("tv.auto_connect_target_label")
\t\t    .putBoolean("tv.auto_connect_enabled", false)
\t\t    .apply();
\t}

\tpublic static void clearTvAutoConnectTargetIfMatches(Context context, String ref)
\t{
\t\tif (ref != null && ref.equals(getTvAutoConnectTarget(context)))
\t\t\tclearTvAutoConnectTarget(context);
\t}

'''
    data = replace_once(data, helper_anchor, helpers + helper_anchor, "add TV helpers")
    write(appsettings, data)

    context_menu = studio / "freeRDPCore/src/main/res/menu/bookmark_context_menu.xml"
    data = read(context_menu)
    edit_item = '''    <item
        android:id="@+id/bookmark_edit"
        app:showAsAction="ifRoom"
        android:title="@string/menu_edit" />
'''
    data = replace_once(data, edit_item, edit_item + '''
    <item
        android:id="@+id/bookmark_set_auto_connect"
        app:showAsAction="never"
        android:title="@string/bookmark_set_auto_connect" />
''', "add auto-connect menu item")
    write(context_menu, data)

    adapter = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/utils/BookmarkListAdapter.java"
    data = read(adapter)
    bookmark_import = 'import com.freerdp.freerdpcore.presentation.BookmarkActivity;\n'
    data = replace_once(data, bookmark_import, bookmark_import + 'import com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity;\n', "import TV settings in adapter")
    edit_case = '''\t\t\telse if (itemId == R.id.bookmark_edit)
\t\t\t{
\t\t\t\tBundle bundle = new Bundle();
\t\t\t\tbundle.putString(BookmarkActivity.PARAM_CONNECTION_REFERENCE, refStr);
\t\t\t\tIntent intent = new Intent(anchor.getContext(), BookmarkActivity.class);
\t\t\t\tintent.putExtras(bundle);
\t\t\t\tanchor.getContext().startActivity(intent);
\t\t\t\treturn true;
\t\t\t}
'''
    auto_case = '''\t\t\telse if (itemId == R.id.bookmark_set_auto_connect)
\t\t\t{
\t\t\t\tApplicationSettingsActivity.setTvAutoConnectTarget(anchor.getContext(), refStr, bookmark.getLabel());
\t\t\t\tandroid.widget.Toast.makeText(anchor.getContext(),
\t\t\t\t    anchor.getContext().getString(R.string.bookmark_auto_connect_set, bookmark.getLabel()),
\t\t\t\t    android.widget.Toast.LENGTH_SHORT).show();
\t\t\t\treturn true;
\t\t\t}
'''
    data = replace_once(data, edit_case, edit_case + auto_case, "handle auto-connect target")
    delete_case = '''\t\t\telse if (itemId == R.id.bookmark_delete)
\t\t\t{
\t\t\t\tif (callbacks != null)
\t\t\t\t\tcallbacks.onDelete(bookmarkId);
\t\t\t\treturn true;
\t\t\t}
'''
    delete_new = '''\t\t\telse if (itemId == R.id.bookmark_delete)
\t\t\t{
\t\t\t\tApplicationSettingsActivity.clearTvAutoConnectTargetIfMatches(anchor.getContext(), refStr);
\t\t\t\tif (callbacks != null)
\t\t\t\t\tcallbacks.onDelete(bookmarkId);
\t\t\t\treturn true;
\t\t\t}
'''
    data = replace_once(data, delete_case, delete_new, "clear auto-target when selected bookmark is deleted")
    write(adapter, data)

    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    back_anchor = '\t\tgetOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {\n'
    data = replace_once(data, back_anchor, '\t\tmaybeTvAutoConnect(caller);\n\n' + back_anchor, "call auto-connect")
    resume_anchor = '''\t@Override protected void onResume()
\t{
'''
    auto_method = '''\tprivate void maybeTvAutoConnect(Intent caller)
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
    data = replace_once(data, resume_anchor, auto_method + resume_anchor, "add auto-connect method")
    write(home, data)

    write(studio / "aFreeRDP/src/main/java/com/freerdp/afreerdp/TvBootReceiver.java", '''package com.freerdp.afreerdp;

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
        if (intent == null || !Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;
        if (!ApplicationSettingsActivity.getTvStartOnBoot(context)) return;
        Log.i(TAG, "Boot completed: launching FreeRDP TV");
        Intent launch = new Intent(context, HomeActivity.class);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        launch.putExtra("tv.boot_launch", true);
        context.startActivity(launch);
    }
}
''')

    manifest = studio / "aFreeRDP/src/main/AndroidManifest.xml"
    data = read(manifest)
    data = replace_once(data, '    android:installLocation="auto">\n', '''    android:installLocation="auto">

    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-feature android:name="android.software.leanback" android:required="false" />
    <uses-feature android:name="android.hardware.touchscreen" android:required="false" />
''', "add TV manifest features")
    launcher = '                <category android:name="android.intent.category.LAUNCHER" />\n'
    data = replace_once(data, launcher, launcher + '                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />\n', "add leanback launcher")
    home_name = '            android:name="com.freerdp.freerdpcore.presentation.HomeActivity"\n'
    data = replace_once(data, home_name, home_name + '            android:screenOrientation="landscape"\n', "lock HomeActivity landscape")
    provider = '''        <provider
            android:name="androidx.core.content.FileProvider"
'''
    receiver = '''        <receiver
            android:name="com.freerdp.afreerdp.TvBootReceiver"
            android:enabled="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
            </intent-filter>
        </receiver>

'''
    data = replace_once(data, provider, receiver + provider, "register boot receiver")
    write(manifest, data)

    core_manifest = studio / "freeRDPCore/src/main/AndroidManifest.xml"
    data = read(core_manifest)
    data = replace_once(data, 'android:name=".presentation.SessionActivity"', 'android:name=".presentation.SessionActivity"\n            android:screenOrientation="landscape"', "lock session landscape")
    write(core_manifest, data)

    en = '''
    <string name="settings_cat_tv">TV / Automatic connection</string>
    <string name="settings_tv_start_on_boot">Start app after TV boot</string>
    <string name="settings_tv_start_on_boot_summary">Open FreeRDP TV after Android boots. Automatic connection is controlled separately.</string>
    <string name="settings_tv_auto_connect">Automatically enter selected connection</string>
    <string name="settings_tv_auto_connect_summary">When the app opens, automatically connect to the explicitly selected RDP or RemoteApp profile.</string>
    <string name="settings_tv_auto_target">Automatic connection profile</string>
    <string name="settings_tv_auto_target_none">Not selected. From a saved connection menu choose Set as automatic connection.</string>
    <string name="settings_tv_clear_auto_target">Clear automatic connection profile</string>
    <string name="settings_tv_clear_auto_target_summary">Disable automatic connection and clear the selected profile.</string>
    <string name="settings_tv_auto_target_cleared">Automatic connection profile cleared</string>
    <string name="settings_tv_connect_delay">Automatic connection delay</string>
    <string name="bookmark_set_auto_connect">Set as automatic connection</string>
    <string name="bookmark_auto_connect_set">Automatic connection: %1$s</string>
    <string-array name="tv_connect_delay_entries"><item>Immediately</item><item>3 seconds</item><item>5 seconds</item><item>10 seconds</item><item>15 seconds</item></string-array>
    <string-array name="tv_connect_delay_values"><item>0</item><item>3</item><item>5</item><item>10</item><item>15</item></string-array>
'''
    strings = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(strings)
    write(strings, insert_before_last(data, "</resources>", en, "add English TV strings"))

    zh = '''
    <string name="settings_cat_tv">电视与自动连接</string>
    <string name="settings_tv_start_on_boot">电视开机自动启动 APP</string>
    <string name="settings_tv_start_on_boot_summary">开启后 Android 开机完成自动打开 FreeRDP TV；是否自动进入服务器由下面选项单独控制。</string>
    <string name="settings_tv_auto_connect">打开 APP 自动进入指定连接</string>
    <string name="settings_tv_auto_connect_summary">APP 启动时自动进入明确指定的 RDP 或 RemoteApp 配置，不会因手动连接其他服务器而改变。</string>
    <string name="settings_tv_auto_target">当前自动进入的连接</string>
    <string name="settings_tv_auto_target_none">尚未选择。回到连接列表，在已保存配置的菜单中选择“设为自动连接”。</string>
    <string name="settings_tv_clear_auto_target">清除自动连接配置</string>
    <string name="settings_tv_clear_auto_target_summary">关闭自动连接，并清除当前指定的服务器配置。</string>
    <string name="settings_tv_auto_target_cleared">已清除自动连接配置</string>
    <string name="settings_tv_connect_delay">自动连接延时</string>
    <string name="bookmark_set_auto_connect">设为自动连接</string>
    <string name="bookmark_auto_connect_set">已设为自动连接：%1$s</string>
    <string-array name="tv_connect_delay_entries"><item>立即</item><item>3 秒</item><item>5 秒</item><item>10 秒</item><item>15 秒</item></string-array>
    <string-array name="tv_connect_delay_values"><item>0</item><item>3</item><item>5</item><item>10</item><item>15</item></string-array>
'''
    zh_strings = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh_strings)
    write(zh_strings, insert_before_last(data, "</resources>", zh, "add Chinese TV strings"))

    app_strings = studio / "aFreeRDP/src/main/res/values/strings.xml"
    data = read(app_strings)
    data = replace_once(data, '<string name="app_title" translatable="false">aFreeRDP</string>', '<string name="app_title" translatable="false">FreeRDP TV</string>', "set app title")
    write(app_strings, data)

    print("FreeRDP TV patch applied:", VERSION)
    print("Android 9 / ARM32+ARM64 / RDP+RemoteApp")
    print("Multiple profiles + explicit auto-connect target + optional boot start")


if __name__ == "__main__":
    main()
