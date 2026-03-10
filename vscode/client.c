#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <errno.h>
#include <signal.h>
#include <sys/time.h>
#include <netinet/tcp.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <linux/videodev2.h>
#include <SDL2/SDL.h>
#include <time.h>

// 服务器配置
#define SERVER_IP "47.109.36.246"
#define SERVER_PORT 8080

// 摄像头配置
#define CAMERA_WIDTH 640
#define CAMERA_HEIGHT 480
#define RGB_SIZE (CAMERA_WIDTH * CAMERA_HEIGHT * 3)

// 摄像头缓冲区结构
struct camerabuf {
    void *start;
    int size;
};

// 全局数据结构
typedef struct {
    int running;
    int capture_request;
    int save_local_request;
    pthread_mutex_t mutex;
    unsigned char *current_frame;
    int frame_ready;
    int camerafd;
    struct camerabuf array[4];
    int *argb_buffer;  // ARGB缓冲区
    int pixel_format;  // 像素格式
} camera_data_t;

camera_data_t cam_data;

// SDL相关变量
SDL_Window *window = NULL;
SDL_Renderer *renderer = NULL;
SDL_Texture *texture = NULL;

// ========== 函数声明 ==========
// 摄像头相关函数
int camera_init();
void camera_cleanup();
void yuyv_to_rgb(unsigned char *yuyv_data, unsigned char *rgb_data);
void nv12_to_rgb(unsigned char *nv12_data, unsigned char *rgb_data);
void nv21_to_rgb(unsigned char *nv21_data, unsigned char *rgb_data);

// 网络相关函数
int connect_to_server();
int send_image_data(int sock, unsigned char *rgb_data);

// SDL相关函数
int sdl_init();
void sdl_cleanup();
void display_with_sdl(unsigned char *rgb_data);

// 其他函数
void *camera_thread(void *arg);
void *sdl_event_thread(void *arg);
void signal_handler(int sig);
void save_image_to_file(unsigned char *rgb_data, const char *filename);
// =============================

// YUYV转RGB函数
void yuyv_to_rgb(unsigned char *yuyv_data, unsigned char *rgb_data) {
    int i, j;
    for (i = 0, j = 0; i < CAMERA_WIDTH * CAMERA_HEIGHT * 2; i += 4, j += 6) {
        int y1 = yuyv_data[i];
        int u  = yuyv_data[i + 1];
        int y2 = yuyv_data[i + 2];
        int v  = yuyv_data[i + 3];

        // 转换第一个像素
        int r1 = y1 + 1.4075 * (v - 128);
        int g1 = y1 - 0.3455 * (u - 128) - 0.7169 * (v - 128);
        int b1 = y1 + 1.779 * (u - 128);

        // 转换第二个像素
        int r2 = y2 + 1.4075 * (v - 128);
        int g2 = y2 - 0.3455 * (u - 128) - 0.7169 * (v - 128);
        int b2 = y2 + 1.779 * (u - 128);

        // 限制范围
        r1 = (r1 < 0) ? 0 : (r1 > 255) ? 255 : r1;
        g1 = (g1 < 0) ? 0 : (g1 > 255) ? 255 : g1;
        b1 = (b1 < 0) ? 0 : (b1 > 255) ? 255 : b1;
        
        r2 = (r2 < 0) ? 0 : (r2 > 255) ? 255 : r2;
        g2 = (g2 < 0) ? 0 : (g2 > 255) ? 255 : g2;
        b2 = (b2 < 0) ? 0 : (b2 > 255) ? 255 : b2;

        // 存储RGB数据
        rgb_data[j]     = r1;     // R
        rgb_data[j + 1] = g1;     // G
        rgb_data[j + 2] = b1;     // B
        rgb_data[j + 3] = r2;     // R
        rgb_data[j + 4] = g2;     // G
        rgb_data[j + 5] = b2;     // B
    }
}

