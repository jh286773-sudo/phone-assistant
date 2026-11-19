package org.example.phoneassistant;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.telephony.TelephonyManager;

public final class IncomingCallMonitor extends BroadcastReceiver {
    public interface Callback {
        void onIncomingCall();
        void onCallEnded();
    }

    private static IncomingCallMonitor receiver;
    private static Callback callback;
    private boolean ringing = false;

    public static synchronized void register(Context context, Callback listener) {
        if (receiver != null) return;
        callback = listener;
        receiver = new IncomingCallMonitor();
        IntentFilter filter = new IntentFilter(TelephonyManager.ACTION_PHONE_STATE_CHANGED);
        if (Build.VERSION.SDK_INT >= 33) {
            context.getApplicationContext().registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED);
        } else {
            context.getApplicationContext().registerReceiver(receiver, filter);
        }
    }

    public static synchronized void unregister(Context context) {
        if (receiver == null) return;
        try { context.getApplicationContext().unregisterReceiver(receiver); } catch (Exception ignored) {}
        receiver = null;
        callback = null;
    }

    @Override public void onReceive(Context context, Intent intent) {
        if (!TelephonyManager.ACTION_PHONE_STATE_CHANGED.equals(intent.getAction())) return;
        String state = intent.getStringExtra(TelephonyManager.EXTRA_STATE);
        if (TelephonyManager.EXTRA_STATE_RINGING.equals(state) && !ringing) {
            ringing = true;
            Callback current = callback;
            if (current != null) current.onIncomingCall();
        } else if ((TelephonyManager.EXTRA_STATE_IDLE.equals(state)
                || TelephonyManager.EXTRA_STATE_OFFHOOK.equals(state)) && ringing) {
            ringing = false;
            Callback current = callback;
            if (current != null) current.onCallEnded();
        }
    }
}
