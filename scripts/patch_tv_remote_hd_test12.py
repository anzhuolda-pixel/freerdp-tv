#!/usr/bin/env python3
import sys
from pathlib import Path

VERSION = "3.31.1-billion-a9-test12"
VERSION_CODE = "331112"


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
        fail("usage: patch_tv_remote_hd_test12.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    if not studio.is_dir():
        fail("FreeRDP Android Studio directory not found")

    props = studio / "release.properties"
    data = read(props)
    data = replace_once(data, "VERSION_NAME=3.31.1-billion-a9-test11",
                        "VERSION_NAME=" + VERSION, "update Test12 version")
    data = replace_once(data, "VERSION_CODE=331111", "VERSION_CODE=" + VERSION_CODE,
                        "update Test12 version code")
    write(props, data)

    item = studio / "freeRDPCore/src/main/res/layout/bookmark_list_item.xml"
    data = read(item)
    data = replace_once(
        data,
        '<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"\n    android:layout_width="match_parent"',
        '<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"\n    android:id="@+id/bookmark_row"\n    android:layout_width="match_parent"',
        "give bookmark row an id")

    root_focus = '''    android:focusable="true"\n    android:focusableInTouchMode="false"\n    android:minHeight="?attr/listPreferredItemHeight">'''
    root_focus_new = '''    android:focusable="true"\n    android:focusableInTouchMode="false"\n    android:nextFocusRight="@id/bookmark_icon2"\n    android:minHeight="?attr/listPreferredItemHeight">'''
    data = replace_once(data, root_focus, root_focus_new,
                        "route bookmark row right focus")

    icon_focus = '''        android:clickable="true"\n        android:focusable="true"\n        android:focusableInTouchMode="false"\n        android:padding="12dp"'''
    icon_focus_new = '''        android:clickable="true"\n        android:focusable="true"\n        android:focusableInTouchMode="false"\n        android:nextFocusLeft="@id/bookmark_row"\n        android:padding="10dp"'''
    data = replace_once(data, icon_focus, icon_focus_new,
                        "route three-dot menu left focus")
    write(item, data)

    row_focus = '''<?xml version="1.0" encoding="utf-8"?>
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:state_focused="true"><shape android:shape="rectangle"><solid android:color="#FFF0F1" /><stroke android:width="3dp" android:color="#B5121B" /><corners android:radius="6dp" /></shape></item>
    <item android:state_pressed="true"><shape android:shape="rectangle"><solid android:color="#FFE2E5" /><stroke android:width="3dp" android:color="#B5121B" /><corners android:radius="6dp" /></shape></item>
    <item><shape android:shape="rectangle"><solid android:color="@android:color/transparent" /></shape></item>
</selector>
'''
    write(studio / "freeRDPCore/src/main/res/drawable/billion_bookmark_tv_focus.xml", row_focus)

    more_focus = '''<?xml version="1.0" encoding="utf-8"?>
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:state_focused="true"><shape android:shape="rectangle"><solid android:color="#B5121B" /><stroke android:width="2dp" android:color="#FFFFFF" /><corners android:radius="8dp" /></shape></item>
    <item android:state_pressed="true"><shape android:shape="rectangle"><solid android:color="#8E0E15" /><corners android:radius="8dp" /></shape></item>
    <item><shape android:shape="rectangle"><solid android:color="@android:color/transparent" /></shape></item>
</selector>
'''
    write(studio / "freeRDPCore/src/main/res/drawable/billion_more_tv_focus.xml", more_focus)

    adapter = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/utils/BookmarkListAdapter.java"
    data = read(adapter)
    if "import android.view.KeyEvent;" not in data:
        data = replace_once(data, "import android.view.LayoutInflater;\n",
                            "import android.view.LayoutInflater;\nimport android.view.KeyEvent;\n",
                            "import KeyEvent")
    if "import com.freerdp.freerdpcore.presentation.DeviceMode;" not in data:
        data = replace_once(data,
                            "import com.freerdp.freerdpcore.presentation.BookmarkActivity;\n",
                            "import com.freerdp.freerdpcore.presentation.BookmarkActivity;\nimport com.freerdp.freerdpcore.presentation.DeviceMode;\n",
                            "import DeviceMode")

    click_block = '''\t\tholder.itemView.setOnClickListener(v -> {\n\t\t\tif (callbacks != null)\n\t\t\t\tcallbacks.onItemClick(v.getTag().toString());\n\t\t});\n'''
    data = replace_once(data, click_block,
                        click_block + '''\n\t\tconfigureTvRemoteNavigation(holder, bookmark, refStr);\n''',
                        "install TV bookmark key navigation")

    get_count = '''\t@Override public int getItemCount()\n\t{\n'''
    helper = '''\tprivate void configureTvRemoteNavigation(ViewHolder holder, BookmarkBase bookmark,\n\t                                               String refStr)\n\t{\n\t\tif (!DeviceMode.isTv(holder.itemView.getContext()))\n\t\t\treturn;\n\n\t\tholder.itemView.setBackgroundResource(R.drawable.billion_bookmark_tv_focus);\n\t\tholder.itemView.setFocusable(true);\n\t\tholder.itemView.setFocusableInTouchMode(false);\n\t\tholder.itemView.setContentDescription(holder.itemView.getContext().getString(\n\t\t    R.string.tv_connection_row_description, bookmark.getLabel()));\n\n\t\tfinal boolean hasMenu = actionsEnabled &&\n\t\t    holder.binding.bookmarkIcon2.getVisibility() == View.VISIBLE;\n\t\tif (hasMenu)\n\t\t{\n\t\t\tholder.binding.bookmarkIcon2.setFocusable(true);\n\t\t\tholder.binding.bookmarkIcon2.setFocusableInTouchMode(false);\n\t\t\tholder.binding.bookmarkIcon2.setBackgroundResource(R.drawable.billion_more_tv_focus);\n\t\t\tholder.binding.bookmarkIcon2.setContentDescription(\n\t\t\t    holder.itemView.getContext().getString(R.string.tv_more_actions_description));\n\t\t\tholder.binding.bookmarkIcon2.setOnKeyListener((v, keyCode, event) -> {\n\t\t\t\tif (event.getAction() != KeyEvent.ACTION_DOWN) return false;\n\t\t\t\tif (keyCode == KeyEvent.KEYCODE_DPAD_LEFT)\n\t\t\t\t{ holder.itemView.requestFocus(); return true; }\n\t\t\t\tif (keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER || keyCode == KeyEvent.KEYCODE_NUMPAD_ENTER)\n\t\t\t\t{ v.performClick(); return true; }\n\t\t\t\treturn false;\n\t\t\t});\n\t\t}\n\n\t\tholder.itemView.setOnKeyListener((v, keyCode, event) -> {\n\t\t\tif (event.getAction() != KeyEvent.ACTION_DOWN) return false;\n\t\t\tif (keyCode == KeyEvent.KEYCODE_DPAD_RIGHT && hasMenu)\n\t\t\t{ holder.binding.bookmarkIcon2.requestFocus(); return true; }\n\t\t\tif (keyCode == KeyEvent.KEYCODE_MENU && hasMenu)\n\t\t\t{ holder.binding.bookmarkIcon2.performClick(); return true; }\n\t\t\tif (keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER || keyCode == KeyEvent.KEYCODE_NUMPAD_ENTER)\n\t\t\t{\n\t\t\t\tif (callbacks != null && refStr != null && !refStr.isEmpty()) callbacks.onItemClick(refStr);\n\t\t\t\treturn true;\n\t\t\t}\n\t\t\treturn false;\n\t\t});\n\t}\n\n'''
    data = replace_once(data, get_count, helper + get_count,
                        "add deterministic TV remote focus helper")
    write(adapter, data)

    session = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionActivity.java"
    data = read(session)
    old = '''\t\tboolean hideStatusBar = ApplicationSettingsActivity.getHideStatusBar(this);\n\t\tboolean hideNavBar = ApplicationSettingsActivity.getHideNavigationBar(this);\n'''
    new = '''\t\tboolean tvDisplay = DeviceMode.isTv(this);\n\t\tboolean hideStatusBar = tvDisplay || ApplicationSettingsActivity.getHideStatusBar(this);\n\t\tboolean hideNavBar = tvDisplay || ApplicationSettingsActivity.getHideNavigationBar(this);\n'''
    count = data.count(old)
    if count != 2:
        fail(f"force immersive full-screen bars hidden on TV: expected 2 matches, found {count}")
    data = data.replace(old, new)

    quality_anchor = '''\t\tBookmarkBase.ScreenSettings screenSettings =\n\t\t    session.getBookmark().getActiveScreenSettings();\n\t\tLog.v(TAG, "Screen Resolution: " + screenSettings.getResolutionString());\n'''
    quality_new = quality_anchor + '''\t\tif (DeviceMode.isTv(this))\n\t\t{\n\t\t\tscreenSettings.setColors(32);\n\t\t\tBookmarkBase.PerformanceFlags tvFlags = session.getBookmark().getActivePerformanceFlags();\n\t\t\ttvFlags.setGfx(true);\n\t\t\ttvFlags.setH264(true);\n\t\t\ttvFlags.setFontSmoothing(true);\n\t\t\tLog.i(TAG, "TV HD mode: viewport=" + screen_width + "x" + screen_height + ", 32bpp, GFX, font smoothing");\n\t\t}\n'''
    data = replace_once(data, quality_anchor, quality_new,
                        "apply TV high-quality RDP flags")
    write(session, data)

    lib = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/services/LibFreeRDP.java"
    data = read(lib)
    if "import com.freerdp.freerdpcore.presentation.DeviceMode;" not in data:
        data = replace_once(data,
            "import com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity;\n",
            "import com.freerdp.freerdpcore.presentation.ApplicationSettingsActivity;\nimport com.freerdp.freerdpcore.presentation.DeviceMode;\n",
            "import DeviceMode in LibFreeRDP")
    args_anchor = '''\t\targs.add(TAG);\n\t\targs.add("/gdi:sw");\n'''
    args_new = args_anchor + '''\t\tfinal String networkProfile =\n\t\t    DeviceMode.isTv(context) ? "/network:lan" : "/network:auto";\n'''
    anchor_count = data.count(args_anchor)
    if anchor_count != 2:
        fail(f"select LAN quality profile for TV: expected 2 matches, found {anchor_count}")
    # Both bookmark-based and URI-based connection builders need the same
    # networkProfile variable because the upstream file has this setup twice.
    data = data.replace(args_anchor, args_new)
    auto_count = data.count('args.add("/network:auto");')
    if auto_count < 2:
        fail("expected FreeRDP network:auto flags not found")
    data = data.replace('args.add("/network:auto");', 'args.add(networkProfile);')
    write(lib, data)

    tv_xml = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    data = read(tv_xml)
    quality_pref = '''\n    <Preference\n        android:key="ui.tv_hd_display_status"\n        android:title="@string/settings_tv_hd_display"\n        android:summary="@string/settings_tv_hd_display_summary"\n        android:selectable="false" />\n\n'''
    data = insert_before_last(data, "</PreferenceScreen>", quality_pref,
                              "add TV HD display status")
    write(tv_xml, data)

    bookmark = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/BookmarkActivity.java"
    data = read(bookmark)
    default_anchor = '''\t\t\t\t    .putInt("bookmark.scale_device", 100)\n\t\t\t\t    .apply();\n'''
    default_new = '''\t\t\t\t    .putInt("bookmark.scale_device", 100)\n\t\t\t\t    .putBoolean("bookmark.perf_gfx", true)\n\t\t\t\t    .putBoolean("bookmark.perf_gfx_h264", true)\n\t\t\t\t    .putBoolean("bookmark.perf_font_smoothing", true)\n\t\t\t\t    .apply();\n'''
    data = replace_once(data, default_anchor, default_new,
                        "set TV high-quality defaults for new bookmarks")
    write(bookmark, data)

    en = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(en)
    en_add = '''\n    <string name="tv_connection_row_description">%1$s. Press OK to connect; press Right for more actions.</string>\n    <string name="tv_more_actions_description">More actions. Press OK to open the edit menu; press Left to return to the connection.</string>\n    <string name="settings_tv_hd_display">TV high-definition display optimization</string>\n    <string name="settings_tv_hd_display_summary">Automatic in TV mode: full-screen viewport, 32-bit color, font smoothing, GFX and LAN-quality graphics. Automatic resolution matches the Android render viewport to avoid unnecessary scaling.</string>\n'''
    data = insert_before_last(data, "</resources>", en_add,
                              "add Test12 English strings")
    write(en, data)

    zh = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh)
    zh_add = '''\n    <string name="tv_connection_row_description">%1$s。按确认键直接连接；按右键进入更多操作。</string>\n    <string name="tv_more_actions_description">更多操作。按确认键打开编辑菜单；按左键返回远程主机。</string>\n    <string name="settings_tv_hd_display">电视大屏高清显示优化</string>\n    <string name="settings_tv_hd_display_summary">电视模式自动启用：全屏显示、32位色彩、字体平滑、GFX及局域网画质策略；自动分辨率按Android实际渲染画面匹配，避免不必要的二次缩放。</string>\n'''
    data = insert_before_last(data, "</resources>", zh_add,
                              "add Test12 Chinese strings")
    write(zh, data)

    print("Test12 TV remote navigation + HD display patch applied")
    print("TV: OK connects; RIGHT focuses three-dot menu; LEFT returns; MENU opens actions")
    print("TV: immersive viewport + 32bpp + GFX + font smoothing + LAN quality profile")


if __name__ == "__main__":
    main()
