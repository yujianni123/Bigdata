#ifndef __UI_H__
#define __UI_H__

#include "../common/common.h"

// 屏幕分辨率
#define SCREEN_WIDTH  1024
#define SCREEN_HEIGHT 600

// 颜色定义
#define COLOR_BLACK   0x0000
#define COLOR_WHITE   0xFFFF
#define COLOR_RED     0xF800
#define COLOR_GREEN   0x07E0
#define COLOR_BLUE    0x001F
#define COLOR_YELLOW  0xFFE0
#define COLOR_GRAY    0x8410

// 按钮定义
typedef struct {
    int x;
    int y;
    int width;
    int height;
    const char *text;
    unsigned short color;
    unsigned short text_color;
    int pressed;
    void (*callback)(void);
} Button;

// 初始化显示
int display_init(void);

// 清理显示资源
void display_cleanup(void);

// 显示背景图
int display_background(const char *bmp_path);

// 绘制按钮
void draw_button(Button *btn);

// 更新显示
void display_update(void);

// 触摸屏事件处理
int touch_init(void);
void touch_cleanup(void);
int touch_wait_event(int *x, int *y);

// 全局变量
extern unsigned short *framebuffer;
extern int fb_fd;
extern int fb_stride;
extern AppMode current_mode;

#endif // __UI_H__