// NV12转RGB函数
void nv12_to_rgb(unsigned char *nv12_data, unsigned char *rgb_data) {
    int y_size = CAMERA_WIDTH * CAMERA_HEIGHT;
    unsigned char *y_plane = nv12_data;
    unsigned char *uv_plane = nv12_data + y_size;
    
    for (int y = 0; y < CAMERA_HEIGHT; y++) {
        for (int x = 0; x < CAMERA_WIDTH; x++) {
            int y_index = y * CAMERA_WIDTH + x;
            int uv_index = (y / 2) * (CAMERA_WIDTH / 2) * 2 + (x / 2) * 2;
            
            int y_val = y_plane[y_index];
            int u_val = uv_plane[uv_index];
            int v_val = uv_plane[uv_index + 1];
            
            // YUV转RGB
            int r = y_val + 1.4075 * (v_val - 128);
            int g = y_val - 0.3455 * (u_val - 128) - 0.7169 * (v_val - 128);
            int b = y_val + 1.779 * (u_val - 128);
            
            // 限制范围
            r = (r < 0) ? 0 : (r > 255) ? 255 : r;
            g = (g < 0) ? 0 : (g > 255) ? 255 : g;
            b = (b < 0) ? 0 : (b > 255) ? 255 : b;
            
            int rgb_index = (y * CAMERA_WIDTH + x) * 3;
            rgb_data[rgb_index] = r;
            rgb_data[rgb_index + 1] = g;
            rgb_data[rgb_index + 2] = b;
        }
    }
}

// NV21转RGB函数
void nv21_to_rgb(unsigned char *nv21_data, unsigned char *rgb_data) {
    int y_size = CAMERA_WIDTH * CAMERA_HEIGHT;
    unsigned char *y_plane = nv21_data;
    unsigned char *uv_plane = nv21_data + y_size;
    
    for (int y = 0; y < CAMERA_HEIGHT; y++) {
        for (int x = 0; x < CAMERA_WIDTH; x++) {
            int y_index = y * CAMERA_WIDTH + x;
            int uv_index = (y / 2) * (CAMERA_WIDTH / 2) * 2 + (x / 2) * 2;
            
            int y_val = y_plane[y_index];
            int v_val = uv_plane[uv_index];      // NV21中V在前
            int u_val = uv_plane[uv_index + 1];  // NV21中U在后
            
            // YUV转RGB
            int r = y_val + 1.4075 * (v_val - 128);
            int g = y_val - 0.3455 * (u_val - 128) - 0.7169 * (v_val - 128);
            int b = y_val + 1.779 * (u_val - 128);
            
            // 限制范围
            r = (r < 0) ? 0 : (r > 255) ? 255 : r;
            g = (g < 0) ? 0 : (g > 255) ? 255 : g;
            b = (b < 0) ? 0 : (b > 255) ? 255 : b;
            
            int rgb_index = (y * CAMERA_WIDTH + x) * 3;
            rgb_data[rgb_index] = r;
            rgb_data[rgb_index + 1] = g;
            rgb_data[rgb_index + 2] = b;
        }
    }
}

// SDL初始化函数
int sdl_init() {
    // 初始化SDL
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL初始化失败: %s\n", SDL_GetError());
        return -1;
    }
    
    // 创建窗口
    window = SDL_CreateWindow("Camera Viewer - Press SPACE to capture, S to save locally, Q to quit",
                             SDL_WINDOWPOS_CENTERED,
                             SDL_WINDOWPOS_CENTERED,
                             CAMERA_WIDTH, CAMERA_HEIGHT,
                             SDL_WINDOW_SHOWN);
    if (!window) {
        printf("创建SDL窗口失败: %s\n", SDL_GetError());
        SDL_Quit();
        return -1;
    }
    
    // 创建渲染器
    renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    if (!renderer) {
        printf("创建SDL渲染器失败: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return -1;
    }
    
    // 创建纹理
    texture = SDL_CreateTexture(renderer,
                               SDL_PIXELFORMAT_RGB24,
                               SDL_TEXTUREACCESS_STREAMING,
                               CAMERA_WIDTH, CAMERA_HEIGHT);
    if (!texture) {
        printf("创建SDL纹理失败: %s\n", SDL_GetError());
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return -1;
    }
    
    printf("SDL初始化成功\n");
    return 0;
}

// SDL清理函数
void sdl_cleanup() {
    if (texture) {
        SDL_DestroyTexture(texture);
    }
    if (renderer) {
        SDL_DestroyRenderer(renderer);
    }
    if (window) {
        SDL_DestroyWindow(window);
    }
    SDL_Quit();
}

