[app]

# 应用名称
title = 哈基米南北路多

# 应用版本
version = 1.0.0

# 包名（唯一标识）
package.name = hajimirunner

# 包域名（反域名格式）
package.domain = org.hajimi

# 源代码目录
source.dir = .

# 应用入口脚本
source.main = main.py

# Python 版本
python.version = 3.12

# Android API 级别
android.api = 34
android.minapi = 21

# SDK 和 NDK
android.sdk = 34
android.ndk = 27

# 屏幕方向（竖屏）
orientation = portrait

# 权限
android.permissions = INTERNET

# 应用图标（可选，使用默认）
# icon.filename = %(source.dir)s/icon.png

# 应用商店图标（可选，使用默认）
# presplash.filename = %(source.dir)s/splash.png

# 支持的架构
android.archs = arm64-v8a

# 数值类型（确保 NumPy 兼容）
android.numerical = armeabi-v7a,arm64-v8a

# 包含的 Python 模块
requirements = python3,pygame,math,random,time,dataclasses,os,pickle,json,typing

# 只打包必要的文件
android.add_src = .

# 排除不需要的文件
android.exclude_dirs = __pycache__,debug_frames,.git

# 存储权限
android.store.folder = .

# 启动时显示日志
android.logcat_filters = *:S python:D

# 全屏模式
fullscreen = 1

# 不显示状态栏
android.hide_status_bar = 1

# 窗口尺寸（游戏内分辨率）
android.window_size = 720x960

[buildozer]

# 日志级别
log_level = 2

# 构建目录
build_dir = ./build

# 二进制目录
bin_dir = ./bin

# 下载目录
download_dir = ./.buildozer/downloads

# 使用之前下载的 SDK/NDK
android.accept_sdk_license = True

# 当出现警告时继续构建
warn_on_root = 1