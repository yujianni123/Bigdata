#include "common.h"
#include <stdarg.h>
#include <sys/stat.h>
#include <sys/types.h>

void log_print(LogLevel level, const char *format, ...) {
    va_list args;
    char timestamp[20];
    get_timestamp(timestamp, sizeof(timestamp));
    
    const char *level_str[] = {"DEBUG", "INFO", "WARNING", "ERROR"};
    
    fprintf(stderr, "[%s] [%s] ", timestamp, level_str[level]);
    va_start(args, format);
    vfprintf(stderr, format, args);
    va_end(args);
    fprintf(stderr, "\n");
}

void get_timestamp(char *timestamp, int len) {
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    strftime(timestamp, len, "%Y-%m-%d %H:%M:%S", t);
}

int create_directory(const char *path) {
    struct stat st = {0};
    
    if (stat(path, &st) == -1) {
        if (mkdir(path, 0755) == -1) {
            log_print(LOG_ERROR, "Failed to create directory %s: %s", path, strerror(errno));
            return ERROR;
        }
    }
    
    return SUCCESS;
}

void *safe_malloc(size_t size) {
    void *ptr = malloc(size);
    if (!ptr) {
        log_print(LOG_ERROR, "Memory allocation failed");
        exit(EXIT_FAILURE);
    }
    return ptr;
}

void safe_free(void **ptr) {
    if (*ptr) {
        free(*ptr);
        *ptr = NULL;
    }
}

int write_file(const char *filename, const unsigned char *data, int size) {
    int fd = open(filename, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd == -1) {
        log_print(LOG_ERROR, "Failed to open file %s: %s", filename, strerror(errno));
        return ERROR;
    }
    
    int ret = write(fd, data, size);
    if (ret != size) {
        log_print(LOG_ERROR, "Failed to write file %s: %s", filename, strerror(errno));
        close(fd);
        return ERROR;
    }
    
    close(fd);
    return SUCCESS;
}

unsigned char *read_file(const char *filename, int *size) {
    struct stat st;
    if (stat(filename, &st) == -1) {
        log_print(LOG_ERROR, "Failed to stat file %s: %s", filename, strerror(errno));
        return NULL;
    }
    
    *size = st.st_size;
    unsigned char *data = (unsigned char *)safe_malloc(*size);
    
    int fd = open(filename, O_RDONLY);
    if (fd == -1) {
        log_print(LOG_ERROR, "Failed to open file %s: %s", filename, strerror(errno));
        safe_free((void **)&data);
        return NULL;
    }
    
    int ret = read(fd, data, *size);
    if (ret != *size) {
        log_print(LOG_ERROR, "Failed to read file %s: %s", filename, strerror(errno));
        close(fd);
        safe_free((void **)&data);
        return NULL;
    }
    
    close(fd);
    return data;
}
