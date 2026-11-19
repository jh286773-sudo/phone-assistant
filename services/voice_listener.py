# -*- coding: utf-8 -*-
"""Foreground Android speech listener. Recognition restarts after each turn."""
import socket
from jnius import autoclass, PythonJavaClass, java_method

PythonService = autoclass("org.kivy.android.PythonService")
service = PythonService.mService
Looper = autoclass("android.os.Looper")
Handler = autoclass("android.os.Handler")
Intent = autoclass("android.content.Intent")
RecognizerIntent = autoclass("android.speech.RecognizerIntent")
SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")

if Looper.myLooper() is None:
    Looper.prepare()
handler = Handler(Looper.myLooper())
recognizer = SpeechRecognizer.createSpeechRecognizer(service)
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

class RestartTask(PythonJavaClass):
    __javainterfaces__ = ["java/lang/Runnable"]
    __javacontext__ = "app"
    @java_method("()V")
    def run(self):
        start_recognition()

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
        handler.postDelayed(RestartTask(), 1500)
    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):
        try:
            values = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if values and values.size() > 0:
                phrase = str(values.get(0)).strip()
                if phrase:
                    udp.sendto(phrase.encode("utf-8"), ("127.0.0.1", 8765))
        except Exception:
            pass
        handler.postDelayed(RestartTask(), 400)
    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, partial): pass
    @java_method("(ILandroid/os/Bundle;)V")
    def onEvent(self, eventType, params): pass

listener = Listener()
recognizer.setRecognitionListener(listener)

def start_recognition():
    try:
        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, False)
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        recognizer.startListening(intent)
    except Exception:
        handler.postDelayed(RestartTask(), 2000)

start_recognition()
Looper.loop()
