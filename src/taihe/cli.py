"""命令行接口"""
import sys
import os
import click
from pathlib import Path
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taihe.lexer import Lexer
from taihe.parser import Parser
from taihe.codegen import CodeGenerator
from taihe.compiler import read_source_file, compile_source


def find_executable(name):

    import shutil
    path = shutil.which(name)
    if path:
        return path
    if sys.platform == "win32":
        common_paths = [
            r"C:\Program Files\LLVM\bin",
            r"C:\Program Files (x86)\LLVM\bin",
            r"C:\LLVM\bin",
            # Visual Studio内置LLVM，天啊我太贴心了，还支持了2026，下面全AI写的，不用看了
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2019\Community\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2019\Enterprise\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2019\Professional\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2026\Community\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2026\Enterprise\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2026\Professional\VC\Tools\Llvm\bin",
        ]
        exe_name = name + ".exe"
        for base in common_paths:
            full_path = os.path.join(base, exe_name)
            if os.path.exists(full_path):
                return full_path
    
    return None


class TaiheCLI(click.Group):
    """自定义CLI组，支持直接传递文件参数"""
    
    def get_command(self, ctx, cmd_name):
        # 首先尝试获取常规命令
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd
        
        # 如果命令不存在，检查它是否是一个文件
        if os.path.exists(cmd_name):
            # 创建一个命令对象来包装run函数
            from click import Command
            class FileRunCommand(Command):
                def __init__(self, filename):
                    super().__init__(name=filename)
                    self.filename = filename
                    self.help = f"运行太和文件: {filename}"
                
                def invoke(self, ctx):
                    # 调用实际的run函数
                    return ctx.invoke(run, source_file=self.filename)
            
            return FileRunCommand(cmd_name)
        
        # 不是文件也不是已知命令
        return None
    
    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError:
            # 如果常规解析失败，检查第一个参数是否是文件
            if args and os.path.exists(args[0]):
                # 创建一个命令对象
                cmd_name = args[0]
                from click import Command
                class FileRunCommand(Command):
                    def __init__(self, filename):
                        super().__init__(name=filename)
                        self.filename = filename
                        self.help = f"运行太和文件: {filename}"
                    
                    def invoke(self, ctx):
                        return ctx.invoke(run, source_file=self.filename)
                
                return cmd_name, FileRunCommand(cmd_name), args[1:]
            raise


@click.group(cls=TaiheCLI, invoke_without_command=True)
@click.pass_context
@click.option('--help', '-h', is_flag=True, help='显示帮助信息')
def main(ctx, help):
    """太和编程语言编译器
    
    使用方式:
      taihe <源文件>           # 编译并执行太和程序
      taihe run <源文件> --dll # 编译并执行太和程序
      taihe compile <源文件>   # 仅编译为LLVM IR
      taihe tokens <源文件>    # 显示词法分析结果
      taihe ast <源文件>       # 显示抽象语法树
      taihe version           # 显示版本信息

    GitHub 开源项目 https://github.com/naodingaoaoao/TaiHeLang/
    """
    # 如果有帮助标志，显示帮助
    if help:
        click.echo(ctx.get_help())
        ctx.exit(0)
    
    # 如果没有子命令被调用（即直接传递文件参数）
    if ctx.invoked_subcommand is None:
        # 显示帮助
        click.echo(ctx.get_help())
        ctx.exit(0)


