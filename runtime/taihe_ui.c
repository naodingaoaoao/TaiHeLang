/**
 * TaiHeLang UI Runtime - WinUI3 Style
 * 使用 Windows API 实现高性能 UI
 * 
 * 函数名前缀: _taihe_
 */

#ifdef _WIN32
#define TAIHE_API __declspec(dllexport)
#else
#define TAIHE_API
#endif

#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ============================================
// 数据结构
// ============================================

#define MAX_WINDOWS 64
#define MAX_CONTROLS 1024
#define MAX_LAYOUTS 256

typedef enum {
    COMP_NONE = 0,
    COMP_WINDOW,
    COMP_BUTTON,
    COMP_EDIT,
    COMP_LABEL,
    COMP_GRID,
    COMP_VLAYOUT
} ComponentType;

typedef struct {
    HWND hwnd;
    int id;
    int in_use;
    ComponentType type;
    int window_id;  // 所属窗口
    void* callback;
    // 布局相关
    int row, col;
    int colspan;
} TaiheComponent;

typedef struct {
    int in_use;
    int window_id;
    int rows, cols;
    int cell_count;
    TaiheComponent* cells[MAX_CONTROLS];  // 简化：按顺序存储
} TaiheLayout;

// 全局状态
static TaiheComponent g_windows[MAX_WINDOWS];
static TaiheComponent g_controls[MAX_CONTROLS];
static TaiheLayout g_layouts[MAX_LAYOUTS];
static int g_initialized = 0;
static HINSTANCE g_hInstance = NULL;
static int g_next_ctrl_id = 100;

// ============================================
// 初始化
// ============================================

static void ensure_init() {
    if (g_initialized) return;
    
    g_hInstance = GetModuleHandle(NULL);
    
    // 初始化 Common Controls
    INITCOMMONCONTROLSEX icc;
    icc.dwSize = sizeof(INITCOMMONCONTROLSEX);
    icc.dwICC = ICC_WIN95_CLASSES | ICC_STANDARD_CLASSES;
    InitCommonControlsEx(&icc);
    
    memset(g_windows, 0, sizeof(g_windows));
    memset(g_controls, 0, sizeof(g_controls));
    memset(g_layouts, 0, sizeof(g_layouts));
    
    g_initialized = 1;
}

// ============================================
// 窗口类注册
// ============================================

static const wchar_t* TAIHE_WINDOW_CLASS = L"TaiheWindowClass";

static LRESULT CALLBACK TaiheWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_COMMAND: {
            int ctrl_id = LOWORD(wParam);
            if (ctrl_id >= 100 && ctrl_id < 100 + MAX_CONTROLS) {
                int idx = ctrl_id - 100;
                if (g_controls[idx].in_use && g_controls[idx].callback) {
                    // 调用回调（回调是函数名字符串，需要通过运行时查找）
                    // 这里简化处理，实际需要更复杂的回调机制
                }
            }
            break;
        }
        case WM_CLOSE:
            DestroyWindow(hwnd);
            break;
        case WM_DESTROY:
            PostQuitMessage(0);
            break;
        default:
            return DefWindowProcW(hwnd, msg, wParam, lParam);
    }
    return 0;
}

static void register_window_class() {
    static int registered = 0;
    if (registered) return;
    
    WNDCLASSEXW wc = {0};
    wc.cbSize = sizeof(WNDCLASSEXW);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = TaiheWindowProc;
    wc.hInstance = g_hInstance;
    wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetSysColorBrush(COLOR_BTNFACE);
    wc.lpszClassName = TAIHE_WINDOW_CLASS;
    wc.hIconSm = LoadIcon(NULL, IDI_APPLICATION);
    
    RegisterClassExW(&wc);
    registered = 1;
}

// ============================================
// 辅助函数
// ============================================

static wchar_t* utf8_to_wchar(const char* str) {
    if (!str) return NULL;
    int len = MultiByteToWideChar(CP_UTF8, 0, str, -1, NULL, 0);
    wchar_t* wstr = (wchar_t*)malloc(len * sizeof(wchar_t));
    MultiByteToWideChar(CP_UTF8, 0, str, -1, wstr, len);
    return wstr;
}

static char* wchar_to_utf8(const wchar_t* wstr) {
    if (!wstr) return NULL;
    int len = WideCharToMultiByte(CP_UTF8, 0, wstr, -1, NULL, 0, NULL, NULL);
    char* str = (char*)malloc(len);
    WideCharToMultiByte(CP_UTF8, 0, wstr, -1, str, len, NULL, NULL);
    return str;
}

static int find_free_slot(TaiheComponent* arr, int size) {
    for (int i = 1; i < size; i++) {
        if (!arr[i].in_use) return i;
    }
    return -1;
}

// ============================================
// 导出函数
// ============================================