// 使用SDL显示函数
void display_with_sdl(unsigned char *rgb_data) {
    if (!renderer || !texture || !rgb_data) return;
    
    // 更新纹理
    SDL_UpdateTexture(texture, NULL, rgb_data, CAMERA_WIDTH * 3);
    
    // 清除渲染器
    SDL_RenderClear(renderer);
    
    // 复制纹理到渲染器
    SDL_RenderCopy(renderer, texture, NULL, NULL);
    
    // 显示渲染内容
    SDL_RenderPresent(renderer);
}

// 保存图像到文件
void save_image_to_file(unsigned char *rgb_data, const char *filename) {
    FILE *file = fopen(filename, "wb");
    if (!file) {
        printf("无法创建文件: %s\n", filename);
        return;
    }
    
    // 写入PPM文件头
    fprintf(file, "P6\n%d %d\n255\n", CAMERA_WIDTH, CAMERA_HEIGHT);
    
    // 写入RGB数据
    fwrite(rgb_data, 1, RGB_SIZE, file);
    
    fclose(file);
    printf("图像已保存到: %s\n", filename);
}

// 初始化摄像头
int camera_init() {
    int ret;
    
    // 使用USB摄像头设备 - 在Ubuntu中通常是 /dev/video10
    cam_data.camerafd = open("/dev/video10", O_RDWR);
    if (cam_data.camerafd == -1) {
        printf("打开摄像头设备 /dev/video10 失败: %s\n", strerror(errno));
        // 尝试备用设备
        cam_data.camerafd = open("/dev/video9", O_RDWR);
        if (cam_data.camerafd == -1) {
            printf("打开摄像头设备 /dev/video9 失败: %s\n", strerror(errno));
            return -1;
        } else {
            printf("成功打开备用摄像头设备: /dev/video9\n");
        }
    } else {
        printf("成功打开摄像头设备: /dev/video10\n");
    }

    // 设置摄像头格式 - 优先使用YUYV格式
    struct v4l2_format myfmt;
    bzero(&myfmt, sizeof(myfmt));
    myfmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    myfmt.fmt.pix.width = CAMERA_WIDTH;
    myfmt.fmt.pix.height = CAMERA_HEIGHT;
    
    // 尝试YUYV格式
    myfmt.fmt.pix.pixelformat = V4L2_PIX_FMT_YUYV;
    ret = ioctl(cam_data.camerafd, VIDIOC_S_FMT, &myfmt);
    
    if (ret == -1) {
        printf("YUYV格式设置失败，尝试NV12格式: %s\n", strerror(errno));
        myfmt.fmt.pix.pixelformat = V4L2_PIX_FMT_NV12;
        ret = ioctl(cam_data.camerafd, VIDIOC_S_FMT, &myfmt);
    }
    
    if (ret == -1) {
        printf("NV12格式设置失败，尝试NV21格式: %s\n", strerror(errno));
        myfmt.fmt.pix.pixelformat = V4L2_PIX_FMT_NV21;
        ret = ioctl(cam_data.camerafd, VIDIOC_S_FMT, &myfmt);
    }
    
    if (ret == -1) {
        printf("所有格式设置失败: %s\n", strerror(errno));
        close(cam_data.camerafd);
        return -1;
    }
    
    cam_data.pixel_format = myfmt.fmt.pix.pixelformat;
    
    printf("摄像头格式设置成功: ");
    switch (cam_data.pixel_format) {
        case V4L2_PIX_FMT_YUYV:
            printf("YUYV\n");
            break;
        case V4L2_PIX_FMT_NV12:
            printf("NV12\n");
            break;
        case V4L2_PIX_FMT_NV21:
            printf("NV21\n");
            break;
        default:
            printf("Unknown format: 0x%08X\n", cam_data.pixel_format);
    }

    // 申请缓冲区
    struct v4l2_requestbuffers reqbuf;
    bzero(&reqbuf, sizeof(reqbuf));
    reqbuf.count = 4;
    reqbuf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    reqbuf.memory = V4L2_MEMORY_MMAP;
    
    ret = ioctl(cam_data.camerafd, VIDIOC_REQBUFS, &reqbuf);
    if (ret == -1) {
        printf("申请缓冲区失败: %s\n", strerror(errno));
        close(cam_data.camerafd);
        return -1;
    }

    // 映射缓冲区
    struct v4l2_buffer otherbuf;
    for (int i = 0; i < 4; i++) {
        bzero(&otherbuf, sizeof(otherbuf));
        otherbuf.index = i;
        otherbuf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        otherbuf.memory = V4L2_MEMORY_MMAP;
        
        ret = ioctl(cam_data.camerafd, VIDIOC_QUERYBUF, &otherbuf);
        if (ret == -1) {
            printf("查询缓冲区失败: %s\n", strerror(errno));
            return -1;
        }
        
        cam_data.array[i].size = otherbuf.length;
        cam_data.array[i].start = mmap(NULL, otherbuf.length, 
                                     PROT_READ | PROT_WRITE, MAP_SHARED, 
                                     cam_data.camerafd, otherbuf.m.offset);
        if (cam_data.array[i].start == MAP_FAILED) {
            printf("映射缓冲区失败: %s\n", strerror(errno));
            return -1;
        }
        
        // 入队缓冲区
        ret = ioctl(cam_data.camerafd, VIDIOC_QBUF, &otherbuf);
        if (ret == -1) {
            printf("缓冲区入队失败: %s\n", strerror(errno));
            return -1;
        }
    }

    // 启动摄像头
    enum v4l2_buf_type mytype = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    ret = ioctl(cam_data.camerafd, VIDIOC_STREAMON, &mytype);
    if (ret == -1) {
        printf("启动摄像头失败: %s\n", strerror(errno));
        return -1;
    }

    printf("摄像头初始化成功\n");
    return 0;
}

