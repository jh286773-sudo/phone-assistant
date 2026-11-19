package org.example.phoneassistant;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;

import java.util.ArrayList;
import java.util.Locale;

public final class AvaWakeService extends Service {
    private static final String CHANNEL = "ava_wake";
    private static final int NOTIFICATION_ID = 731;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private SpeechRecognizer recognizer;
    private boolean awaitingCommand = false;
    private boolean running = false;

    @Override public void onCreate() {
        super.onCreate();
        createChannel();
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? "START" : intent.getAction();
        if ("STOP".equals(action)) {
            stopListening();
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }
        startForeground(NOTIFICATION_ID, notification("آوا در پس‌زمینه آماده شنیدن است."));
        if (!running) {
            running = true;
            handler.post(this::beginRecognition);
        }
        return START_STICKY;
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(CHANNEL, "شنود آوا",
                    NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("اعلان فعال بودن سرویس شنود آوا");
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
        }
    }

    private Notification notification(String text) {
        Intent launch = getPackageManager().getLaunchIntentForPackage(getPackageName());
        PendingIntent pending = null;
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            pending = PendingIntent.getActivity(this, 731, launch,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        }
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL) : new Notification.Builder(this);
        builder.setSmallIcon(getApplicationInfo().icon)
                .setContentTitle("آوا")
                .setContentText(text)
                .setOngoing(running)
                .setCategory(Notification.CATEGORY_SERVICE);
        if (pending != null) builder.setContentIntent(pending);
        return builder.build();
    }

    private void updateNotification(String text) {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        manager.notify(NOTIFICATION_ID, notification(text));
    }

    private void beginRecognition() {
        if (!running) return;
        try {
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                updateNotification("سرویس تشخیص گفتار روی این گوشی در دسترس نیست.");
                scheduleRestart(5000);
                return;
            }
            if (recognizer == null) {
                recognizer = SpeechRecognizer.createSpeechRecognizer(this);
                recognizer.setRecognitionListener(listener);
            }
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "fa-IR");
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
            recognizer.startListening(intent);
        } catch (Exception error) {
            scheduleRestart(2500);
        }
    }

    private final RecognitionListener listener = new RecognitionListener() {
        @Override public void onResults(android.os.Bundle results) {
            ArrayList<String> values = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (values != null && !values.isEmpty()) handlePhrase(values.get(0));
            scheduleRestart(650);
        }
        @Override public void onError(int error) { scheduleRestart(1600); }
        @Override public void onReadyForSpeech(android.os.Bundle params) { }
        @Override public void onBeginningOfSpeech() { }
        @Override public void onRmsChanged(float rmsdB) { }
        @Override public void onBufferReceived(byte[] buffer) { }
        @Override public void onEndOfSpeech() { }
        @Override public void onPartialResults(android.os.Bundle partialResults) { }
        @Override public void onEvent(int eventType, android.os.Bundle params) { }
    };

    private void handlePhrase(String raw) {
        String phrase = raw == null ? "" : raw.trim().replace('ي', 'ی').replace('ك', 'ک');
        String normalized = phrase.replace("‌", " ").toLowerCase(Locale.ROOT);
        if (!awaitingCommand) {
            int at = normalized.indexOf("سلام آوا");
            int length = 8;
            if (at < 0) { at = normalized.indexOf("آوا"); length = 3; }
            if (at >= 0) {
                String remainder = phrase.substring(Math.min(phrase.length(), at + length)).trim();
                if (remainder.isEmpty()) {
                    awaitingCommand = true;
                    updateNotification("آوا بیدار شد؛ فرمان را بگو و اعلان را لمس کن.");
                    saveCommand("");
                } else {
                    awaitingCommand = false;
                    saveCommand(remainder);
                    updateNotification("فرمان صوتی دریافت شد؛ برای اجرا اعلان را لمس کن.");
                }
            }
        } else {
            awaitingCommand = false;
            saveCommand(phrase);
            updateNotification("فرمان صوتی دریافت شد؛ برای اجرا اعلان را لمس کن.");
        }
    }

    private void saveCommand(String command) {
        SharedPreferences prefs = getSharedPreferences("ava_wake", MODE_PRIVATE);
        prefs.edit().putString("pending_command", command).apply();
        Intent launch = getPackageManager().getLaunchIntentForPackage(getPackageName());
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            launch.putExtra("ava_command", command);
            PendingIntent pending = PendingIntent.getActivity(this, 732, launch,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            updateNotification("آوا آماده اجرای فرمان است؛ برای بازکردن لمس کن.");
        }
    }

    private void scheduleRestart(long delay) {
        if (!running) return;
        handler.removeCallbacks(restart);
        handler.postDelayed(restart, delay);
    }
    private final Runnable restart = this::beginRecognition;

    private void stopListening() {
        running = false;
        handler.removeCallbacksAndMessages(null);
        if (recognizer != null) {
            try { recognizer.cancel(); recognizer.destroy(); } catch (Exception ignored) { }
            recognizer = null;
        }
    }

    @Override public void onDestroy() {
        stopListening();
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
