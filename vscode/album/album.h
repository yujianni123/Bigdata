#ifndef __ALBUM_H__
#define __ALBUM_H__

#include "../common/common.h"
#include "../network/network.h"

// 相册状态
typedef enum {
    ALBUM_IDLE,
    ALBUM_LOADING,
    ALBUM_LOADED,
    ALBUM_ERROR
} AlbumState;

// 相册结构体
typedef struct {
    NetworkClient *network;
    AlbumItem *album_list;
    int album_count;
    int current_index;
    AlbumState state;
    unsigned char *current_image;
    int current_image_size;
} Album;

// 初始化相册
int album_init(Album *album, NetworkClient *network);

// 加载相册列表
int album_load_list(Album *album);

// 获取相册列表
int album_get_list(Album *album, AlbumItem **album_list, int *album_count);

// 加载指定图片
int album_load_image(Album *album, int index);

// 加载上一张图片
int album_prev_image(Album *album);

// 加载下一张图片
int album_next_image(Album *album);

// 获取当前图片
int album_get_current_image(Album *album, unsigned char **image_data, int *image_size, char *filename);

// 释放相册资源
void album_cleanup(Album *album);

#endif // __ALBUM_H__