// 清理摄像头资源
void camera_cleanup() {
    if (cam_data.camerafd >= 0) {
        enum v4l2_buf_type mytype = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        ioctl(cam_data.camerafd, VIDIOC_STREAMOFF, &mytype);
        
        for (int i = 0; i < 4; i++) {
            if (cam_data.array[i].start != MAP_FAILED) {
                munmap(cam_data.array[i].start, cam_data.array[i].size);
            }
        }
        close(cam_data.camerafd);
    }
}

// 网络连接函数
int connect_to_server() {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        printf("Socket creation failed: %s\n", strerror(errno));
        return -1;
    }
    
    struct sockaddr_in serv_addr;
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(SERVER_PORT);
    
    if (inet_pton(AF_INET, SERVER_IP, &serv_addr.sin_addr) <= 0) {
        printf("Invalid address: %s\n", SERVER_IP);
        close(sock);
        return -1;
    }
    
    // 设置超时
    struct timeval timeout;
    timeout.tv_sec = 10;
    timeout.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    
    printf("Connecting to server %s:%d...\n", SERVER_IP, SERVER_PORT);
    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        printf("Connection failed: %s\n", strerror(errno));
        close(sock);
        return -1;
    }
    
    printf("Connected to server successfully!\n");
    return sock;
}

// 发送图像数据到服务器
int send_image_data(int sock, unsigned char *rgb_data) {
    if (!rgb_data || sock < 0) {
        return -1;
    }
    
    // 准备图像头信息
    int header[3] = {CAMERA_WIDTH, CAMERA_HEIGHT, RGB_SIZE};
    int header_size = sizeof(header);
    int total_size = header_size + RGB_SIZE;
    
    // 分配发送缓冲区
    unsigned char *send_buffer = malloc(total_size);
    if (!send_buffer) {
        printf("Send buffer allocation failed\n");
        return -1;
    }
    
    // 拷贝头信息和图像数据
    memcpy(send_buffer, header, header_size);
    memcpy(send_buffer + header_size, rgb_data, RGB_SIZE);
    
    // 设置TCP无延迟
    int flag = 1;
    setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, (char *)&flag, sizeof(flag));
    
    // 发送数据
    int total_sent = 0;
    while (total_sent < total_size && cam_data.running) {
        int sent = send(sock, send_buffer + total_sent, total_size - total_sent, 0);
        if (sent <= 0) {
            printf("Send error: %s\n", strerror(errno));
            break;
        }
        total_sent += sent;
    }
    
    free(send_buffer);
    
    if (total_sent == total_size) {
        printf("Image sent successfully! %d bytes\n", total_sent);
        
        // 接收服务器响应
        char response[256] = {0};
        int response_len = recv(sock, response, sizeof(response) - 1, 0);
        if (response_len > 0) {
            printf("Server response: %s\n", response);
        }
        return 1;
    } else {
        printf("Image send incomplete: %d/%d bytes\n", total_sent, total_size);
        return 0;
    }
}

