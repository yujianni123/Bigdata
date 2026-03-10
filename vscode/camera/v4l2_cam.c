#include "camera.h"
#include <sys/ioctl.h>
#include <linux/videodev2.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/mman.h>

static void *capture_thread(void *arg);

int camera_init(CameraDevice *cam, const char *device, int width, int height, int format) {
    if (!cam || !device) {
        log_print(LOG_ERROR, "Invalid camera device or parameters");
        return ERROR_INVALID_PARAM;
    }
    
    memset(cam, 0, sizeof(CameraDevice));
    
    // 打开相机设备
    cam->fd = open(device, O_RDWR);
    if (cam->fd == -1) {
        log_print(LOG_ERROR, "Failed to open camera device %s: %s", device, strerror(errno));
        return ERROR_DEVICE_NOT_FOUND;
    }
    
    cam->device = strdup(device);
    cam->width = width;
    cam->height = height;
    cam->format = format;
    cam->state = CAMERA_IDLE;
    
    // 设置相机格式
    struct v4l2_format fmt = {0};
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = width;
    fmt.fmt.pix.height = height;
    fmt.fmt.pix.pixelformat = format;
    fmt.fmt.pix.field = V4L2_FIELD_ANY;
    
    if (ioctl(cam->fd, VIDIOC_S_FMT, &fmt) == -1) {
        log_print(LOG_ERROR, "Failed to set camera format: %s", strerror(errno));
        camera_cleanup(cam);
        return ERROR_IO;
    }
    
    // 检查是否支持请求的格式
    if (fmt.fmt.pix.width != width || fmt.fmt.pix.height != height) {
        log_print(LOG_WARNING, "Camera format adjusted: %dx%d vs requested %dx%d",
                 fmt.fmt.pix.width, fmt.fmt.pix.height, width, height);
        cam->width = fmt.fmt.pix.width;
        cam->height = fmt.fmt.pix.height;
    }
    
    if (fmt.fmt.pix.pixelformat != format) {
        log_print(LOG_WARNING, "Camera pixel format adjusted: 0x%04X vs requested 0x%04X",
                 fmt.fmt.pix.pixelformat, format);
        cam->format = fmt.fmt.pix.pixelformat;
    }
    
    // 请求缓冲区
    struct v4l2_requestbuffers req = {0};
    req.count = 4; // 请求4个缓冲区
    req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    req.memory = V4L2_MEMORY_MMAP;
    
    if (ioctl(cam->fd, VIDIOC_REQBUFS, &req) == -1) {
        log_print(LOG_ERROR, "Failed to request camera buffers: %s", strerror(errno));
        camera_cleanup(cam);
        return ERROR_IO;
    }
    
    cam->buffer_count = req.count;
    cam->buffers = (struct v4l2_buffer *)safe_malloc(sizeof(struct v4l2_buffer) * cam->buffer_count);
    cam->buffer_data = (unsigned char **)safe_malloc(sizeof(unsigned char *) * cam->buffer_count);
    
    // 映射缓冲区
    for (int i = 0; i < cam->buffer_count; i++) {
        struct v4l2_buffer buf = {0};
        buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP;
        buf.index = i;
        
        if (ioctl(cam->fd, VIDIOC_QUERYBUF, &buf) == -1) {
            log_print(LOG_ERROR, "Failed to query buffer %d: %s", i, strerror(errno));
            camera_cleanup(cam);
            return ERROR_IO;
        }
        
        cam->buffers[i] = buf;
        cam->buffer_data[i] = (unsigned char *)mmap(NULL, buf.length, PROT_READ | PROT_WRITE, MAP_SHARED, cam->fd, buf.m.offset);
        
        if (cam->buffer_data[i] == MAP_FAILED) {
            log_print(LOG_ERROR, "Failed to map buffer %d: %s", i, strerror(errno));
            camera_cleanup(cam);
            return ERROR_IO;
        }
    }
    
    // 初始化互斥锁
    pthread_mutex_init(&cam->mutex, NULL);
    
    log_print(LOG_INFO, "Camera initialized: %s, %dx%d, format 0x%04X",
             device, cam->width, cam->height, cam->format);
    
    return SUCCESS;
}

int camera_start(CameraDevice *cam) {
    if (!cam || cam->state != CAMERA_IDLE) {
        log_print(LOG_ERROR, "Camera not initialized or already running");
        return ERROR_INVALID_PARAM;
    }
    
    // 将缓冲区加入队列
    for (int i = 0; i < cam->buffer_count; i++) {
        struct v4l2_buffer buf = {0};
        buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP;
        buf.index = i;
        
        if (ioctl(cam->fd, VIDIOC_QBUF, &buf) == -1) {
            log_print(LOG_ERROR, "Failed to queue buffer %d: %s", i, strerror(errno));
            return ERROR_IO;
        }
    }
    
    // 开始视频流
    enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(cam->fd, VIDIOC_STREAMON, &type) == -1) {
        log_print(LOG_ERROR, "Failed to start camera stream: %s", strerror(errno));
        return ERROR_IO;
    }
    
    // 创建捕获线程
    cam->exit_flag = 0;
    if (pthread_create(&cam->capture_thread, NULL, capture_thread, cam) != 0) {
        log_print(LOG_ERROR, "Failed to create capture thread: %s", strerror(errno));
        ioctl(cam->fd, VIDIOC_STREAMOFF, &type);
        return ERROR;
    }
    
    cam->state = CAMERA_RUNNING;
    log_print(LOG_INFO, "Camera started");
    
    return SUCCESS;
}

