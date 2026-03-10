#ifndef __CAMERA_H__
#define __CAMERA_H__

#include "../common/common.h"

// 相机参数
#define CAMERA_WIDTH  640
#define CAMERA_HEIGHT 480
#define CAMERA_FORMAT V4L2_PIX_FMT_YUYV

// 相机设备路径
#define CAMERA_DEVICE "/dev/video0"

// 相机状态
typedef enum {
    CAMERA_IDLE,
    CAMERA_RUNNING,
    CAMERA_CAPTURING
} CameraState;

// 相机设备结构体
typedef struct {
    int fd;
    char *device;
    int width;
    int height;
    int format;
    int buffer_count;
    struct v4l2_buffer *buffers;
    unsigned char **buffer_data;
    CameraState state;
    pthread_t capture_thread;
    pthread_mutex_t mutex;
    ImageFrame *current_frame;
    int exit_flag;
} CameraDevice;

// 初始化相机
int camera_init(CameraDevice *cam, const char *device, int width, int height, int format);

// 启动相机预览
int camera_start(CameraDevice *cam);

// 停止相机预览
void camera_stop(CameraDevice *cam);

// 释放相机资源
void camera_cleanup(CameraDevice *cam);

// 获取当前帧
ImageFrame *camera_get_frame(CameraDevice *cam);

// 抓拍照片
int camera_capture(CameraDevice *cam, ImageFrame **frame);

// YUV转RGB
int yuv420sp_to_rgb565(const unsigned char *yuv, unsigned short *rgb, int width, int height);

// 添加时间水印
int add_timestamp_watermark(unsigned short *rgb, int width, int height, const char *timestamp);

#endif // __CAMERA_H__
