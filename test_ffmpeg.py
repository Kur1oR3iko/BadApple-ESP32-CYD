#!/usr/bin/env python3
import os
import subprocess

print("Testing FFmpeg detection...")

# 测试本地FFmpeg
local_ffmpeg = os.path.join(os.getcwd(), 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffmpeg.exe')
print(f"Looking for FFmpeg at: {local_ffmpeg}")
print(f"Exists: {os.path.exists(local_ffmpeg)}")

if os.path.exists(local_ffmpeg):
    try:
        result = subprocess.run([local_ffmpeg, '-version'], capture_output=True, check=True)
        print("FFmpeg found and working!")
        print(f"First line of output: {result.stdout.decode().split(chr(10))[0]}")
    except Exception as e:
        print(f"Error running FFmpeg: {e}")
else:
    print("FFmpeg not found at expected location")