// _taihe_window_create(title, width, height) -> window_handle
TAIHE_API void* _taihe_window_create(const char* title, int width, int height) {
    ensure_init();
    register_window_class();
    
    int id = find_free_slot(g_windows, MAX_WINDOWS);
    if (id < 0) return NULL;
    
    wchar_t* wtitle = utf8_to_wchar(title ? title : "窗口");
    
    HWND hwnd = CreateWindowExW(
        0, TAIHE_WINDOW_CLASS, wtitle,
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT, width, height,
        NULL, NULL, g_hInstance, NULL
    );
    
    free(wtitle);
    if (!hwnd) return NULL;
    
    g_windows[id].hwnd = hwnd;
    g_windows[id].id = id;
    g_windows[id].in_use = 1;
    g_windows[id].type = COMP_WINDOW;
    
    return &g_windows[id];
}

// _taihe_button_create(text) -> button_handle
TAIHE_API void* _taihe_button_create(const char* text) {
    ensure_init();
    
    int id = find_free_slot(g_controls, MAX_CONTROLS);
    if (id < 0) return NULL;
    
    wchar_t* wtext = utf8_to_wchar(text ? text : "");
    int ctrl_id = g_next_ctrl_id++;
    
    // 创建一个临时父窗口（实际应该添加到具体窗口）
    HWND parent = g_windows[1].hwnd;  // 默认使用第一个窗口
    
    HWND hwnd = CreateWindowExW(
        0, L"BUTTON", wtext,
        WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
        0, 0, 80, 30,
        parent, (HMENU)(intptr_t)ctrl_id, g_hInstance, NULL
    );
    
    free(wtext);
    if (!hwnd) return NULL;
    
    g_controls[id].hwnd = hwnd;
    g_controls[id].id = id;
    g_controls[id].in_use = 1;
    g_controls[id].type = COMP_BUTTON;
    
    return &g_controls[id];
}

// _taihe_textbox_create(text, readonly) -> textbox_handle
TAIHE_API void* _taihe_textbox_create(const char* text, int readonly) {
    ensure_init();
    
    int id = find_free_slot(g_controls, MAX_CONTROLS);
    if (id < 0) return NULL;
    
    wchar_t* wtext = utf8_to_wchar(text ? text : "");
    HWND parent = g_windows[1].hwnd;
    
    DWORD style = WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL | WS_BORDER;
    if (readonly) style |= ES_READONLY;
    
    HWND hwnd = CreateWindowExW(
        WS_EX_CLIENTEDGE, L"EDIT", wtext,
        style,
        0, 0, 200, 25,
        parent, NULL, g_hInstance, NULL
    );
    
    free(wtext);
    if (!hwnd) return NULL;
    
    g_controls[id].hwnd = hwnd;
    g_controls[id].id = id;
    g_controls[id].in_use = 1;
    g_controls[id].type = COMP_EDIT;
    
    return &g_controls[id];
}

// _taihe_label_create(text) -> label_handle
TAIHE_API void* _taihe_label_create(const char* text) {
    ensure_init();
    
    int id = find_free_slot(g_controls, MAX_CONTROLS);
    if (id < 0) return NULL;
    
    wchar_t* wtext = utf8_to_wchar(text ? text : "");
    HWND parent = g_windows[1].hwnd;
    
    HWND hwnd = CreateWindowExW(
        0, L"STATIC", wtext,
        WS_CHILD | WS_VISIBLE | SS_LEFT,
        0, 0, 100, 20,
        parent, NULL, g_hInstance, NULL
    );
    
    free(wtext);
    if (!hwnd) return NULL;
    
    g_controls[id].hwnd = hwnd;
    g_controls[id].id = id;
    g_controls[id].in_use = 1;
    g_controls[id].type = COMP_LABEL;
    
    return &g_controls[id];
}

// _taihe_grid_create(rows, cols) -> grid_handle
TAIHE_API void* _taihe_grid_create(int rows, int cols) {
    ensure_init();
    
    int id = find_free_slot((TaiheComponent*)g_layouts, MAX_LAYOUTS);
    if (id < 0) return NULL;
    
    g_layouts[id].in_use = 1;
    g_layouts[id].rows = rows;
    g_layouts[id].cols = cols;
    g_layouts[id].cell_count = 0;
    
    return &g_layouts[id];
}

// _taihe_vlayout_create() -> layout_handle
TAIHE_API void* _taihe_vlayout_create() {
    ensure_init();
    
    int id = find_free_slot((TaiheComponent*)g_layouts, MAX_LAYOUTS);
    if (id < 0) return NULL;
    
    g_layouts[id].in_use = 1;
    g_layouts[id].rows = 0;
    g_layouts[id].cols = 1;
    g_layouts[id].cell_count = 0;
    
    return &g_layouts[id];
}

