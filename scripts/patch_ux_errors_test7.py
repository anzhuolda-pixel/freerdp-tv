#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-billion-a9-test7"


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
        fail("usage: patch_ux_errors_test7.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found: " + str(studio))

    # ------------------------------------------------------------------
    # 1. Version
    # ------------------------------------------------------------------
    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data,
        "VERSION_NAME=3.31.1-billion-a9-test6",
        VERSION,
        "update Test7 version name")
    data = replace_once(data, "VERSION_CODE=331106", "VERSION_CODE=331107",
                        "update Test7 version code")
    write(props, data)

    # ------------------------------------------------------------------
    # 2. Connection editor wording: user-facing terms, not protocol jargon.
    # ------------------------------------------------------------------
    zh = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh)
    replacements = {
        '<string name="settings_cat_host">主机</string>':
            '<string name="settings_cat_host">连接信息</string>',
        '<string name="settings_label">标签</string>':
            '<string name="settings_label">连接名称</string>',
        '<string name="settings_hostname">主机名</string>':
            '<string name="settings_hostname">服务器地址（IP / 主机名）</string>',
        '<string name="settings_port">端口</string>':
            '<string name="settings_port">端口（默认 3389）</string>',
        '<string name="settings_cat_credentials">凭据</string>':
            '<string name="settings_cat_credentials">账号信息</string>',
        '<string name="settings_credentials">凭据</string>':
            '<string name="settings_credentials">用户名与密码</string>',
        '<string name="settings_domain">域名</string>':
            '<string name="settings_domain">域（可选）</string>',
        '<string name="settings_cat_settings">设置</string>':
            '<string name="settings_cat_settings">显示与高级设置</string>',
        '<string name="settings_screen">屏幕</string>':
            '<string name="settings_screen">显示设置</string>',
        '<string name="settings_performance">性能</string>':
            '<string name="settings_performance">性能设置</string>',
        '<string name="settings_advanced">高级</string>':
            '<string name="settings_advanced">高级设置</string>'
    }
    for old, new in replacements.items():
        data = replace_once(data, old, new, "improve Chinese connection wording")

    extra_zh = '''
    <string name="settings_label_hint">例如：ERP服务器、办公服务器</string>
    <string name="settings_hostname_hint">例如：192.168.88.241 或 server01</string>
    <string name="settings_not_set">未设置</string>

    <string name="rdp_error_title">连接失败</string>
    <string name="rdp_error_back">返回连接列表</string>
    <string name="rdp_error_edit">修改连接信息</string>
    <string name="rdp_error_wrong_password">密码错误，请重新检查密码后再连接。</string>
    <string name="rdp_error_logon_failure">用户名或密码错误，请检查账号信息后重试。</string>
    <string name="rdp_error_auth_failed">身份验证失败，请检查用户名、密码以及域设置。</string>
    <string name="rdp_error_missing_credentials">未填写完整的登录账号或密码。</string>
    <string name="rdp_error_account_disabled">此账号已被禁用，请联系服务器管理员。</string>
    <string name="rdp_error_account_locked">此账号已被锁定，请稍后重试或联系服务器管理员。</string>
    <string name="rdp_error_password_expired">账号密码已过期，请先修改密码。</string>
    <string name="rdp_error_password_change">此账号必须先修改密码，修改后才能远程登录。</string>
    <string name="rdp_error_account_expired">此账号已过期，请联系服务器管理员。</string>
    <string name="rdp_error_access_denied">此账号没有远程桌面登录权限，请检查服务器远程登录权限。</string>
    <string name="rdp_error_account_restriction">此账号受到登录策略限制，当前不允许远程登录。</string>
    <string name="rdp_error_server_not_found">找不到服务器。请检查服务器地址（IP / 主机名）是否填写正确。</string>
    <string name="rdp_error_network">无法连接到服务器。请检查服务器 IP / 主机名、3389 端口以及网络是否正常。</string>
    <string name="rdp_error_security">服务器安全协商失败。请检查服务器的 RDP / NLA / TLS 设置。</string>
    <string name="rdp_error_domain_service">无法联系域身份验证服务，请检查服务器网络、DNS 和域环境。</string>
    <string name="rdp_error_remoteapp">服务器未正确启用 RemoteApp，或当前 RemoteApp 发布配置不可用。</string>
    <string name="rdp_error_generic">连接服务器失败。请检查服务器地址、端口、网络以及登录账号。</string>

    <string name="about_product_desc">RDP 与 RemoteApp 远程访问客户端</string>
    <string name="about_version_format">版本：%1$s</string>
    <string name="about_device_format">设备：%1$s</string>
    <string name="about_android_format">Android：%1$s</string>
    <string name="about_features">支持 RDP / RemoteApp · 手机 / 平板 / 电视自适应</string>
'''
    data = insert_before_last(data, "</resources>", extra_zh, "add Test7 Chinese strings")
    write(zh, data)

    en = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(en)
    replacements = {
        '<string name="settings_cat_host">Host</string>': '<string name="settings_cat_host">Connection</string>',
        '<string name="settings_label">Label</string>': '<string name="settings_label">Connection name</string>',
        '<string name="settings_hostname">Hostname</string>': '<string name="settings_hostname">Server address (IP / hostname)</string>',
        '<string name="settings_port">Port</string>': '<string name="settings_port">Port (default 3389)</string>',
        '<string name="settings_cat_credentials">Credentials</string>': '<string name="settings_cat_credentials">Account</string>',
        '<string name="settings_credentials">Credentials</string>': '<string name="settings_credentials">Username and password</string>',
        '<string name="settings_domain">Domain</string>': '<string name="settings_domain">Domain (optional)</string>'
    }
    for old, new in replacements.items():
        if old in data:
            data = replace_once(data, old, new, "improve English connection wording")

    extra_en = '''
    <string name="settings_label_hint">Example: ERP server, Office server</string>
    <string name="settings_hostname_hint">Example: 192.168.88.241 or server01</string>
    <string name="settings_not_set">Not set</string>

    <string name="rdp_error_title">Connection failed</string>
    <string name="rdp_error_back">Back to connections</string>
    <string name="rdp_error_edit">Edit connection</string>
    <string name="rdp_error_wrong_password">The password is incorrect. Check the password and try again.</string>
    <string name="rdp_error_logon_failure">The username or password is incorrect. Check the account and try again.</string>
    <string name="rdp_error_auth_failed">Authentication failed. Check the username, password, and domain.</string>
    <string name="rdp_error_missing_credentials">The username or password is missing.</string>
    <string name="rdp_error_account_disabled">This account is disabled. Contact the server administrator.</string>
    <string name="rdp_error_account_locked">This account is locked. Try again later or contact the server administrator.</string>
    <string name="rdp_error_password_expired">The password has expired. Change it before connecting.</string>
    <string name="rdp_error_password_change">This account must change its password before remote sign-in.</string>
    <string name="rdp_error_account_expired">This account has expired. Contact the server administrator.</string>
    <string name="rdp_error_access_denied">This account is not permitted to sign in with Remote Desktop.</string>
    <string name="rdp_error_account_restriction">This account is restricted by sign-in policy.</string>
    <string name="rdp_error_server_not_found">Server not found. Check the server IP address or hostname.</string>
    <string name="rdp_error_network">Cannot reach the server. Check the IP / hostname, port 3389, and network.</string>
    <string name="rdp_error_security">RDP security negotiation failed. Check the server RDP / NLA / TLS settings.</string>
    <string name="rdp_error_domain_service">The domain authentication service cannot be reached. Check network, DNS, and domain connectivity.</string>
    <string name="rdp_error_remoteapp">RemoteApp is not enabled correctly on the server or the published app is unavailable.</string>
    <string name="rdp_error_generic">Could not connect. Check the server address, port, network, and sign-in account.</string>

    <string name="about_product_desc">RDP and RemoteApp remote access client</string>
    <string name="about_version_format">Version: %1$s</string>
    <string name="about_device_format">Device: %1$s</string>
    <string name="about_android_format">Android: %1$s</string>
    <string name="about_features">RDP / RemoteApp · adaptive phone / tablet / TV interface</string>
'''
    data = insert_before_last(data, "</resources>", extra_en, "add Test7 English strings")
    write(en, data)

    # Remove developer/debug entry from normal connection editing UI.
    settings_xml = studio / "freeRDPCore/src/main/res/xml/bookmark_settings.xml"
    data = read(settings_xml)
    debug_block = '''\n        <Preference\n            android:key="bookmark.debug"\n            android:title="@string/settings_debug"\n            app:fragment="com.freerdp.freerdpcore.presentation.BookmarkActivity$DebugFragment" />\n'''
    if debug_block in data:
        data = data.replace(debug_block, "", 1)
    write(settings_xml, data)

    # Fix hard-coded English category in credentials page.
    credentials_xml = studio / "freeRDPCore/src/main/res/xml/credentials_settings.xml"
    data = read(credentials_xml)
    data = replace_once(data,
        '<PreferenceCategory android:title="Credentials">',
        '<PreferenceCategory android:title="@string/settings_cat_credentials">',
        "localize credentials category")
    write(credentials_xml, data)

    # Add empty-value guidance and remove '<none>' from Chinese/TV UI.
    bookmark_activity = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/BookmarkActivity.java"
    data = read(bookmark_activity)
    main_anchor = '''\t\t\tsetPreferencesFromResource(R.xml.bookmark_settings, rootKey);\n\n\t\t\tPreference credPref = findPreference("bookmark.credentials");\n'''
    main_new = '''\t\t\tsetPreferencesFromResource(R.xml.bookmark_settings, rootKey);\n\n\t\t\tPreference labelPref = findPreference("bookmark.label");\n\t\t\tif (labelPref != null)\n\t\t\t{\n\t\t\t\tlabelPref.setSummaryProvider(preference -> {\n\t\t\t\t\tString value = getPreferenceManager().getSharedPreferences()\n\t\t\t\t\t    .getString("bookmark.label", "");\n\t\t\t\t\treturn value.isEmpty() ? getString(R.string.settings_label_hint) : value;\n\t\t\t\t});\n\t\t\t}\n\n\t\t\tPreference hostPref = findPreference("bookmark.hostname");\n\t\t\tif (hostPref != null)\n\t\t\t{\n\t\t\t\thostPref.setSummaryProvider(preference -> {\n\t\t\t\t\tString value = getPreferenceManager().getSharedPreferences()\n\t\t\t\t\t    .getString("bookmark.hostname", "");\n\t\t\t\t\treturn value.isEmpty() ? getString(R.string.settings_hostname_hint) : value;\n\t\t\t\t});\n\t\t\t}\n\n\t\t\tPreference credPref = findPreference("bookmark.credentials");\n'''
    data = replace_once(data, main_anchor, main_new, "add connection field guidance")
    data = data.replace('String username = sp.getString("bookmark.username", "<none>");',
                        'String username = sp.getString("bookmark.username", "");')
    data = data.replace('return "<none>";', 'return getString(R.string.settings_not_set);')
    write(bookmark_activity, data)

    # Save action should be visible as text on TV instead of an ambiguous tiny icon.
    menu = studio / "freeRDPCore/src/main/res/menu/bookmark_menu.xml"
    data = read(menu)
    data = replace_once(data,
        'app:showAsAction="always"',
        'app:showAsAction="always|withText"',
        "show Save text in action bar")
    write(menu, data)

    # ------------------------------------------------------------------
    # 3. Strong focus states for TV remote controls.
    # ------------------------------------------------------------------
    focus_item = '''<?xml version="1.0" encoding="utf-8"?>\n<selector xmlns:android="http://schemas.android.com/apk/res/android">\n    <item android:state_focused="true">\n        <shape android:shape="rectangle">\n            <solid android:color="#FFF0F1" />\n            <stroke android:width="3dp" android:color="#B5121B" />\n            <corners android:radius="8dp" />\n            <padding android:left="6dp" android:top="2dp" android:right="6dp" android:bottom="2dp" />\n        </shape>\n    </item>\n    <item android:state_pressed="true">\n        <shape android:shape="rectangle">\n            <solid android:color="#FFE0E2" />\n            <stroke android:width="2dp" android:color="#B5121B" />\n            <corners android:radius="8dp" />\n        </shape>\n    </item>\n    <item>\n        <shape android:shape="rectangle">\n            <solid android:color="@android:color/transparent" />\n        </shape>\n    </item>\n</selector>\n'''
    write(studio / "freeRDPCore/src/main/res/drawable/billion_preference_focus.xml", focus_item)

    action_focus = '''<?xml version="1.0" encoding="utf-8"?>\n<selector xmlns:android="http://schemas.android.com/apk/res/android">\n    <item android:state_focused="true">\n        <shape android:shape="rectangle">\n            <solid android:color="#B5121B" />\n            <stroke android:width="2dp" android:color="#FFFFFF" />\n            <corners android:radius="8dp" />\n            <padding android:left="10dp" android:top="4dp" android:right="10dp" android:bottom="4dp" />\n        </shape>\n    </item>\n    <item android:state_pressed="true">\n        <shape android:shape="rectangle">\n            <solid android:color="#8E0E15" />\n            <corners android:radius="8dp" />\n        </shape>\n    </item>\n    <item>\n        <shape android:shape="rectangle">\n            <solid android:color="@android:color/transparent" />\n        </shape>\n    </item>\n</selector>\n'''
    write(studio / "freeRDPCore/src/main/res/drawable/billion_action_focus.xml", action_focus)

    theme = studio / "freeRDPCore/src/main/res/values/theme.xml"
    data = read(theme)
    theme_anchor = '''        <item name="android:statusBarColor">#FFFFFF</item> <!--Temporary workaround for status bar color in light mode-->\n'''
    theme_new = theme_anchor + '''        <item name="selectableItemBackground">@drawable/billion_preference_focus</item>\n        <item name="android:selectableItemBackground">@drawable/billion_preference_focus</item>\n        <item name="actionButtonStyle">@style/Billion.ActionButton</item>\n'''
    data = replace_once(data, theme_anchor, theme_new, "add strong focus styling")
    style_anchor = '''    <style name="Theme.Main.Session" parent="@style/Theme.Main">\n'''
    style_new = '''    <style name="Billion.ActionButton" parent="@style/Widget.AppCompat.ActionButton">\n        <item name="android:background">@drawable/billion_action_focus</item>\n        <item name="android:minWidth">76dp</item>\n        <item name="android:focusable">true</item>\n    </style>\n\n''' + style_anchor
    data = replace_once(data, style_anchor, style_new, "add action button focus style")
    write(theme, data)

    # ------------------------------------------------------------------
    # 4. Expose numeric/native RDP failure details from the JNI layer.
    # ------------------------------------------------------------------
    lib_java = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/services/LibFreeRDP.java"
    data = read(lib_java)
    native_anchor = '\tprivate static native String freerdp_get_last_error_string(long inst);\n'
    native_new = native_anchor + '\n\tprivate static native int freerdp_get_last_error_code(long inst);\n'
    data = replace_once(data, native_anchor, native_new, "declare last error code JNI")
    listener_anchor = '''\tpublic static void setEventListener(EventListener l)\n\t{\n'''
    wrappers = '''\tpublic static int getLastErrorCode(long inst)\n\t{\n\t\treturn freerdp_get_last_error_code(inst);\n\t}\n\n\tpublic static String getLastErrorString(long inst)\n\t{\n\t\tString value = freerdp_get_last_error_string(inst);\n\t\treturn value == null ? "" : value;\n\t}\n\n''' + listener_anchor
    data = replace_once(data, listener_anchor, wrappers, "expose RDP last error")
    write(lib_java, data)

    native_c = studio / "freeRDPCore/src/main/cpp/android_freerdp.c"
    data = read(native_c)
    c_anchor = '''JNIEXPORT jboolean JNICALL\nJava_com_freerdp_freerdpcore_services_LibFreeRDP_freerdp_1parse_1arguments(JNIEnv* env, jclass cls,\n'''
    c_new = '''JNIEXPORT jint JNICALL\nJava_com_freerdp_freerdpcore_services_LibFreeRDP_freerdp_1get_1last_1error_1code(JNIEnv* env,\n                                                                                 jclass cls,\n                                                                                 jlong instance)\n{\n\tfreerdp* inst = (freerdp*)instance;\n\tWINPR_UNUSED(env);\n\tWINPR_UNUSED(cls);\n\tif (!inst || !inst->context)\n\t\treturn 0;\n\treturn (jint)freerdp_get_last_error(inst->context);\n}\n\n''' + c_anchor
    data = replace_once(data, c_anchor, c_new, "add JNI last error code")
    write(native_c, data)

    translator = '''package com.freerdp.freerdpcore.presentation;\n\nimport android.content.Context;\nimport com.freerdp.freerdpcore.R;\nimport java.util.Locale;\n\npublic final class RdpFailureMessage\n{\n    private RdpFailureMessage() {}\n\n    public static String get(Context context, int code, String nativeMessage)\n    {\n        final int cls = (code >>> 16) & 0xFFFF;\n        final int type = code & 0xFFFF;\n\n        if (cls == 2)\n        {\n            switch (type)\n            {\n                case 0x15: return context.getString(R.string.rdp_error_wrong_password);\n                case 0x14: return context.getString(R.string.rdp_error_logon_failure);\n                case 0x09: return context.getString(R.string.rdp_error_auth_failed);\n                case 0x1B: return context.getString(R.string.rdp_error_missing_credentials);\n                case 0x12: return context.getString(R.string.rdp_error_account_disabled);\n                case 0x18: return context.getString(R.string.rdp_error_account_locked);\n                case 0x0E:\n                case 0x0F: return context.getString(R.string.rdp_error_password_expired);\n                case 0x13: return context.getString(R.string.rdp_error_password_change);\n                case 0x19: return context.getString(R.string.rdp_error_account_expired);\n                case 0x0A:\n                case 0x16:\n                case 0x1A: return context.getString(R.string.rdp_error_access_denied);\n                case 0x17: return context.getString(R.string.rdp_error_account_restriction);\n                case 0x04:\n                case 0x05: return context.getString(R.string.rdp_error_server_not_found);\n                case 0x06:\n                case 0x0D: return context.getString(R.string.rdp_error_network);\n                case 0x08:\n                case 0x0C:\n                case 0x1E: return context.getString(R.string.rdp_error_security);\n                case 0x11: return context.getString(R.string.rdp_error_domain_service);\n                default: break;\n            }\n        }\n\n        // ERRINFO_REMOTEAPP_NOT_ENABLED = class 1, type 0x10F3.\n        if (cls == 1 && type == 0x10F3)\n            return context.getString(R.string.rdp_error_remoteapp);\n\n        // Fallback for servers/builds that provide only a textual last error.\n        String s = nativeMessage == null ? "" : nativeMessage.toLowerCase(Locale.ROOT);\n        if (s.contains("wrong password"))\n            return context.getString(R.string.rdp_error_wrong_password);\n        if (s.contains("logon failure") || s.contains("logon failed"))\n            return context.getString(R.string.rdp_error_logon_failure);\n        if (s.contains("authentication failed") || s.contains("authenticate"))\n            return context.getString(R.string.rdp_error_auth_failed);\n        if (s.contains("password expired"))\n            return context.getString(R.string.rdp_error_password_expired);\n        if (s.contains("account locked"))\n            return context.getString(R.string.rdp_error_account_locked);\n        if (s.contains("dns") || s.contains("name not found"))\n            return context.getString(R.string.rdp_error_server_not_found);\n        if (s.contains("remoteapp"))\n            return context.getString(R.string.rdp_error_remoteapp);\n        if (s.contains("transport") || s.contains("connection failed"))\n            return context.getString(R.string.rdp_error_network);\n        return context.getString(R.string.rdp_error_generic);\n    }\n}\n'''
    write(studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/RdpFailureMessage.java", translator)

    # Replace generic toast with a readable failure dialog and an Edit action.
    session_activity = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionActivity.java"
    data = read(session_activity)
    import_anchor = 'import androidx.appcompat.app.AppCompatActivity;\n'
    data = replace_once(data, import_anchor,
                        'import androidx.appcompat.app.AlertDialog;\n' + import_anchor,
                        "import AlertDialog")
    field_anchor = '\tprivate boolean sessionRunning = false;\n'
    data = replace_once(data, field_anchor,
                        field_anchor + '\tprivate boolean failureDialogShown = false;\n',
                        "add failure dialog guard")

    old_failed = '''\tprivate void onSessionFailed()\n\t{\n\t\tLog.v(TAG, "onSessionFailed");\n\n\t\t// cancel any pending input events\n\t\tif (inputManager != null)\n\t\t\tinputManager.cancelPendingEvents();\n\n\t\tdialogs.dismissProgress();\n\n\t\t// post error message on UI thread\n\t\tif (!connectCancelledByUser)\n\t\t\tuiHandler.sendMessage(Message.obtain(\n\t\t\t    null, DISPLAY_TOAST, getResources().getText(R.string.error_connection_failure)));\n\n\t\tcloseSessionActivity(RESULT_CANCELED);\n\t}\n'''
    new_failed = '''\tprivate void onSessionFailed()\n\t{\n\t\tLog.v(TAG, "onSessionFailed");\n\n\t\tif (inputManager != null)\n\t\t\tinputManager.cancelPendingEvents();\n\n\t\tdialogs.dismissProgress();\n\n\t\tif (connectCancelledByUser)\n\t\t{\n\t\t\tcloseSessionActivity(RESULT_CANCELED);\n\t\t\treturn;\n\t\t}\n\n\t\tif (failureDialogShown)\n\t\t\treturn;\n\t\tfailureDialogShown = true;\n\n\t\tfinal int code = LibFreeRDP.getLastErrorCode(session.getInstance());\n\t\tfinal String nativeMessage = LibFreeRDP.getLastErrorString(session.getInstance());\n\t\tfinal String message = RdpFailureMessage.get(this, code, nativeMessage);\n\t\tLog.w(TAG, String.format(java.util.Locale.US,\n\t\t    "RDP connection failed: code=0x%08X, detail=%s", code, nativeMessage));\n\n\t\tAlertDialog.Builder builder = new AlertDialog.Builder(this)\n\t\t    .setTitle(R.string.rdp_error_title)\n\t\t    .setMessage(message)\n\t\t    .setCancelable(false)\n\t\t    .setNegativeButton(R.string.rdp_error_back,\n\t\t        (dialog, which) -> closeSessionActivity(RESULT_CANCELED));\n\n\t\tBundle bundle = getIntent() == null ? null : getIntent().getExtras();\n\t\tString refStr = bundle == null ? null : bundle.getString(PARAM_CONNECTION_REFERENCE);\n\t\tif (refStr != null && ConnectionReference.isBookmarkReference(refStr))\n\t\t{\n\t\t\tbuilder.setPositiveButton(R.string.rdp_error_edit, (dialog, which) -> {\n\t\t\t\tIntent edit = new Intent(SessionActivity.this, BookmarkActivity.class);\n\t\t\t\tedit.putExtra(BookmarkActivity.PARAM_CONNECTION_REFERENCE, refStr);\n\t\t\t\tstartActivity(edit);\n\t\t\t\tcloseSessionActivity(RESULT_CANCELED);\n\t\t\t});\n\t\t}\n\n\t\tbuilder.show();\n\t}\n'''
    data = replace_once(data, old_failed, new_failed, "show friendly connection errors")
    write(session_activity, data)

    # ------------------------------------------------------------------
    # 5. Clean About page: product info only; remove technical FreeRDP dump.
    # ------------------------------------------------------------------
    about_java = '''package com.freerdp.freerdpcore.presentation;\n\nimport android.content.pm.PackageManager;\nimport android.os.Build;\nimport android.os.Bundle;\nimport android.widget.TextView;\nimport androidx.appcompat.app.AppCompatActivity;\nimport com.freerdp.freerdpcore.R;\n\npublic class AboutActivity extends AppCompatActivity\n{\n    @Override protected void onCreate(Bundle savedInstanceState)\n    {\n        super.onCreate(savedInstanceState);\n        setContentView(R.layout.activity_about);\n        if (getSupportActionBar() != null)\n            getSupportActionBar().setDisplayHomeAsUpEnabled(true);\n\n        String version;\n        try\n        {\n            version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;\n        }\n        catch (PackageManager.NameNotFoundException e)\n        {\n            version = "-";\n        }\n\n        ((TextView)findViewById(R.id.aboutVersion)).setText(\n            getString(R.string.about_version_format, version));\n        ((TextView)findViewById(R.id.aboutDevice)).setText(\n            getString(R.string.about_device_format, Build.MODEL));\n        ((TextView)findViewById(R.id.aboutAndroid)).setText(\n            getString(R.string.about_android_format, Build.VERSION.RELEASE));\n    }\n\n    @Override public boolean onSupportNavigateUp()\n    {\n        finish();\n        return true;\n    }\n}\n'''
    write(studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/AboutActivity.java", about_java)

    about_xml = '''<?xml version="1.0" encoding="utf-8"?>\n<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"\n    android:layout_width="match_parent"\n    android:layout_height="match_parent"\n    android:fillViewport="true">\n\n    <LinearLayout\n        android:layout_width="match_parent"\n        android:layout_height="wrap_content"\n        android:orientation="vertical"\n        android:gravity="center_horizontal"\n        android:padding="32dp">\n\n        <TextView\n            android:layout_width="wrap_content"\n            android:layout_height="wrap_content"\n            android:text="BILLION RDP REMOTE"\n            android:textStyle="bold"\n            android:textSize="28sp"\n            android:paddingTop="24dp"\n            android:paddingBottom="12dp" />\n\n        <TextView\n            android:layout_width="wrap_content"\n            android:layout_height="wrap_content"\n            android:text="@string/about_product_desc"\n            android:textSize="18sp"\n            android:paddingBottom="30dp" />\n\n        <TextView\n            android:id="@+id/aboutVersion"\n            android:layout_width="match_parent"\n            android:layout_height="wrap_content"\n            android:textSize="17sp"\n            android:gravity="center"\n            android:padding="8dp" />\n\n        <TextView\n            android:id="@+id/aboutDevice"\n            android:layout_width="match_parent"\n            android:layout_height="wrap_content"\n            android:textSize="17sp"\n            android:gravity="center"\n            android:padding="8dp" />\n\n        <TextView\n            android:id="@+id/aboutAndroid"\n            android:layout_width="match_parent"\n            android:layout_height="wrap_content"\n            android:textSize="17sp"\n            android:gravity="center"\n            android:padding="8dp" />\n\n        <TextView\n            android:layout_width="match_parent"\n            android:layout_height="wrap_content"\n            android:text="@string/about_features"\n            android:textSize="16sp"\n            android:gravity="center"\n            android:paddingTop="28dp" />\n\n    </LinearLayout>\n</ScrollView>\n'''
    write(studio / "freeRDPCore/src/main/res/layout/activity_about.xml", about_xml)

    print("Test7 UX/error patch applied:", VERSION)
    print("Clear TV focus + explicit connection labels + detailed RDP errors + clean About")


if __name__ == "__main__":
    main()
