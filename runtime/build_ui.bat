@echo off
REM 编译 TaiHeLang UI 运行时库

echo 编译 UI 运行时库...

cd /d "%~dp0"

REM 查找编译器
where cl >nul 2>&1
if %errorlevel% == 0 (
    echo 使用 MSVC 编译...
    cl /LD /O2 /utf-8 taihe_ui.c /Fe:taihe_ui.dll /link user32.lib gdi32.lib comctl32.lib
    goto :end
)

where gcc >nul 2>&1
if %errorlevel% == 0 (
    echo 使用 GCC 编译...
    gcc -shared -O2 -o taihe_ui.dll taihe_ui.c -luser32 -lgdi32 -lcomctl32
    goto :end
)

where clang >nul 2>&1
if %errorlevel% == 0 (
    echo 使用 Clang 编译...
    clang -shared -O2 -o taihe_ui.dll taihe_ui.c -luser32 -lgdi32 -lcomctl32
    goto :end
)

echo 错误: 未找到编译器 (cl, gcc, clang)
exit /b 1

:end
if exist taihe_ui.dll (
    echo 编译成功: taihe_ui.dll
) else (
    echo 编译失败
    exit /b 1
)
