#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-billion-a9-test11"
VERSION_CODE = "331111"


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
        fail("usage: patch_tv_always_on_test11.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    # ------------------------------------------------------------------
    # Version bump. Test11 continues using the stable Test10 signing key.
    # ------------------------------------------------------------------
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-billion-a9-test10",
                        "VERSION_NAME=" + VERSION, "update Test11 version")
    data = replace_once(data, "VERSION_CODE=331110", "VERSION_CODE=" + VERSION_CODE,
                        "update Test11 version code")
    write(props, data)

    # ------------------------------------------------------------------
    # The TV/phone build only needs ARM. Apply ABI filters at the app module
    # too, so transitive AARs such as SQLCipher cannot bring x86/x86_64 JNI
    # libraries back into the universal APK.
    # ------------------------------------------------------------------
    app_gradle = studio / "aFreeRDP/build.gradle"
    data = read(app_gradle)
    anchor = '''    defaultConfig {\n        applicationId "com.freerdp.afreerdp"\n'''
    replacement = '''    defaultConfig {\n        applicationId "com.freerdp.afreerdp"\n        ndk {\n            abiFilters "armeabi-v7a", "arm64-v8a"\n        }\n'''
    data = replace_once(data, anchor, replacement, "limit application packaging to ARM ABIs")
    write(app_gradle, data)

    # ------------------------------------------------------------------
    # TV mode is a display appliance mode:
    #   * never start FreeRDP's screen-off disconnect timer
    #   * always request the Android window to keep the display awake
    # Phone/tablet behaviour remains user-configurable.
    # ------------------------------------------------------------------
    appsettings = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/ApplicationSettingsActivity.java"
    data = read(appsettings)

    main_old = '''\tpublic static class MainFragment extends PreferenceFragmentCompat\n\t{\n\t\t@Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey)\n\t\t{\n\t\t\tsetPreferencesFromResource(R.xml.settings_app_headers, rootKey);\n\t\t}\n\t}\n'''
    main_new = '''\tpublic static class MainFragment extends PreferenceFragmentCompat\n\t{\n\t\t@Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey)\n\t\t{\n\t\t\tsetPreferencesFromResource(R.xml.settings_app_headers, rootKey);\n\t\t\t// TV power behaviour is automatic in BILLION RDP REMOTE, so do not\n\t\t\t// expose a second power page whose unchecked defaults could confuse\n\t\t\t// installers. Phone/tablet users keep the original power controls.\n\t\t\tif (DeviceMode.isTv(requireContext()))\n\t\t\t{\n\t\t\t\tPreference power = findPreference("settings.power");\n\t\t\t\tif (power != null)\n\t\t\t\t\tgetPreferenceScreen().removePreference(power);\n\t\t\t}\n\t\t}\n\t}\n'''
    data = replace_once(data, main_old, main_new, "hide redundant power settings page on TV")

    old = '''\tpublic static int getDisconnectTimeout(Context context)\n\t{\n\t\tSharedPreferences preferences = get(context);\n\t\treturn preferences.getInt(\n\t\t    context.getString(R.string.preference_key_power_disconnect_timeout), 0);\n\t}\n'''
    new = '''\tpublic static int getDisconnectTimeout(Context context)\n\t{\n\t\t// TV/large-screen mode is intended for continuous public-display use.\n\t\t// Never disconnect an active RDP session merely because Android reports\n\t\t// the display as off or there has been no local remote-control input.\n\t\tif (DeviceMode.isTv(context))\n\t\t\treturn 0;\n\n\t\tSharedPreferences preferences = get(context);\n\t\treturn preferences.getInt(\n\t\t    context.getString(R.string.preference_key_power_disconnect_timeout), 0);\n\t}\n'''
    data = replace_once(data, old, new, "disable screen-off disconnect timeout on TV")

    old = '''\tpublic static boolean getKeepScreenOnWhenConnected(Context context)\n\t{\n\t\tSharedPreferences preferences = get(context);\n\t\treturn preferences.getBoolean(\n\t\t    context.getString(R.string.preference_key_power_keep_screen_on_when_connected), false);\n\t}\n'''
    new = '''\tpublic static boolean getKeepScreenOnWhenConnected(Context context)\n\t{\n\t\t// TV mode is a signage/display mode: keep the panel awake automatically.\n\t\tif (DeviceMode.isTv(context))\n\t\t\treturn true;\n\n\t\tSharedPreferences preferences = get(context);\n\t\treturn preferences.getBoolean(\n\t\t    context.getString(R.string.preference_key_power_keep_screen_on_when_connected), false);\n\t}\n'''
    data = replace_once(data, old, new, "force keep-screen-on setting on TV")
    write(appsettings, data)

    # ------------------------------------------------------------------
    # Keep the entire RDP SessionActivity awake in TV mode, including
    # connecting/reconnecting/error-dialog periods. Reassert on resume in
    # case an OEM firmware altered window flags while the activity was paused.
    # ------------------------------------------------------------------
    session = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionActivity.java"
    data = read(session)

    old = '''\t\tsuper.onCreate(savedInstanceState);\n\t\tDeviceMode.applyActivityOrientation(this);\n\n\t\thideSystemBars();\n'''
    new = '''\t\tsuper.onCreate(savedInstanceState);\n\t\tDeviceMode.applyActivityOrientation(this);\n\t\tif (DeviceMode.isTv(this))\n\t\t\tgetWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n\n\t\thideSystemBars();\n'''
    data = replace_once(data, old, new, "keep TV session awake from activity creation")

    old = '''\t@Override protected void onResume()\n\t{\n\t\tsuper.onResume();\n\t\tLog.v(TAG, "Session.onResume");\n\t\tactiveSession = this;\n\t}\n'''
    new = '''\t@Override protected void onResume()\n\t{\n\t\tsuper.onResume();\n\t\tLog.v(TAG, "Session.onResume");\n\t\tif (DeviceMode.isTv(this))\n\t\t\tgetWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n\t\tactiveSession = this;\n\t}\n'''
    data = replace_once(data, old, new, "reassert TV keep-awake on resume")

    old_clear = '''\t\tif (ApplicationSettingsActivity.getKeepScreenOnWhenConnected(this))\n\t\t{\n\t\t\tgetWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n\t\t}\n'''
    count = data.count(old_clear)
    if count < 1:
        fail("TV keep-awake disconnect clear block not found")
    new_clear = '''\t\tif (!DeviceMode.isTv(this) &&\n\t\t    ApplicationSettingsActivity.getKeepScreenOnWhenConnected(this))\n\t\t{\n\t\t\tgetWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n\t\t}\n'''
    data = data.replace(old_clear, new_clear)
    write(session, data)

    # ------------------------------------------------------------------
    # Make the automatic TV protection visible as status information rather
    # than another switch the installer has to remember to enable.
    # ------------------------------------------------------------------
    tv_xml = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    data = read(tv_xml)
    status_pref = '''\n    <Preference\n        android:key="ui.tv_continuous_display_status"\n        android:title="@string/settings_tv_continuous_display"\n        android:summary="@string/settings_tv_continuous_display_summary"\n        android:selectable="false" />\n\n'''
    data = insert_before_last(data, "</PreferenceScreen>", status_pref,
                              "add TV continuous-display status")
    write(tv_xml, data)

    en = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(en)
    en_add = '''\n    <string name="settings_tv_continuous_display">TV continuous-display protection</string>\n    <string name="settings_tv_continuous_display_summary">Automatic in TV mode: keeps the RDP screen awake and disables the screen-off disconnect timer. No extra switch is required.</string>\n'''
    data = insert_before_last(data, "</resources>", en_add,
                              "add TV continuous-display English strings")
    write(en, data)

    zh = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh)
    zh_add = '''\n    <string name="settings_tv_continuous_display">电视大屏持续显示保护</string>\n    <string name="settings_tv_continuous_display_summary">电视模式自动启用：RDP画面保持常亮，并禁用因屏幕关闭触发的会话断开计时，无需另外设置。</string>\n'''
    data = insert_before_last(data, "</resources>", zh_add,
                              "add TV continuous-display Chinese strings")
    write(zh, data)

    print("Test11 TV continuous-display patch applied")
    print("TV mode: keep screen awake + no screen-off disconnect timeout")
    print("TV settings simplified; APK packaging limited to ARMv7 + ARM64")


if __name__ == "__main__":
    main()
