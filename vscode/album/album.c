#include "album.h"

int album_init(Album *album, NetworkClient *network) {
    if (!album || !network) {
        log_print(LOG_ERROR, "Invalid album parameters");
        return ERROR_INVALID_PARAM;
    }
    
    memset(album, 0, sizeof(Album));
    album->network = network;
    album->state = ALBUM_IDLE;
    
    log_print(LOG_INFO, "Album initialized");
    return SUCCESS;
}

int album_load_list(Album *album) {
    if (!album || !album->network) {
        log_print(LOG_ERROR, "Album not initialized");
        return ERROR_INVALID_PARAM;
    }
    
    if (album->network->connected != 1) {
        log_print(LOG_ERROR, "Not connected to server");
        return ERROR_NETWORK;
    }
    
    album->state = ALBUM_LOADING;
    
    // 请求相册列表
    int ret = network_request_album(album->network);
    if (ret != SUCCESS) {
        log_print(LOG_ERROR, "Failed to request album list");
        album->state = ALBUM_ERROR;
        return ret;
    }
    
    // 等待相册列表响应
    int timeout = 0;
    while (timeout < 100) { // 等待10秒
        if (network_get_album(album->network, &album->album_list, &album->album_count) == SUCCESS) {
            album->state = ALBUM_LOADED;
            album->current_index = 0;
            log_print(LOG_INFO, "Album list loaded with %d items", album->album_count);
            return SUCCESS;
        }
        
        usleep(100000); // 100ms
        timeout++;
    }
    
    log_print(LOG_ERROR, "Timeout waiting for album list");
    album->state = ALBUM_ERROR;
    return ERROR;
}

int album_get_list(Album *album, AlbumItem **album_list, int *album_count) {
    if (!album || !album_list || !album_count) {
        log_print(LOG_ERROR, "Invalid parameters");
        return ERROR_INVALID_PARAM;
    }
    
    if (album->state != ALBUM_LOADED) {
        log_print(LOG_ERROR, "Album list not loaded");
        return ERROR;
    }
    
    *album_list = album->album_list;
    *album_count = album->album_count;
    
    return SUCCESS;
}

int album_load_image(Album *album, int index) {
    if (!album || album->state != ALBUM_LOADED) {
        log_print(LOG_ERROR, "Album not initialized or list not loaded");
        return ERROR_INVALID_PARAM;
    }
    
    if (index < 0 || index >= album->album_count) {
        log_print(LOG_ERROR, "Invalid album index: %d", index);
        return ERROR_INVALID_PARAM;
    }
    
    // 释放当前图片
    if (album->current_image) {
        safe_free((void **)&album->current_image);
        album->current_image_size = 0;
    }
    
    // 请求图片
    int ret = network_request_image(album->network, album->album_list[index].filename);
    if (ret != SUCCESS) {
        log_print(LOG_ERROR, "Failed to request image: %s", album->album_list[index].filename);
        return ret;
    }
    
    // 等待图片响应
    int timeout = 0;
    while (timeout < 100) { // 等待10秒
        unsigned char *image_data = NULL;
        int image_size = 0;
        char image_name[256];
        
        if (network_get_image(album->network, &image_data, &image_size, image_name) == SUCCESS) {
            album->current_image = image_data;
            album->current_image_size = image_size;
            album->current_index = index;
            
            log_print(LOG_INFO, "Loaded image: %s, size %d bytes", image_name, image_size);
            return SUCCESS;
        }
        
        usleep(100000); // 100ms
        timeout++;
    }
    
    log_print(LOG_ERROR, "Timeout waiting for image: %s", album->album_list[index].filename);
    return ERROR;
}

int album_prev_image(Album *album) {
    if (!album || album->state != ALBUM_LOADED) {
        log_print(LOG_ERROR, "Album not initialized or list not loaded");
        return ERROR_INVALID_PARAM;
    }
    
    if (album->album_count == 0) {
        log_print(LOG_ERROR, "Album is empty");
        return ERROR;
    }
    
    int prev_index = (album->current_index - 1 + album->album_count) % album->album_count;
    return album_load_image(album, prev_index);
}

int album_next_image(Album *album) {
    if (!album || album->state != ALBUM_LOADED) {
        log_print(LOG_ERROR, "Album not initialized or list not loaded");
        return ERROR_INVALID_PARAM;
    }
    
    if (album->album_count == 0) {
        log_print(LOG_ERROR, "Album is empty");
        return ERROR;
    }
    
    int next_index = (album->current_index + 1) % album->album_count;
    return album_load_image(album, next_index);
}

int album_get_current_image(Album *album, unsigned char **image_data, int *image_size, char *filename) {
    if (!album || !image_data || !image_size || !filename) {
        log_print(LOG_ERROR, "Invalid parameters");
        return ERROR_INVALID_PARAM;
    }
    
    if (album->state != ALBUM_LOADED || !album->current_image) {
        log_print(LOG_ERROR, "No image loaded");
        return ERROR;
    }
    
    *image_data = album->current_image;
    *image_size = album->current_image_size;
    
    if (album->current_index >= 0 && album->current_index < album->album_count) {
        strncpy(filename, album->album_list[album->current_index].filename, 256);
    } else {
        filename[0] = '\0';
    }
    
    return SUCCESS;
}

void album_cleanup(Album *album) {
    if (!album) {
        return;
    }
    
    // 释放相册列表
    if (album->album_list) {
        safe_free((void **)&album->album_list);
        album->album_count = 0;
    }
    
    // 释放当前图片
    if (album->current_image) {
        safe_free((void **)&album->current_image);
        album->current_image_size = 0;
    }
    
    log_print(LOG_INFO, "Album cleaned up");
}
