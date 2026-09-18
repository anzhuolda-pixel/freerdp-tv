package com.freerdp.freerdpcore.presentation;

import android.graphics.Typeface;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import com.freerdp.freerdpcore.R;
import com.freerdp.freerdpcore.utils.BaihongEventLog;

public class ConnectionLogActivity extends AppCompatActivity
{
    private TextView content;
    private TextView summary;

    @Override protected void onCreate(Bundle savedInstanceState)
    {
        super.onCreate(savedInstanceState);
        setTitle(R.string.connection_log_title);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(16), dp(20), dp(16));

        summary = new TextView(this);
        summary.setTextSize(16);
        summary.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        root.addView(summary, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setGravity(Gravity.START);
        actions.setPadding(0, dp(12), 0, dp(12));

        Button refresh = new Button(this);
        refresh.setText(R.string.connection_log_refresh);
        refresh.setOnClickListener(v -> refresh());

        Button clear = new Button(this);
        clear.setText(R.string.connection_log_clear);
        clear.setOnClickListener(v -> confirmClear());

        actions.addView(refresh);
        actions.addView(clear);
        root.addView(actions);

        ScrollView scroll = new ScrollView(this);
        content = new TextView(this);
        content.setTextSize(14);
        content.setTextIsSelectable(true);
        content.setPadding(dp(4), dp(4), dp(4), dp(24));
        scroll.addView(content, new ScrollView.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        setContentView(root);
        refresh();
    }

    @Override protected void onResume()
    {
        super.onResume();
        refresh();
    }

    private void refresh()
    {
        int days = BaihongEventLog.getRetentionDays(this);
        summary.setText(getString(R.string.connection_log_retention_summary, days));
        String text = BaihongEventLog.readRecent(this);
        content.setText(text.isEmpty() ? getString(R.string.connection_log_empty) : text);
    }

    private void confirmClear()
    {
        new AlertDialog.Builder(this)
            .setTitle(R.string.connection_log_clear)
            .setMessage(R.string.connection_log_clear_confirm)
            .setPositiveButton(R.string.yes, (d, w) -> {
                BaihongEventLog.clear(this);
                refresh();
            })
            .setNegativeButton(R.string.no, null)
            .show();
    }

    private int dp(int value)
    {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
