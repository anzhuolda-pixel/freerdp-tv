#!/usr/bin/env python3
import re
import sys
from pathlib import Path


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
        fail("usage: patch_session_diag_test22.py <freerdp-source-dir>")

    src = Path(sys.argv[1]).resolve()
    studio = src / "client" / "Android" / "Studio"
    session = studio / "freeRDPCore/src/main/java/com/freerdp/freerdpcore/presentation/SessionActivity.java"
    data = read(session)

    if 'import com.freerdp.freerdpcore.utils.BaihongEventLog;' not in data:
        data = replace_once(
            data,
            'import com.freerdp.freerdpcore.utils.ClipboardManagerProxy;\n',
            'import com.freerdp.freerdpcore.utils.ClipboardManagerProxy;\n'
            'import com.freerdp.freerdpcore.utils.BaihongEventLog;\n'
            'import com.freerdp.freerdpcore.utils.BaihongHostProbe;\n\n'
            'import java.util.concurrent.ExecutorService;\n'
            'import java.util.concurrent.Executors;\n',
            'import session diagnostics')

    reconnect_fields = '\tprivate ConnectivityManager.NetworkCallback reconnectNetworkCallback = null;\n'
    new_fields = reconnect_fields + '''\tprivate final ExecutorService baihongProbeExecutor = Executors.newSingleThreadExecutor();
\tprivate final Handler baihongHealthHandler = new Handler(Looper.getMainLooper());
\tprivate final ExecutorService baihongHealthExecutor = Executors.newSingleThreadExecutor();
\tprivate boolean baihongReconnectProbeRunning = false;
\tprivate boolean baihongWaitingForServer = false;
\tprivate boolean baihongHealthActive = false;
\tprivate boolean baihongLinkProblemLogged = false;
\tprivate boolean baihongHighLatencyLogged = false;
\tprivate int baihongLinkFailureStreak = 0;
\tprivate int baihongHighLatencyStreak = 0;
\tprivate final Runnable baihongHealthRunnable = () -> runBaihongHealthProbe();
'''
    data = replace_once(data, reconnect_fields, new_fields, 'add session diagnostics fields')

    data = replace_once(
        data,
        'private static final long[] AUTO_RECONNECT_DELAYS_MS = { 3000L, 5000L, 10000L, 20000L, 30000L };',
        'private static final long[] AUTO_RECONNECT_DELAYS_MS = { 5000L, 10000L, 15000L, 30000L };',
        'change offline probe backoff')

    destroy_anchor = '''\t\treconnectHandler.removeCallbacksAndMessages(null);\n\t\tunregisterReconnectNetworkCallback();\n'''
    destroy_new = '''\t\tstopBaihongHealthMonitor();\n\t\tbaihongProbeExecutor.shutdownNow();\n\t\tbaihongHealthExecutor.shutdownNow();\n''' + destroy_anchor
    data = replace_once(data, destroy_anchor, destroy_new, 'cleanup session diagnostics')

    connected_start = data.find('\tprivate void onSessionConnected()\n')
    if connected_start < 0:
        fail('onSessionConnected not found')
    connected_end = data.find('\n\tprivate void ', connected_start + 1)
    if connected_end < 0:
        fail('onSessionConnected end not found')
    connected_block = data[connected_start:connected_end]
    marker = '\t\tfailureDialogShown = false;\n'
    if connected_block.count(marker) != 1:
        fail(f'onSessionConnected failureDialog marker expected 1, found {connected_block.count(marker)}')
    connected_block = connected_block.replace(
        marker,
        marker + '''\t\tbaihongWaitingForServer = false;\n\t\tlogBaihongSessionEvent(R.string.log_event_rdp_connected, getString(R.string.log_detail_rdp_connected));\n\t\tstartBaihongHealthMonitor();\n''',
        1)
    data = data[:connected_start] + connected_block + data[connected_end:]

    start = data.find('\tprivate void performAutoReconnect()\n')
    end = data.find('\tprivate void onSessionFailed()\n', start)
    if start < 0 or end < 0:
        fail('performAutoReconnect method bounds not found')
    new_perform = r'''\tprivate void performAutoReconnect()
\t{
\t\treconnectScheduled = false;
\t\tif (!autoReconnectMode || connectCancelledByUser || reconnectBookmark == null ||
\t\t    isFinishing())
\t\t\treturn;

\t\tif (!isNetworkReadyForReconnect())
\t\t{
\t\t\treconnectAttempt = Math.min(reconnectAttempt + 1, AUTO_RECONNECT_DELAYS_MS.length - 1);
\t\t\tscheduleAutoReconnect();
\t\t\treturn;
\t\t}

\t\tif (connectThread != null && connectThread.isAlive())
\t\t{
\t\t\tscheduleAutoReconnect();
\t\t\treturn;
\t\t}

\t\tif (baihongReconnectProbeRunning)
\t\t{
\t\t\tscheduleAutoReconnect();
\t\t\treturn;
\t\t}

\t\tfinal BookmarkBase target = reconnectBookmark;
\t\tfinal int targetPort = target.getPort() > 0 ? target.getPort() : 3389;
\t\tbaihongReconnectProbeRunning = true;
\t\tbaihongProbeExecutor.execute(() -> {
\t\t\tBaihongHostProbe.Result probe = BaihongHostProbe.probe(
\t\t\t    target.getHostname(), targetPort, 1500, false);
\t\t\treconnectHandler.post(() -> {
\t\t\t\tbaihongReconnectProbeRunning = false;
\t\t\t\tif (!autoReconnectMode || connectCancelledByUser || reconnectBookmark == null ||
\t\t\t\t    isFinishing()) return;

\t\t\t\tif (!probe.tcpReachable)
\t\t\t\t{
\t\t\t\t\tif (!baihongWaitingForServer)
\t\t\t\t\t{
\t\t\t\t\t\tbaihongWaitingForServer = true;
\t\t\t\t\t\tlogBaihongSessionEvent(R.string.log_event_waiting_server,
\t\t\t\t\t\t    getString(R.string.log_detail_waiting_server, targetPort));
\t\t\t\t\t}
\t\t\t\t\treconnectAttempt = Math.min(reconnectAttempt + 1,
\t\t\t\t\t    AUTO_RECONNECT_DELAYS_MS.length - 1);
\t\t\t\t\tscheduleAutoReconnect();
\t\t\t\t\treturn;
\t\t\t\t}

\t\t\t\tif (baihongWaitingForServer)
\t\t\t\t{
\t\t\t\t\tbaihongWaitingForServer = false;
\t\t\t\t\tlogBaihongSessionEvent(R.string.log_event_server_recovered,
\t\t\t\t\t    getString(R.string.log_detail_tcp_recovered, targetPort, probe.tcpMs));
\t\t\t\t}

\t\t\t\tif (session != null)
\t\t\t\t{
\t\t\t\t\tlong oldInstance = session.getInstance();
\t\t\t\t\ttry
\t\t\t\t\t{
\t\t\t\t\t\tsession.setUIEventListener(null);
\t\t\t\t\t\tsessionViewModel.unregister();
\t\t\t\t\t\tGlobalApp.freeSession(oldInstance);
\t\t\t\t\t}
\t\t\t\t\tcatch (Throwable t)
\t\t\t\t\t{
\t\t\t\t\t\tLog.w(TAG, "Failed to fully release old RDP instance before reconnect", t);
\t\t\t\t\t}
\t\t\t\t\tsession = null;
\t\t\t\t}

\t\t\t\tfailureDialogShown = false;
\t\t\t\treconnectAttempt = Math.min(reconnectAttempt + 1,
\t\t\t\t    AUTO_RECONNECT_DELAYS_MS.length - 1);
\t\t\t\tLog.i(TAG, "RDP port reachable; attempting automatic reconnect, attempt=" + reconnectAttempt);
\t\t\t\tconnect(reconnectBookmark);
\t\t\t});
\t\t});
\t}

'''
    data = data[:start] + new_perform + data[end:]

    failed_anchor = '''\tprivate void onSessionFailed()\n\t{\n'''
    failed_new = failed_anchor + '''\t\tstopBaihongHealthMonitor();\n\t\tString baihongError = session == null ? "" : LibFreeRDP.getLastErrorString(session.getInstance());\n\t\tlogBaihongSessionEvent(R.string.log_event_rdp_failed, baihongError == null ? "" : baihongError);\n'''
    data = replace_once(data, failed_anchor, failed_new, 'log RDP failures')

    disconnected_anchor = '''\tprivate void onSessionDisconnected()\n\t{\n'''
    disconnected_new = disconnected_anchor + '''\t\tstopBaihongHealthMonitor();\n\t\tif (!connectCancelledByUser)\n\t\t\tlogBaihongSessionEvent(R.string.log_event_rdp_disconnected, getString(R.string.log_detail_rdp_disconnected));\n'''
    data = replace_once(data, disconnected_anchor, disconnected_new, 'log unexpected disconnects')

    state_anchor = '\tprivate void onConnectionStateChanged(SessionViewModel.ConnectionState state)\n'
    diag_methods = r'''\tprivate BookmarkBase getBaihongBookmark()
\t{
\t\tif (session != null && session.getBookmark() != null) return session.getBookmark();
\t\treturn reconnectBookmark;
\t}

\tprivate void logBaihongSessionEvent(int eventRes, String detail)
\t{
\t\tBookmarkBase bookmark = getBaihongBookmark();
\t\tif (bookmark == null) return;
\t\tint port = bookmark.getPort() > 0 ? bookmark.getPort() : 3389;
\t\tBaihongEventLog.log(this, bookmark.getLabel(), bookmark.getHostname(), port,
\t\t    getString(eventRes), detail == null ? "" : detail);
\t}

\tprivate void startBaihongHealthMonitor()
\t{
\t\tbaihongHealthActive = true;
\t\tbaihongLinkProblemLogged = false;
\t\tbaihongHighLatencyLogged = false;
\t\tbaihongLinkFailureStreak = 0;
\t\tbaihongHighLatencyStreak = 0;
\t\tbaihongHealthHandler.removeCallbacks(baihongHealthRunnable);
\t\tbaihongHealthHandler.postDelayed(baihongHealthRunnable, 10000L);
\t}

\tprivate void stopBaihongHealthMonitor()
\t{
\t\tbaihongHealthActive = false;
\t\tbaihongHealthHandler.removeCallbacks(baihongHealthRunnable);
\t}

\tprivate void runBaihongHealthProbe()
\t{
\t\tif (!baihongHealthActive || isFinishing()) return;
\t\tfinal BookmarkBase bookmark = getBaihongBookmark();
\t\tif (bookmark == null)
\t\t{
\t\t\tbaihongHealthHandler.postDelayed(baihongHealthRunnable, 10000L);
\t\t\treturn;
\t\t}
\t\tfinal int targetPort = bookmark.getPort() > 0 ? bookmark.getPort() : 3389;
\t\tbaihongHealthExecutor.execute(() -> {
\t\t\tBaihongHostProbe.Result result = BaihongHostProbe.probe(
\t\t\t    bookmark.getHostname(), targetPort, 1500, false);
\t\t\tbaihongHealthHandler.post(() -> {
\t\t\t\tif (!baihongHealthActive || isFinishing()) return;
\t\t\t\tif (!result.tcpReachable)
\t\t\t\t{
\t\t\t\t\tbaihongLinkFailureStreak++;
\t\t\t\t\tif (baihongLinkFailureStreak >= 2 && !baihongLinkProblemLogged)
\t\t\t\t\t{
\t\t\t\t\t\tbaihongLinkProblemLogged = true;
\t\t\t\t\t\tlogBaihongSessionEvent(R.string.log_event_link_unreachable,
\t\t\t\t\t\t    getString(R.string.log_detail_link_unreachable, targetPort));
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\telse
\t\t\t\t{
\t\t\t\t\tbaihongLinkFailureStreak = 0;
\t\t\t\t\tif (baihongLinkProblemLogged)
\t\t\t\t\t{
\t\t\t\t\t\tbaihongLinkProblemLogged = false;
\t\t\t\t\t\tlogBaihongSessionEvent(R.string.log_event_link_recovered,
\t\t\t\t\t\t    getString(R.string.log_detail_link_recovered, result.tcpMs));
\t\t\t\t\t}
\t\t\t\t\tif (result.tcpMs >= 300)
\t\t\t\t\t{
\t\t\t\t\t\tbaihongHighLatencyStreak++;
\t\t\t\t\t\tif (baihongHighLatencyStreak >= 3 && !baihongHighLatencyLogged)
\t\t\t\t\t\t{
\t\t\t\t\t\t\tbaihongHighLatencyLogged = true;
\t\t\t\t\t\t\tlogBaihongSessionEvent(R.string.log_event_high_latency,
\t\t\t\t\t\t\t    getString(R.string.log_detail_high_latency, result.tcpMs));
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t\telse
\t\t\t\t\t{
\t\t\t\t\t\tbaihongHighLatencyStreak = 0;
\t\t\t\t\t\tif (baihongHighLatencyLogged && result.tcpMs < 200)
\t\t\t\t\t\t{
\t\t\t\t\t\t\tbaihongHighLatencyLogged = false;
\t\t\t\t\t\t\tlogBaihongSessionEvent(R.string.log_event_latency_recovered,
\t\t\t\t\t\t\t    getString(R.string.log_detail_latency_recovered, result.tcpMs));
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\tbaihongHealthHandler.postDelayed(baihongHealthRunnable, 10000L);
\t\t\t});
\t\t});
\t}

'''
    data = replace_once(data, state_anchor, diag_methods + state_anchor,
                        'add session health monitor methods')

    for marker in [
        'BaihongHostProbe.probe(',
        'R.string.log_event_rdp_connected',
        'R.string.log_event_link_unreachable',
        'baihongWaitingForServer',
        'RDP port reachable; attempting automatic reconnect',
        'AUTO_RECONNECT_DELAYS_MS = { 5000L, 10000L, 15000L, 30000L }',
    ]:
        if marker not in data:
            fail('missing Test22 session marker: ' + marker)

    write(session, data)
    print('Test22 session diagnostics patch applied')
    print('Reconnect gate: lightweight TCP probe first; no repeated RDP handshakes while port is down')
    print('Health log: 10s TCP checks, 2 failures => link event, 3x >=300ms => high-latency event')


if __name__ == '__main__':
    main()
