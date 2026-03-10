#include "ui.h"
#include <linux/input.h>
#include <fcntl.h>
#include <errno.h>

#define TOUCH_DEVICE "/dev/input/event0"

static int touch_fd = -1;

int touch_init(void) {
    // 打开触摸屏设备
    touch_fd = open(TOUCH_DEVICE, O_RDONLY);
    if (touch_fd == -1) {
        log_print(LOG_ERROR, "Failed to open touch device %s: %s", TOUCH_DEVICE, strerror(errno));
        return ERROR_DEVICE_NOT_FOUND;
    }
    
    log_print(LOG_INFO, "Touch screen initialized successfully");
    return SUCCESS;
}

void touch_cleanup(void) {
    if (touch_fd != -1) {
        close(touch_fd);
        touch_fd = -1;
    }
    
    log_print(LOG_INFO, "Touch screen cleaned up");
}

int touch_wait_event(int *x, int *y) {
    if (touch_fd == -1) {
        log_print(LOG_ERROR, "Touch device not initialized");
        return ERROR;
    }
    
    struct input_event event;
    static int x_pos = 0, y_pos = 0;
    static int touch_down = 0;
    
    while (1) {
        ssize_t ret = read(touch_fd, &event, sizeof(event));
        if (ret == -1) {
            if (errno == EINTR) {
                continue;
            }
            
            log_print(LOG_ERROR, "Failed to read touch event: %s", strerror(errno));
            return ERROR_IO;
        }
        
        if (ret != sizeof(event)) {
            log_print(LOG_WARNING, "Incomplete touch event read");
            continue;
        }
        
        if (event.type == EV_ABS) {
            if (event.code == ABS_X) {
                // 转换为屏幕坐标（假设触摸屏和屏幕分辨率相同）
                x_pos = event.value;
            } else if (event.code == ABS_Y) {
                // 转换为屏幕坐标（假设触摸屏和屏幕分辨率相同）
                y_pos = event.value;
            }
        } else if (event.type == EV_KEY && event.code == BTN_TOUCH) {
            if (event.value == 1) {
                // 触摸按下
                touch_down = 1;
            } else if (event.value == 0 && touch_down) {
                // 触摸释放
                touch_down = 0;
                
                if (x) *x = x_pos;
                if (y) *y = y_pos;
                
                return SUCCESS;
            }
        }
    }
}

// 检查触摸是否在按钮区域内
int is_touch_in_button(int x, int y, Button *btn) {
    if (!btn) return 0;
    
    return (x >= btn->x && x < btn->x + btn->width &&
            y >= btn->y && y < btn->y + btn->height);
}

// 处理按钮触摸事件
void handle_button_touch(int x, int y, Button *buttons, int num_buttons) {
    for (int i = 0; i < num_buttons; i++) {
        if (is_touch_in_button(x, y, &buttons[i])) {
            buttons[i].pressed = 1;
            draw_button(&buttons[i]);
            display_update();
            
            // 模拟按钮按下效果
            usleep(100000);
            
            buttons[i].pressed = 0;
            draw_button(&buttons[i]);
            display_update();
            
            // 调用回调函数
            if (buttons[i].callback) {
                buttons[i].callback();
            }
            
            break;
        }
    }
}
