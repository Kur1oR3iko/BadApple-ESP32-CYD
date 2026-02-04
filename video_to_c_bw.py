#!/usr/bin/env python3
"""
ESP32黑白视频转换器
使用纯RLE压缩，2色阶（全黑/全白）
针对ESP32性能和存储空间优化
"""

import sys
import os
import subprocess
import struct

def check_ffmpeg():
    """检查是否安装了ffmpeg"""
    # 首先检查脚本所在目录的本地ffmpeg
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffmpeg = os.path.join(script_dir, 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffmpeg.exe')
    
    if os.path.exists(local_ffmpeg):
        try:
            result = subprocess.run([local_ffmpeg, '-version'], capture_output=True, check=True)
            if result.returncode == 0:
                return True
        except (subprocess.CalledProcessError, FileNotFoundError, Exception):
            pass
    
    # 检查当前工作目录的本地ffmpeg
    local_ffmpeg = os.path.join(os.getcwd(), 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        try:
            result = subprocess.run([local_ffmpeg, '-version'], capture_output=True, check=True)
            if result.returncode == 0:
                return True
        except (subprocess.CalledProcessError, FileNotFoundError, Exception):
            pass
    
    # 然后检查系统PATH中的ffmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        if result.returncode == 0:
            return True
    except (subprocess.CalledProcessError, FileNotFoundError, Exception):
        pass
    
    return False

def get_ffmpeg_path():
    """获取ffmpeg可执行文件路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffmpeg = os.path.join(script_dir, 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffmpeg.exe')
    
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    
    local_ffmpeg = os.path.join(os.getcwd(), 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    
    return 'ffmpeg'

def get_ffprobe_path():
    """获取ffprobe可执行文件路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffprobe = os.path.join(script_dir, 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffprobe.exe')
    
    if os.path.exists(local_ffprobe):
        return local_ffprobe
    
    local_ffprobe = os.path.join(os.getcwd(), 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffprobe.exe')
    if os.path.exists(local_ffprobe):
        return local_ffprobe
    
    return 'ffprobe'

def get_video_info(input_file):
    """获取视频信息"""
    ffprobe_cmd = get_ffprobe_path()
    
    try:
        result = subprocess.run(
            [ffprobe_cmd, '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height,duration,r_frame_rate',
             '-of', 'default=noprint_wrappers=1', input_file],
            capture_output=True, text=True, check=True
        )
        info = {}
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                info[key] = value
        return info
    except subprocess.CalledProcessError:
        return None

def convert_to_bw(frame_data, threshold=128):
    """将灰度帧转换为黑白（二值化）"""
    bw_data = []
    for pixel in frame_data:
        # 阈值判断：大于等于threshold为白色(1)，小于为黑色(0)
        bw_data.append(1 if pixel >= threshold else 0)
    return bw_data

def rle_compress_bw(bw_data):
    """
    对黑白数据进行RLE压缩
    格式: [颜色(0/1), 连续像素数(1-255), ...]
    """
    if not bw_data:
        return []
    
    compressed = []
    current_color = bw_data[0]
    count = 1
    
    for i in range(1, len(bw_data)):
        if bw_data[i] == current_color and count < 255:
            count += 1
        else:
            # 存储当前段
            compressed.append(current_color)
            compressed.append(count)
            # 开始新段
            current_color = bw_data[i]
            count = 1
    
    # 存储最后一段
    compressed.append(current_color)
    compressed.append(count)
    
    return compressed

def convert_video(input_file, output_file, max_size_mb=0.4, target_fps=10, threshold=128):
    """
    转换视频为ESP32黑白格式
    """
    print(f"ESP32 Black & White Video Converter")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Target resolution: 128x96")
    print(f"Target FPS: {target_fps}")
    print(f"Color mode: Black & White (threshold={threshold})")
    print(f"Max size: {max_size_mb}MB")
    print(f"Compression: Pure RLE")
    print("-" * 60)
    
    # 创建临时目录
    temp_dir = "temp_frames_bw"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 获取视频信息
        info = get_video_info(input_file)
        if not info:
            print("Error: Cannot get video info")
            return False
        
        duration = float(info.get('duration', 0))
        print(f"Original video duration: {duration:.1f}s")
        
        # 计算最大帧数（基于大小限制）
        # 128x96 = 12288像素
        # 黑白RLE压缩后预计可减少约95%的大小
        # 0.4MB = 419430字节
        # 保守估计：每帧平均约350字节，预留10%余量
        target_size = max_size_mb * 1024 * 1024 * 0.85  # 使用85%的空间，更保守
        avg_frame_size = 380  # 保守估计平均每帧大小（实际可能更大）
        max_frames = int(target_size / avg_frame_size)
        
        max_duration = max_frames / target_fps
        
        print(f"Target FLASH usage: {target_size / 1024:.1f}KB")
        print(f"Max frames: {max_frames}")
        print(f"Max duration: {max_duration:.1f}s")
        
        # 提取帧
        print("\nExtracting video frames...")
        
        ffmpeg_cmd = get_ffmpeg_path()
        
        # 构建ffmpeg命令 - 先转为灰度
        vf_filters = f"fps={target_fps},scale=128:96:flags=lanczos,format=gray"
        
        # 限制时长
        duration_limit = min(duration, max_duration)
        
        cmd = [
            ffmpeg_cmd, '-y',
            '-i', input_file,
            '-t', str(duration_limit),
            '-vf', vf_filters,
            '-pix_fmt', 'gray',
            '-f', 'image2',
            os.path.join(temp_dir, 'frame_%04d.raw')
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return False
        
        # 获取生成的帧数
        frames = sorted([f for f in os.listdir(temp_dir) if f.endswith('.raw')])
        actual_frames = len(frames)
        
        print(f"Extracted {actual_frames} frames")
        
        # 读取所有帧并压缩
        print("\nProcessing frames (B&W + RLE)...")
        compressed_frames = []
        frame_sizes = []
        
        for i, frame_file in enumerate(frames):
            frame_path = os.path.join(temp_dir, frame_file)
            
            with open(frame_path, 'rb') as f:
                frame_data = list(f.read())
            
            # 转换为黑白
            bw_data = convert_to_bw(frame_data, threshold)
            
            # RLE压缩
            compressed = rle_compress_bw(bw_data)
            compressed_frames.append(compressed)
            frame_sizes.append(len(compressed))
            
            # 显示进度
            if (i + 1) % 10 == 0 or i == len(frames) - 1:
                print(f"Progress: {i+1}/{actual_frames} frames")
        
        # 计算压缩率
        original_size = actual_frames * 128 * 96  # 原始灰度大小
        compressed_size = sum(frame_sizes)
        compression_ratio = (1 - compressed_size / original_size) * 100
        max_frame_size = max(frame_sizes) if frame_sizes else 256
        
        print(f"\nOriginal size: {original_size / 1024:.1f}KB")
        print(f"Compressed size: {compressed_size / 1024:.1f}KB")
        print(f"Compression ratio: {compression_ratio:.1f}%")
        print(f"Max frame size: {max_frame_size} bytes")
        
        # 生成C代码
        print("\nGenerating C code...")
        
        c_code = """// ESP32 Black & White Video Data
// Source: """ + os.path.basename(input_file) + """
// Resolution: 128x96
// FPS: """ + str(target_fps) + """
// Total frames: """ + str(actual_frames) + """
// Color mode: Black & White (threshold=""" + str(threshold) + """)
// Compression: Pure RLE

#ifndef VIDEO_H
#define VIDEO_H

#include <Arduino.h>

// Video parameters
#define VIDEO_WIDTH 128
#define VIDEO_HEIGHT 96
#define VIDEO_FPS """ + str(target_fps) + """
#define VIDEO_FRAMES """ + str(actual_frames) + """
#define VIDEO_BW 1
#define VIDEO_USE_RLE 1
#define VIDEO_THRESHOLD """ + str(threshold) + """
#define VIDEO_MAX_FRAME_SIZE """ + str(max_frame_size) + """

// Video info structure
typedef struct {
  uint16_t totalFrames;
  uint8_t fps;
  uint16_t width;
  uint16_t height;
  uint8_t bw;
  uint8_t useRLE;
} VideoInfo_t;

// Video frame data
const uint8_t video_frames[""" + str(actual_frames) + """][""" + str(max_frame_size) + """] PROGMEM = {
"""
        
        # 生成帧数据
        for i, data in enumerate(compressed_frames):
            c_code += "  // Frame " + str(i+1) + "/" + str(actual_frames) + " (Size: " + str(len(data)) + " bytes)\n  {"
            
            # 将所有数据转换为十六进制字符串
            hex_values = []
            for value in data:
                hex_values.append("0x{:02X}".format(value))
            
            # 每16个值换行
            for j in range(0, len(hex_values), 16):
                chunk = hex_values[j:j+16]
                c_code += ",".join(chunk) + ",\n   "
            
            c_code = c_code.rstrip(',\n ') + "},\n"
        
        c_code += """
};

// Video frame sizes
const uint16_t video_frame_sizes[""" + str(actual_frames) + """] PROGMEM = {
""" + ', '.join(map(str, frame_sizes)) + """
};

// Video info
const VideoInfo_t video_info = {
  """ + str(actual_frames) + """,  // Total frames
  """ + str(target_fps) + """,     // FPS
  128,              // Width
  96,               // Height
  1,                // Black & White
  1                 // RLE compression
};

#endif // VIDEO_H
"""
        
        # 保存C头文件
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file)
        with open(output_path, 'w') as f:
            f.write(c_code)
        
        file_size = os.path.getsize(output_path)
        print(f"\nConversion complete!")
        print(f"Output file: {output_path}")
        print(f"File size: {file_size / 1024:.1f}KB ({file_size / (1024*1024):.2f}MB)")
        print(f"Total frames: {actual_frames}")
        print(f"Video duration: {actual_frames / target_fps:.1f}s")
        
        # 计算实际FLASH占用
        actual_flash_usage = compressed_size
        print(f"Actual FLASH usage: {actual_flash_usage / 1024:.1f}KB ({actual_flash_usage / (1024*1024):.2f}MB)")
        print(f"Remaining space: {(max_size_mb * 1024 * 1024 - actual_flash_usage) / 1024:.1f}KB")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理临时文件
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    print("=" * 60)
    print("ESP32 Black & White Video Converter")
    print("=" * 60)
    print()
    
    # 检查ffmpeg
    if not check_ffmpeg():
        print("Error: FFmpeg not found")
        print("Download: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    print("Working directory:", os.getcwd())
    print()
    
    # 默认参数
    input_file = "badapple.mp4"
    output_file = "video.h"
    max_size_mb = 0.4
    target_fps = 10
    threshold = 128
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--input="):
                input_file = arg.split("=")[1]
            elif arg.startswith("--output="):
                output_file = arg.split("=")[1]
            elif arg.startswith("--size="):
                max_size_mb = float(arg.split("=")[1])
            elif arg.startswith("--fps="):
                target_fps = int(arg.split("=")[1])
            elif arg.startswith("--threshold="):
                threshold = int(arg.split("=")[1])
    
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Max size: {max_size_mb}MB")
    print(f"FPS: {target_fps}")
    print(f"B&W threshold: {threshold}")
    print()
    
    # 处理输入文件路径
    if not os.path.isabs(input_file):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_dir_file = os.path.join(script_dir, input_file)
        if os.path.exists(script_dir_file):
            input_file = script_dir_file
        else:
            current_dir_file = os.path.join(os.getcwd(), input_file)
            if os.path.exists(current_dir_file):
                input_file = current_dir_file
            else:
                print(f"Error: File not found: {input_file}")
                print(f"  Tried: {script_dir_file}")
                print(f"  Tried: {current_dir_file}")
                sys.exit(1)
    
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    if not output_file.endswith('.h'):
        output_file += '.h'
    
    print("-" * 60)
    success = convert_video(input_file, output_file, max_size_mb=max_size_mb,
                           target_fps=target_fps, threshold=threshold)
    
    if success:
        print()
        print("Next steps:")
        print(f"1. Copy {output_file} to project directory")
        print(f"2. Include in main program: #include \"{output_file}\"")
        print(f"3. Upload to ESP32")
    else:
        print("\nConversion failed!")
        sys.exit(1)
    
    print()

if __name__ == "__main__":
    main()
