#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-adaptive-a9-test4"


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
        fail("usage: patch_adaptive_test4.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found: " + str(studio))

    # ------------------------------------------------------------------
    # 1. Version / package build metadata
    # ------------------------------------------------------------------
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-tv-a9-test3", "VERSION_NAME=3.31.1-adaptive-a9-test4", "update version name")
    data = replace_once(data, "VERSION_CODE=331103", "VERSION_CODE=331104", "update version code")
    write(props, data)

    # ------------------------------------------------------------------
    # 2. Adaptive device-mode runtime helper.
    #    Automatic detection is intentionally multi-signal because many
    #    OEM Chinese TVs do not expose every standard Android TV feature.
    # ------------------------------------------------------------------
    device_mode = r'''package com.freerdp.freerdpcore.presentation;

import android.app.Activity;
import android.app.UiModeManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.content.res.Configuration;

import androidx.appcompat.app.AlertDialog;
import androidx.preference.PreferenceManager;

import com.freerdp.freerdpcore.R;

public final class DeviceMode
{
    public static final String MODE_AUTO = "auto";
    public static final String MODE_TV = "tv";
    public static final String MODE_MOBILE = "mobile";
    private static final String KEY_DEVICE_MODE = "ui.device_mode";
    private static final String KEY_GUIDE_SHOWN = "ui.adaptive_guide_v1_shown";

    private DeviceMode() {}

    public static String getConfiguredMode(Context context)
    {
        return PreferenceManager.getDefaultSharedPreferences(context)
            .getString(KEY_DEVICE_MODE, MODE_AUTO);
    }

    public static boolean isPhysicalTv(Context context)
    {
        PackageManager pm = context.getPackageManager();

        UiModeManager uiMode = (UiModeManager) context.getSystemService(Context.UI_MODE_SERVICE);
        if (uiMode != null && uiMode.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION)
            return true;

        if (pm.hasSystemFeature(PackageManager.FEATURE_LEANBACK) ||
            pm.hasSystemFeature(PackageManager.FEATURE_TELEVISION) ||
            pm.hasSystemFeature("android.software.leanback_only"))
            return true;

        // Fallback for OEM TV firmware that fails to publish Leanback/UI mode.
        Configuration cfg = context.getResources().getConfiguration();
        boolean noTouch = !pm.hasSystemFeature(PackageManager.FEATURE_TOUCHSCREEN) ||
                          cfg.touchscreen == Configuration.TOUCHSCREEN_NOTOUCH;
        return noTouch && cfg.smallestScreenWidthDp >= 600;
    }

    public static boolean isTv(Context context)
    {
        return isTvForMode(context, getConfiguredMode(context));
    }

    public static boolean isTvForMode(Context context, String mode)
    {
        if (MODE_TV.equals(mode))
            return true;
        if (MODE_MOBILE.equals(mode))
            return false;
        return isPhysicalTv(context);
    }

    public static void applyActivityOrientation(Activity activity)
    {
        if (isTv(activity))
            activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        else
            activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
    }

    public static String getPhysicalEnvironmentSummary(Context context)
    {
        return context.getString(isPhysicalTv(context)
            ? R.string.settings_device_detected_tv
            : R.string.settings_device_detected_mobile);
    }

    public static String getEffectiveModeSummary(Context context, String mode)
    {
        return context.getString(isTvForMode(context, mode)
            ? R.string.settings_device_effective_tv
            : R.string.settings_device_effective_mobile);
    }

    public static void maybeShowFirstRunGuide(Activity activity)
    {
        var prefs = PreferenceManager.getDefaultSharedPreferences(activity);
        if (prefs.getBoolean(KEY_GUIDE_SHOWN, false))
            return;

        // Do not block an already configured automatic connection after an upgrade.
        if (prefs.getBoolean("tv.auto_connect_enabled", false))
        {
            prefs.edit().putBoolean(KEY_GUIDE_SHOWN, true).apply();
            return;
        }

        prefs.edit().putBoolean(KEY_GUIDE_SHOWN, true).apply();
        boolean tv = isTv(activity);
        int message = tv ? R.string.adaptive_first_run_tv : R.string.adaptive_first_run_mobile;

        new AlertDialog.Builder(activity)
            .setTitle(R.string.adaptive_first_run_title)
            .setMessage(message)
            .setPositiveButton(R.string.adaptive_first_run_continue, null)
            .setNeutralButton(R.string.adaptive_first_run_settings, (dialog, which) -> {
                activity.startActivity(new Intent(activity, ApplicationSettingsActivity.class));
            })
            .show();
    }
}
'''
    write(studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/DeviceMode.java", device_mode)

    # ------------------------------------------------------------------
    # 3. Replace hard-coded TV landscape with runtime orientation.
    # ------------------------------------------------------------------
    manifest = studio / "aFreeRDP/src/main/AndroidManifest.xml"
    data = read(manifest)
    data = data.replace('            android:screenOrientation="landscape"\n', '', 1)
    write(manifest, data)

    core_manifest = studio / "freeRDPCore/src/main/AndroidManifest.xml"
    data = read(core_manifest)
    data = replace_once(data,
        'android:name=".presentation.SessionActivity"\n            android:screenOrientation="landscape"',
        'android:name=".presentation.SessionActivity"',
        "remove fixed SessionActivity landscape")
    write(core_manifest, data)

    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    anchor = '''\t@Override public void onCreate(Bundle savedInstanceState)
\t{
\t\tsuper.onCreate(savedInstanceState);
\t\tbinding = HomeBinding.inflate(getLayoutInflater());
\t\tsetContentView(binding.getRoot());
'''
    replacement = '''\t@Override public void onCreate(Bundle savedInstanceState)
\t{
\t\tsuper.onCreate(savedInstanceState);
\t\tDeviceMode.applyActivityOrientation(this);
\t\tbinding = HomeBinding.inflate(getLayoutInflater());
\t\tsetContentView(binding.getRoot());
\t\tDeviceMode.maybeShowFirstRunGuide(this);
'''
    data = replace_once(data, anchor, replacement, "apply adaptive HomeActivity mode")
    write(home, data)

    session = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionActivity.java"
    data = read(session)
    anchor = '''\t@Override public void onCreate(Bundle savedInstanceState)
\t{
\t\tsuper.onCreate(savedInstanceState);

\t\thideSystemBars();
'''
    replacement = '''\t@Override public void onCreate(Bundle savedInstanceState)
\t{
\t\tsuper.onCreate(savedInstanceState);
\t\tDeviceMode.applyActivityOrientation(this);

\t\thideSystemBars();
'''
    data = replace_once(data, anchor, replacement, "apply adaptive SessionActivity mode")
    write(session, data)

    # ------------------------------------------------------------------
    # 4. Device mode selector + detection status in settings.
    # ------------------------------------------------------------------
    settings_xml = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    data = read(settings_xml)
    pref_screen = '''<PreferenceScreen xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">
'''
    adaptive_prefs = pref_screen + '''
    <ListPreference
        android:key="ui.device_mode"
        android:defaultValue="auto"
        android:title="@string/settings_device_mode"
        android:summary="@string/settings_device_mode_summary"
        android:entries="@array/device_mode_entries"
        android:entryValues="@array/device_mode_values"
        app:useSimpleSummaryProvider="true" />

    <Preference
        android:key="ui.device_detected"
        android:title="@string/settings_device_detected"
        android:summary="@string/settings_device_detected_mobile"
        android:selectable="false" />
'''
    data = replace_once(data, pref_screen, adaptive_prefs, "insert adaptive device preferences")
    write(settings_xml, data)

    appsettings = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/ApplicationSettingsActivity.java"
    data = read(appsettings)
    anchor = '''\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);
\t\t\tPreference target = findPreference("tv.auto_connect_target_display");
'''
    replacement = '''\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);

\t\t\tPreference detected = findPreference("ui.device_detected");
\t\t\tif (detected != null)
\t\t\t\tdetected.setSummary(DeviceMode.getPhysicalEnvironmentSummary(requireContext()));

\t\t\tPreference mode = findPreference("ui.device_mode");
\t\t\tif (mode != null)
\t\t\t{
\t\t\t\tmode.setOnPreferenceChangeListener((preference, newValue) -> {
\t\t\t\t\tString selected = String.valueOf(newValue);
\t\t\t\t\tToast.makeText(requireContext(),
\t\t\t\t\t    DeviceMode.getEffectiveModeSummary(requireContext(), selected),
\t\t\t\t\t    Toast.LENGTH_SHORT).show();
\t\t\t\t\treturn true;
\t\t\t\t});
\t\t\t}

\t\t\tPreference target = findPreference("tv.auto_connect_target_display");
'''
    data = replace_once(data, anchor, replacement, "show adaptive environment in settings")
    write(appsettings, data)

    # ------------------------------------------------------------------
    # 5. TV remote / D-pad usability: every saved connection row and the
    #    overflow menu can receive focus, while touch remains supported.
    # ------------------------------------------------------------------
    item = studio / "freeRDPCore/src/main/res/layout/bookmark_list_item.xml"
    data = read(item)
    root = '''    android:background="?attr/selectableItemBackground"
    android:minHeight="?attr/listPreferredItemHeight">
'''
    root_new = '''    android:background="?attr/selectableItemBackground"
    android:clickable="true"
    android:focusable="true"
    android:focusableInTouchMode="false"
    android:minHeight="?attr/listPreferredItemHeight">
'''
    data = replace_once(data, root, root_new, "make bookmark row D-pad focusable")
    data = replace_once(data,
        '''        android:focusable="false"
        android:focusableInTouchMode="false"
''',
        '''        android:clickable="true"
        android:focusable="true"
        android:focusableInTouchMode="false"
''',
        "make bookmark overflow D-pad focusable")
    write(item, data)

    # ------------------------------------------------------------------
    # 6. Localized strings. Neutral app name because one APK serves both.
    # ------------------------------------------------------------------
    strings = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(strings)
    data = replace_once(data,
        '<string name="settings_cat_tv">TV / Automatic connection</string>',
        '<string name="settings_cat_tv">Device / Automatic connection</string>',
        "rename adaptive settings category EN")
    en = '''
    <string name="settings_device_mode">Device mode</string>
    <string name="settings_device_mode_summary">Automatic is recommended. Override only if the device is detected incorrectly.</string>
    <string name="settings_device_detected">Hardware detection</string>
    <string name="settings_device_detected_tv">Detected as TV / large non-touch device</string>
    <string name="settings_device_detected_mobile">Detected as phone / tablet</string>
    <string name="settings_device_effective_tv">TV mode will be used when the next screen opens</string>
    <string name="settings_device_effective_mobile">Phone / tablet mode will be used when the next screen opens</string>
    <string-array name="device_mode_entries"><item>Automatic (recommended)</item><item>TV</item><item>Phone / tablet</item></string-array>
    <string-array name="device_mode_values"><item>auto</item><item>tv</item><item>mobile</item></string-array>
    <string name="adaptive_first_run_title">FreeRDP Remote is ready</string>
    <string name="adaptive_first_run_tv">TV mode was selected automatically. The app uses landscape layout and D-pad focus. Add one or more saved RDP / RemoteApp connections. From a saved connection menu you can choose which profile opens automatically. Boot start and automatic connection are separate options.</string>
    <string name="adaptive_first_run_mobile">Phone / tablet mode was selected automatically. Rotation remains adaptive and touch operation is retained. Add one or more saved RDP / RemoteApp connections. A saved profile can also be selected for automatic connection.</string>
    <string name="adaptive_first_run_continue">Continue</string>
    <string name="adaptive_first_run_settings">Settings</string>
'''
    data = insert_before_last(data, "</resources>", en, "add adaptive English strings")
    write(strings, data)

    zh_strings = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh_strings)
    data = replace_once(data,
        '<string name="settings_cat_tv">电视与自动连接</string>',
        '<string name="settings_cat_tv">设备与自动连接</string>',
        "rename adaptive settings category ZH")
    zh = '''
    <string name="settings_device_mode">设备模式</string>
    <string name="settings_device_mode_summary">推荐使用“自动”。只有设备识别不正确时才需要手工指定。</string>
    <string name="settings_device_detected">硬件识别结果</string>
    <string name="settings_device_detected_tv">已识别为电视 / 大屏无触摸设备</string>
    <string name="settings_device_detected_mobile">已识别为手机 / 平板</string>
    <string name="settings_device_effective_tv">下次打开页面将使用电视模式</string>
    <string name="settings_device_effective_mobile">下次打开页面将使用手机 / 平板模式</string>
    <string-array name="device_mode_entries"><item>自动（推荐）</item><item>电视</item><item>手机 / 平板</item></string-array>
    <string-array name="device_mode_values"><item>auto</item><item>tv</item><item>mobile</item></string-array>
    <string name="adaptive_first_run_title">FreeRDP Remote 已准备好</string>
    <string name="adaptive_first_run_tv">已自动进入电视模式：横屏显示，并加强遥控器方向键焦点。可以保存多个 RDP / RemoteApp 连接；在连接右侧菜单中可指定哪个配置自动进入。开机启动 APP 与自动连接服务器为两个独立开关。</string>
    <string name="adaptive_first_run_mobile">已自动进入手机 / 平板模式：保留自动旋转和触摸操作。可以保存多个 RDP / RemoteApp 连接，也可以指定其中一个作为 APP 启动后的自动连接目标。</string>
    <string name="adaptive_first_run_continue">继续</string>
    <string name="adaptive_first_run_settings">设置</string>
'''
    data = insert_before_last(data, "</resources>", zh, "add adaptive Chinese strings")
    write(zh_strings, data)

    app_strings = studio / "aFreeRDP/src/main/res/values/strings.xml"
    data = read(app_strings)
    data = replace_once(data,
        '<string name="app_title" translatable="false">FreeRDP TV</string>',
        '<string name="app_title" translatable="false">FreeRDP Remote</string>',
        "set neutral adaptive app title")
    write(app_strings, data)

    print("Adaptive patch applied:", VERSION)
    print("Automatic TV/mobile detection + manual override")
    print("TV: landscape + D-pad focus; Mobile: adaptive rotation + touch")
    print("RDP/RemoteApp + multiple profiles + explicit auto-connect + optional boot start")


if __name__ == "__main__":
    main()
