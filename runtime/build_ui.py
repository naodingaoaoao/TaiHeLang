#!/usr/bin/env python3
"""
编译 TaiHeLang UI 运行时库
自动检测可用的编译器
"""

import os
import sys
import subprocess
import shutil

def find_compiler():
    """查找可用的 C 编译器"""
    compilers = [
        ('gcc', ['gcc', '--version']),
        ('clang', ['clang', '--version']),
        ('cl', ['cl', '/?']),
    ]
    
    for name, cmd in compilers:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0 or name == 'cl':  # cl 返回非零但也表示可用
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    return None

def compile_with_gcc(src, out):
    """使用 GCC 编译"""
    cmd = [
        'gcc', '-shared', '-O2',
        '-o', out, src,
        '-luser32', '-lgdi32', '-lcomctl32'
    ]
    return subprocess.run(cmd, capture_output=True)

def compile_with_clang(src, out):
    """使用 Clang 编译"""
    cmd = [
        'clang', '-shared', '-O2',
        '-o', out, src,
        '-luser32', '-lgdi32', '-lcomctl32'
    ]
    return subprocess.run(cmd, capture_output=True)

def compile_with_msvc(src, out):
    """使用 MSVC 编译"""
    # 需要在 Visual Studio 环境中运行
    obj = src.replace('.c', '.obj')
    dll = out
    
    # 编译为对象文件
    cmd1 = ['cl', '/c', '/O2', '/utf-8', src, f'/Fo:{obj}']
    result1 = subprocess.run(cmd1, capture_output=True, shell=True)
    
    if result1.returncode != 0:
        return result1
    
    # 链接为 DLL
    cmd2 = ['link', '/DLL', obj, 
            '/OUT:' + dll,
            'user32.lib', 'gdi32.lib', 'comctl32.lib']
    return subprocess.run(cmd2, capture_output=True, shell=True)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_file = os.path.join(script_dir, 'taihe_ui.c')
    dll_file = os.path.join(script_dir, 'taihe_ui.dll')
    
    if not os.path.exists(src_file):
        print(f"错误: 源文件不存在: {src_file}")
        return 1
    
    compiler = find_compiler()
    
    if not compiler:
        print("错误: 未找到可用的 C 编译器")
        print("请安装以下任一编译器:")
        print("  - MinGW-w64 (https://www.mingw-w64.org/)")
        print("  - LLVM/Clang (https://llvm.org/)")
        print("  - Visual Studio (https://visualstudio.microsoft.com/)")
        return 1
    
    print(f"使用编译器: {compiler}")
    print(f"编译 {src_file} -> {dll_file}")
    
    if compiler == 'gcc':
        result = compile_with_gcc(src_file, dll_file)
    elif compiler == 'clang':
        result = compile_with_clang(src_file, dll_file)
    elif compiler == 'cl':
        result = compile_with_msvc(src_file, dll_file)
    
    if result.returncode != 0:
        print("编译失败!")
        if result.stdout:
            print("stdout:", result.stdout.decode('utf-8', errors='replace'))
        if result.stderr:
            print("stderr:", result.stderr.decode('utf-8', errors='replace'))
        return 1
    
    if os.path.exists(dll_file):
        print(f"编译成功: {dll_file}")
        return 0
    else:
        print("编译失败: 未生成 DLL 文件")
        return 1

if __name__ == '__main__':
    sys.exit(main())
