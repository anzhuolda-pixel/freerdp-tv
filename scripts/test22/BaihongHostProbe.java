package com.freerdp.freerdpcore.utils;

import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;

public final class BaihongHostProbe
{
    private BaihongHostProbe() {}

    public static final class Result
    {
        public final boolean tcpReachable;
        public final boolean pingReachable;
        public final long tcpMs;
        public final long pingMs;
        public final String error;

        Result(boolean tcpReachable, boolean pingReachable, long tcpMs, long pingMs, String error)
        {
            this.tcpReachable = tcpReachable;
            this.pingReachable = pingReachable;
            this.tcpMs = tcpMs;
            this.pingMs = pingMs;
            this.error = error == null ? "" : error;
        }

        public long bestLatencyMs()
        {
            if (tcpReachable && tcpMs >= 0) return tcpMs;
            if (pingReachable && pingMs >= 0) return pingMs;
            return -1;
        }
    }

    public static Result probe(String host, int port, int timeoutMs, boolean includePing)
    {
        if (host == null || host.trim().isEmpty())
            return new Result(false, false, -1, -1, "empty host");

        String value = host.trim();
        int connectPort = port > 0 ? port : 3389;
        boolean tcp = false;
        boolean ping = false;
        long tcpMs = -1;
        long pingMs = -1;
        String error = "";

        long started = System.nanoTime();
        try (Socket socket = new Socket())
        {
            socket.connect(new InetSocketAddress(value, connectPort), Math.max(250, timeoutMs));
            tcpMs = Math.max(0L, (System.nanoTime() - started) / 1000000L);
            tcp = true;
        }
        catch (Throwable t)
        {
            error = shortError(t);
        }

        if (includePing)
        {
            long pingStarted = System.nanoTime();
            try
            {
                InetAddress address = InetAddress.getByName(value);
                ping = address.isReachable(Math.max(250, Math.min(timeoutMs, 1000)));
                if (ping) pingMs = Math.max(0L, (System.nanoTime() - pingStarted) / 1000000L);
            }
            catch (Throwable t)
            {
                if (error.isEmpty()) error = shortError(t);
            }
        }
        return new Result(tcp, ping, tcpMs, pingMs, error);
    }

    private static String shortError(Throwable t)
    {
        if (t == null) return "";
        String value = t.getMessage();
        if (value == null || value.trim().isEmpty()) value = t.getClass().getSimpleName();
        value = value.replace('\n', ' ').replace('\r', ' ').trim();
        return value.length() > 120 ? value.substring(0, 120) : value;
    }
}
