#ifndef DISPLAY_DRIVER_H
#define DISPLAY_DRIVER_H

#include <TFT_eSPI.h>
#include "config.h"

// 外部引用
extern TFT_eSPI tft;

// 显示状态枚举
enum DisplayState_e {
  DISPLAY_STATE_NORMAL,     // 正常显示
  DISPLAY_STATE_WAITING,    // 等待连接
  DISPLAY_STATE_ERROR,      // 错误状态
  DISPLAY_STATE_DEBUG,      // 调试信息
  DISPLAY_STATE_ROM_SELECT  // ROM选择界面
};
typedef enum DisplayState_e DisplayState_t;

// 全局变量
extern DisplayState_t currentDisplayState;
extern bool isScreenOn;
extern unsigned long lastActivityTime;

// 函数声明
void displayDriverInit();
void updateDisplayState(DisplayState_t newState);
void drawWaitingScreen();
void drawErrorScreen(const char* errorMsg);
void drawDebugInfo(int fps, int frameCount, float frameTime);
void drawGameFrame(const uint8_t* frameBuffer, int width, int height);
void drawGamepadUI();
void updateGamepadUI(bool up, bool down, bool left, bool right, bool a, bool b, bool select, bool start);
void handleScreenTimeout();
void drawRomSelectScreen();

#endif // DISPLAY_DRIVER_H
