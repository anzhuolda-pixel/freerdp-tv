#!/usr/bin/env python3
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

VERSION = "3.31.1-billion-a9-test13"
VERSION_CODE = "331113"


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
    replacement = f'<string name="{name}">{value}</string>'
    if pattern.search(data):
        return pattern.sub(replacement, data, count=1)
    marker = "</resources>"
    pos = data.rfind(marker)
    if pos < 0:
        fail("strings.xml missing </resources>")
    return data[:pos] + "    " + replacement + "\n" + data[pos:]


def add_array_if_missing(data, name, items):
    if re.search(r'<string-array\s+name="' + re.escape(name) + r'"', data):
        return data
    lines = [f'    <string-array name="{name}">']
    lines.extend(f'        <item>{item}</item>' for item in items)
    lines.append("    </string-array>")
    block = "\n".join(lines) + "\n"
    pos = data.rfind("</resources>")
    if pos < 0:
        fail("strings.xml missing </resources>")
    return data[:pos] + block + data[pos:]


def audit_chinese_resources(en_path, zh_path):
    try:
        en_root = ET.parse(en_path).getroot()
        zh_root = ET.parse(zh_path).getroot()
    except ET.ParseError as exc:
        fail("resource XML parse failed: " + str(exc))

    zh_names = {
        node.attrib.get("name")
        for node in zh_root
        if node.tag in ("string", "string-array") and node.attrib.get("name")
    }
    missing = []
    for node in en_root:
        if node.tag not in ("string", "string-array"):
            continue
        if node.attrib.get("translatable") == "false":
            continue
        name = node.attrib.get("name")
        if name and name not in zh_names:
            missing.append(name)
    if missing:
        fail("Chinese localization still missing: " + ", ".join(sorted(missing)))


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_chinese_ui_test13.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    # Version.
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-billion-a9-test12",
                        "VERSION_NAME=" + VERSION, "update Test13 version")
    data = replace_once(data, "VERSION_CODE=331112", "VERSION_CODE=" + VERSION_CODE,
                        "update Test13 version code")
    write(props, data)

    # Remove the outdated upstream Help entry from the TV/mobile home toolbar.
    menu = studio / "freeRDPCore/src/main/res/menu/home_menu.xml"
    data = read(menu)
    help_item = '''\n    <item
        android:id="@+id/help"
        android:icon="@drawable/ic_menu_help"
        app:showAsAction="ifRoom"
        android:title="@string/menu_help" />'''
    data = replace_once(data, help_item, "", "remove Help toolbar item")
    write(menu, data)

    home = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HomeActivity.java"
    data = read(home)
    help_handler = '''\t\telse if (itemId == R.id.help)
\t\t{
\t\t\tIntent helpIntent = new Intent(this, HelpActivity.class);
\t\t\tstartActivity(helpIntent);
\t\t}
'''
    data = replace_once(data, help_handler, "", "remove Help click handler")
    write(home, data)

    manifest = studio / "freeRDPCore/src/main/AndroidManifest.xml"
    data = read(manifest)
    help_activity = '''        <activity
            android:exported="true"
            android:name=".presentation.HelpActivity"
            android:label="@string/title_help"
            android:theme="@style/Theme.Main"
            android:configChanges="orientation|keyboardHidden|screenSize" />
'''
    data = replace_once(data, help_activity, "", "remove Help activity manifest entry")
    write(manifest, data)

    # Remove Help Java/layout/assets so old English upstream content is not packaged.
    help_java = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/HelpActivity.java"
    if help_java.exists():
        help_java.unlink()
    help_layout = studio / "freeRDPCore/src/main/res/layout/activity_help.xml"
    if help_layout.exists():
        help_layout.unlink()
    assets = studio / "aFreeRDP/src/main/assets"
    if assets.is_dir():
        for child in list(assets.iterdir()):
            if child.is_dir() and (child.name == "help_page" or child.name.endswith("_help_page")):
                shutil.rmtree(child)

    # Fill every user-facing Chinese resource that upstream currently leaves to
    # English fallback. Also rewrite important feedback dialogs in plain Chinese.
    zh = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh)

    translations = {
        "save": "保存",
        "menu_search": "搜索",
        "bookmark_export": "分享连接配置",
        "export_failed": "分享连接配置失败。",
        "kbd_win_key": "Windows 键",
        "quick_connect_to": "连接到：%s",
        "settings_cat_scale": "缩放设置",
        "settings_scale": "显示缩放",
        "settings_scale_desktop": "远程桌面缩放",
        "settings_scale_device": "设备显示缩放",
        "settings_tlsSecLevel": "TLS 安全级别",
        "settings_tlsMinLevel": "最低 TLS 版本",
        "settings_redirect_camera": "重定向摄像头",
        "settings_redirect_printer": "重定向打印机",
        "settings_alternate_shell": "备用启动程序",
        "settings_cat_hyperv": "Hyper-V",
        "settings_cat_redirection": "设备与资源重定向",
        "settings_cat_session": "会话设置",
        "settings_vmconnect_mode": "Hyper-V 控制台（vmconnect）",
        "settings_vmconnect_guid": "虚拟机 ID（GUID）",
        "settings_ui_hide_navigation_bar": "隐藏导航栏",
        "settings_power_keep_screen_on_when_connected": "远程连接时保持屏幕常亮",
        "session_double_back_to_exit": "再按一次返回键断开远程连接",
        "settings_cat_experimental": "扩展功能",
        "settings_experimental_remoteapp": "RemoteApp 远程应用窗口",
        "settings_experimental_remoteapp_summary": "将服务器发布的 RemoteApp 作为独立窗口显示。",
        "experimental_feature_remoteapp": "RemoteApp",
        "settings_experimental_camera": "摄像头重定向",
        "settings_experimental_camera_summary": "将本机摄像头提供给远程会话使用。",
        "experimental_feature_camera": "摄像头重定向",
        "dlg_title_experimental_feature": "启用扩展功能",
        "dlg_msg_experimental_feature": "%1$s 当前未启用，请先在设置中启用后再使用。",
        "preference_title_client_name": "客户端名称",
        "settings_ui_fit_rounded_corners": "适配圆角屏幕",
        "pref_title_theme": "界面主题",
        "settings_loadBalanceInfo": "负载均衡信息",
        "select_display_title": "选择显示屏",
        "display_main_screen": "主显示屏",
        "print_notif_channel": "远程打印任务",
        "print_notif_title": "收到远程打印任务",
        "print_notif_open": "打开",
        "print_notif_print": "打印",
        "accessibility_keyboard_label": "BILLION RDP REMOTE 物理键盘",
        "accessibility_keyboard_description": "将物理键盘快捷键（例如 Windows 键）发送到远程桌面。",
        "pref_title_keyboard_accessibility": "物理键盘快捷键",
        "pref_summary_keyboard_accessibility": "将 Windows 键和系统快捷键发送到远程桌面，需要辅助功能权限。",

        # Important feedback / confirmation text.
        "error_bookmark_incomplete_title": "连接信息未完成",
        "error_bookmark_incomplete": "当前连接信息不完整。选择“继续”补充必填项，或选择“取消”放弃本次编辑。",
        "error_connection_failure": "无法连接到远程服务器。",
        "info_capabilities_changed": "服务器不支持原显示设置，已自动调整为兼容设置。",
        "info_reset_success": "证书缓存已清除。",
        "info_reset_failed": "证书缓存清除失败。",
        "dlg_title_verify_certificate": "确认服务器证书",
        "dlg_msg_verify_certificate": "无法验证远程服务器的身份。是否仍要继续连接？",
        "dlg_title_credentials": "请输入用户名和密码",
        "dlg_title_create_shortcut": "创建连接快捷方式",
        "dlg_msg_create_shortcut": "快捷方式名称：",
        "dlg_msg_connecting": "正在连接…",
        "dlg_title_save_bookmark": "保存连接设置？",
        "dlg_save_bookmark": "连接设置已修改，是否保存这些更改？",
        "dlg_title_exit": "退出 BILLION RDP REMOTE？",
        "dlg_msg_exit": "确定要退出 BILLION RDP REMOTE 吗？",
        "dlg_title_clear_cert_cache": "清除证书缓存？",
        "dlg_msg_clear_cert_cache": "确定要清除已保存的远程服务器证书缓存吗？",
        "settings_debug": "诊断设置",
        "debug_level": "诊断级别",
    }
    for name, value in translations.items():
        data = set_string(data, name, value)

    data = add_array_if_missing(data, "scale_mode_array",
                                ["100%", "140%", "180%", "自定义"])
    data = add_array_if_missing(data, "scale_device_array",
                                ["100%", "140%", "180%"])
    data = add_array_if_missing(data, "tlsSecLevel_array",
                                ["使用默认设置", "允许所有安全级别", "80 位", "112 位", "128 位", "192 位", "256 位"])
    data = add_array_if_missing(data, "tlsMinLevel_array",
                                ["使用默认设置", "TLS 1.0", "TLS 1.1", "TLS 1.2", "TLS 1.3"])
    data = add_array_if_missing(data, "pref_theme_entries",
                                ["跟随系统", "浅色", "深色"])
    write(zh, data)

    # Ensure a Chinese device cannot silently fall back to an English user-facing
    # resource after future upstream changes or patches.
    audit_chinese_resources(studio / "freeRDPCore/src/main/res/values/strings.xml", zh)

    print("Test13 Chinese UI patch applied:", VERSION)
    print("Help removed; user-facing feedback/settings resources audited for Chinese coverage")


if __name__ == "__main__":
    main()
