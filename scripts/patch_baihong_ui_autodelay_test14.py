#!/usr/bin/env python3
import re
import sys
from pathlib import Path

VERSION = "3.31.1-baihong-a9-test14"
VERSION_CODE = "331114"
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


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_baihong_ui_autodelay_test14.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    # ------------------------------------------------------------------
    # Version + visible product name. Keep package/signing identity unchanged
    # so Test10+ profiles/settings can upgrade in place.
    # ------------------------------------------------------------------
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-billion-a9-test13",
                        "VERSION_NAME=" + VERSION, "update Test14 version")
    data = replace_once(data, "VERSION_CODE=331113", "VERSION_CODE=" + VERSION_CODE,
                        "update Test14 version code")
    write(props, data)

    app_strings = studio / "aFreeRDP/src/main/res/values/strings.xml"
    data = read(app_strings)
    data = replace_once(data,
                        '<string name="app_title" translatable="false">BILLION RDP REMOTE</string>',
                        '<string name="app_title" translatable="false">百宏RDP</string>',
                        "rename application label")
    write(app_strings, data)

    for rel in ["freeRDPCore/src/main/res/values/strings.xml",
                "freeRDPCore/src/main/res/values-zh/strings.xml"]:
        path = studio / rel
        data = read(path)
        data = data.replace("BILLION RDP REMOTE", BRAND)
        data = data.replace("Baihong RDP REMOTE", BRAND)
        data = data.replace("百宏 RDP REMOTE", BRAND)
        write(path, data)

    # ------------------------------------------------------------------
    # TV settings are reorganized around the actual installation workflow.
    # Startup-to-connect delay is now a true 0..120 second setting, adjustable
    # one second at a time with the TV remote left/right keys.
    # ------------------------------------------------------------------
    tv_xml = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    write(tv_xml, '''<?xml version="1.0" encoding="utf-8"?>
<PreferenceScreen xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">

    <PreferenceCategory android:title="@string/settings_tv_group_mode">
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
    </PreferenceCategory>

    <PreferenceCategory android:title="@string/settings_tv_group_boot">
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
        <SeekBarPreference
            android:key="tv.auto_connect_delay_seconds_v2"
            android:defaultValue="10"
            android:title="@string/settings_tv_connect_delay"
            android:summary="@string/settings_tv_connect_delay_summary"
            android:max="120"
            app:min="0"
            app:seekBarIncrement="1"
            app:showSeekBarValue="true"
            app:adjustable="true" />
        <Preference
            android:key="tv.clear_auto_connect_target"
            android:title="@string/settings_tv_clear_auto_target"
            android:summary="@string/settings_tv_clear_auto_target_summary" />
    </PreferenceCategory>

    <PreferenceCategory android:title="@string/settings_tv_group_display">
        <Preference
            android:key="ui.tv_continuous_display_status"
            android:title="@string/settings_tv_continuous_display"
            android:summary="@string/settings_tv_continuous_display_summary"
            android:selectable="false" />
        <Preference
            android:key="ui.tv_hd_display_status"
            android:title="@string/settings_tv_hd_display"
            android:summary="@string/settings_tv_hd_display_summary"
            android:selectable="false" />
        <ListPreference
            android:key="ui.floating_toolbar_mode"
            android:defaultValue="auto"
            android:title="@string/settings_floating_toolbar"
            android:summary="@string/settings_floating_toolbar_summary"
            android:entries="@array/floating_toolbar_entries"
            android:entryValues="@array/floating_toolbar_values"
            app:useSimpleSummaryProvider="true" />
    </PreferenceCategory>

    <PreferenceCategory android:title="@string/settings_tv_group_help">
        <Preference
            android:key="ui.tv_remote_help"
            android:title="@string/settings_tv_remote_help"
            android:summary="@string/settings_tv_remote_help_summary"
            android:selectable="false" />
    </PreferenceCategory>
</PreferenceScreen>
''')

    appsettings = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/ApplicationSettingsActivity.java"
    data = read(appsettings)

    # Migrate old fixed-choice delay before the new SeekBarPreference is inflated.
    create_anchor = '''\t\t@Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey)\n\t\t{\n\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);\n'''
    create_new = '''\t\t@Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey)\n\t\t{\n\t\t\tmigrateTvAutoConnectDelay(requireContext());\n\t\t\tsetPreferencesFromResource(R.xml.settings_app_tv, rootKey);\n'''
    data = replace_once(data, create_anchor, create_new,
                        "migrate auto-connect delay before TV settings inflate")

    old_delay = '''\tpublic static int getTvAutoConnectDelayMs(Context context)\n\t{\n\t\tString raw = get(context).getString("tv.auto_connect_delay", "5");\n\t\ttry\n\t\t{\n\t\t\tint seconds = Integer.parseInt(raw);\n\t\t\tif (seconds < 0) seconds = 0;\n\t\t\tif (seconds > 30) seconds = 30;\n\t\t\treturn seconds * 1000;\n\t\t}\n\t\tcatch (NumberFormatException e)\n\t\t{\n\t\t\treturn 5000;\n\t\t}\n\t}\n'''
    new_delay = '''\tpublic static void migrateTvAutoConnectDelay(Context context)\n\t{\n\t\tSharedPreferences prefs = get(context);\n\t\tif (prefs.contains("tv.auto_connect_delay_seconds_v2"))\n\t\t\treturn;\n\t\tint seconds = 10;\n\t\ttry\n\t\t{\n\t\t\tString legacy = prefs.getString("tv.auto_connect_delay", "10");\n\t\t\tseconds = Integer.parseInt(legacy);\n\t\t}\n\t\tcatch (Exception ignored)\n\t\t{\n\t\t\tseconds = 10;\n\t\t}\n\t\tif (seconds < 0) seconds = 0;\n\t\tif (seconds > 120) seconds = 120;\n\t\tprefs.edit().putInt("tv.auto_connect_delay_seconds_v2", seconds).apply();\n\t}\n\n\tpublic static int getTvAutoConnectDelaySeconds(Context context)\n\t{\n\t\tmigrateTvAutoConnectDelay(context);\n\t\tint seconds = get(context).getInt("tv.auto_connect_delay_seconds_v2", 10);\n\t\tif (seconds < 0) seconds = 0;\n\t\tif (seconds > 120) seconds = 120;\n\t\treturn seconds;\n\t}\n\n\tpublic static int getTvAutoConnectDelayMs(Context context)\n\t{\n\t\treturn getTvAutoConnectDelaySeconds(context) * 1000;\n\t}\n'''
    data = replace_once(data, old_delay, new_delay,
                        "replace fixed auto-connect delay with configurable seconds")
    write(appsettings, data)

    # ------------------------------------------------------------------
    # Home screen: cleaner TV layout, visible remote-control help and an
    # at-a-glance summary of the currently selected auto-connect profile/delay.
    # ------------------------------------------------------------------
    home_xml = studio / "freeRDPCore/src/main/res/layout/home.xml"
    write(home_xml, '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="#F4F6F8"
    android:fitsSystemWindows="true">

    <TextView
        android:id="@+id/tvHomeHint"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginLeft="16dp"
        android:layout_marginTop="12dp"
        android:layout_marginRight="16dp"
        android:paddingLeft="16dp"
        android:paddingTop="11dp"
        android:paddingRight="16dp"
        android:paddingBottom="11dp"
        android:background="@drawable/baihong_home_info_background"
        android:text="@string/home_tv_hint"
        android:textSize="16sp"
        android:textColor="#34383E"
        android:visibility="gone" />

    <TextView
        android:id="@+id/tvAutoConnectStatus"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginLeft="16dp"
        android:layout_marginTop="8dp"
        android:layout_marginRight="16dp"
        android:paddingLeft="16dp"
        android:paddingTop="10dp"
        android:paddingRight="16dp"
        android:paddingBottom="10dp"
        android:background="@drawable/baihong_auto_status_background"
        android:textSize="16sp"
        android:textStyle="bold"
        android:textColor="#8E0E15"
        android:visibility="gone" />

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/recyclerViewBookmarks"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:paddingTop="8dp"
        android:paddingBottom="16dp"
        android:clipToPadding="false" />
</LinearLayout>
''')

    write(studio / "freeRDPCore/src/main/res/drawable/baihong_home_info_background.xml", '''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="#FFFFFFFF" />
    <stroke android:width="1dp" android:color="#FFDDE1E6" />
    <corners android:radius="10dp" />
</shape>
''')
    write(studio / "freeRDPCore/src/main/res/drawable/baihong_auto_status_background.xml", '''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="#FFFFF1F2" />
    <stroke android:width="1dp" android:color="#FFE1A9AD" />
    <corners android:radius="10dp" />
</shape>
''')

    # Make TV connection rows look like distinct cards while retaining the
    # strong red remote-control focus introduced in Test12.
    focus_drawable = studio / "freeRDPCore/src/main/res/drawable/billion_bookmark_tv_focus.xml"
    write(focus_drawable, '''<?xml version="1.0" encoding="utf-8"?>
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:state_focused="true"><shape android:shape="rectangle"><solid android:color="#FFFFF0F1" /><stroke android:width="3dp" android:color="#FFB5121B" /><corners android:radius="10dp" /></shape></item>
    <item android:state_pressed="true"><shape android:shape="rectangle"><solid android:color="#FFFFE2E5" /><stroke android:width="3dp" android:color="#FFB5121B" /><corners android:radius="10dp" /></shape></item>
    <item><shape android:shape="rectangle"><solid android:color="#FFFFFFFF" /><stroke android:width="1dp" android:color="#FFE3E6EA" /><corners android:radius="10dp" /></shape></item>
</selector>
''')

    item = studio / "freeRDPCore/src/main/res/layout/bookmark_list_item.xml"
    data = read(item)
    data = replace_once(data,
        '    android:minHeight="?attr/listPreferredItemHeight">',
        '''    android:minHeight="76dp"\n    android:layout_marginLeft="16dp"\n    android:layout_marginTop="5dp"\n    android:layout_marginRight="16dp"\n    android:layout_marginBottom="5dp"\n    android:paddingLeft="8dp"\n    android:paddingRight="4dp">''',
        "make connection rows larger card-like items")
    data = replace_once(data,
        '            android:textAppearance="?android:attr/textAppearanceLarge" />',
        '''            android:textAppearance="?android:attr/textAppearanceLarge"\n            android:textSize="20sp"\n            android:textStyle="bold" />''',
        "increase primary connection text")
    data = replace_once(data,
        '            android:textAppearance="?android:attr/textAppearanceSmall" />',
        '''            android:textAppearance="?android:attr/textAppearanceSmall"\n            android:textSize="15sp" />''',
        "increase secondary connection text")
    write(item, data)

    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    if "import android.view.View;" not in data:
        data = replace_once(data, "import android.view.MenuItem;\n",
                            "import android.view.MenuItem;\nimport android.view.View;\n",
                            "import View for TV home status")

    setup_anchor = '''\t\tsetContentView(binding.getRoot());\n\t\tDeviceMode.maybeShowFirstRunGuide(this);\n'''
    setup_new = setup_anchor + '''\t\tconfigureBaihongHome();\n'''
    data = replace_once(data, setup_anchor, setup_new,
                        "configure polished TV home screen")

    resume_anchor = '''\t@Override protected void onResume()\n\t{\n'''
    methods = '''\tprivate void configureBaihongHome()\n\t{\n\t\tboolean tv = DeviceMode.isTv(this);\n\t\tbinding.tvHomeHint.setVisibility(tv ? View.VISIBLE : View.GONE);\n\t\tbinding.tvAutoConnectStatus.setVisibility(tv ? View.VISIBLE : View.GONE);\n\t\tif (tv)\n\t\t{\n\t\t\tbinding.recyclerViewBookmarks.setItemAnimator(null);\n\t\t\tupdateBaihongAutoConnectStatus();\n\t\t}\n\t}\n\n\tprivate void updateBaihongAutoConnectStatus()\n\t{\n\t\tif (!DeviceMode.isTv(this))\n\t\t\treturn;\n\t\tString target = ApplicationSettingsActivity.getTvAutoConnectTarget(this);\n\t\tString label = ApplicationSettingsActivity.getTvAutoConnectTargetLabel(this);\n\t\tboolean enabled = ApplicationSettingsActivity.getTvAutoConnectEnabled(this);\n\t\tif (!enabled || target == null || target.isEmpty())\n\t\t{\n\t\t\tbinding.tvAutoConnectStatus.setText(R.string.home_auto_connect_status_off);\n\t\t\treturn;\n\t\t}\n\t\tif (label == null || label.isEmpty())\n\t\t\tlabel = target;\n\t\tint seconds = ApplicationSettingsActivity.getTvAutoConnectDelaySeconds(this);\n\t\tbinding.tvAutoConnectStatus.setText(\n\t\t    getString(R.string.home_auto_connect_status_format, label, seconds));\n\t}\n\n'''
    data = replace_once(data, resume_anchor, methods + resume_anchor,
                        "add TV home status methods")

    load_line = '\t\tviewModel.loadBookmarks(viewModel.getCurrentQuery());\n'
    # There are two loadBookmarks calls in the class; onResume is the last one.
    pos = data.rfind(load_line)
    if pos < 0:
        fail("HomeActivity onResume loadBookmarks line not found")
    end = pos + len(load_line)
    data = data[:end] + '\t\tupdateBaihongAutoConnectStatus();\n' + data[end:]
    write(home, data)

    # ------------------------------------------------------------------
    # Clear, explicit Chinese/English wording for the new UI and branding.
    # ------------------------------------------------------------------
    en = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(en)
    for name, value in {
        "settings_cat_tv": "TV / automatic connection",
        "settings_tv_group_mode": "Device mode",
        "settings_tv_group_boot": "Startup and automatic connection",
        "settings_tv_group_display": "TV display",
        "settings_tv_group_help": "Remote-control guide",
        "settings_tv_start_on_boot": "Start 百宏RDP after device boot",
        "settings_tv_start_on_boot_summary": "Open 百宏RDP automatically after Android finishes booting. Automatic server connection is configured separately below.",
        "settings_tv_auto_connect": "Automatically connect after app starts",
        "settings_tv_auto_connect_summary": "When enabled, 百宏RDP opens the selected saved connection after the startup delay below.",
        "settings_tv_auto_target": "Automatic connection target",
        "settings_tv_auto_target_none": "Not selected. On the home screen, press Right on a saved connection and choose Set as automatic connection.",
        "settings_tv_connect_delay": "Startup-to-connect delay (seconds)",
        "settings_tv_connect_delay_summary": "Set 0–120 seconds. For TVs that start with the device, 10–30 seconds is recommended so Android and the network can finish starting.",
        "settings_tv_remote_help": "TV remote control",
        "settings_tv_remote_help_summary": "On a connection: OK connects; Right selects the three-dot menu; Left returns. In settings, use Up/Down to move and Left/Right to adjust values.",
        "home_tv_hint": "Remote: OK = connect   ·   Right = more actions   ·   Settings = startup / automatic connection",
        "home_auto_connect_status_off": "Automatic connection: not configured",
        "home_auto_connect_status_format": "Automatic connection: %1$s · connect %2$d seconds after app starts",
        "adaptive_first_run_title": "百宏RDP is ready",
        "accessibility_keyboard_label": "百宏RDP physical keyboard",
    }.items():
        data = set_string(data, name, value)
    write(en, data)

    zh = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh)
    for name, value in {
        "settings_cat_tv": "电视大屏与自动连接",
        "settings_tv_group_mode": "设备模式",
        "settings_tv_group_boot": "开机与自动连接",
        "settings_tv_group_display": "电视大屏显示",
        "settings_tv_group_help": "遥控器操作提示",
        "settings_tv_start_on_boot": "设备开机后自动启动百宏RDP",
        "settings_tv_start_on_boot_summary": "Android 开机完成后自动打开百宏RDP。是否自动进入服务器，由下面的自动连接设置单独控制。",
        "settings_tv_auto_connect": "软件启动后自动连接服务器",
        "settings_tv_auto_connect_summary": "开启后，百宏RDP启动完成会等待下面设定的秒数，然后自动进入指定连接。",
        "settings_tv_auto_target": "自动连接的远程主机",
        "settings_tv_auto_target_none": "尚未指定。回到首页，在远程主机上按右方向键进入三个点菜单，选择“设为自动连接”。",
        "settings_tv_connect_delay": "软件启动后等待多少秒自动连接",
        "settings_tv_connect_delay_summary": "可定义 0～120 秒，遥控器左右键逐秒调整。电视随设备开机时建议 10～30 秒，让系统和网络先启动稳定。",
        "settings_tv_remote_help": "电视遥控器操作",
        "settings_tv_remote_help_summary": "远程主机上：确认键直接连接；右方向键进入三个点菜单；左方向键返回。设置页面用上下键移动、左右键调整数值。",
        "home_tv_hint": "遥控器：确认键＝直接连接   ·   右方向键＝更多操作   ·   设置＝开机与自动连接",
        "home_auto_connect_status_off": "自动连接：尚未设置",
        "home_auto_connect_status_format": "自动连接：%1$s · 软件启动 %2$d 秒后进入",
        "adaptive_first_run_title": "百宏RDP 已准备好",
        "accessibility_keyboard_label": "百宏RDP 物理键盘",
        "dlg_title_exit": "退出百宏RDP？",
        "dlg_msg_exit": "确定要退出百宏RDP吗？",
    }.items():
        data = set_string(data, name, value)
    write(zh, data)

    print("Test14 Baihong branding/UI/autodelay patch applied:", VERSION)
    print("Visible app name: 百宏RDP")
    print("TV startup auto-connect delay: configurable 0..120 seconds")
    print("TV home/status/settings UI polished; Test13 localization and Test12 display UX retained")


if __name__ == "__main__":
    main()
