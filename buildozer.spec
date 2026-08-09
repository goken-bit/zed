[app]
title = Zed
package.name = zed
package.domain = org.zed
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf
version = 0.1.0
requirements = python3,kivy,pygments
orientation = portrait
fullscreen = 0
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.archs = arm64-v8a
android.api = 33
android.minapi = 21
android.private_storage = False

[buildozer]
log_level = 2
warn_on_root = 1
