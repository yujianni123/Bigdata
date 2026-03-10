#include "ui.h"
#include <linux/fb.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <errno.h>

// 全局变量
unsigned short *framebuffer = NULL;
int fb_fd = -1;
int fb_stride = 0;
AppMode current_mode = MODE_MAIN;

// BMP文件头结构
typedef struct {
    unsigned short bfType;
    unsigned int bfSize;
    unsigned short bfReserved1;
    unsigned short bfReserved2;
    unsigned int bfOffBits;
} BmpFileHeader;

// BMP信息头结构
typedef struct {
    unsigned int biSize;
    int biWidth;
    int biHeight;
    unsigned short biPlanes;
    unsigned short biBitCount;
    unsigned int biCompression;
    unsigned int biSizeImage;
    int biXPelsPerMeter;
    int biYPelsPerMeter;
    unsigned int biClrUsed;
    unsigned int biClrImportant;
} BmpInfoHeader;

int display_init(void) {
    // 打开帧缓冲设备
    fb_fd = open("/dev/fb0", O_RDWR);
    if (fb_fd == -1) {
        log_print(LOG_ERROR, "Failed to open framebuffer device: %s", strerror(errno));
        return ERROR_DEVICE_NOT_FOUND;
    }
    
    // 获取屏幕信息
    struct fb_var_screeninfo var_info;
    if (ioctl(fb_fd, FBIOGET_VSCREENINFO, &var_info) == -1) {
        log_print(LOG_ERROR, "Failed to get screen info: %s", strerror(errno));
        close(fb_fd);
        return ERROR_IO;
    }
    
    struct fb_fix_screeninfo fix_info;
    if (ioctl(fb_fd, FBIOGET_FSCREENINFO, &fix_info) == -1) {
        log_print(LOG_ERROR, "Failed to get fixed screen info: %s", strerror(errno));
        close(fb_fd);
        return ERROR_IO;
    }
    
    // 检查屏幕分辨率
    if (var_info.xres != SCREEN_WIDTH || var_info.yres != SCREEN_HEIGHT) {
        log_print(LOG_WARNING, "Screen resolution mismatch: %dx%d vs expected %dx%d",
                 var_info.xres, var_info.yres, SCREEN_WIDTH, SCREEN_HEIGHT);
    }
    
    // 检查像素格式
    if (var_info.bits_per_pixel != 16) {
        log_print(LOG_ERROR, "Unsupported pixel format: %d bits per pixel", var_info.bits_per_pixel);
        close(fb_fd);
        return ERROR;
    }
    
    // 计算帧缓冲大小
    unsigned long fb_size = fix_info.smem_len;
    
    // 映射帧缓冲
    framebuffer = (unsigned short *)mmap(NULL, fb_size, PROT_READ | PROT_WRITE, MAP_SHARED, fb_fd, 0);
    if (framebuffer == MAP_FAILED) {
        log_print(LOG_ERROR, "Failed to map framebuffer: %s", strerror(errno));
        close(fb_fd);
        return ERROR_IO;
    }
    
    fb_stride = fix_info.line_length / 2; // 每个像素2字节
    
    log_print(LOG_INFO, "Display initialized successfully");
    return SUCCESS;
}

void display_cleanup(void) {
    if (framebuffer) {
        munmap(framebuffer, fb_stride * SCREEN_HEIGHT * 2);
        framebuffer = NULL;
    }
    
    if (fb_fd != -1) {
        close(fb_fd);
        fb_fd = -1;
    }
    
    log_print(LOG_INFO, "Display cleaned up");
}

static unsigned short rgb888_to_rgb565(unsigned char r, unsigned char g, unsigned char b) {
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
}