// 摄像头线程函数
void *camera_thread(void *arg) {
    printf("Camera thread started\n");
    
    // 初始化SDL显示
    if (sdl_init() != 0) {
        printf("SDL初始化失败，无法显示视频\n");
    }
    
    // 初始化摄像头
    if (camera_init() != 0) {
        printf("Camera initialization failed\n");
        sdl_cleanup();
        cam_data.running = 0;
        return NULL;
    }
    
    // 分配RGB缓冲区
    unsigned char *rgb_buffer = malloc(RGB_SIZE);
    if (!rgb_buffer) {
        printf("RGB buffer allocation failed\n");
        camera_cleanup();
        sdl_cleanup();
        cam_data.running = 0;
        return NULL;
    }
    
    struct v4l2_buffer otherbuf;
    int frame_count = 0;
    
    while (cam_data.running) {
        // 出队获取一帧画面
        bzero(&otherbuf, sizeof(otherbuf));
        otherbuf.index = frame_count % 4;
        otherbuf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        otherbuf.memory = V4L2_MEMORY_MMAP;
        
        if (ioctl(cam_data.camerafd, VIDIOC_DQBUF, &otherbuf) == -1) {
            printf("画面出队失败: %s\n", strerror(errno));
            continue;
        }
        
        pthread_mutex_lock(&cam_data.mutex);
        
        // 根据像素格式转换图像
        switch (cam_data.pixel_format) {
            case V4L2_PIX_FMT_YUYV:
                yuyv_to_rgb(cam_data.array[otherbuf.index].start, rgb_buffer);
                break;
            case V4L2_PIX_FMT_NV12:
                nv12_to_rgb(cam_data.array[otherbuf.index].start, rgb_buffer);
                break;
            case V4L2_PIX_FMT_NV21:
                nv21_to_rgb(cam_data.array[otherbuf.index].start, rgb_buffer);
                break;
            default:
                printf("不支持的像素格式: 0x%08X\n", cam_data.pixel_format);
                break;
        }
        
        // 在SDL上显示
        display_with_sdl(rgb_buffer);
        
        // 保存当前帧
        if (cam_data.current_frame) {
            memcpy(cam_data.current_frame, rgb_buffer, RGB_SIZE);
            cam_data.frame_ready = 1;
        }
        
        // 检查抓拍请求
        if (cam_data.capture_request) {
            printf("Capture request received, sending frame %d...\n", frame_count);
            
            int sock = connect_to_server();
            if (sock >= 0) {
                if (send_image_data(sock, rgb_buffer)) {
                    printf("Frame %d uploaded successfully\n", frame_count);
                } else {
                    printf("Frame %d upload failed\n", frame_count);
                }
                close(sock);
            }
            
            cam_data.capture_request = 0;
        }
        
        // 检查本地保存请求
        if (cam_data.save_local_request) {
            printf("Local save request received, saving frame %d...\n", frame_count);
            
            // 生成文件名
            time_t now = time(NULL);
            struct tm *t = localtime(&now);
            char filename[256];
            snprintf(filename, sizeof(filename), 
                    "capture_%04d%02d%02d_%02d%02d%02d.ppm",
                    t->tm_year + 1900, t->tm_mon + 1, t->tm_mday,
                    t->tm_hour, t->tm_min, t->tm_sec);
            
            save_image_to_file(rgb_buffer, filename);
            cam_data.save_local_request = 0;
        }
        
        pthread_mutex_unlock(&cam_data.mutex);
        
        // 重新入队缓冲区
        if (ioctl(cam_data.camerafd, VIDIOC_QBUF, &otherbuf) == -1) {
            printf("画面入队失败: %s\n", strerror(errno));
        }
        
        frame_count++;
        usleep(50000); // 控制帧率，20fps
    }
    
    // 清理资源
    free(rgb_buffer);
    camera_cleanup();
    sdl_cleanup();
    printf("Camera thread stopped\n");
    return NULL;
}

