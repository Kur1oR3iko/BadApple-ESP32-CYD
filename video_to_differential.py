import cv2
import numpy as np
import sys

def convert_video_to_differential(input_video, output_file, width=128, height=96, max_frames=8000, threshold=128, target_fps=30):
    try:
        cap = cv2.VideoCapture(input_video)
    except Exception as e:
        print(f"Error: Cannot open video file {input_video}")
        print(f"Exception: {e}")
        return
    
    if not cap.isOpened():
        print(f"Error: Cannot open video file {input_video}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video info: {total_frames} frames, {fps} FPS")
    print(f"Target resolution: {width}x{height}")
    print(f"Target FPS: {target_fps}")
    print(f"Max frames to convert: {max_frames}")
    print(f"Threshold: {threshold}")
    print(f"Using differential encoding")
    
    frame_skip = fps / target_fps
    frame_counter = 0.0
    
    mp = [[False for j in range(height)] for i in range(width)]
    frame_data = bytearray()
    frame_count = 0
    total_changes = 0
    
    while frame_count < max_frames:
        ret, frame = cap.read()
        
        if not ret:
            break
        
        frame_counter += frame_skip
        if frame_counter < 1.0:
            continue
        frame_counter -= 1.0
        
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_resized = cv2.resize(frame_gray, (width, height), interpolation=cv2.INTER_NEAREST)
        
        _, binary = cv2.threshold(frame_resized, threshold, 255, cv2.THRESH_BINARY)
        
        frame_changes = 0
        for i in range(width):
            for j in range(height):
                if binary[j, i] == 255:
                    if mp[i][j] == False:
                        frame_data.append(i | 0x80)
                        frame_data.append(j | 0x80)
                        mp[i][j] = True
                        frame_changes += 1
                else:
                    if mp[i][j] == True:
                        frame_data.append(i | 0x80)
                        frame_data.append(j & 0x7F)
                        mp[i][j] = False
                        frame_changes += 1
        
        frame_data.append(0x01)
        frame_count += 1
        total_changes += frame_changes
        
        if frame_count % 500 == 0:
            avg_changes = total_changes / frame_count
            print(f"Processed {frame_count} frames, avg {avg_changes:.1f} changes/frame")
    
    cap.release()
    
    frame_data.append(0x00)
    
    print(f"Total frames: {frame_count}")
    print(f"Total data size: {len(frame_data)} bytes")
    print(f"Average changes per frame: {total_changes / frame_count:.1f}")
    print(f"Estimated file size: {len(frame_data) / 1024:.1f} KB")
    
    compression_ratio = (total_changes * 4) / len(frame_data) if len(frame_data) > 0 else 0
    print(f"Compression ratio: {compression_ratio:.2f}x")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"// Bad Apple Video Data (Differential) - {width}x{height}, {frame_count} frames\n")
        f.write(f"// Generated from: {input_video}\n")
        f.write(f"// Threshold: {threshold}, Target FPS: {target_fps}\n")
        f.write(f"// Total data: {len(frame_data)} bytes\n\n")
        f.write(f"#ifndef VIDEO_DATA_H\n")
        f.write(f"#define VIDEO_DATA_H\n\n")
        f.write(f"#include <pgmspace.h>\n\n")
        f.write(f"const uint16_t VIDEO_WIDTH = {width};\n")
        f.write(f"const uint16_t VIDEO_HEIGHT = {height};\n")
        f.write(f"const uint16_t VIDEO_FRAMES = {frame_count};\n")
        f.write(f"const uint32_t VIDEO_DATA_SIZE = {len(frame_data)};\n")
        f.write(f"const uint16_t VIDEO_FPS = {target_fps};\n\n")
        f.write(f"PROGMEM const uint8_t badAppleVideo[] = {{\n")
        
        for i in range(0, len(frame_data), 16):
            chunk = frame_data[i:i+16]
            line = "  "
            for val in chunk:
                line += f"0x{val:02X}, "
            # Keep trailing comma for each line
            f.write(line + "\n")
        
        f.write("};\n\n")
        f.write("#endif // VIDEO_DATA_H\n")
    
    print(f"Output written to: {output_file}")
    print(f"Conversion complete!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_video = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "video_data.h"
        width = int(sys.argv[3]) if len(sys.argv) > 3 else 128
        height = int(sys.argv[4]) if len(sys.argv) > 4 else 96
        max_frames = int(sys.argv[5]) if len(sys.argv) > 5 else 13145
        threshold = int(sys.argv[6]) if len(sys.argv) > 6 else 128
        target_fps = int(sys.argv[7]) if len(sys.argv) > 7 else 50
        
        convert_video_to_differential(input_video, output_file, width, height, max_frames, threshold, target_fps)
    else:
        print("Usage: python video_to_differential.py <input_video> [output_file] [width] [height] [max_frames] [threshold] [target_fps]")