int display_background(const char *bmp_path) {
    if (!framebuffer) {
        log_print(LOG_ERROR, "Framebuffer not initialized");
        return ERROR;
    }
    
    // 打开BMP文件
    FILE *file = fopen(bmp_path, "rb");
    if (!file) {
        log_print(LOG_ERROR, "Failed to open BMP file %s: %s", bmp_path, strerror(errno));
        return ERROR_FILE_NOT_FOUND;
    }
    
    // 读取文件头
    BmpFileHeader file_header;
    if (fread(&file_header, sizeof(BmpFileHeader), 1, file) != 1) {
        log_print(LOG_ERROR, "Failed to read BMP file header");
        fclose(file);
        return ERROR_IO;
    }
    
    // 检查是否为BMP文件
    if (file_header.bfType != 0x4D42) { // 'BM'
        log_print(LOG_ERROR, "Not a BMP file");
        fclose(file);
        return ERROR;
    }
    
    // 读取信息头
    BmpInfoHeader info_header;
    if (fread(&info_header, sizeof(BmpInfoHeader), 1, file) != 1) {
        log_print(LOG_ERROR, "Failed to read BMP info header");
        fclose(file);
        return ERROR_IO;
    }
    
    // 检查是否为24位BMP
    if (info_header.biBitCount != 24) {
        log_print(LOG_ERROR, "Unsupported BMP format: %d bits per pixel", info_header.biBitCount);
        fclose(file);
        return ERROR;
    }
    
    // 检查是否为未压缩格式
    if (info_header.biCompression != 0) {
        log_print(LOG_ERROR, "Unsupported BMP compression");
        fclose(file);
        return ERROR;
    }
    
    // 计算每行像素的字节数（必须是4的倍数）
    int line_size = (info_header.biWidth * 3 + 3) & ~3;
    
    // 移动到像素数据位置
    fseek(file, file_header.bfOffBits, SEEK_SET);
    
    // 读取像素数据（BMP是从下到上存储的）
    unsigned char *line_buffer = (unsigned char *)safe_malloc(line_size);
    
    for (int y = 0; y < info_header.biHeight; y++) {
        // 读取一行像素数据
        if (fread(line_buffer, 1, line_size, file) != line_size) {
            log_print(LOG_ERROR, "Failed to read BMP pixel data");
            safe_free((void **)&line_buffer);
            fclose(file);
            return ERROR_IO;
        }
        
        // 转换为RGB565并写入帧缓冲
        for (int x = 0; x < info_header.biWidth; x++) {
            unsigned char b = line_buffer[x * 3];
            unsigned char g = line_buffer[x * 3 + 1];
            unsigned char r = line_buffer[x * 3 + 2];
            
            unsigned short color = rgb888_to_rgb565(r, g, b);
            
            // BMP是从下到上存储的，所以需要翻转y坐标
            int fb_y = SCREEN_HEIGHT - 1 - y;
            if (x < SCREEN_WIDTH && fb_y >= 0) {
                framebuffer[fb_y * fb_stride + x] = color;
            }
        }
    }
    
    safe_free((void **)&line_buffer);
    fclose(file);
    
    log_print(LOG_INFO, "Background image displayed: %s", bmp_path);
    return SUCCESS;
}

void draw_button(Button *btn) {
    if (!framebuffer || !btn) {
        return;
    }
    
    // 绘制按钮背景
    unsigned short bg_color = btn->pressed ? (btn->color & 0x7BEF) : btn->color; // 按下时颜色变深
    
    for (int y = 0; y < btn->height; y++) {
        for (int x = 0; x < btn->width; x++) {
            int fb_x = btn->x + x;
            int fb_y = btn->y + y;
            
            if (fb_x >= 0 && fb_x < SCREEN_WIDTH && fb_y >= 0 && fb_y < SCREEN_HEIGHT) {
                framebuffer[fb_y * fb_stride + fb_x] = bg_color;
            }
        }
    }
    
    // 绘制按钮边框
    unsigned short border_color = COLOR_BLACK;
    
    // 上边框
    for (int x = 0; x < btn->width; x++) {
        int fb_x = btn->x + x;
        int fb_y = btn->y;
        
        if (fb_x >= 0 && fb_x < SCREEN_WIDTH && fb_y >= 0 && fb_y < SCREEN_HEIGHT) {
            framebuffer[fb_y * fb_stride + fb_x] = border_color;
        }
    }
    
    // 下边框
    for (int x = 0; x < btn->width; x++) {
        int fb_x = btn->x + x;
        int fb_y = btn->y + btn->height - 1;
        
        if (fb_x >= 0 && fb_x < SCREEN_WIDTH && fb_y >= 0 && fb_y < SCREEN_HEIGHT) {
            framebuffer[fb_y * fb_stride + fb_x] = border_color;
        }
    }
    
    // 左边框
    for (int y = 0; y < btn->height; y++) {
        int fb_x = btn->x;
        int fb_y = btn->y + y;
        
        if (fb_x >= 0 && fb_x < SCREEN_WIDTH && fb_y >= 0 && fb_y < SCREEN_HEIGHT) {
            framebuffer[fb_y * fb_stride + fb_x] = border_color;
        }
    }
    
    // 右边框
    for (int y = 0; y < btn->height; y++) {
        int fb_x = btn->x + btn->width - 1;
        int fb_y = btn->y + y;
        
        if (fb_x >= 0 && fb_x < SCREEN_WIDTH && fb_y >= 0 && fb_y < SCREEN_HEIGHT) {
            framebuffer[fb_y * fb_stride + fb_x] = border_color;
        }
    }
    
    // 如果有文本，绘制文本（简化版，实际应用中可能需要更复杂的字体渲染）
    if (btn->text) {
        // 这里只是简单示例，实际应用中应该使用字体库
        int text_x = btn->x + (btn->width - strlen(btn->text) * 8) / 2;
        int text_y = btn->y + (btn->height - 16) / 2;
        
        // 简化的文本绘制，实际应用中应该使用更复杂的实现
        for (int i = 0; i < strlen(btn->text); i++) {
            // 这里只是绘制一个矩形代表字符
            for (int y = 0; y < 16; y++) {
                for (int x = 0; x < 8; x++) {
                    int fb_x = text_x + i * 8 + x;
                    int fb_y = text_y + y;
                    
                    if (fb_x >= 0 && fb_x < SCREEN_WIDTH && fb_y >= 0 && fb_y < SCREEN_HEIGHT) {
                        framebuffer[fb_y * fb_stride + fb_x] = btn->text_color;
                    }
                }
            }
        }
    }
}

void display_update(void) {
    // 在某些系统上可能需要刷新帧缓冲
    // 这里简化处理，假设写入帧缓冲后自动显示
}
