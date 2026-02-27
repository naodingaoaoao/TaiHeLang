/**
 * TaiHeLang Runtime Library - Console Functions
 * 控制台功能运行时库
 * 
 * 编译方式（Windows MSVC）：
 * cl /LD taihe_runtime.c /Fe:taihe_runtime.dll
 * 
 * 编译方式（Windows MinGW）：
 * gcc -shared -o taihe_runtime.dll taihe_runtime.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

// 控制台结构体
typedef struct {
    HANDLE hProcess;
    HANDLE hThread;
    HANDLE hStdOutRead;
    HANDLE hStdInWrite;
    char* content_buffer;
    int buffer_size;
    int hidden;
    int keep;
} TaiHeConsole;

// 创建控制台
// hidden: 0=显示, 1=隐藏
// keep: 0=执行完销毁, 1=保留
// command: 要执行的命令
__declspec(dllexport) void* _taihe_console_create(int hidden, int keep, const char* command) {
    TaiHeConsole* console = (TaiHeConsole*)malloc(sizeof(TaiHeConsole));
    if (!console) return NULL;
    
    memset(console, 0, sizeof(TaiHeConsole));
    console->hidden = hidden;
    console->keep = keep;
    console->buffer_size = 4096;
    console->content_buffer = (char*)malloc(console->buffer_size);
    if (console->content_buffer) {
        memset(console->content_buffer, 0, console->buffer_size);
    }
    
    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = TRUE;
    sa.lpSecurityDescriptor = NULL;
    
    // 创建管道用于读取输出
    HANDLE hStdOutRead, hStdOutWrite;
    if (!CreatePipe(&hStdOutRead, &hStdOutWrite, &sa, 0)) {
        free(console->content_buffer);
        free(console);
        return NULL;
    }
    SetHandleInformation(hStdOutRead, HANDLE_FLAG_INHERIT, 0);
    console->hStdOutRead = hStdOutRead;
    
    // 设置启动信息
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    memset(&si, 0, sizeof(si));
    memset(&pi, 0, sizeof(pi));
    si.cb = sizeof(si);
    si.hStdError = hStdOutWrite;
    si.hStdOutput = hStdOutWrite;
    si.dwFlags |= STARTF_USESTDHANDLES;
    
    // 根据hidden参数决定是否显示窗口
    DWORD creationFlags = 0;
    if (hidden) {
        creationFlags |= CREATE_NO_WINDOW;
    }
    
    // 创建进程
    char cmdLine[1024];
    strncpy(cmdLine, command, sizeof(cmdLine) - 1);
    cmdLine[sizeof(cmdLine) - 1] = '\0';
    
    if (!CreateProcessA(
        NULL,           // 模块名
        cmdLine,        // 命令行
        NULL,           // 进程安全属性
        NULL,           // 线程安全属性
        TRUE,           // 继承句柄
        creationFlags,  // 创建标志
        NULL,           // 环境变量
        NULL,           // 当前目录
        &si,            // 启动信息
        &pi             // 进程信息
    )) {
        CloseHandle(hStdOutRead);
        CloseHandle(hStdOutWrite);
        free(console->content_buffer);
        free(console);
        return NULL;
    }
    
    CloseHandle(hStdOutWrite);  // 子进程已继承，关闭父进程的写端
    
    console->hProcess = pi.hProcess;
    console->hThread = pi.hThread;
    
    // 等待进程结束（最多等待5秒）
    WaitForSingleObject(console->hProcess, 5000);
    
    // 读取所有输出
    DWORD bytesRead;
    char tempBuffer[1024];
    
    // 尝试读取输出
    while (PeekNamedPipe(console->hStdOutRead, NULL, 0, NULL, &bytesRead, NULL) && bytesRead > 0) {
        if (ReadFile(console->hStdOutRead, tempBuffer, sizeof(tempBuffer) - 1, &bytesRead, NULL)) {
            tempBuffer[bytesRead] = '\0';
            
            // 扩展缓冲区如果需要
            int newLen = strlen(console->content_buffer) + bytesRead + 1;
            if (newLen > console->buffer_size) {
                console->buffer_size = newLen * 2;
                console->content_buffer = (char*)realloc(console->content_buffer, console->buffer_size);
            }
            strcat(console->content_buffer, tempBuffer);
        }
    }
    
    return console;
}

// 获取控制台内容
__declspec(dllexport) const char* _taihe_console_get_content(void* console_handle) {
    if (!console_handle) return "";
    
    TaiHeConsole* console = (TaiHeConsole*)console_handle;
    
    // 尝试读取更多输出
    DWORD bytesRead;
    char tempBuffer[1024];
    
    while (PeekNamedPipe(console->hStdOutRead, NULL, 0, NULL, &bytesRead, NULL) && bytesRead > 0) {
        if (ReadFile(console->hStdOutRead, tempBuffer, sizeof(tempBuffer) - 1, &bytesRead, NULL)) {
            tempBuffer[bytesRead] = '\0';
            
            // 扩展缓冲区如果需要
            int newLen = strlen(console->content_buffer) + bytesRead + 1;
            if (newLen > console->buffer_size) {
                console->buffer_size = newLen * 2;
                console->content_buffer = (char*)realloc(console->content_buffer, console->buffer_size);
            }
            strcat(console->content_buffer, tempBuffer);
        }
    }
    
    return console->content_buffer ? console->content_buffer : "";
}

// 在控制台执行新命令
__declspec(dllexport) void _taihe_console_execute(void* console_handle, const char* command) {
    if (!console_handle || !command) return;
    
    TaiHeConsole* console = (TaiHeConsole*)console_handle;
    
    // 检查进程是否还在运行
    DWORD exitCode;
    if (GetExitCodeProcess(console->hProcess, &exitCode) && exitCode == STILL_ACTIVE) {
        // 进程还在运行，可以向输入管道写入命令
        // 注意：这需要控制台程序支持从stdin读取
        DWORD bytesWritten;
        WriteFile(console->hStdInWrite, command, strlen(command), &bytesWritten, NULL);
        WriteFile(console->hStdInWrite, "\n", 1, &bytesWritten, NULL);
    } else {
        // 进程已结束，启动新进程执行命令
        CloseHandle(console->hProcess);
        CloseHandle(console->hThread);
        
        SECURITY_ATTRIBUTES sa;
        sa.nLength = sizeof(SECURITY_ATTRIBUTES);
        sa.bInheritHandle = TRUE;
        sa.lpSecurityDescriptor = NULL;
        
        HANDLE hStdOutWrite;
        CreatePipe(&console->hStdOutRead, &hStdOutWrite, &sa, 0);
        SetHandleInformation(console->hStdOutRead, HANDLE_FLAG_INHERIT, 0);
        
        STARTUPINFOA si;
        PROCESS_INFORMATION pi;
        memset(&si, 0, sizeof(si));
        memset(&pi, 0, sizeof(pi));
        si.cb = sizeof(si);
        si.hStdError = hStdOutWrite;
        si.hStdOutput = hStdOutWrite;
        si.dwFlags |= STARTF_USESTDHANDLES;
        
        DWORD creationFlags = console->hidden ? CREATE_NO_WINDOW : 0;
        
        char cmdLine[1024];
        strncpy(cmdLine, command, sizeof(cmdLine) - 1);
        cmdLine[sizeof(cmdLine) - 1] = '\0';
        
        CreateProcessA(NULL, cmdLine, NULL, NULL, TRUE, creationFlags, NULL, NULL, &si, &pi);
        
        CloseHandle(hStdOutWrite);
        console->hProcess = pi.hProcess;
        console->hThread = pi.hThread;
        
        // 等待进程结束（最多等待5秒）
        WaitForSingleObject(console->hProcess, 5000);
        
        // 读取输出
        DWORD bytesRead;
        char tempBuffer[1024];
        while (PeekNamedPipe(console->hStdOutRead, NULL, 0, NULL, &bytesRead, NULL) && bytesRead > 0) {
            if (ReadFile(console->hStdOutRead, tempBuffer, sizeof(tempBuffer) - 1, &bytesRead, NULL)) {
                tempBuffer[bytesRead] = '\0';
                int newLen = strlen(console->content_buffer) + bytesRead + 1;
                if (newLen > console->buffer_size) {
                    console->buffer_size = newLen * 2;
                    console->content_buffer = (char*)realloc(console->content_buffer, console->buffer_size);
                }
                strcat(console->content_buffer, tempBuffer);
            }
        }
    }
}

// 销毁控制台
__declspec(dllexport) void _taihe_console_destroy(void* console_handle) {
    if (!console_handle) return;
    
    TaiHeConsole* console = (TaiHeConsole*)console_handle;
    
    // 终止进程
    if (console->hProcess) {
        TerminateProcess(console->hProcess, 0);
        CloseHandle(console->hProcess);
        CloseHandle(console->hThread);
    }
    
    // 关闭管道
    if (console->hStdOutRead) {
        CloseHandle(console->hStdOutRead);
    }
    if (console->hStdInWrite) {
        CloseHandle(console->hStdInWrite);
    }
    
    // 释放缓冲区
    if (console->content_buffer) {
        free(console->content_buffer);
    }
    
    free(console);
}

// ==================== GUI 函数 ====================

// GUI 组件类型
typedef enum {
    TAIHE_WINDOW,
    TAIHE_BUTTON,
    TAIHE_TEXTBOX,
    TAIHE_LABEL,
    TAIHE_LAYOUT
} TaiHeComponentType;

// GUI 组件结构体
typedef struct TaiHeComponent {
    TaiHeComponentType type;
    HWND hwnd;
    struct TaiHeComponent* parent;
    char* text;
    char* style;
    int width;
    int height;
    int x;
    int y;
    // 回调函数指针（存储为字符串形式的函数名）
    char* onclick_func;
    void* onclick_closure;
    // 布局相关
    int row;
    int col;
    int colspan;
    int rowspan;
} TaiHeComponent;

// 全局变量
static HINSTANCE g_hInstance = NULL;
static TaiHeComponent* g_main_window = NULL;
static TaiHeComponent* g_components[1024];
static int g_component_count = 0;
static char g_window_class[] = "TaiHeWindowClass";
static char g_button_class[] = "TaiHeButtonClass";
static char g_textbox_class[] = "TaiHeTextboxClass";

// 窗口过程
LRESULT CALLBACK TaiHeWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_COMMAND: {
            // 查找按钮点击事件
            HWND btnHwnd = (HWND)lParam;
            for (int i = 0; i < g_component_count; i++) {
                if (g_components[i]->hwnd == btnHwnd && g_components[i]->onclick_func) {
                    // 找到对应的按钮，执行回调
                    // 这里简单输出调试信息
                    char debug[256];
                    snprintf(debug, sizeof(debug), "Button clicked: %s\n", g_components[i]->text);
                    OutputDebugStringA(debug);
                }
            }
            break;
        }
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcA(hwnd, msg, wParam, lParam);
}

// 初始化 GUI
static void init_gui() {
    if (g_hInstance) return;
    g_hInstance = GetModuleHandleA(NULL);
    
    // 注册窗口类
    WNDCLASSA wc = {0};
    wc.lpfnWndProc = TaiHeWindowProc;
    wc.hInstance = g_hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = g_window_class;
    RegisterClassA(&wc);
}

// 创建窗口
__declspec(dllexport) void* _taihe_window_create(const char* title, int width, int height) {
    init_gui();
    
    TaiHeComponent* comp = (TaiHeComponent*)malloc(sizeof(TaiHeComponent));
    memset(comp, 0, sizeof(TaiHeComponent));
    comp->type = TAIHE_WINDOW;
    comp->width = width > 0 ? width : 400;
    comp->height = height > 0 ? height : 300;
    comp->text = title ? _strdup(title) : _strdup("Window");
    
    // 计算居中位置
    int screenW = GetSystemMetrics(SM_CXSCREEN);
    int screenH = GetSystemMetrics(SM_CYSCREEN);
    int x = (screenW - comp->width) / 2;
    int y = (screenH - comp->height) / 2;
    
    comp->hwnd = CreateWindowExA(
        0,
        g_window_class,
        comp->text,
        WS_OVERLAPPEDWINDOW,
        x, y, comp->width, comp->height,
        NULL, NULL, g_hInstance, NULL
    );
    
    g_main_window = comp;
    g_components[g_component_count++] = comp;
    
    return comp;
}

// 创建按钮
__declspec(dllexport) void* _taihe_button_create(const char* text) {
    init_gui();
    
    TaiHeComponent* comp = (TaiHeComponent*)malloc(sizeof(TaiHeComponent));
    memset(comp, 0, sizeof(TaiHeComponent));
    comp->type = TAIHE_BUTTON;
    comp->text = text ? _strdup(text) : _strdup("Button");
    comp->width = 80;
    comp->height = 30;
    
    // 暂时不创建窗口句柄，等到添加到布局时再创建
    g_components[g_component_count++] = comp;
    
    return comp;
}

// 创建文本框
__declspec(dllexport) void* _taihe_textbox_create(const char* text, int readonly) {
    init_gui();
    
    TaiHeComponent* comp = (TaiHeComponent*)malloc(sizeof(TaiHeComponent));
    memset(comp, 0, sizeof(TaiHeComponent));
    comp->type = TAIHE_TEXTBOX;
    comp->text = text ? _strdup(text) : _strdup("");
    comp->width = 200;
    comp->height = 30;
    
    // 暂时不创建窗口句柄
    g_components[g_component_count++] = comp;
    
    return comp;
}

// 创建标签
__declspec(dllexport) void* _taihe_label_create(const char* text) {
    init_gui();
    
    TaiHeComponent* comp = (TaiHeComponent*)malloc(sizeof(TaiHeComponent));
    memset(comp, 0, sizeof(TaiHeComponent));
    comp->type = TAIHE_LABEL;
    comp->text = text ? _strdup(text) : _strdup("");
    comp->width = 100;
    comp->height = 20;
    
    g_components[g_component_count++] = comp;
    
    return comp;
}

// 创建网格布局
__declspec(dllexport) void* _taihe_grid_create(int rows, int cols) {
    TaiHeComponent* comp = (TaiHeComponent*)malloc(sizeof(TaiHeComponent));
    memset(comp, 0, sizeof(TaiHeComponent));
    comp->type = TAIHE_LAYOUT;
    comp->width = rows;
    comp->height = cols;
    
    g_components[g_component_count++] = comp;
    
    return comp;
}

// 创建垂直布局
__declspec(dllexport) void* _taihe_vlayout_create() {
    TaiHeComponent* comp = (TaiHeComponent*)malloc(sizeof(TaiHeComponent));
    memset(comp, 0, sizeof(TaiHeComponent));
    comp->type = TAIHE_LAYOUT;
    comp->width = 1;  // 垂直布局
    comp->height = 0;  // 子组件数量
    
    g_components[g_component_count++] = comp;
    
    return comp;
}

// 设置组件样式
__declspec(dllexport) void _taihe_component_set_style(void* component, const char* style) {
    if (!component) return;
    TaiHeComponent* comp = (TaiHeComponent*)component;
    if (comp->style) free(comp->style);
    comp->style = style ? _strdup(style) : NULL;
}

// 设置组件文本
__declspec(dllexport) void _taihe_component_set_text(void* component, const char* text) {
    if (!component) return;
    TaiHeComponent* comp = (TaiHeComponent*)component;
    if (comp->text) free(comp->text);
    comp->text = text ? _strdup(text) : _strdup("");
    if (comp->hwnd) {
        SetWindowTextA(comp->hwnd, comp->text);
    }
}

// 获取组件文本
__declspec(dllexport) const char* _taihe_component_get_text(void* component) {
    if (!component) return "";
    TaiHeComponent* comp = (TaiHeComponent*)component;
    if (comp->hwnd) {
        static char buffer[4096];
        GetWindowTextA(comp->hwnd, buffer, sizeof(buffer));
        if (comp->text) free(comp->text);
        comp->text = _strdup(buffer);
    }
    return comp->text ? comp->text : "";
}

// 设置点击事件回调
__declspec(dllexport) void _taihe_component_set_onclick(void* component, const char* func_name, void* closure) {
    if (!component) return;
    TaiHeComponent* comp = (TaiHeComponent*)component;
    if (comp->onclick_func) free(comp->onclick_func);
    comp->onclick_func = func_name ? _strdup(func_name) : NULL;
    comp->onclick_closure = closure;
}

// 添加组件到布局
__declspec(dllexport) void _taihe_layout_add(void* layout, void* component, int row, int col) {
    if (!layout || !component) return;
    TaiHeComponent* layoutComp = (TaiHeComponent*)layout;
    TaiHeComponent* child = (TaiHeComponent*)component;
    
    child->parent = layoutComp;
    child->row = row;
    child->col = col;
    
    // 如果是网格布局，创建实际的控件
    if (layoutComp->type == TAIHE_LAYOUT && g_main_window && g_main_window->hwnd) {
        HWND parentHwnd = g_main_window->hwnd;
        
        // 计算控件位置和大小
        int cellWidth = g_main_window->width / layoutComp->height;  // cols
        int cellHeight = 60;  // 按钮高度
        int y = 50 + row * cellHeight;  // 留出顶部文本框空间
        int x = col * cellWidth;
        int width = cellWidth;
        int height = cellHeight;
        
        if (child->colspan > 1) {
            width = child->colspan * cellWidth;
        }
        
        if (child->type == TAIHE_BUTTON) {
            child->hwnd = CreateWindowExA(
                0, "BUTTON", child->text,
                WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                x, y, width - 4, height - 4,
                parentHwnd, NULL, g_hInstance, NULL
            );
        } else if (child->type == TAIHE_TEXTBOX) {
            DWORD style = WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL;
            if (child->style && strstr(child->style, "只读")) {
                style |= ES_READONLY;
            }
            child->hwnd = CreateWindowExA(
                WS_EX_CLIENTEDGE, "EDIT", child->text,
                style,
                x, y, width - 4, height - 4,
                parentHwnd, NULL, g_hInstance, NULL
            );
        }
    }
}

// 设置窗口布局
__declspec(dllexport) void _taihe_window_set_layout(void* window, void* layout) {
    // 简化处理：布局信息已存储在组件中
}

// 设置组件跨列
__declspec(dllexport) void _taihe_component_set_colspan(void* component, int colspan) {
    if (!component) return;
    TaiHeComponent* comp = (TaiHeComponent*)component;
    comp->colspan = colspan;
}

// 显示窗口
__declspec(dllexport) void _taihe_window_show(void* window) {
    if (!window) return;
    TaiHeComponent* comp = (TaiHeComponent*)window;
    
    // 先创建布局中的控件
    // 遍历所有组件，找到属于此窗口的子组件
    for (int i = 0; i < g_component_count; i++) {
        TaiHeComponent* child = g_components[i];
        if (child->parent && child->parent->type == TAIHE_LAYOUT) {
            // 找到网格布局
            TaiHeComponent* grid = child->parent;
            HWND parentHwnd = comp->hwnd;
            
            // 计算控件位置
            int cellWidth = comp->width / grid->height;
            int cellHeight = 60;
            int y = 50 + child->row * cellHeight;
            int x = child->col * cellWidth;
            int width = cellWidth;
            int height = cellHeight;
            
            if (child->colspan > 1) {
                width = child->colspan * cellWidth;
            }
            
            if (child->type == TAIHE_BUTTON && !child->hwnd) {
                child->hwnd = CreateWindowExA(
                    0, "BUTTON", child->text,
                    WS_VISIBLE | WS_CHILD | BS_PUSHBUTTON,
                    x, y, width - 4, height - 4,
                    parentHwnd, NULL, g_hInstance, NULL
                );
            } else if (child->type == TAIHE_TEXTBOX && !child->hwnd) {
                DWORD style = WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL;
                child->hwnd = CreateWindowExA(
                    WS_EX_CLIENTEDGE, "EDIT", child->text,
                    style,
                    x, y, width - 4, height - 4,
                    parentHwnd, NULL, g_hInstance, NULL
                );
            }
        } else if (child->parent == NULL && child->type != TAIHE_WINDOW && child->type != TAIHE_LAYOUT) {
            // 直接添加到窗口的组件（如顶部的文本框）
            HWND parentHwnd = comp->hwnd;
            int width = comp->width - 20;
            
            if (child->type == TAIHE_TEXTBOX && !child->hwnd) {
                child->hwnd = CreateWindowExA(
                    WS_EX_CLIENTEDGE, "EDIT", child->text,
                    WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL | ES_READONLY,
                    10, 10, width, 30,
                    parentHwnd, NULL, g_hInstance, NULL
                );
            }
        }
    }
    
    ShowWindow(comp->hwnd, SW_SHOW);
    UpdateWindow(comp->hwnd);
}

// 运行消息循环
__declspec(dllexport) int _taihe_run() {
    MSG msg;
    while (GetMessageA(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    return (int)msg.wParam;
}

// 简单的消息框
__declspec(dllexport) int _taihe_message_box(const char* title, const char* message) {
    return MessageBoxA(NULL, message, title, MB_OK);
}