// SDL事件处理线程
void *sdl_event_thread(void *arg) {
    printf("SDL event thread started\n");
    printf("\n=== Camera Control System ===\n");
    printf("SPACE - Capture and upload image\n");
    printf("S - Save image locally\n");
    printf("Q - Quit program\n");
    printf("==============================\n");
    
    SDL_Event event;
    while (cam_data.running) {
        while (SDL_PollEvent(&event)) {
            switch (event.type) {
                case SDL_QUIT:
                    printf("SDL quit event received\n");
                    cam_data.running = 0;
                    break;
                    
                case SDL_KEYDOWN:
                    switch (event.key.keysym.sym) {
                        case SDLK_q:
                        case SDLK_ESCAPE:
                            printf("Quit key pressed\n");
                            cam_data.running = 0;
                            break;
                            
                        case SDLK_SPACE:
                            printf("Capture and upload requested\n");
                            pthread_mutex_lock(&cam_data.mutex);
                            cam_data.capture_request = 1;
                            pthread_mutex_unlock(&cam_data.mutex);
                            break;
                            
                        case SDLK_s:
                            printf("Local save requested\n");
                            pthread_mutex_lock(&cam_data.mutex);
                            cam_data.save_local_request = 1;
                            pthread_mutex_unlock(&cam_data.mutex);
                            break;
                            
                        default:
                            break;
                    }
                    break;
                    
                default:
                    break;
            }
        }
        usleep(10000); // 10ms
    }
    
    printf("SDL event thread stopped\n");
    return NULL;
}

// 信号处理函数
void signal_handler(int sig) {
    printf("\nReceived signal %d, shutting down...\n", sig);
    cam_data.running = 0;
}

int main() {
    pthread_t camera_tid, event_tid;
    
    // 初始化全局数据
    memset(&cam_data, 0, sizeof(camera_data_t));
    cam_data.running = 1;
    cam_data.capture_request = 0;
    cam_data.save_local_request = 0;
    cam_data.frame_ready = 0;
    cam_data.camerafd = -1;
    cam_data.pixel_format = 0;
    pthread_mutex_init(&cam_data.mutex, NULL);
    
    // 分配当前帧缓冲区
    cam_data.current_frame = malloc(RGB_SIZE);
    if (!cam_data.current_frame) {
        printf("Failed to allocate frame buffer\n");
        return -1;
    }
    
    // 分配ARGB缓冲区
    cam_data.argb_buffer = malloc(CAMERA_WIDTH * CAMERA_HEIGHT * sizeof(int));
    if (!cam_data.argb_buffer) {
        printf("Failed to allocate ARGB buffer\n");
        free(cam_data.current_frame);
        return -1;
    }
    
    // 设置信号处理
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    printf("=== Ubuntu Camera Client with SDL ===\n");
    printf("Server: %s:%d\n", SERVER_IP, SERVER_PORT);
    printf("Camera: %dx%d RGB\n", CAMERA_WIDTH, CAMERA_HEIGHT);
    printf("Using USB Camera: /dev/video0\n");
    
    // 创建摄像头线程
    if (pthread_create(&camera_tid, NULL, camera_thread, NULL) != 0) {
        printf("Failed to create camera thread\n");
        free(cam_data.current_frame);
        free(cam_data.argb_buffer);
        return -1;
    }
    
    // 创建SDL事件处理线程
    if (pthread_create(&event_tid, NULL, sdl_event_thread, NULL) != 0) {
        printf("Failed to create SDL event thread\n");
        cam_data.running = 0;
        pthread_join(camera_tid, NULL);
        free(cam_data.current_frame);
        free(cam_data.argb_buffer);
        return -1;
    }
    
    // 等待线程结束
    pthread_join(event_tid, NULL);
    pthread_join(camera_tid, NULL);
    
    // 清理资源
    pthread_mutex_destroy(&cam_data.mutex);
    free(cam_data.current_frame);
    free(cam_data.argb_buffer);
    
    printf("Camera client exited normally\n");
    return 0;
}