void camera_stop(CameraDevice *cam) {
    if (!cam || cam->state != CAMERA_RUNNING) {
        return;
    }
    
    // 设置退出标志
    cam->exit_flag = 1;
    
    // 等待线程退出
    pthread_join(cam->capture_thread, NULL);
    
    // 停止视频流
    enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    ioctl(cam->fd, VIDIOC_STREAMOFF, &type);
    
    cam->state = CAMERA_IDLE;
    log_print(LOG_INFO, "Camera stopped");
}

void camera_cleanup(CameraDevice *cam) {
    if (!cam) {
        return;
    }
    
    camera_stop(cam);
    
    // 释放缓冲区
    if (cam->buffer_data) {
        for (int i = 0; i < cam->buffer_count; i++) {
            if (cam->buffer_data[i]) {
                munmap(cam->buffer_data[i], cam->buffers[i].length);
            }
        }
        safe_free((void **)&cam->buffer_data);
    }
    
    safe_free((void **)&cam->buffers);
    
    // 关闭相机设备
    if (cam->fd != -1) {
        close(cam->fd);
        cam->fd = -1;
    }
    
    safe_free((void **)&cam->device);
    
    // 销毁互斥锁
    pthread_mutex_destroy(&cam->mutex);
    
    // 释放当前帧
    if (cam->current_frame) {
        safe_free((void **)&cam->current_frame->data);
        safe_free((void **)&cam->current_frame);
    }
    
    log_print(LOG_INFO, "Camera cleaned up");
}

ImageFrame *camera_get_frame(CameraDevice *cam) {
    if (!cam || cam->state != CAMERA_RUNNING) {
        return NULL;
    }
    
    pthread_mutex_lock(&cam->mutex);
    ImageFrame *frame = cam->current_frame;
    pthread_mutex_unlock(&cam->mutex);
    
    return frame;
}

int camera_capture(CameraDevice *cam, ImageFrame **frame) {
    if (!cam || !frame || cam->state != CAMERA_RUNNING) {
        log_print(LOG_ERROR, "Invalid parameters or camera not running");
        return ERROR_INVALID_PARAM;
    }
    
    // 获取当前帧
    pthread_mutex_lock(&cam->mutex);
    
    if (!cam->current_frame) {
        pthread_mutex_unlock(&cam->mutex);
        log_print(LOG_ERROR, "No frame available");
        return ERROR;
    }
    
    // 创建新的图像帧
    ImageFrame *captured_frame = (ImageFrame *)safe_malloc(sizeof(ImageFrame));
    memcpy(captured_frame, cam->current_frame, sizeof(ImageFrame));
    
    // 复制图像数据
    captured_frame->data = (unsigned char *)safe_malloc(captured_frame->size);
    memcpy(captured_frame->data, cam->current_frame->data, captured_frame->size);
    
    // 获取时间戳
    get_timestamp(captured_frame->timestamp, sizeof(captured_frame->timestamp));
    
    pthread_mutex_unlock(&cam->mutex);
    
    *frame = captured_frame;
    return SUCCESS;
}

static void *capture_thread(void *arg) {
    CameraDevice *cam = (CameraDevice *)arg;
    struct v4l2_buffer buf = {0};
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;
    
    while (!cam->exit_flag) {
        // 等待帧数据
        if (ioctl(cam->fd, VIDIOC_DQBUF, &buf) == -1) {
            if (errno == EINTR) {
                continue;
            }
            
            log_print(LOG_ERROR, "Failed to dequeue buffer: %s", strerror(errno));
            break;
        }
        
        // 处理帧数据
        pthread_mutex_lock(&cam->mutex);
        
        // 如果当前帧已存在，释放它
        if (cam->current_frame) {
            safe_free((void **)&cam->current_frame->data);
            safe_free((void **)&cam->current_frame);
        }
        
        // 创建新的图像帧
        cam->current_frame = (ImageFrame *)safe_malloc(sizeof(ImageFrame));
        cam->current_frame->width = cam->width;
        cam->current_frame->height = cam->height;
        cam->current_frame->format = cam->format;
        cam->current_frame->size = buf.bytesused;
        
        // 复制图像数据
        cam->current_frame->data = (unsigned char *)safe_malloc(buf.bytesused);
        memcpy(cam->current_frame->data, cam->buffer_data[buf.index], buf.bytesused);
        
        // 获取时间戳
        get_timestamp(cam->current_frame->timestamp, sizeof(cam->current_frame->timestamp));
        
        pthread_mutex_unlock(&cam->mutex);
        
        // 将缓冲区重新加入队列
        if (ioctl(cam->fd, VIDIOC_QBUF, &buf) == -1) {
            log_print(LOG_ERROR, "Failed to requeue buffer: %s", strerror(errno));
            break;
        }
    }
    
    return NULL;
}
