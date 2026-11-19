[app]
title = Phone Assistant
package.name = phoneassistant
package.domain = org.example
source.dir = .
source.include_exts = py
android.add_src = android_src
version = 0.2
requirements = python3,kivy,requests,plyer
orientation = portrait
android.permissions = INTERNET,RECORD_AUDIO,CALL_PHONE,READ_CONTACTS,READ_PHONE_STATE,ANSWER_PHONE_CALLS
android.api = 35
android.minapi = 24
