#ifndef __COMMON_H__
#define __COMMON_H__

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <pthread.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/videodev2.h>

// 错误码定义
#define SUCCESS 0
#define ERROR -1
#define ERROR_NOMEM -2
#define ERROR_IO -3
#define ERROR_NETWORK -4
#define ERROR_INVALID_PARAM -5
#define ERROR_FILE_NOT_FOUND -6
#define ERROR_DEVICE_NOT_FOUND -7

// 日志级别
typedef enum {
    LOG_DEBUG,
    LOG_INFO,
    LOG_WARNING,
    LOG_ERROR
} LogLevel;

// 图像数据结构
typedef struct {
    unsigned char *data;
    int width;
    int height;
    int format; // 0: YUV420SP, 1: RGB565, 2: BMP
    int size;
    char timestamp[20]; // 时间戳
} ImageFrame;

// 网络传输包结构
typedef struct {
    int type; // 0: 图像数据, 1: 相册请求, 2: 相册响应, 3: 图片下载请求, 4: 图片下载响应
    int length;
    char filename[256];
    char timestamp[20];
    unsigned char data[];
} NetworkPacket;

// 应用状态
typedef enum {
    MODE_MAIN,
    MODE_CAMERA,
    MODE_ALBUM
} AppMode;

// 相册图片信息
typedef struct {
    char filename[256];
    char timestamp[20];
    int size;
} AlbumItem;

// 公共函数声明
void log_print(LogLevel level, const char *format, ...);
void get_timestamp(char *timestamp, int len);
int create_directory(const char *path);
void *safe_malloc(size_t size);
void safe_free(void **ptr);
int write_file(const char *filename, const unsigned char *data, int size);
unsigned char *read_file(const char *filename, int *size);

#endif // __COMMON_H__
