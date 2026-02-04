// ESP32黑白视频播放器
// 播放128x96分辨率的黑白视频

#include <SPI.h>
#include <TFT_eSPI.h>
#include <string.h>

// 引入视频数据头文件
#include "video.h"

// 定义默认压缩模式（如果video.h中没有定义）
#ifndef VIDEO_BW
#define VIDEO_BW 0
#endif

#ifndef VIDEO_USE_RLE
#define VIDEO_USE_RLE 0
#endif

// 创建显示对象
TFT_eSPI tft = TFT_eSPI();

// Current frame index
int currentFrame = 0;
unsigned long lastFrameTime = 0;

// Decompression buffer
uint8_t decompressedFrame[VIDEO_WIDTH * VIDEO_HEIGHT];

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("ESP32 B&W Video Player starting...");
  
  // Initialize display
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  
  Serial.println("Display initialized");
  Serial.printf("Video resolution: %dx%d\n", VIDEO_WIDTH, VIDEO_HEIGHT);
  Serial.printf("Frame rate: %dfps\n", VIDEO_FPS);
  Serial.printf("Total frames: %d\n", VIDEO_FRAMES);
  Serial.printf("Color mode: %s\n", VIDEO_BW ? "Black & White" : "Grayscale");
  Serial.printf("Compression: %s\n", VIDEO_USE_RLE ? "RLE" : "None");
  
  // Display start message
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.setCursor(40, 100);
  tft.println("B&W Player");
  tft.setTextSize(1);
  tft.setCursor(60, 140);
  tft.println("Press to start");
  
  delay(2000);
  tft.fillScreen(TFT_BLACK);
}

void loop() {
  // Calculate frame interval
  unsigned long frameInterval = 1000 / VIDEO_FPS;
  unsigned long currentTime = millis();
  
  // Check if next frame needs to be displayed
  if (currentTime - lastFrameTime >= frameInterval) {
    lastFrameTime = currentTime;
    
    // Play video frame
    playFrame(currentFrame);
    
    // Update frame index
    currentFrame++;
    if (currentFrame >= VIDEO_FRAMES) {
      currentFrame = 0; // Loop playback
    }
  }
}

// RLE decompression function for B&W
void decompressRLE_BW(const uint8_t* compressedData, uint16_t frameSize, uint8_t* output) {
  int index = 0;
  int pos = 0;
  int totalPixels = VIDEO_WIDTH * VIDEO_HEIGHT;
  
  while (index < frameSize && pos < totalPixels) {
    // Read color and count
    uint8_t color = pgm_read_byte(&compressedData[index++]);
    uint8_t count = pgm_read_byte(&compressedData[index++]);
    
    // Fill output buffer
    for (int i = 0; i < count && pos < totalPixels; i++) {
      output[pos++] = color;
    }
  }
}

// Play single video frame - optimized for smooth display
void playFrame(int frameIndex) {
  // Get screen dimensions
  int screenWidth = tft.width();
  int screenHeight = tft.height();
  
  // Calculate scaling to fill the screen while maintaining aspect ratio
  float scaleX = (float)screenWidth / VIDEO_WIDTH;
  float scaleY = (float)screenHeight / VIDEO_HEIGHT;
  float scale = min(scaleX, scaleY);
  
  // Calculate display dimensions
  int displayWidth = (int)(VIDEO_WIDTH * scale);
  int displayHeight = (int)(VIDEO_HEIGHT * scale);
  
  // Calculate offsets to center the video
  int offsetX = (screenWidth - displayWidth) / 2;
  int offsetY = (screenHeight - displayHeight) / 2;
  
  // Get current frame data
  const uint8_t* frameData = (const uint8_t*)&video_frames[frameIndex][0];
  uint16_t frameSize = pgm_read_word(&video_frame_sizes[frameIndex]);
  
  // Decompress frame
  if (VIDEO_USE_RLE) {
    decompressRLE_BW(frameData, frameSize, decompressedFrame);
  }
  
  // Draw frame - use pushImage for faster rendering
  if (VIDEO_BW) {
    // For 1:1 or simple scaling, use optimized rendering
    if (scale >= 1.0) {
      // Scale up - use fillRect for each pixel block
      // Process in batches to reduce SPI transactions
      tft.startWrite();
      for (int y = 0; y < VIDEO_HEIGHT; y++) {
        int drawY = offsetY + (int)(y * scale);
        int pixelHeight = (int)((y + 1) * scale) - (int)(y * scale);
        if (drawY >= screenHeight) break;
        
        int srcIndex = y * VIDEO_WIDTH;
        
        // Draw horizontal strips of same color
        int x = 0;
        while (x < VIDEO_WIDTH) {
          uint8_t pixel = decompressedFrame[srcIndex + x];
          uint16_t color = pixel ? TFT_WHITE : TFT_BLACK;
          
          // Find run of same color
          int runLength = 1;
          int drawX = offsetX + (int)(x * scale);
          while (x + runLength < VIDEO_WIDTH && 
                 decompressedFrame[srcIndex + x + runLength] == pixel &&
                 (int)((x + runLength) * scale) == drawX + (int)(runLength * scale)) {
            runLength++;
          }
          
          int pixelWidth = (int)((x + runLength) * scale) - (int)(x * scale);
          
          // Draw the run
          if (drawX < screenWidth) {
            tft.fillRect(drawX, drawY, pixelWidth, pixelHeight, color);
          }
          
          x += runLength;
        }
      }
      tft.endWrite();
    } else {
      // Scale down - use pushImage with downsampled buffer
      // Create a temporary buffer for the scaled image
      static uint16_t scaledBuffer[128]; // Max width buffer for one row
      
      for (int y = 0; y < displayHeight; y++) {
        int srcY = (int)(y / scale);
        if (srcY >= VIDEO_HEIGHT) srcY = VIDEO_HEIGHT - 1;
        int srcIndex = srcY * VIDEO_WIDTH;
        
        // Scale one row
        for (int x = 0; x < displayWidth; x++) {
          int srcX = (int)(x / scale);
          if (srcX >= VIDEO_WIDTH) srcX = VIDEO_WIDTH - 1;
          uint8_t pixel = decompressedFrame[srcIndex + srcX];
          scaledBuffer[x] = pixel ? TFT_WHITE : TFT_BLACK;
        }
        
        // Push the entire row at once
        tft.pushImage(offsetX, offsetY + y, displayWidth, 1, scaledBuffer);
      }
    }
  }
}
