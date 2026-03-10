#include "camera.h"

// YUV转RGB的查找表
static unsigned char y_table[256];
static short u_table[256];
static short v_table[256];
static short initialized = 0;

// 初始化YUV转RGB转换表
static void init_yuv_tables() {
    if (initialized) return;
    
    for (int i = 0; i < 256; i++) {
        y_table[i] = (unsigned char)(i - 16);
        
        // U和V的范围是16-240，需要转换到-112到112
        u_table[i] = (short)((i - 128) * 1.13983);
        v_table[i] = (short)((i - 128) * 1.5748);
    }
    
    initialized = 1;
}

int yuv420sp_to_rgb565(const unsigned char *yuv, unsigned short *rgb, int width, int height) {
    if (!yuv || !rgb || width <= 0 || height <= 0) {
        log_print(LOG_error, "invalid parameters for yuv to rgb conversion");
        return error_invalid_param;
    }
    
    init_yuv_tables();
    
    int y_size = width * height;
    const unsigned char *y_data = yuv;
    const unsigned char *uv_data = yuv + y_size;
    
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            // 获取y分量
            unsigned char y_val = y_data[y * width + x];
            
            // 获取u和v分量（每2x2像素共享一个u和v）
            int uv_index = (y >> 1) * (width >> 1) + (x >> 1);
            unsigned char u_val = uv_data[uv_index * 2];
            unsigned char v_val = uv_data[uv_index * 2 + 1];
            
            // 转换为rgb
            int r = y_table[y_val] + v_table[v_val];
            int g = y_table[y_val] - ((u_table[u_val] * 54 + v_table[v_val] * 183) >> 8);
            int b = y_table[y_val] + u_table[u_val];
            
            // 裁剪到0-255范围
            r = (r < 0) ? 0 : ((r > 255) ? 255 : r);
            g = (g < 0) ? 0 : ((g > 255) ? 255 : g);
            b = (b < 0) ? 0 : ((b > 255) ? 255 : b);
            
            // 转换为rgb565格式
            unsigned short rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
            
            // 写入结果
            rgb[y * width + x] = rgb565;
        }
    }
    
    return success;
}

// 简化的字体数据（仅包含0-9, :, - 字符）
static const unsigned char font_data[][8] = {
    // 0
    {0x3C, 0x66, 0x6E, 0x76, 0x66, 0x66, 0x3C, 0x00},
    // 1
    {0x10, 0x30, 0x50, 0x10, 0x10, 0x10, 0x7C, 0x00},
    // 2
    {0x3E, 0x60, 0x60, 0x3E, 0x06, 0x06, 0x7E, 0x00},
    // 3
    {0x3E, 0x60, 0x60, 0x3E, 0x60, 0x60, 0x3E, 0x00},
    // 4
    {0x66, 0x66, 0x66, 0x7E, 0x06, 0x06, 0x06, 0x00},
    // 5
    {0x7E, 0x06, 0x06, 0x7E, 0x60, 0x60, 0x3E, 0x00},
    // 6
    {0x3E, 0x06, 0x06, 0x7E, 0x66, 0x66, 0x3E, 0x00},
    // 7
    {0x7E, 0x60, 0x60, 0x60, 0x60, 0x60, 0x60, 0x00},
    // 8
    {0x3E, 0x66, 0x66, 0x3E, 0x66, 0x66, 0x3E, 0x00},
    // 9
    {0x3E, 0x66, 0x66, 0x3E, 0x60, 0x60, 0x3E, 0x00},
    // :
    {0x00, 0x18, 0x18, 0x00, 0x00, 0x18, 0x18, 0x00},
    // -
    {0x00, 0x00, 0x00, 0x7E, 0x00, 0x00, 0x00, 0x00}
};

int add_timestamp_watermark(unsigned short *rgb, int width, int height, const char *timestamp) {
    if (!rgb || !timestamp || width <= 0 || height <= 0) {
        log_print(LOG_ERROR, "Invalid parameters for adding watermark");
        return ERROR_INVALID_PARAM;
    }
    
    int text_color = COLOR_WHITE;
    int bg_color = COLOR_BLACK;
    
    // 水印位置（右下角）
    int x = width - 120;
    int y = height - 20;
    
    // 绘制背景矩形
    for (int dy = 0; dy < 16; dy++) {
        for (int dx = 0; dx < 120; dx++) {
            int pos_x = x + dx;
            int pos_y = y + dy;
            
            if (pos_x >= 0 && pos_x < width && pos_y >= 0 && pos_y < height) {
                rgb[pos_y * width + pos_x] = bg_color;
            }
        }
    }
    
    // 绘制时间戳文本
    for (int i = 0; i < strlen(timestamp); i++) {
        char c = timestamp[i];
        int char_index = -1;
        
        if (c >= '0' && c <= '9') {
            char_index = c - '0';
        } else if (c == ':') {
            char_index = 10;
        } else if (c == '-') {
            char_index = 11;
        }
        
        if (char_index == -1) {
            continue; // 跳过不支持的字符
        }
        
        // 绘制每个字符的8x8像素
        for (int dy = 0; dy < 8; dy++) {
            unsigned char row = font_data[char_index][dy];
            
            for (int dx = 0; dx < 8; dx++) {
                if (row & (1 << (7 - dx))) {
                    int pos_x = x + i * 8 + dx;
                    int pos_y = y + dy + 4; // 居中显示
                    
                    if (pos_x >= 0 && pos_x < width && pos_y >= 0 && pos_y < height) {
                        rgb[pos_y * width + pos_x] = text_color;
                    }
                }
            }
        }
    }
    
    return SUCCESS;
}