// _taihe_component_set_style(component, style) -> void
TAIHE_API void _taihe_component_set_style(void* component, const char* style) {
    if (!component) return;
    TaiheComponent* comp = (TaiheComponent*)component;
    // 简化：暂不实现样式解析
}

// _taihe_component_set_text(component, text) -> void
TAIHE_API void _taihe_component_set_text(void* component, const char* text) {
    if (!component || !text) return;
    TaiheComponent* comp = (TaiheComponent*)component;
    if (!comp->hwnd) return;
    
    wchar_t* wtext = utf8_to_wchar(text);
    SetWindowTextW(comp->hwnd, wtext);
    free(wtext);
}

// _taihe_component_get_text(component) -> char*
TAIHE_API const char* _taihe_component_get_text(void* component) {
    static char buffer[4096];
    if (!component) return "";
    
    TaiheComponent* comp = (TaiheComponent*)component;
    if (!comp->hwnd) return "";
    
    int len = GetWindowTextLengthW(comp->hwnd);
    if (len <= 0) return "";
    
    wchar_t* wbuf = (wchar_t*)malloc((len + 1) * sizeof(wchar_t));
    GetWindowTextW(comp->hwnd, wbuf, len + 1);
    
    WideCharToMultiByte(CP_UTF8, 0, wbuf, -1, buffer, sizeof(buffer), NULL, NULL);
    free(wbuf);
    
    return buffer;
}

// _taihe_component_set_onclick(component, func_name, closure) -> void
TAIHE_API void _taihe_component_set_onclick(void* component, const char* func_name, void* closure) {
    if (!component) return;
    TaiheComponent* comp = (TaiheComponent*)component;
    comp->callback = (void*)func_name;  // 简化：存储函数名
}

// _taihe_layout_add(layout, component, row, col) -> void
TAIHE_API void _taihe_layout_add(void* layout, void* component, int row, int col) {
    if (!layout || !component) return;
    
    TaiheLayout* lay = (TaiheLayout*)layout;
    TaiheComponent* comp = (TaiheComponent*)component;
    
    comp->row = row;
    comp->col = col;
    
    // 计算控件位置（简单网格布局）
    if (comp->hwnd && lay->window_id >= 0) {
        int cell_w = 80, cell_h = 40;
        int x = col * cell_w + 10;
        int y = row * cell_h + 10;
        SetWindowPos(comp->hwnd, NULL, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);
    }
}

// _taihe_window_set_layout(window, layout) -> void
TAIHE_API void _taihe_window_set_layout(void* window, void* layout) {
    if (!window || !layout) return;
    
    TaiheComponent* win = (TaiheComponent*)window;
    TaiheLayout* lay = (TaiheLayout*)layout;
    
    lay->window_id = win->id;
    
    // 更新所有控件的位置
    RECT rect;
    GetClientRect(win->hwnd, &rect);
    int client_w = rect.right - rect.left;
    int client_h = rect.bottom - rect.top;
    
    int cell_w = client_w / (lay->cols > 0 ? lay->cols : 1);
    int cell_h = 40;
    
    for (int i = 0; i < MAX_CONTROLS; i++) {
        if (g_controls[i].in_use && g_controls[i].window_id == win->id) {
            int x = g_controls[i].col * cell_w + 5;
            int y = g_controls[i].row * cell_h + 5;
            int w = cell_w * g_controls[i].colspan - 10;
            SetWindowPos(g_controls[i].hwnd, NULL, x, y, w, cell_h - 10, SWP_NOZORDER);
        }
    }
}

// _taihe_component_set_colspan(component, colspan) -> void
TAIHE_API void _taihe_component_set_colspan(void* component, int colspan) {
    if (!component) return;
    TaiheComponent* comp = (TaiheComponent*)component;
    comp->colspan = colspan > 0 ? colspan : 1;
}

// _taihe_window_show(window) -> void
TAIHE_API void _taihe_window_show(void* window) {
    if (!window) return;
    TaiheComponent* win = (TaiheComponent*)window;
    ShowWindow(win->hwnd, SW_SHOW);
    UpdateWindow(win->hwnd);
}

// _taihe_run() -> int
TAIHE_API int _taihe_run() {
    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return (int)msg.wParam;
}

// _taihe_message_box(title, message) -> int
TAIHE_API int _taihe_message_box(const char* title, const char* message) {
    wchar_t* wtitle = utf8_to_wchar(title ? title : "");
    wchar_t* wmsg = utf8_to_wchar(message ? message : "");
    
    int result = MessageBoxW(NULL, wmsg, wtitle, MB_OK | MB_ICONINFORMATION);
    
    free(wtitle);
    free(wmsg);
    
    return result;
}

// ============================================
// DllMain
// ============================================

#ifdef _WINDLL
BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID reserved) {
    switch (reason) {
        case DLL_PROCESS_ATTACH:
            g_hInstance = hModule;
            break;
    }
    return TRUE;
}
#endif
