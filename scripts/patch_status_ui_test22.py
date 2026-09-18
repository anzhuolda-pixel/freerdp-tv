#!/usr/bin/env python3
import re
import shutil
import sys
from pathlib import Path

VERSION = "3.31.1-baihong-konka32-api28-test22"
VERSION_CODE = "331122"

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

def set_string(data, name, value):
    pattern = re.compile(r'<string\s+name="' + re.escape(name) + r'"(?:\s+[^>]*)?>.*?</string>')
    repl = f'<string name="{name}">{value}</string>'
    if pattern.search(data):
        return pattern.sub(repl, data, count=1)
    return insert_before_last(data, '</resources>', '    ' + repl + '\n', 'add string ' + name)

def main():
    if len(sys.argv) != 2:
        fail("usage: patch_status_ui_test22.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parent
    overlay = root / "test22"
    studio = src / "client" / "Android" / "Studio"
    core_java = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore"
    utils = core_java / "utils"
    presentation = core_java / "presentation"

    props = studio / "release.properties"
    data = read(props)
    data = re.sub(r'^VERSION_NAME=.*$', 'VERSION_NAME=' + VERSION, data, count=1, flags=re.M)
    data = re.sub(r'^VERSION_CODE=.*$', 'VERSION_CODE=' + VERSION_CODE, data, count=1, flags=re.M)
    write(props, data)

    shutil.copyfile(overlay / "BaihongHostProbe.java", utils / "BaihongHostProbe.java")
    shutil.copyfile(overlay / "BaihongEventLog.java", utils / "BaihongEventLog.java")
    shutil.copyfile(overlay / "ConnectionLogActivity.java", presentation / "ConnectionLogActivity.java")

    manifest = studio / "freeRDPCore/src/main/AndroidManifest.xml"
    data = read(manifest)
    marker = '''        <activity
            android:exported="false"
            android:name=".presentation.PrintProxyActivity"'''
    activity = '''        <activity
            android:exported="false"
            android:name=".presentation.ConnectionLogActivity"
            android:label="@string/connection_log_title"
            android:theme="@style/Theme.Main" />
'''
    data = replace_once(data, marker, activity + marker, "register connection log activity")
    write(manifest, data)

    menu = studio / "freeRDPCore/src/main/res/menu/home_menu.xml"
    data = read(menu)
    settings_marker = '''    <item
        android:id="@+id/appSettings"'''
    log_item = '''    <item
        android:id="@+id/connectionLogs"
        app:showAsAction="never"
        android:title="@string/menu_connection_logs" />

'''
    data = replace_once(data, settings_marker, log_item + settings_marker, "add logs menu")
    write(menu, data)

    layout = studio / "freeRDPCore/src/main/res/layout/bookmark_list_item.xml"
    data = read(layout)
    if 'android:minHeight="76dp"' in data:
        data = data.replace('android:minHeight="76dp"', 'android:minHeight="118dp"', 1)
    elif 'android:minHeight="?attr/listPreferredItemHeight"' in data:
        data = data.replace('android:minHeight="?attr/listPreferredItemHeight"', 'android:minHeight="118dp"', 1)
    else:
        fail("bookmark row minHeight marker not found")
    status_views = '''
        <TextView
            android:id="@+id/bookmark_status"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:paddingTop="4dp"
            android:textSize="15sp"
            android:textStyle="bold"
            android:visibility="gone" />

        <TextView
            android:id="@+id/bookmark_detail"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:paddingTop="2dp"
            android:paddingBottom="4dp"
            android:textSize="13sp"
            android:visibility="gone" />
'''
    data = insert_before_last(data, '    </LinearLayout>', status_views, "add status text views")
    write(layout, data)

    adapter = utils / "BookmarkListAdapter.java"
    data = read(adapter)
    if "import android.graphics.Color;" not in data:
        data = replace_once(data, "import android.content.Intent;\n",
                            "import android.content.Intent;\nimport android.graphics.Color;\n",
                            "import Color")
    if "import java.util.HashMap;" not in data:
        data = replace_once(data, "import java.util.ArrayList;\n",
                            "import java.util.ArrayList;\nimport java.util.HashMap;\nimport java.util.Map;\n",
                            "import status map")
    data = replace_once(data, "\tprivate boolean actionsEnabled = true;\n",
                        "\tprivate boolean actionsEnabled = true;\n"
                        "\tprivate final Map<Long, BaihongHostProbe.Result> hostStatus = new HashMap<>();\n",
                        "add host status map")

    set_items = '''\tpublic void setItems(List<BookmarkBase> newItems)
\t{
\t\titems = newItems != null ? newItems : new ArrayList<>();
\t\tnotifyDataSetChanged();
\t}
'''
    data = replace_once(data, set_items, set_items + '''
\tpublic void setHostStatus(long bookmarkId, BaihongHostProbe.Result result)
\t{
\t\thostStatus.put(bookmarkId, result);
\t\tnotifyDataSetChanged();
\t}
''', "add setHostStatus")

    manual = '''\t\tif (bookmark.getType() == BookmarkBase.TYPE_MANUAL)
\t\t{
\t\t\tholder.binding.bookmarkIcon1.setImageResource(R.drawable.ic_computer);
'''
    data = replace_once(data, manual, '''\t\tif (bookmark.getType() == BookmarkBase.TYPE_MANUAL)
\t\t{
\t\t\tbindBaihongStatus(holder, bookmark);
\t\t\tholder.binding.bookmarkIcon1.setImageResource(R.drawable.ic_computer);
''', "bind manual status")
    data = replace_once(data, '''\t\telse if (bookmark.getType() == BookmarkBase.TYPE_QUICKCONNECT)
\t\t{
''', '''\t\telse if (bookmark.getType() == BookmarkBase.TYPE_QUICKCONNECT)
\t\t{
\t\t\tholder.binding.bookmarkStatus.setVisibility(View.GONE);
\t\t\tholder.binding.bookmarkDetail.setVisibility(View.GONE);
''', "hide quick status")
    data = replace_once(data, '''\t\telse
\t\t{
\t\t\tholder.binding.bookmarkIcon1.setVisibility(View.GONE);
''', '''\t\telse
\t\t{
\t\t\tholder.binding.bookmarkStatus.setVisibility(View.GONE);
\t\t\tholder.binding.bookmarkDetail.setVisibility(View.GONE);
\t\t\tholder.binding.bookmarkIcon1.setVisibility(View.GONE);
''', "hide invalid status")

    helper = r'''	private void bindBaihongStatus(ViewHolder holder, BookmarkBase bookmark)
	{
		holder.binding.bookmarkStatus.setVisibility(View.VISIBLE);
		holder.binding.bookmarkDetail.setVisibility(View.VISIBLE);
		BaihongHostProbe.Result status = hostStatus.get(bookmark.getId());
		int port = bookmark.getPort() > 0 ? bookmark.getPort() : 3389;
		if (status == null)
		{
			holder.binding.bookmarkStatus.setText(R.string.server_status_checking);
			holder.binding.bookmarkStatus.setTextColor(Color.parseColor("#6B7280"));
			holder.binding.bookmarkDetail.setText(holder.itemView.getContext().getString(
			    R.string.server_status_endpoint, bookmark.getHostname(), port));
			return;
		}

		long latency = status.bestLatencyMs();
		String quality;
		if (latency < 0) quality = "--";
		else if (latency <= 50) quality = holder.itemView.getContext().getString(R.string.server_latency_excellent);
		else if (latency <= 120) quality = holder.itemView.getContext().getString(R.string.server_latency_normal);
		else if (latency <= 250) quality = holder.itemView.getContext().getString(R.string.server_latency_high);
		else quality = holder.itemView.getContext().getString(R.string.server_latency_very_high);

		if (status.tcpReachable)
		{
			holder.binding.bookmarkStatus.setText(holder.itemView.getContext().getString(
			    R.string.server_status_tcp_online, port, status.tcpMs, quality));
			holder.binding.bookmarkStatus.setTextColor(
			    latency > 250 ? Color.parseColor("#B45309") : Color.parseColor("#15803D"));
			if (status.pingReachable)
				holder.binding.bookmarkDetail.setText(holder.itemView.getContext().getString(
				    R.string.server_status_ping_online, status.pingMs));
			else
				holder.binding.bookmarkDetail.setText(R.string.server_status_ping_blocked_tcp_ok);
		}
		else if (status.pingReachable)
		{
			holder.binding.bookmarkStatus.setText(holder.itemView.getContext().getString(
			    R.string.server_status_host_online_port_down, port));
			holder.binding.bookmarkStatus.setTextColor(Color.parseColor("#B45309"));
			holder.binding.bookmarkDetail.setText(holder.itemView.getContext().getString(
			    R.string.server_status_ping_only, status.pingMs));
		}
		else
		{
			holder.binding.bookmarkStatus.setText(R.string.server_status_offline);
			holder.binding.bookmarkStatus.setTextColor(Color.parseColor("#B91C1C"));
			holder.binding.bookmarkDetail.setText(holder.itemView.getContext().getString(
			    R.string.server_status_no_reply, port));
		}
	}

'''
    data = replace_once(data, "\t@Override public int getItemCount()\n",
                        helper + "\t@Override public int getItemCount()\n",
                        "add status renderer")
    write(adapter, data)

    home = presentation / "HomeActivity.java"
    data = read(home)
    if "import android.os.Handler;" not in data:
        data = replace_once(data, "import android.os.Bundle;\n",
                            "import android.os.Bundle;\nimport android.os.Handler;\nimport android.os.Looper;\n",
                            "import home handler")
    if "import com.freerdp.freerdpcore.utils.BaihongHostProbe;" not in data:
        data = replace_once(data, "import com.freerdp.freerdpcore.utils.BookmarkListAdapter;\n",
                            "import com.freerdp.freerdpcore.utils.BookmarkListAdapter;\n"
                            "import com.freerdp.freerdpcore.utils.BaihongEventLog;\n"
                            "import com.freerdp.freerdpcore.utils.BaihongHostProbe;\n",
                            "import home diagnostics")
    if "import java.util.HashMap;" not in data:
        data = replace_once(data, "import java.nio.charset.StandardCharsets;\n",
                            "import java.nio.charset.StandardCharsets;\n"
                            "import java.util.HashMap;\nimport java.util.List;\nimport java.util.Map;\n"
                            "import java.util.concurrent.ExecutorService;\nimport java.util.concurrent.Executors;\n",
                            "import home status support")

    data = replace_once(data, "\tprivate ExternalDisplayManager externalDisplayManager;\n",
                        "\tprivate ExternalDisplayManager externalDisplayManager;\n"
                        "\tprivate final Handler baihongStatusHandler = new Handler(Looper.getMainLooper());\n"
                        "\tprivate final ExecutorService baihongStatusExecutor = Executors.newFixedThreadPool(3);\n"
                        "\tprivate final Map<Long, String> baihongLastReachability = new HashMap<>();\n"
                        "\tprivate boolean baihongStatusActive = false;\n"
                        "\tprivate final Runnable baihongStatusRunnable = () -> runBaihongStatusRound();\n",
                        "add home monitor fields")

    data = replace_once(data, '''\t@Override protected void onResume()
\t{
\t\tsuper.onResume();
''', '''\t@Override protected void onResume()
\t{
\t\tsuper.onResume();
\t\tstartBaihongStatusMonitor();
''', "start home status monitor")

    lifecycle = r'''	@Override protected void onPause()
	{
		baihongStatusActive = false;
		baihongStatusHandler.removeCallbacks(baihongStatusRunnable);
		super.onPause();
	}

	@Override protected void onDestroy()
	{
		baihongStatusActive = false;
		baihongStatusHandler.removeCallbacksAndMessages(null);
		baihongStatusExecutor.shutdownNow();
		super.onDestroy();
	}

	private void startBaihongStatusMonitor()
	{
		baihongStatusActive = true;
		baihongStatusHandler.removeCallbacks(baihongStatusRunnable);
		baihongStatusHandler.postDelayed(baihongStatusRunnable, 500L);
	}

	private void runBaihongStatusRound()
	{
		if (!baihongStatusActive || isFinishing()) return;
		List<BookmarkBase> items = bookmarkListAdapter.getItems();
		if (items != null)
		{
			for (BookmarkBase bookmark : items)
			{
				if (bookmark == null || bookmark.getType() != BookmarkBase.TYPE_MANUAL) continue;
				final BookmarkBase target = bookmark;
				baihongStatusExecutor.execute(() -> {
					BaihongHostProbe.Result result = BaihongHostProbe.probe(
					    target.getHostname(), target.getPort(), 1200, true);
					baihongStatusHandler.post(() -> {
						if (!baihongStatusActive || isFinishing()) return;
						bookmarkListAdapter.setHostStatus(target.getId(), result);
						logBaihongReachabilityChange(target, result);
					});
				});
			}
		}
		baihongStatusHandler.postDelayed(baihongStatusRunnable, 8000L);
	}

	private void logBaihongReachabilityChange(BookmarkBase bookmark, BaihongHostProbe.Result result)
	{
		String current = result.tcpReachable ? "tcp" : result.pingReachable ? "ping" : "offline";
		String previous = baihongLastReachability.put(bookmark.getId(), current);
		if (previous == null || previous.equals(current)) return;
		int port = bookmark.getPort() > 0 ? bookmark.getPort() : 3389;
		if ("offline".equals(current))
			BaihongEventLog.log(this, bookmark.getLabel(), bookmark.getHostname(), port,
			    getString(R.string.log_event_server_unreachable),
			    getString(R.string.log_detail_ping_tcp_unreachable, port));
		else if ("ping".equals(current))
			BaihongEventLog.log(this, bookmark.getLabel(), bookmark.getHostname(), port,
			    getString(R.string.log_event_rdp_port_unreachable),
			    getString(R.string.log_detail_ping_ok_port_down, result.pingMs, port));
		else
			BaihongEventLog.log(this, bookmark.getLabel(), bookmark.getHostname(), port,
			    getString(R.string.log_event_server_recovered),
			    getString(R.string.log_detail_tcp_recovered, port, result.tcpMs));
	}

'''
    data = replace_once(data, "\t@Override protected void onSaveInstanceState(Bundle outState)\n",
                        lifecycle + "\t@Override protected void onSaveInstanceState(Bundle outState)\n",
                        "add home monitor lifecycle")

    data = replace_once(data, '''\t\telse if (itemId == R.id.appSettings)
\t\t{
''', '''\t\telse if (itemId == R.id.connectionLogs)
\t\t{
\t\t\tstartActivity(new Intent(this, ConnectionLogActivity.class));
\t\t}
\t\telse if (itemId == R.id.appSettings)
\t\t{
''', "open log viewer")
    write(home, data)

    tv = studio / "freeRDPCore/src/main/res/xml/settings_app_tv.xml"
    data = read(tv)
    data = insert_before_last(data, "</PreferenceScreen>", '''
    <PreferenceCategory android:title="@string/settings_diag_group">
        <ListPreference
            android:key="diagnostics.log_retention_days"
            android:defaultValue="3"
            android:title="@string/settings_log_retention"
            android:summary="@string/settings_log_retention_summary"
            android:entries="@array/baihong_log_retention_entries"
            android:entryValues="@array/baihong_log_retention_values"
            app:useSimpleSummaryProvider="true" />
        <Preference
            android:key="diagnostics.status_note"
            android:title="@string/settings_status_detection"
            android:summary="@string/settings_status_detection_summary"
            android:selectable="false" />
    </PreferenceCategory>
''', "add diagnostics preferences")
    write(tv, data)

    write(studio / "freeRDPCore/src/main/res/values/baihong_test22_arrays.xml", '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string-array name="baihong_log_retention_entries">
        <item>3 days</item><item>7 days</item><item>14 days</item><item>30 days</item>
        <item>90 days</item><item>180 days</item><item>365 days</item>
    </string-array>
    <string-array name="baihong_log_retention_values">
        <item>3</item><item>7</item><item>14</item><item>30</item>
        <item>90</item><item>180</item><item>365</item>
    </string-array>
</resources>
''')

    write(studio / "freeRDPCore/src/main/res/values-zh/baihong_test22_arrays.xml", '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string-array name="baihong_log_retention_entries">
        <item>3 天</item><item>7 天</item><item>14 天</item><item>30 天</item>
        <item>90 天</item><item>180 天</item><item>365 天</item>
    </string-array>
</resources>
''')

    en = studio / "freeRDPCore/src/main/res/values/strings.xml"
    data = read(en)
    values = {
        "menu_connection_logs": "Connection logs",
        "connection_log_title": "Connection logs",
        "connection_log_refresh": "Refresh",
        "connection_log_clear": "Clear logs",
        "connection_log_clear_confirm": "Delete all saved connection logs?",
        "connection_log_empty": "No connection events have been recorded.",
        "connection_log_retention_summary": "Local connection events are kept for %1$d day(s).",
        "settings_diag_group": "Connection status and diagnostics",
        "settings_log_retention": "Connection log retention",
        "settings_log_retention_summary": "Default is 3 days. Older logs are removed automatically.",
        "settings_status_detection": "Server status detection",
        "settings_status_detection_summary": "Checks the RDP TCP port and uses Ping as a secondary signal. A blocked Ping does not mark a reachable RDP port offline.",
        "server_status_checking": "Checking communication…",
        "server_status_endpoint": "%1$s · RDP port %2$d",
        "server_status_tcp_online": "● Online · RDP port %1$d reachable · %2$d ms · %3$s",
        "server_status_ping_online": "Ping reachable · %1$d ms",
        "server_status_ping_blocked_tcp_ok": "Ping has no reply (possibly blocked) · RDP TCP port is normal",
        "server_status_host_online_port_down": "● Host reachable · RDP port %1$d unavailable",
        "server_status_ping_only": "Ping reachable · %1$d ms · RDP waits for the TCP port",
        "server_status_offline": "● Offline / unreachable",
        "server_status_no_reply": "Ping has no reply · TCP port %1$d has no reply",
        "server_latency_excellent": "excellent",
        "server_latency_normal": "normal",
        "server_latency_high": "high",
        "server_latency_very_high": "very high",
        "log_event_server_unreachable": "Server unreachable",
        "log_event_rdp_port_unreachable": "RDP port unavailable",
        "log_event_server_recovered": "Server communication restored",
        "log_event_rdp_connected": "RDP connected",
        "log_event_rdp_disconnected": "Unexpected RDP disconnect",
        "log_event_rdp_failed": "RDP connection failed",
        "log_event_waiting_server": "Waiting for RDP server",
        "log_event_link_unreachable": "Session link probe failed",
        "log_event_link_recovered": "Session link restored",
        "log_event_high_latency": "Very high TCP latency",
        "log_event_latency_recovered": "TCP latency recovered",
        "log_detail_ping_tcp_unreachable": "Ping and TCP port %1$d did not respond",
        "log_detail_ping_ok_port_down": "Ping %1$d ms, TCP port %2$d unavailable",
        "log_detail_tcp_recovered": "TCP port %1$d reachable, %2$d ms",
        "log_detail_rdp_connected": "FreeRDP session established",
        "log_detail_rdp_disconnected": "The remote session ended unexpectedly; automatic recovery started",
        "log_detail_waiting_server": "TCP port %1$d is not reachable. RDP handshakes are paused; only lightweight probes continue.",
        "log_detail_link_unreachable": "Two consecutive TCP checks to port %1$d failed during the session",
        "log_detail_link_recovered": "TCP check recovered to %1$d ms",
        "log_detail_high_latency": "TCP connect latency remained at %1$d ms or above for consecutive checks",
        "log_detail_latency_recovered": "TCP connect latency returned to %1$d ms",
    }
    for k, v in values.items():
        data = set_string(data, k, v)
    write(en, data)

    zh = studio / "freeRDPCore/src/main/res/values-zh/strings.xml"
    data = read(zh)
    values = {
        "menu_connection_logs": "连接日志",
        "connection_log_title": "连接与网络日志",
        "connection_log_refresh": "刷新",
        "connection_log_clear": "清空日志",
        "connection_log_clear_confirm": "确定删除全部已保存的连接日志吗？",
        "connection_log_empty": "当前还没有记录到连接事件。",
        "connection_log_retention_summary": "本机连接日志当前保留 %1$d 天。",
        "settings_diag_group": "连接状态与诊断",
        "settings_log_retention": "连接日志保留时间",
        "settings_log_retention_summary": "默认 3 天，超过保留时间的旧日志自动删除。",
        "settings_status_detection": "服务器在线状态判断",
        "settings_status_detection_summary": "首页同时检测 RDP TCP端口，并用 Ping 辅助判断；服务器禁 Ping 时，只要RDP端口正常仍显示在线。",
        "server_status_checking": "正在检测通讯状态…",
        "server_status_endpoint": "%1$s · RDP端口 %2$d",
        "server_status_tcp_online": "● 在线 · RDP端口 %1$d 可达 · %2$d ms · %3$s",
        "server_status_ping_online": "Ping 可达 · %1$d ms",
        "server_status_ping_blocked_tcp_ok": "Ping 无响应（可能被禁用）· RDP TCP端口正常",
        "server_status_host_online_port_down": "● 主机在线 · RDP端口 %1$d 不可达",
        "server_status_ping_only": "Ping 可达 · %1$d ms · RDP端口恢复前不发起远程连接",
        "server_status_offline": "● 离线 / 不可达",
        "server_status_no_reply": "Ping 无响应 · TCP端口 %1$d 无响应",
        "server_latency_excellent": "延迟优秀",
        "server_latency_normal": "延迟正常",
        "server_latency_high": "延迟偏高",
        "server_latency_very_high": "延迟很高",
        "log_event_server_unreachable": "服务器不可达",
        "log_event_rdp_port_unreachable": "RDP端口不可达",
        "log_event_server_recovered": "服务器通讯恢复",
        "log_event_rdp_connected": "RDP连接成功",
        "log_event_rdp_disconnected": "RDP意外断开",
        "log_event_rdp_failed": "RDP连接失败",
        "log_event_waiting_server": "等待RDP服务器恢复",
        "log_event_link_unreachable": "远程中链路探测失败",
        "log_event_link_recovered": "远程中链路恢复",
        "log_event_high_latency": "TCP延迟持续很高",
        "log_event_latency_recovered": "TCP延迟恢复正常",
        "log_detail_ping_tcp_unreachable": "Ping 与 TCP端口 %1$d 均无响应",
        "log_detail_ping_ok_port_down": "Ping %1$d ms，TCP端口 %2$d 不可达",
        "log_detail_tcp_recovered": "TCP端口 %1$d 已恢复，延迟 %2$d ms",
        "log_detail_rdp_connected": "FreeRDP 远程会话已建立",
        "log_detail_rdp_disconnected": "远程会话非主动结束，已进入自动恢复流程",
        "log_detail_waiting_server": "TCP端口 %1$d 当前不可达，暂停重复RDP握手，仅保留轻量状态探测。",
        "log_detail_link_unreachable": "远程使用中连续两次检测 TCP端口 %1$d 失败",
        "log_detail_link_recovered": "TCP通讯已恢复，当前 %1$d ms",
        "log_detail_high_latency": "连续检测到 TCP连接延迟达到 %1$d ms 或更高",
        "log_detail_latency_recovered": "TCP连接延迟已恢复到 %1$d ms",
    }
    for k, v in values.items():
        data = set_string(data, k, v)
    write(zh, data)

    print("Test22 UI/status/log overlay applied")

if __name__ == "__main__":
    main()