@main.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='输出文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
def compile(source_file, output, verbose):
    # 编译源文件
    try:
        if verbose:
            click.echo(f"读取源文件: {source_file}")
        
        # 读取源代码（自动处理编码）
        source_code = read_source_file(source_file, verbose)
        
        if verbose:
            click.echo("源代码:")
            click.echo("---")
            click.echo(source_code)
            click.echo("---")
        
        # 词法分析
        if verbose:
            click.echo("开始词法分析...")
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        
        if verbose:
            click.echo(f"生成 {len(tokens)} 个词法单元")
            for i, token in enumerate(tokens[:10]):
                click.echo(f"  [{i}] {token}")
            if len(tokens) > 10:
                click.echo(f"  ... 还有 {len(tokens) - 10} 个")
        
        # 语法分析
        if verbose:
            click.echo("开始语法分析...")
        parser = Parser(tokens)
        ast = parser.parse()
        
        if verbose:
            click.echo("语法分析完成")
        
        # 代码生成
        if verbose:
            click.echo("开始LLVM IR生成...")
        codegen = CodeGenerator()
        llvm_ir = codegen.generate(ast)
        
        # 输出IR
        if output:
            output_path = output
        else:
            source_path = Path(source_file)
            output_path = source_path.with_suffix('.ll')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(llvm_ir)
        
        click.echo(f"编译完成！LLVM IR已保存到: {output_path}")
        
        if verbose:
            click.echo("\n生成的LLVM IR:")
            click.echo("---")
            click.echo(llvm_ir)
            click.echo("---")
        
    except FileNotFoundError as e:
        click.echo(f"错误: 文件未找到 - {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"编译错误: {e}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


@main.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.option('--keep/--no-keep', default=True, help='是否保留生成的exe文件')
@click.option('--dll', 'build_dll', is_flag=True, help='编译为DLL动态链接库')
def run(source_file, keep, build_dll):
    # 编译并执行程序
    try:
        click.echo(f"编译并执行: {source_file}")
        
        # 获取源文件的绝对路径和目录
        source_path = Path(source_file).resolve()
        source_dir = source_path.parent
        source_name = source_path.stem
        
        # 创建输出目录（源文件同目录下的build文件夹）
        output_dir = source_dir / "build"
        output_dir.mkdir(exist_ok=True)
        
        # 读取源代码
        source_code = read_source_file(source_file, verbose=False)
        
        # 编译为LLVM IR
        llvm_ir = compile_source(source_code, verbose=False)
        
        # 在输出目录中创建IR文件
        ir_file = output_dir / f"{source_name}.ll"
        with open(ir_file, 'w', encoding='utf-8') as f:
            f.write(llvm_ir)
        
        try:
            # 查找clang可执行文件
            clang_path = find_executable('clang')
            if not clang_path:
                click.echo("错误: 未找到Clang编译器。请确保已安装Clang并添加到PATH环境变量。", err=True)
                click.echo("Windows用户可安装以下任一选项:", err=True)
                click.echo("  1. LLVM for Windows: https://github.com/llvm/llvm-project/releases", err=True)
                click.echo("  2. Visual Studio with C++工具集", err=True)
                click.echo("  3. MinGW-w64 with Clang", err=True)
                sys.exit(1)
            
            click.echo(f"使用Clang: {clang_path}")
            
            # 查找运行时库
            runtime_dir = Path(__file__).parent.parent.parent / "runtime"
            runtime_obj = runtime_dir / "taihe_runtime.o"
            runtime_c = runtime_dir / "taihe_runtime.c"
            
            # 如果运行时目标文件不存在，尝试编译它
            if not runtime_obj.exists() and runtime_c.exists():
                click.echo("运行时库不存在，尝试编译...")
                compiled = False
                
                # 优先尝试使用 clang 编译为目标文件
                if clang_path:
                    try:
                        subprocess.run([clang_path, '-c', '-o', str(runtime_obj), str(runtime_c)],
                                     check=True, capture_output=True)
                        click.echo(f"运行时库编译成功 (使用clang): {runtime_obj}")
                        compiled = True
                    except subprocess.CalledProcessError:
                        pass
                
                # 如果 clang 失败，尝试使用 msvc (cl)
                if not compiled:
                    cl_path = find_executable('cl')
                    if cl_path:
                        try:
                            # MSVC 编译为目标文件
                            old_cwd = os.getcwd()
                            os.chdir(str(runtime_dir))
                            subprocess.run([cl_path, '/c', 'taihe_runtime.c', '/Fo:taihe_runtime.obj'],
                                         check=True, capture_output=True, shell=True)
                            os.chdir(old_cwd)
                            # MSVC 生成 .obj 文件，重命名为 .o
                            runtime_obj_msvc = runtime_dir / "taihe_runtime.obj"
                            if runtime_obj_msvc.exists():
                                runtime_obj_msvc.rename(runtime_obj)
                            click.echo(f"运行时库编译成功 (使用msvc): {runtime_obj}")
                            compiled = True
                        except subprocess.CalledProcessError:
                            pass
                
                # 最后尝试 gcc
                if not compiled:
                    gcc_path = find_executable('gcc')
                    if gcc_path:
                        try:
                            subprocess.run([gcc_path, '-c', '-o', str(runtime_obj), str(runtime_c)],
                                         check=True, capture_output=True)
                            click.echo(f"运行时库编译成功 (使用gcc): {runtime_obj}")
                            compiled = True
                        except subprocess.CalledProcessError:
                            pass
                
                if not compiled:
                    click.echo("警告: 无法编译运行时库，可能是LLVM没有正确安装导致的，如果你确保安装，请重启cmd窗口，否则可能导致控制台功能可能不可用。")
            elif not runtime_c.exists():
                click.echo("警告: 运行时库源文件不存在。控制台功能可能不可用。")
            
            # 方法1: 先尝试使用llc编译为目标文件，然后clang链接
            obj_file = None
            
            # 链接选项
            link_args = []
            if runtime_obj.exists():
                link_args.extend([str(runtime_obj)])
                click.echo(f"链接运行时库: {runtime_obj}")
            
            # 添加 UI 运行时库 先别用
            ui_lib = runtime_dir / "taihe_ui.dll"
            ui_lib_a = runtime_dir / "taihe_ui.lib"
            if ui_lib_a.exists():
                link_args.append(str(ui_lib_a))
                click.echo(f"链接 UI 库: {ui_lib_a}")
            elif ui_lib.exists():
                # 直接链接 DLL
                link_args.append(str(ui_lib))
                click.echo(f"链接 UI 库: {ui_lib}")
            
            if build_dll:
                # 编译为DLL
                dll_file = output_dir / f"{source_name}.dll"
                obj_file = output_dir / f"{source_name}.o"
                
                llc_path = find_executable('llc')
                if llc_path:
                    subprocess.run([llc_path, '-filetype=obj', str(ir_file), '-o', str(obj_file)], check=True, capture_output=True)
                    
                    # 使用clang链接为DLL，添加导出属性
                    subprocess.run([clang_path, '-shared', '-o', str(dll_file), str(obj_file), 
                                   '-Wl,--export-all-symbols'], check=True, capture_output=True)
                else:
                    click.echo("警告: llc不可用，尝试使用clang直接编译...")
                    subprocess.run([clang_path, '-x', 'ir', '-shared', '-o', str(dll_file), str(ir_file),
                                   '-Wl,--export-all-symbols'], check=True, capture_output=True)
                
                click.echo(f"DLL编译成功: {dll_file}")
                click.echo(f"\n输出文件:")
                click.echo(f"  LLVM IR: {ir_file}")
                click.echo(f"  DLL文件: {dll_file}")
                if obj_file and obj_file.exists():
                    click.echo(f"  目标文件: {obj_file}")
                return
            else:
                # 编译为可执行文件
                exe_file = output_dir / f"{source_name}.exe"
                
                try:
                    llc_path = find_executable('llc')
                    if llc_path:
                        obj_file = output_dir / f"{source_name}.o"
                        subprocess.run([llc_path, '-filetype=obj', str(ir_file), '-o', str(obj_file)], check=True, capture_output=True)
                        
                        # 使用clang链接为可执行文件，包含运行时库
                        compile_cmd = [clang_path, str(obj_file), '-o', str(exe_file)]
                        compile_cmd.extend(link_args)
                        subprocess.run(compile_cmd, check=True, capture_output=True)
                    else:
                        # 当llc不可用，尝试使用clang直接编译LLVM IR
                        click.echo("警告: llc不可用，尝试使用clang直接编译...")
                        # clang可以直接编译LLVM IR文件，使用 -x ir 指定输入语言
                        compile_cmd = [clang_path, '-x', 'ir', str(ir_file), '-o', str(exe_file)]
                        compile_cmd.extend(link_args)
                        subprocess.run(compile_cmd, check=True, capture_output=True)
                    
                except FileNotFoundError:
                    # 不应该发生，因为我们已经找到了clang
                    click.echo("错误: Clang不可用", err=True)
                    sys.exit(1)
                
                # 运行可执行文件
                click.echo("运行程序:")
                click.echo("-" * 50)
                # 设置环境变量跳过暂停
                env = os.environ.copy()
                env['TAIHE_NO_PAUSE'] = '1'
                # 在 Windows 上设置控制台代码页为 UTF-8
                if os.name == 'nt':
                    env['PYTHONIOENCODING'] = 'utf-8'
                
                # 使用二进制模式捕获输出，然后智能解码
                result = subprocess.run([str(exe_file)], capture_output=True, env=env)
                
                def smart_decode(data: bytes) -> str:
                    #优先尝试UTF-8，失败则使用GBK
                    if not data:
                        return ""
                    try:
                        return data.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            return data.decode('gbk', errors='replace')
                        except:
                            return data.decode('utf-8', errors='replace')
                
                stdout_text = smart_decode(result.stdout)
                stderr_text = smart_decode(result.stderr)
                
                if stdout_text:
                    click.echo(stdout_text)
                if stderr_text:
                    click.echo(stderr_text, err=True)
                click.echo("-" * 50)
                click.echo(f"程序退出码: {result.returncode}")
                
                # 显示输出文件路径
                click.echo(f"\n输出文件:")
                click.echo(f"  LLVM IR: {ir_file}")
                click.echo(f"  可执行文件: {exe_file}")
                if obj_file and obj_file.exists():
                    click.echo(f"  目标文件: {obj_file}")
            
            # 清理
            if not keep:
                if obj_file and obj_file.exists():
                    os.unlink(obj_file)
            
        except subprocess.CalledProcessError as e:
            click.echo(f"编译/链接失败: {e}", err=True)
            if e.stdout:
                click.echo(f"标准输出: {e.stdout}", err=True)
            if e.stderr:
                click.echo(f"标准错误: {e.stderr}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"执行错误: {e}", err=True)
        import traceback
        click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


@main.command()
@click.argument('source_file', type=click.Path(exists=True))
def tokens(source_file):
    """显示词法分析结果"""
    try:
        # 读取源代码（自动处理编码）
        source_code = read_source_file(source_file, verbose=False)
        
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        
        click.echo(f"文件: {source_file}")
        click.echo(f"词法单元数量: {len(tokens)}")
        click.echo("-" * 50)
        
        for i, token in enumerate(tokens):
            click.echo(f"{i:4d}: {token}")
        
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('source_file', type=click.Path(exists=True))
def ast(source_file):
    """显示抽象语法树"""
    try:
        # 读取源代码（自动处理编码）
        source_code = read_source_file(source_file, verbose=False)
        
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast_tree = parser.parse()
        
        click.echo(f"文件: {source_file}")
        click.echo("抽象语法树:")
        click.echo("-" * 50)
        
        # 简单的AST显示
        def print_ast(node, indent=0):
            if hasattr(node, 'type'):
                click.echo("  " * indent + f"{node.type}: {getattr(node, 'value', '')}")
                if hasattr(node, 'children'):
                    for child in node.children:
                        print_ast(child, indent + 1)
            else:
                click.echo("  " * indent + str(node))
        
        print_ast(ast_tree)
        
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@main.command()
def version():
    click.echo("太和编译器 v0.1.0")
    click.echo("如果你的第六感告诉你这不是最新版，先去Github看看是不是最新：https://github.com/naodingaoaoao/TaiHeLang/")


@main.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
def interpret(source_file, verbose):
    # 解释执行
    try:
        from taihe.interpreter import interpret_file
        click.echo(f"解释执行: {source_file}")
        click.echo("-" * 50)
        interpret_file(source_file)
    except Exception as e:
        click.echo(f"执行错误: {e}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()