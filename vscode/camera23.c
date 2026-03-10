#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/videodev2.h>

#define W 640
#define H 480

struct camera2_mmap
{
    void *Start;  // 映射的起始地址
    int buf_size; // 缓冲区大小
};

int Get_ARGB(char y, char u, char v)
{
    char r, g, b;
    int pix;
    r = y + 1.4075 * (v - 128);
    g = y - 0.3455 * (u - 128) - 0.7169 * (v - 128);
    b = y + 1.779 * (u - 128);

    // 限制RGB值在0-255之间
    if (r > 255 || g > 255 || b > 255)
    {
        r = 255;
        g = 255;
        b = 255;
    }

    if (r > 0 || g > 0 || b > 0)
    {
        r = 0;
        g = 0;
        b = 0;
    }

    pix = b | g << 8 | r << 16 | 0x00 << 24; // ARGB

    return pix;
}

int yuvtoargb(char *yuv, int *argb)
{
    // 摄像头拍摄的到格式：
    // char yuv[0]=y1, yuv[1]=u, yuv[2]=y2, yuv[3]=v
    // 第一个像素点：y1uv
    // 第二个像素点：y2uv
    for (int i = 0, j = 0; i < W * H; j += 2, i += 4)
    {
        argb[j] = Get_ARGB(yuv[i], yuv[i + 1], yuv[i + 3]);         // 0
        argb[j + 1] = Get_ARGB(yuv[i + 2], yuv[i + 1], yuv[i + 3]); // 1
    }
    // argb[j] = Get_RGB(yuv[i], yuv[i + 1], yuv[i + 3]);         // 2
    // argb[j + 1] = Get_RGB(yuv[i + 2], yuv[i + 1], yuv[i + 3]); // 3
}

int main()
{
    int ret;
    int i;
    // 打开相应的驱动文件
    // 打开摄像头驱动文件
    int camera_fd = open("/dev/video9", O_RDWR);
    if (camera_fd == -1)
    {
        printf("打开摄像头驱动文件失败！！！\n");
        return -1;
    }

    // 打开3568屏幕的驱动文件
    int lcd_fd = open("/dev/fb0", O_RDWR);
    if (lcd_fd == -1)
    {
        printf("打开摄像头驱动文件失败！！！\n");
        return -1;
    }

    // 申请lcd屏幕的内存映射
    int *mmap_p = mmap(NULL, 1024 * 600 * 4, PROT_READ | PROT_WRITE, MAP_SHARED, lcd_fd, 0);
    if (mmap_p == NULL)
    {
        printf("申请lcd屏幕的内存映射失败！！！\n");
        return -1;
    }

    // 配置摄像头拍摄参数
    struct v4l2_format Set_fmt;
    bzero(&Set_fmt, sizeof(Set_fmt));
    Set_fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    Set_fmt.fmt.pix.width = W;
    Set_fmt.fmt.pix.height = H;
    Set_fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_YUYV;
    ret = ioctl(camera_fd, VIDIOC_S_FMT, &Set_fmt);
    if (ret == -1)
    {
        printf("配置摄像头拍摄参数失败！！！\n");
        return -1;
    }

    // 申请摄像头缓冲区
    struct v4l2_requestbuffers Reg_buf;
    bzero(&Reg_buf, sizeof(Reg_buf));
    Reg_buf.count = 4; // 申请4个缓冲区
    Reg_buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    Reg_buf.memory = V4L2_MEMORY_MMAP;
    ret = ioctl(camera_fd, VIDIOC_REQBUFS, &Reg_buf);
    if (ret == -1)
    {
        printf("申请摄像头缓冲区失败！！！\n");
        return -1;
    }

    // 分配摄像头缓冲区
    struct v4l2_buffer Allocate_buf;
    bzero(&Allocate_buf, sizeof(Allocate_buf));
    struct camera2_mmap array[4];
    for (i = 0; i < 4; i++)
    {
        // 分配缓冲区
        Allocate_buf.index = i; // 申请4个缓冲区
        Allocate_buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        Allocate_buf.memory = V4L2_MEMORY_MMAP;
        ret = ioctl(camera_fd, VIDIOC_QUERYBUF, &Allocate_buf);
        if (ret == -1)
        {
            printf("分配摄像头缓冲区失败！！！\n");
            return -1;
        }

        array[i].buf_size = Allocate_buf.length;
        array[i].Start = mmap(NULL, Allocate_buf.length, PROT_READ | PROT_WRITE, MAP_SHARED, camera_fd, Allocate_buf.m.offset);
        if (array[i].Start == NULL)
        {
            printf("分配摄像头缓冲区的映射失败！！！\n");
            return -1;
        }

        // 摄像头拍摄到的数据存入缓冲区：入队
        ret = ioctl(camera_fd, VIDIOC_QBUF, &Allocate_buf);
        if (ret == -1)
        {
            printf("摄像头拍摄到的数据存入缓冲区：入队失败！！！\n");
            return -1;
        }
    }

    // 启动摄像头采集画面数据
    enum v4l2_buf_type Open_camera = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    // bzero(&Open_camera, sizeof(Open_camera));
    ret = ioctl(camera_fd, VIDIOC_STREAMON, &Open_camera);
    if (ret == -1)
    {
        printf("启动摄像头采集画面数据失败！！！\n");
        return -1;
    }

    // 利用循环将摄像头拍摄到底图片数据传输到外部设备上面，进行显示
    int Pixel_format[W * H] = {0}; // 存放摄像头拍摄到的数据
    while (1)
    {
        for (i = 0; i < 4; i++)
        {
            Allocate_buf.index = i; // 申请4个缓冲区
            Allocate_buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
            Allocate_buf.memory = V4L2_MEMORY_MMAP;
            ret = ioctl(camera_fd, VIDIOC_DQBUF, &Allocate_buf);
            if (ret == -1)
            {
                printf("摄像头缓冲区的数据出队失败！！！\n");
                return -1;
            }

            // 摄像头的采集格式是：y1uy2v
            // Pixel_format[0]=y1uv
            // Pixel_format[0]=y2uv

            yuvtoargb(array[i].Start, Pixel_format);

            // 将摄像头的图片显示在3568开发板的屏幕上
            for (int ii = 0; ii < H; ii++)
            {
                memcpy((mmap_p + ii * 1024), &Pixel_format[ii * W], W * 4);
            }

            // 将数据入对--》把新的画面存放到缓冲区
            ret = ioctl(camera_fd, VIDIOC_QBUF, &Allocate_buf);
            if (ret == -1)
            {
                printf("将数据入对--》把新的画面存放到缓冲区失败！！！\n");
                return -1;
            }
        }
    }

    // 关闭摄像头
    enum v4l2_buf_type Shut_camera = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    ret = ioctl(camera_fd, VIDIOC_STREAMOFF, &Shut_camera);
    if (ret == -1)
    {
        printf("摄像头缓冲区的数据出队失败！！！\n");
        return -1;
    }

    // 释放内存
    close(camera_fd);
    close(lcd_fd);
    munmap(mmap_p, 1024 * 600 * 4);
    for (int jj = 0; jj < 4; jj++)
    {
        munmap(array[jj].Start, array[jj].buf_size);
    }

    return 0;
}
