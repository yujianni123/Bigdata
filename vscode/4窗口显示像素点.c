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

    // 绘制矩形
    // 1.获取窗口的Surface与 SDL_Window相关联
    SDL_Surface *surf = SDL_GetWindowSurface(My_window);
    if (surf == NULL)
    {
        SDL_Log("SDL_Init Error:%s\n", SDL_GetError());
        return -1;
    }

    // 显示像素点
    // 1.找SDL_Surface的像素格式
    Uint32 *My_pixel = (Uint32 *)surf->pixels;
    My_pixel[20000] = 0x000000ff;

    for (int i = 20000; i < 20500; i++)
    {
        My_pixel[i] = 0x0000ff00;
    }
    // 4.更新窗口显示
    SDL_UpdateWindowSurface(My_window);

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