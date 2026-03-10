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
    // // 1.获取窗口的Surface与 SDL_Window相关联
    // SDL_Surface *surf = SDL_GetWindowSurface(My_window);
    // if (surf == NULL)
    // {
    //     SDL_Log("SDL_Init Error:%s\n", SDL_GetError());
    //     return -1;
    // }

    // 创建和使用渲染器
    // 1.创建渲染器
    SDL_Renderer *My_render = SDL_CreateRenderer(My_window, -1, 0);
    if (My_render == NULL)
    {
        SDL_Log("SDL_Init Error:%s\n", SDL_GetError());
        return -1;
    }

    // 2. 设置渲染器绘画颜色
    SDL_SetRenderDrawColor(My_render, 255, 0, 0, 255);

    // 3. 渲染器清空
    SDL_RenderClear(My_render);

    // 渲染器绘制矩形
    // 设置渲染器绘画颜色
    SDL_SetRenderDrawColor(My_render, 155, 156, 222, 255);

    // 绘制矩形形状
    SDL_Rect My_rect = {100, 100, 200, 200};

    // 渲染器绘制矩形
    SDL_RenderDrawRect(My_render, &My_rect);
    // 渲染器填充矩形
    SDL_RenderFillRect(My_render, &My_rect);

    // 4. 渲染器绘制
    SDL_RenderPresent(My_render);

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