"""便捷函数"""
import os
import sys
from typing import Optional
from .lexer import Lexer, tokenize_string
from .parser import Parser
from .codegen import CodeGenerator


def compile_source(source_code: str, verbose: bool = False) -> str:
    """
    编译太和源代码字符串
    
    Args:
        source_code: 太和源代码
        verbose: 是否显示详细输出
    
    Returns:
        LLVM IR字符串
    """
    if verbose:
        print("开始编译源代码...")
        print(f"源代码长度: {len(source_code)} 字符")
    
    # 词法分析
    if verbose:
        print("词法分析...")
    tokens = tokenize_string(source_code)
    
    if verbose:
        print(f"生成 {len(tokens)} 个词法单元")
        for i, token in enumerate(tokens[:5]):
            print(f"  [{i}] {token}")
        if len(tokens) > 5:
            print(f"  ... 还有 {len(tokens) - 5} 个")
    
    # 语法分析
    if verbose:
        print("语法分析...")
    parser = Parser(tokens)
    ast = parser.parse()
    
    if verbose:
        print(f"生成 {len(ast.statements)} 条语句的AST")
    
    # 代码生成
    if verbose:
        print("LLVM IR生成...")
    codegen = CodeGenerator()
    llvm_ir = codegen.generate(ast)
    
    if verbose:
        print(f"生成 {len(llvm_ir.splitlines())} 行LLVM IR")
    
    return llvm_ir


def read_source_file(file_path: str, verbose: bool = False) -> str:
    """
    读取源代码文件，自动处理不同编码
    
    Args:
        file_path: 文件路径
        verbose: 是否显示详细输出
    
    Returns:
        统一为UTF-8编码的源代码字符串
    
    Raises:
        UnicodeDecodeError: 当无法用任何支持的编码解码时
    """
    # 支持的编码列表（按优先级）
    encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16']
    
    last_error = None
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            if verbose and encoding != 'utf-8':
                print(f"警告: 文件 '{file_path}' 使用 {encoding} 编码，已转换为UTF-8")
            
            # 确保返回UTF-8编码的字符串
            # 如果读取成功，Python已经将字节解码为字符串
            # 我们只需要确保字符串是Unicode（Python3默认就是）
            return content
            
        except UnicodeDecodeError as e:
            last_error = e
            continue
    
    # 所有编码都失败
    error_msg = f"无法解码文件 '{file_path}'。尝试的编码: {', '.join(encodings_to_try)}"
    if last_error:
        error_msg += f"\n最后错误: {last_error}"
        # 重新引发最后一个错误，但添加额外信息
        raise UnicodeDecodeError(
            last_error.encoding,
            last_error.object,
            last_error.start,
            last_error.end,
            error_msg
        ) from last_error
    else:
        # 理论上不会发生，因为至少尝试了一个编码
        raise UnicodeDecodeError('utf-8', b'', 0, 1, error_msg)

def compile_file(source_file: str, output_file: Optional[str] = None, verbose: bool = False) -> str:
    """
    编译太和源文件
    
    Args:
        source_file: 源文件路径
        output_file: 输出文件路径（可选）
        verbose: 是否显示详细输出
    
    Returns:
        生成的LLVM IR字符串
    """
    if verbose:
        print(f"读取文件: {source_file}")
    
    # 读取源代码（自动处理编码）
    source_code = read_source_file(source_file, verbose)
    
    # 编译
    llvm_ir = compile_source(source_code, verbose)
    
    # 写入输出文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(llvm_ir)
        
        if verbose:
            print(f"LLVM IR已写入: {output_file}")
    else:
        # 默认输出文件
        base_name = os.path.splitext(source_file)[0]
        output_file = base_name + '.ll'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(llvm_ir)
        
        if verbose:
            print(f"LLVM IR已写入: {output_file}")
    
    return llvm_ir


def compile_and_execute(source_code: str):
    """
    编译并执行太和程序（实验性）
    
    Args:
        source_code: 太和源代码
    
    Returns:
        执行结果（如果有）
    """
    # 编译为LLVM IR
    llvm_ir = compile_source(source_code, verbose=False)
    
    # TODO: 使用LLVM JIT执行
    print("编译成功！执行功能尚未完全实现。")
    print("生成的LLVM IR:")
    print("-" * 50)
    print(llvm_ir)
    
    return None


if __name__ == '__main__':
    # 命令行接口
    if len(sys.argv) < 2:
        print("用法: python -m taihe.compiler <源文件> [输出文件]")
        sys.exit(1)
    
    source_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        llvm_ir = compile_file(source_file, output_file, verbose=True)
        print("编译成功！")
    except Exception as e:
        print(f"编译失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)