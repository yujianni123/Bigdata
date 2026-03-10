#include <SDL2/SDL.h>
#include <stdio.h>

int main(int argc, char *argv[])
{
    // 初始化SDL
    if (SDL_Init(SDL_INIT_VIDEO) == -1)
    {
        SDL_Log("SDL_Init Error:%s\n", SDL_GetError());
        return -1;
    }

    // 创建窗口
    SDL_Window *My_window = SDL_CreateWindow("第一个窗口",
                                             100, 100,
                                             1024, 600,
                                             SDL_WINDOW_RESIZABLE | SDL_WINDOW_SHOWN);
    if (My_window == NULL)
    {
        SDL_Log("SDL_Init Error:%s\n", SDL_GetError());
        return -1;
    }

    // 停止时间显示窗口
    // SDL_Delay(3000);
    SDL_Event My_event;

    while (1)
    {
        if (SDL_PollEvent(&My_event))
        {
            if (My_event.type == SDL_QUIT)
            {
                break;
            }
        }
    }

    // 销毁窗口,释放资源
    SDL_DestroyWindow(My_window);

    // 退出SDL
    SDL_Quit();
    return 0;
}