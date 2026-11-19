[app]
title = Ava
package.name = avaassistant
package.domain = org.example
source.dir = .
source.include_exts = py,kv,png,jpg,xml
android.add_src = android_src
android.add_resources = android_res
android.extra_manifest_application_xml = android_manifest_application.xml
version = 1.0.0
requirements = python3,kivy,requests,plyer,pyjnius
orientation = portrait
android.permissions = INTERNET,RECORD_AUDIO,CALL_PHONE,READ_CONTACTS,READ_PHONE_STATE,ANSWER_PHONE_CALLS,FOREGROUND_SERVICE,POST_NOTIFICATIONS
android.api = 35
android.minapi = 24
p4a.branch = develop
