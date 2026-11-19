# -*- coding: utf-8 -*-
"""Foreground Android speech listener; SpeechRecognizer calls run on Android main looper."""
import socket
import threading
from jnius import autoclass, PythonJavaClass, java_method

PythonService = autoclass("org.kivy.android.PythonService")
service = PythonService.mService
service.setAutoRestartService(True)
Looper = autoclass("android.os.Looper")
Handler = autoclass("android.os.Handler")
Intent = autoclass("android.content.Intent")
RecognizerIntent = autoclass("android.speech.RecognizerIntent")
SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")

main_handler = Handler(Looper.getMainLooper())
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recognizer = None
awaiting_command = False

class RestartTask(PythonJavaClass):
    __javainterfaces__ = ["java/lang/Runnable"]
    __javacontext__ = "app"
    @java_method("()V")
    def run(self):
        start_recognition()

class CreateRecognizerTask(PythonJavaClass):
    __javainterfaces__ = ["java/lang/Runnable"]
    __javacontext__ = "app"
    @java_method("()V")
    def run(self):
        global recognizer
        try:
            if not SpeechRecognizer.isRecognitionAvailable(service):
                return
            recognizer = SpeechRecognizer.createSpeechRecognizer(service)
            recognizer.setRecognitionListener(listener)
            start_recognition()
        except Exception as exc:
            print("Speech recognizer initialization failed:", exc)

class Listener(PythonJavaClass):
    __javainterfaces__ = ["android/speech/RecognitionListener"]
    __javacontext__ = "app"
    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, params): pass
    @java_method("()V")
    def onBeginningOfSpeech(self): pass
    @java_method("(F)V")
    def onRmsChanged(self, rmsdB): pass
    @java_method("([B)V")
    def onBufferReceived(self, buffer): pass
    @java_method("()V")
    def onEndOfSpeech(self): pass
    @java_method("(I)V")
    def onError(self, error):
        main_handler.postDelayed(RestartTask(), 1400)
    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):
        try:
            values = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if values and values.size() > 0:
                phrase = str(values.get(0)).strip()
                if phrase:
                    normalized = phrase.lower().replace("‌", " ").replace("ي", "ی").replace("ك", "ک")
                    normalized = " ".join(normalized.split())
                    wake_words = ("سلام دستیار", "دستیار", "سلام دستیاره")
                    if not awaiting_command:
                        if any(word in normalized for word in wake_words):
                            awaiting_command = True
                            udp.sendto(b"__WAKE__", ("127.0.0.1", 8765))
                            launch_assistant()
                    else:
                        awaiting_command = False
                        udp.sendto(phrase.encode("utf-8"), ("127.0.0.1", 8765))
        except Exception as exc:
            print("Speech result forwarding failed:", exc)
        main_handler.postDelayed(RestartTask(), 400)
    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, partial): pass
    @java_method("(ILandroid/os/Bundle;)V")
    def onEvent(self, eventType, params): pass

def launch_assistant():
    """Try to bring the app UI forward when the wake phrase is heard."""
    try:
        IntentFlags = autoclass("android.content.Intent")
        intent = service.getPackageManager().getLaunchIntentForPackage(service.getPackageName())
        if intent is None:
            return
        intent.addFlags(IntentFlags.FLAG_ACTIVITY_NEW_TASK |
                        IntentFlags.FLAG_ACTIVITY_SINGLE_TOP |
                        IntentFlags.FLAG_ACTIVITY_CLEAR_TOP)
        intent.putExtra("wake_word_triggered", True)
        service.startActivity(intent)
    except Exception as exc:
        # Android 10+ may block background activity launches; app still receives
        # the wake event whenever its receiver is active.
        print("Could not open assistant UI from background:", exc)

listener = Listener()

def start_recognition():
    try:
        if recognizer is None:
            return
        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, False)
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        recognizer.startListening(intent)
    except Exception as exc:
        print("Speech recognition restart failed:", exc)
        main_handler.postDelayed(RestartTask(), 2000)

main_handler.post(CreateRecognizerTask())
threading.Event().wait()
