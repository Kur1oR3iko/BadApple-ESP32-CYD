#include <TFT_eSPI.h>
#include "video_data.h"

TFT_eSPI tft = TFT_eSPI();

const uint32_t FRAME_DELAY_US = 41667; // 24 FPS

const uint8_t CMD_FRAME_END = 0x01;
const uint8_t CMD_VIDEO_END = 0x00;

// Removed pixelState array to save memory and improve performance

// Simplified version - removed complex area merging

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Bad Apple Video Player (Differential)");
  Serial.print("Resolution: ");
  Serial.print(VIDEO_WIDTH);
  Serial.print("x");
  Serial.println(VIDEO_HEIGHT);
  Serial.print("Frames: ");
  Serial.println(VIDEO_FRAMES);
  Serial.print("FPS: ");
  Serial.println(VIDEO_FPS);
  Serial.print("Data size: ");
  Serial.println(VIDEO_DATA_SIZE);
  
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.setCursor(0, 0);
  tft.println("BadApple-ESP32CYD.Ver");
  tft.setTextSize(1);
  tft.println("108x81 @ 24fps");
  tft.println("by KurioReiko");
  
  delay(1000);
  tft.fillScreen(TFT_BLACK);
  
  playVideo();
}

void playVideo() {
  Serial.println("Starting video playback...");
  
  uint32_t dataIndex = 0;
  uint16_t frameCount = 0;
  bool playing = true;
  
  // Screen dimensions (320x240)
  const int SCREEN_WIDTH = 320;
  const int SCREEN_HEIGHT = 240;
  
  // Video dimensions (108x81)
  const int VIDEO_WIDTH = 108;
  const int VIDEO_HEIGHT = 81;
  
  // Scaling: 3x to fill screen (108*3=324, 81*3=243, slightly larger than screen)
  // Center the video on screen
  const int OFFSET_X = (SCREEN_WIDTH - VIDEO_WIDTH * 3) / 2;  // (320 - 324) / 2 = -2
  const int OFFSET_Y = (SCREEN_HEIGHT - VIDEO_HEIGHT * 3) / 2;  // (240 - 243) / 2 = -1
  
  // Initialize frame timing
  unsigned long frameStartTime = micros();
  
  while (playing) {
    uint8_t cmd = pgm_read_byte(&badAppleVideo[dataIndex++]);
    
    if (cmd == CMD_FRAME_END) {
      // Calculate actual frame time and adjust delay
      unsigned long frameEndTime = micros();
      unsigned long frameTime = frameEndTime - frameStartTime;
      
      // Only delay if we have time left
      if (frameTime < FRAME_DELAY_US) {
        delayMicroseconds(FRAME_DELAY_US - frameTime);
      }
      
      frameCount++;
      
      if (frameCount % 20 == 0) {
        Serial.print("Frame: ");
        Serial.println(frameCount);
      }
      
      // Reset frame start time for next frame
      frameStartTime = micros();
    } else if (cmd == CMD_VIDEO_END) {
      playing = false;
    } else {
      uint8_t x = cmd & 0x7F;
      uint8_t y = pgm_read_byte(&badAppleVideo[dataIndex++]);
      
      if (y & 0x80) {
        y &= 0x7F;
        if (x < VIDEO_WIDTH && y < VIDEO_HEIGHT) {
          // Draw filled rectangle for solid white area (3x scaling)
          int sx = x * 3 + OFFSET_X;
          int sy = y * 3 + OFFSET_Y;
          tft.fillRect(sx, sy, 3, 3, TFT_WHITE);
        }
      } else {
        y &= 0x7F;
        if (x < VIDEO_WIDTH && y < VIDEO_HEIGHT) {
          // Clear area (3x scaling)
          int sx = x * 3 + OFFSET_X;
          int sy = y * 3 + OFFSET_Y;
          tft.fillRect(sx, sy, 3, 3, TFT_BLACK);
        }
      }
    }
  }
  
  Serial.print("Video ended. Total frames: ");
  Serial.println(frameCount);
  
  tft.fillScreen(TFT_BLACK);
  tft.setCursor(0, 0);
  tft.print("Done: ");
  tft.print(frameCount);
  tft.println(" frames");
}

void loop() {
  
}
