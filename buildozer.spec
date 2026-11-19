[app]
title = Phone Assistant
package.name = phoneassistant
package.domain = org.example
source.dir = .
source.include_exts = py
android.add_src = android_src
android.add_resources = android_res
android.extra_manifest_application_xml = android_manifest_application.xml
version = 0.2
requirements = python3,kivy,requests,plyer
orientation = portrait
android.permissions = INTERNET,RECORD_AUDIO,CALL_PHONE,READ_CONTACTS,READ_PHONE_STATE,ANSWER_PHONE_CALLS,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MICROPHONE,POST_NOTIFICATIONS
android.api = 35
android.minapi = 24
services = Voicelistener:services/voice_listener.py:foreground:sticky:foregroundServiceType=microphone
