"""LLVM IR代码生成器"""
from llvmlite import ir
from llvmlite import binding as llvm
from .ast import (
    Node, Program, Statement, ExpressionStatement, VariableDeclaration,
    DestructuringVariableDeclaration, ConstantDeclaration, FunctionDeclaration,
    ClassDeclaration, ReturnStatement, IfStatement, WhileStatement,
    ForStatement, CStyleForStatement, Block, ImportStatement, ExportStatement,
    FromImportStatement, DLLFunctionDeclaration, ImportDLLStatement,
    DLLFunctionBinding, UpdateStatement, Expression, Literal, StringInterpolation, Identifier,
    BinaryOperation, UnaryOperation, CallExpression, MemberAccess, Assignment,
    ListLiteral, TupleExpression, DictLiteral, LambdaExpression, ListComprehension,
    SubscriptExpression, SliceExpression, Parameter, TypeAnnotation, DictEntry,
    UIElement, UIAttribute, DLLLoadExpression, DLLFunctionCall,
    ConsoleCreateExpression, ConsoleMemberAccess, UpdateMemberAccess, UpdateCallExpression,
    ThisExpression, NamedArgument
)


class CodeGeneratorError(Exception):
    pass


class CodeGenerator:
    """太和语言LLVM IR代码生成器"""
    
    def __init__(self):
        # 初始化LLVM (已弃用，llvmlite 0.46.0+ 自动处理)
        # llvm.initialize()
        # llvm.initialize_native_target()
        # llvm.initialize_native_asmprinter()
        
        # 创建LLVM模块
        self.module = ir.Module(name="taihe_module")
        self.module.triple = llvm.get_default_triple()
        
        # 符号表
        self.symbols = {}
        
        # 常量名集合（用于区分变量和常量）
        self.constants = set()
        
        # 当前函数
        self.current_function = None
        self.current_basic_block = None
        self.builder = None
        
        # 字符串和格式字符串计数器
        self._str_counter = 0
        self._fmt_counter = 0
        
        # 内置函数声明
        self._declare_builtins()
    
    def _declare_builtins(self):
        """声明内置函数"""
        # 输出函数：输出(字符串)
        printf_type = ir.FunctionType(
            ir.IntType(32),  # 返回类型：int
            [ir.PointerType(ir.IntType(8))],  # 参数：char*
            var_arg=True
        )
        self.printf = ir.Function(self.module, printf_type, name="printf")
        
        # snprintf函数：安全字符串格式化
        snprintf_type = ir.FunctionType(
            ir.IntType(32),  # 返回类型：int
            [ir.PointerType(ir.IntType(8)),  # buffer
             ir.IntType(64),  # size
             ir.PointerType(ir.IntType(8))],  # format
            var_arg=True
        )
        self.sprintf = ir.Function(self.module, snprintf_type, name="snprintf")
        
        # 内存分配函数：malloc
        malloc_type = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),  # 返回类型：void*
            [ir.IntType(64)],  # 参数：size_t
        )
        self.malloc = ir.Function(self.module, malloc_type, name="malloc")
        
        # 内存释放函数：free
        free_type = ir.FunctionType(
            ir.VoidType(),  # 返回类型：void
            [ir.PointerType(ir.IntType(8))],  # 参数：void*
        )
        self.free = ir.Function(self.module, free_type, name="free")
        
        # 字符串长度函数：strlen
        strlen_type = ir.FunctionType(
            ir.IntType(64),  # 返回类型：size_t
            [ir.PointerType(ir.IntType(8))],  # 参数：char*
        )
        self.strlen = ir.Function(self.module, strlen_type, name="strlen")
        
        # 字符串比较函数：strcmp
        strcmp_type = ir.FunctionType(
            ir.IntType(32),  # 返回类型：int
            [ir.PointerType(ir.IntType(8)),  # s1
             ir.PointerType(ir.IntType(8))],  # s2
        )
        self.strcmp = ir.Function(self.module, strcmp_type, name="strcmp")
        
        # 字符串查找函数：strstr
        strstr_type = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),  # 返回类型：char*
            [ir.PointerType(ir.IntType(8)),  # haystack
             ir.PointerType(ir.IntType(8))],  # needle
        )
        self.strstr = ir.Function(self.module, strstr_type, name="strstr")
        
        # 内存复制函数：memcpy
        memcpy_type = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),  # 返回类型：void*
            [ir.PointerType(ir.IntType(8)),  # dest
             ir.PointerType(ir.IntType(8)),  # src
             ir.IntType(64)],  # size
        )
        self.memcpy = ir.Function(self.module, memcpy_type, name="memcpy")
        
        # system函数：执行系统命令
        system_type = ir.FunctionType(
            ir.IntType(32),  # 返回类型：int
            [ir.PointerType(ir.IntType(8))],  # command
        )
        self.system = ir.Function(self.module, system_type, name="system")
        
        # getenv函数：获取环境变量
        getenv_type = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),  # 返回类型：char*
            [ir.PointerType(ir.IntType(8))],  # name
        )
        self.getenv = ir.Function(self.module, getenv_type, name="getenv")
        
        # Sleep函数：暂停执行（Windows）
        sleep_type = ir.FunctionType(
            ir.VoidType(),  # 返回类型：void
            [ir.IntType(32)],  # dwMilliseconds
        )
        self.sleep = ir.Function(self.module, sleep_type, name="Sleep")
        
        # 控制台相关外部函数（运行时库）
        # _taihe_console_create(hidden, keep, command) -> console_handle
        console_create_type = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),  # 返回类型：void* (console handle)
            [ir.IntType(32),  # hidden (0=显示, 1=隐藏)
             ir.IntType(32),  # keep (0=销毁, 1=保留)
             ir.PointerType(ir.IntType(8))]  # command
        )
        self.console_create = ir.Function(self.module, console_create_type, name="_taihe_console_create")
        
        # _taihe_console_get_content(console_handle) -> content_string
        console_get_content_type = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),  # 返回类型：char*
            [ir.PointerType(ir.IntType(8))]  # console handle
        )
        self.console_get_content = ir.Function(self.module, console_get_content_type, name="_taihe_console_get_content")
        
        # _taihe_console_execute(console_handle, command) -> void
        console_execute_type = ir.FunctionType(
            ir.VoidType(),  # 返回类型：void
            [ir.PointerType(ir.IntType(8)),  # console handle
             ir.PointerType(ir.IntType(8))]  # command
        )
        self.console_execute = ir.Function(self.module, console_execute_type, name="_taihe_console_execute")
        
        # _taihe_console_destroy(console_handle) -> void
        console_destroy_type = ir.FunctionType(
            ir.VoidType(),  # 返回类型：void
            [ir.PointerType(ir.IntType(8))]  # console handle
        )
        self.console_destroy = ir.Function(self.module, console_destroy_type, name="_taihe_console_destroy")
        
        # 类型转换函数
        # 字符串(值) -> 字符串
        string_func_type = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),  # 返回类型：char*
            [ir.IntType(32)],  # 参数：整数（简化，实际可能需要多种类型）
        )
        self.字符串_func = ir.Function(self.module, string_func_type, name="字符串")
        
        # 浮点(字符串) -> 浮点数
        float_func_type = ir.FunctionType(
            ir.DoubleType(),  # 返回类型：double
            [ir.PointerType(ir.IntType(8))],  # 参数：char*
        )
        self.浮点_func = ir.Function(self.module, float_func_type, name="浮点")
        
        # 整数(字符串) -> 整数
        int_func_type = ir.FunctionType(
            ir.IntType(32),  # 返回类型：int
            [ir.PointerType(ir.IntType(8))],  # 参数：char*
        )
        self.整数_func = ir.Function(self.module, int_func_type, name="整数")
        
        # ==================== Windows API 函数 ====================
        ptr_type = ir.PointerType(ir.IntType(8))
        
        # MessageBoxA/MessageBoxW
        messagebox_type = ir.FunctionType(
            ir.IntType(32),  # 返回类型：int
            [ptr_type, ptr_type, ptr_type, ir.IntType(32)]  # hwnd, text, title, type
        )
        self.MessageBoxA = ir.Function(self.module, messagebox_type, name="MessageBoxA")
        
        # LoadLibraryA
        loadlibrary_type = ir.FunctionType(
            ptr_type,  # HMODULE
            [ptr_type]  # lpFileName
        )
        self.LoadLibraryA = ir.Function(self.module, loadlibrary_type, name="LoadLibraryA")
        
        # GetProcAddress
        getproc_type = ir.FunctionType(
            ptr_type,  # FARPROC
            [ptr_type, ptr_type]  # hModule, lpProcName
        )
        self.GetProcAddress = ir.Function(self.module, getproc_type, name="GetProcAddress")
        
        # ==================== GUI 运行时函数 ====================
        # 这些函数由 taihe_ui.dll 提供，链接时需要指定
        
        # _taihe_window_create(title, width, height) -> window_handle
        window_create_type = ir.FunctionType(
            ptr_type,  # 返回类型：void*
            [ptr_type, ir.IntType(32), ir.IntType(32)]  # title, width, height
        )
        self.taihe_window_create = ir.Function(self.module, window_create_type, name="_taihe_window_create")
        
        # _taihe_button_create(text) -> button_handle
        button_create_type = ir.FunctionType(
            ptr_type,  # 返回类型：void*
            [ptr_type]  # text
        )
        self.taihe_button_create = ir.Function(self.module, button_create_type, name="_taihe_button_create")
        
        # _taihe_textbox_create(text, readonly) -> textbox_handle
        textbox_create_type = ir.FunctionType(
            ptr_type,  # 返回类型：void*
            [ptr_type, ir.IntType(32)]  # text, readonly
        )
        self.taihe_textbox_create = ir.Function(self.module, textbox_create_type, name="_taihe_textbox_create")
        
        # _taihe_label_create(text) -> label_handle
        label_create_type = ir.FunctionType(
            ptr_type,  # 返回类型：void*
            [ptr_type]  # text
        )
        self.taihe_label_create = ir.Function(self.module, label_create_type, name="_taihe_label_create")
        
        # _taihe_grid_create(rows, cols) -> grid_handle
        grid_create_type = ir.FunctionType(
            ptr_type,  # 返回类型：void*
            [ir.IntType(32), ir.IntType(32)]  # rows, cols
        )
        self.taihe_grid_create = ir.Function(self.module, grid_create_type, name="_taihe_grid_create")
        
        # _taihe_vlayout_create() -> layout_handle
        vlayout_create_type = ir.FunctionType(
            ptr_type,  # 返回类型：void*
            []  # 无参数
        )
        self.taihe_vlayout_create = ir.Function(self.module, vlayout_create_type, name="_taihe_vlayout_create")
        
        # _taihe_component_set_style(component, style) -> void
        set_style_type = ir.FunctionType(
            ir.VoidType(),
            [ptr_type, ptr_type]  # component, style
        )
        self.taihe_set_style = ir.Function(self.module, set_style_type, name="_taihe_component_set_style")
        
        # _taihe_component_set_text(component, text) -> void
        set_text_type = ir.FunctionType(
            ir.VoidType(),
            [ptr_type, ptr_type]  # component, text
        )
        self.taihe_set_text = ir.Function(self.module, set_text_type, name="_taihe_component_set_text")
        
        # _taihe_component_get_text(component) -> char*
        get_text_type = ir.FunctionType(
            ptr_type,  # 返回类型：char*
            [ptr_type]  # component
        )
        self.taihe_get_text = ir.Function(self.module, get_text_type, name="_taihe_component_get_text")
        
        # _taihe_component_set_onclick(component, func_name, closure) -> void
        set_onclick_type = ir.FunctionType(
            ir.VoidType(),
            [ptr_type, ptr_type, ptr_type]  # component, func_name, closure
        )
        self.taihe_set_onclick = ir.Function(self.module, set_onclick_type, name="_taihe_component_set_onclick")
        
        # _taihe_layout_add(layout, component, row, col) -> void
        layout_add_type = ir.FunctionType(
            ir.VoidType(),
            [ptr_type, ptr_type, ir.IntType(32), ir.IntType(32)]  # layout, component, row, col
        )
        self.taihe_layout_add = ir.Function(self.module, layout_add_type, name="_taihe_layout_add")
        
        # _taihe_window_set_layout(window, layout) -> void
        window_set_layout_type = ir.FunctionType(
            ir.VoidType(),
            [ptr_type, ptr_type]  # window, layout
        )
        self.taihe_window_set_layout = ir.Function(self.module, window_set_layout_type, name="_taihe_window_set_layout")
        
        # _taihe_component_set_colspan(component, colspan) -> void
        set_colspan_type = ir.FunctionType(
            ir.VoidType(),
            [ptr_type, ir.IntType(32)]  # component, colspan
        )
        self.taihe_set_colspan = ir.Function(self.module, set_colspan_type, name="_taihe_component_set_colspan")
        
        # _taihe_window_show(window) -> void
        window_show_type = ir.FunctionType(
            ir.VoidType(),
            [ptr_type]  # window
        )
        self.taihe_window_show = ir.Function(self.module, window_show_type, name="_taihe_window_show")
        
        # _taihe_run() -> int
        run_type = ir.FunctionType(
            ir.IntType(32),  # 返回类型：int
            []  # 无参数
        )
        self.taihe_run = ir.Function(self.module, run_type, name="_taihe_run")
        
        # _taihe_message_box(title, message) -> int
        msgbox_type = ir.FunctionType(
            ir.IntType(32),  # 返回类型：int
            [ptr_type, ptr_type]  # title, message
        )
        self.taihe_message_box = ir.Function(self.module, msgbox_type, name="_taihe_message_box")
    
    def generate(self, ast: Program) -> str:
        """从AST生成LLVM IR"""
        # 生成代码
        for stmt in ast.statements:
            self._generate_statement(stmt)
        
        # 验证模块 (llvmlite 0.46.0+ 中已移除)
        # self.module.verify()
        
        # 返回IR字符串
        return str(self.module)
    
    def _generate_statement(self, stmt: Statement):
        """生成语句代码"""
        if isinstance(stmt, VariableDeclaration):
            self._generate_variable_declaration(stmt)
        elif isinstance(stmt, DestructuringVariableDeclaration):
            self._generate_destructuring_variable_declaration(stmt)
        elif isinstance(stmt, ConstantDeclaration):
            self._generate_constant_declaration(stmt)
        elif isinstance(stmt, DLLFunctionDeclaration):
            # 先检查 DLLFunctionDeclaration
            self._generate_dll_function_declaration(stmt)
        elif isinstance(stmt, FunctionDeclaration):
            self._generate_function_declaration(stmt)
        elif isinstance(stmt, ClassDeclaration):
            self._generate_class_declaration(stmt)
        elif isinstance(stmt, DLLFunctionBinding):
            self._generate_dll_function_binding(stmt)
        elif isinstance(stmt, ImportStatement):
            # 导入语句，将模块名存储到符号表
            module_name = stmt.module
            if stmt.alias:
                self.symbols[stmt.alias] = ('module', module_name)
            else:
                # 使用模块最后一部分作为名称
                parts = module_name.split('.')
                self.symbols[parts[-1]] = ('module', module_name)
        elif isinstance(stmt, FromImportStatement):
            # 从...导入...语句，不需要生成代码
            pass
        elif isinstance(stmt, ExpressionStatement):
            # 只有在函数内部才生成表达式代码
            if self.builder:
                self._generate_expression(stmt.expression)
        elif isinstance(stmt, ReturnStatement):
            self._generate_return_statement(stmt)
        elif isinstance(stmt, IfStatement):
            self._generate_if_statement(stmt)
        elif isinstance(stmt, WhileStatement):
            self._generate_while_statement(stmt)
        elif isinstance(stmt, ForStatement):
            self._generate_for_statement(stmt)
        elif isinstance(stmt, CStyleForStatement):
            self._generate_cstyle_for_statement(stmt)
        elif isinstance(stmt, UpdateStatement):
            self._generate_update_statement(stmt)
        elif isinstance(stmt, Block):
            for s in stmt.statements:
                self._generate_statement(s)
        else:
            raise CodeGeneratorError(f"不支持的语句类型: {type(stmt).__name__}")
    
    def _generate_variable_declaration(self, decl: VariableDeclaration):
        """生成变量声明代码"""
        import sys
        print(f"DEBUG var_decl: name={decl.name}, value={decl.value}, type_annotation={decl.type_annotation}", file=sys.stderr, flush=True)
        
        # 检查变量是否已存在于当前函数作用域中
        # 如果已存在，则执行赋值而不是声明新变量
        if self.builder is not None and decl.name in self.symbols:
            ptr = self.symbols[decl.name]
            print(f"DEBUG: {decl.name} already in symbols, ptr={ptr}, type={type(ptr)}", file=sys.stderr, flush=True)
            # 检查是否是指针类型（alloca 或全局变量）
            if isinstance(ptr, (ir.AllocaInstr, ir.GlobalVariable)):
                # 变量已存在，执行赋值
                if decl.value:
                    value = self._generate_expression(decl.value)
                    builder = self._get_builder()
                    
                    # 获取指针指向的类型
                    expected_type = ptr.type.pointee
                    
                    # 如果类型不匹配，进行转换
                    if value.type != expected_type:
                        if isinstance(expected_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                            value = builder.sitofp(value, expected_type)
                        elif isinstance(expected_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                            value = builder.fptosi(value, expected_type)
                    
                    builder.store(value, ptr)
                return
        
        # 确定变量类型
        var_type = None
        if decl.type_annotation:
            # 使用显式类型注解
            type_name = decl.type_annotation.type_name
            var_type = self._llvm_type(type_name)
            print(f"DEBUG explicit type annotation: {type_name} -> {var_type}", file=sys.stderr, flush=True)
        
        # 计算初始值
        value = None
        is_dll_lib = False  # 标记是否是DLL库句柄
        
        if decl.value:
            print(f"DEBUG generating expression for {decl.value}", file=sys.stderr, flush=True)
            
            # 特殊处理 DLLLoadExpression
            if isinstance(decl.value, DLLLoadExpression):
                is_dll_lib = True
                value = self._generate_expression(decl.value)
                print(f"DEBUG DLL lib handle: {value}, type={value.type}", file=sys.stderr, flush=True)
                # 将DLL句柄存储为元组标记
                if self.builder is None:
                    # 全局 - 暂不支持
                    raise CodeGeneratorError("DLL库句柄暂不支持全局变量")
                else:
                    # 局部变量 - 分配空间存储句柄
                    builder = self._get_builder()
                    ptr = builder.alloca(value.type)
                    builder.store(value, ptr)
                    # 使用特殊元组标记这是DLL库句柄
                    self.symbols[decl.name] = ('dll_lib', ptr, value)
                return
            
            # 特殊处理 ConsoleCreateExpression
            if isinstance(decl.value, ConsoleCreateExpression):
                value = self._generate_expression(decl.value)
                print(f"DEBUG Console handle: {value}, type={value.type}", file=sys.stderr, flush=True)
                # 将控制台句柄存储为元组标记
                if self.builder is None:
                    # 全局 - 暂不支持
                    raise CodeGeneratorError("控制台句柄暂不支持全局变量")
                else:
                    # 局部变量 - 分配空间存储句柄
                    builder = self._get_builder()
                    ptr = builder.alloca(value.type)
                    builder.store(value, ptr)
                    # 使用特殊元组标记这是控制台句柄
                    self.symbols[decl.name] = ('console', ptr, value)
                return
            
            value = self._generate_expression(decl.value)
            print(f"DEBUG generated value: {value}, type={value.type}", file=sys.stderr, flush=True)
            
            # 检查是否是类实例化（指针类型指向类结构体）
            class_name_for_var = None
            is_ui_component = False
            
            if isinstance(decl.value, CallExpression) and isinstance(decl.value.callee, Identifier):
                callee_name = decl.value.callee.name
                if callee_name in self.symbols:
                    symbol = self.symbols[callee_name]
                    if isinstance(symbol, tuple) and symbol[0] == 'class':
                        class_name_for_var = symbol[1]
            
            # 检查是否是 UI 组件创建 (ui.窗口, ui.按钮 等)
            if isinstance(decl.value, CallExpression) and isinstance(decl.value.callee, MemberAccess):
                if isinstance(decl.value.callee.object, Identifier):
                    obj_name = decl.value.callee.object.name
                    if obj_name == 'ui':
                        is_ui_component = True
            
            # 如果没有显式类型注解，则根据初始值推断类型
            if var_type is None:
                var_type = value.type
                print(f"DEBUG inferred type from value: {var_type}", file=sys.stderr, flush=True)
            
            # 检查类型是否匹配（简化处理，不进行类型转换）
            # 如果类型不匹配，记录警告但不阻止生成（后续可改进）
            if var_type != value.type:
                print(f"WARNING: 类型不匹配: 期望 {var_type}, 得到 {value.type}", file=sys.stderr, flush=True)
                # 暂时不进行类型转换，保持原值
                # 后续可以添加类型转换逻辑
        else:
            # 没有初始值，使用默认值
            if var_type is None:
                # 既没有类型注解也没有初始值，默认使用整数类型
                var_type = ir.IntType(32)
                print(f"DEBUG default type: {var_type}", file=sys.stderr, flush=True)
            
            # 根据类型创建默认值
            if isinstance(var_type, ir.IntType):
                if var_type.width == 1:  # 布尔类型
                    value = ir.Constant(var_type, 0)
                else:  # 整数类型
                    value = ir.Constant(var_type, 0)
            elif isinstance(var_type, ir.DoubleType):
                value = ir.Constant(var_type, 0.0)
            elif isinstance(var_type, ir.PointerType):
                # 指针类型，使用 null
                value = ir.Constant(var_type, None)
            else:
                value = ir.Constant(var_type, 0) if hasattr(var_type, 'width') else ir.Constant(ir.IntType(32), 0)
        
        # 确保value的类型与var_type匹配（如果需要转换，这里可以添加转换逻辑）
        # 暂时假设value的类型就是var_type
        
        # 判断是全局变量还是局部变量
        if self.builder is None:
            # 全局变量
            if not isinstance(value, ir.Constant):
                raise CodeGeneratorError("全局变量必须使用常量初始值")
            # 创建全局变量
            global_var = ir.GlobalVariable(self.module, var_type, name=decl.name)
            global_var.initializer = value
            global_var.linkage = 'internal'
            # 添加到符号表
            self.symbols[decl.name] = global_var
        else:
            # 局部变量（在函数内部）
            builder = self._get_builder()
            # 分配空间存储值
            ptr = builder.alloca(var_type)
            
            # 存储值
            builder.store(value, ptr)
            
            # 添加到符号表
            # 如果是类实例，存储类名信息以便后续方法调用
            if class_name_for_var:
                self.symbols[decl.name] = ('class_instance', ptr, class_name_for_var, var_type)
            elif is_ui_component:
                # UI 组件，标记类型
                self.symbols[decl.name] = ('ui_component', ptr, var_type)
            else:
                self.symbols[decl.name] = ptr
    
    def _generate_constant_declaration(self, decl: ConstantDeclaration):
        """生成常量声明代码"""
        import sys
        print(f"DEBUG const_decl: name={decl.name}, value={decl.value}", file=sys.stderr, flush=True)
        
        # 常量必须有初始值
        if not decl.value:
            raise CodeGeneratorError(f"常量 '{decl.name}' 必须有初始值")
        
        # 确定常量类型
        const_type = None
        if decl.type_annotation:
            type_name = decl.type_annotation.type_name
            const_type = self._llvm_type(type_name)
        
        # 计算初始值
        value = self._generate_expression(decl.value)
        
        # 如果没有显式类型注解，则根据初始值推断类型
        if const_type is None:
            const_type = value.type
        
        # 判断是全局常量还是局部常量
        if self.builder is None:
            # 全局常量
            if not isinstance(value, ir.Constant):
                # 如果不是常量，需要创建一个全局变量
                global_var = ir.GlobalVariable(self.module, const_type, name=decl.name)
                global_var.initializer = value if isinstance(value, ir.Constant) else ir.Constant(const_type, 0)
                global_var.linkage = 'internal'
                global_var.global_constant = True  # 标记为常量
                self.symbols[decl.name] = global_var
            else:
                # 创建全局常量
                global_var = ir.GlobalVariable(self.module, const_type, name=decl.name)
                global_var.initializer = value
                global_var.linkage = 'internal'
                global_var.global_constant = True  # 标记为常量
                self.symbols[decl.name] = global_var
        else:
            # 局部常量（在函数内部）- 暂时作为普通局部变量处理
            builder = self._get_builder()
            ptr = builder.alloca(const_type)
            builder.store(value, ptr)
            # 存储到符号表时标记为常量（可以用特殊方式存储）
            self.symbols[decl.name] = ptr
            self.constants.add(decl.name)  # 记录常量名
    
    def _generate_destructuring_variable_declaration(self, decl: DestructuringVariableDeclaration):
        """生成解构变量声明代码"""
        import sys
        print(f"DEBUG destructuring_var_decl: names={decl.names}, value={decl.value}, type_annotation={decl.type_annotation}", file=sys.stderr, flush=True)
        # 简化：暂时不支持，抛出错误
        raise CodeGeneratorError("解构变量声明暂不支持")
    
    def _generate_function_declaration(self, func: FunctionDeclaration):
        """生成函数声明代码"""
        # 确定返回类型
        import sys
        print(f"DEBUG func.return_type={func.return_type}", file=sys.stderr, flush=True)
        print(f"DEBUG func.body statements count: {len(func.body.statements) if func.body else 0}", file=sys.stderr, flush=True)
        if func.return_type:
            return_type = self._llvm_type(func.return_type.type_name)
        else:
            # TODO: 根据函数体推断返回类型
            # 暂时假设返回整数类型
            return_type = ir.IntType(32)
        print(f"DEBUG return_type={return_type}", file=sys.stderr, flush=True)
        
        # 确定参数类型
        param_types = []
        for param in func.parameters:
            if param.type_annotation:
                param_types.append(self._llvm_type(param.type_annotation.type_name))
            else:
                param_types.append(ir.IntType(32))  # 默认整数
        
        # 创建函数类型
        func_type = ir.FunctionType(return_type, param_types)
        
        # 将入口函数"主"重命名为"main"以便链接器识别
        llvm_name = "main" if func.name == "主" else func.name
        
        # 检查函数是否已经存在（前向声明）
        existing_func = None
        try:
            existing_func = self.module.get_global(llvm_name)
        except KeyError:
            pass
        
        if existing_func:
            # 函数已存在，使用现有的声明
            function = existing_func
            print(f"DEBUG: 使用已存在的函数声明: {llvm_name}")
        else:
            # 创建新函数
            function = ir.Function(self.module, func_type, name=llvm_name)
        
        # 将函数对象存储在符号表中，使用原始名称作为键
        self.symbols[func.name] = function
        
        # 设置参数名
        for i, param in enumerate(func.parameters):
            function.args[i].name = param.name
        
        # 创建入口基本块
        entry_block = function.append_basic_block(name="entry")
        builder = ir.IRBuilder(entry_block)
        
        # 保存当前状态
        old_function = self.current_function
        old_builder = self.current_basic_block
        old_builder_instance = self.builder
        old_symbols = self.symbols.copy()  # 保存符号表状态
        
        self.current_function = function
        self.current_basic_block = entry_block
        self.builder = builder
        
        # 添加参数到符号表
        for i, param in enumerate(func.parameters):
            param_ptr = builder.alloca(param_types[i])
            builder.store(function.args[i], param_ptr)
            self.symbols[param.name] = param_ptr
        
        # 如果是main函数，添加初始化代码
        if llvm_name == "main":
            self._add_main_init(builder)
        
        # 生成函数体
        self._generate_statement(func.body)
        
        # 如果没有返回语句，添加隐式返回
        if not builder.block.is_terminated:
            # 如果是main函数，在返回前添加 system("pause")
            if llvm_name == "main":
                self._add_pause_before_exit(builder)
            
            if return_type == ir.VoidType():
                builder.ret_void()
            elif isinstance(return_type, ir.IntType):
                if return_type.width == 1:  # 布尔类型
                    builder.ret(ir.Constant(return_type, 0))
                else:  # 整数类型
                    builder.ret(ir.Constant(return_type, 0))
            elif isinstance(return_type, ir.DoubleType):
                builder.ret(ir.Constant(return_type, 0.0))
            elif isinstance(return_type, ir.PointerType):
                builder.ret(ir.Constant(return_type, None))
            else:
                # 默认返回0
                builder.ret(ir.Constant(ir.IntType(32), 0))
        
        # 恢复状态
        self.current_function = old_function
        self.current_basic_block = old_builder
        self.builder = old_builder_instance
        self.symbols = old_symbols  # 恢复符号表状态
    
    def _generate_class_declaration(self, cls: ClassDeclaration):
        """生成类声明代码"""
        import sys
        print(f"DEBUG _generate_class_declaration: name={cls.name}", file=sys.stderr, flush=True)
        
        # 收集成员变量信息
        member_vars = []
        member_methods = []
        
        for member in cls.members:
            if isinstance(member, VariableDeclaration):
                member_vars.append(member)
            elif isinstance(member, FunctionDeclaration):
                member_methods.append(member)
        
        # 创建类结构体类型
        # 结构体包含所有成员变量
        member_types = []
        member_names = []
        
        for var in member_vars:
            if var.type_annotation:
                var_type = self._llvm_type(var.type_annotation.type_name)
            else:
                var_type = ir.IntType(32)  # 默认类型
            member_types.append(var_type)
            member_names.append(var.name)
        
        # 创建结构体类型（使用 IdentifiedStructType 以支持命名）
        class_type = self.module.context.get_identified_type(f"class_{cls.name}")
        class_type.set_body(*member_types)
        
        # 存储类信息
        if not hasattr(self, 'class_info'):
            self.class_info = {}
        
        self.class_info[cls.name] = {
            'type': class_type,
            'member_vars': member_vars,
            'member_names': member_names,
            'member_types': member_types,
            'methods': {}
        }
        
        # 生成方法函数 - 第一阶段：创建所有方法的原型
        method_info_list = []
        for method in member_methods:
            method_name = f"{cls.name}_{method.name}"
            print(f"DEBUG: Creating method prototype {method_name}", file=sys.stderr, flush=True)
            
            # 确定返回类型
            if method.return_type:
                return_type = self._llvm_type(method.return_type.type_name)
            else:
                return_type = ir.IntType(32)
            
            # 方法参数：第一个参数是 `这` (this指针)
            param_types = [ir.PointerType(class_type)]  # this 指针
            for param in method.parameters:
                if param.type_annotation:
                    param_types.append(self._llvm_type(param.type_annotation.type_name))
                else:
                    param_types.append(ir.IntType(32))
            
            # 创建函数类型
            func_type = ir.FunctionType(return_type, param_types)
            
            # 创建函数
            function = ir.Function(self.module, func_type, name=method_name)
            
            # 存储方法信息
            self.class_info[cls.name]['methods'][method.name] = {
                'function': function,
                'return_type': return_type,
                'param_types': param_types[1:],  # 不包括this
                'parameters': method.parameters
            }
            
            # 设置参数名
            function.args[0].name = "这"  # this 参数
            for i, param in enumerate(method.parameters):
                function.args[i + 1].name = param.name
            
            # 保存方法信息以便后续生成方法体
            method_info_list.append({
                'method': method,
                'function': function,
                'return_type': return_type,
                'param_types': param_types,
                'class_type': class_type
            })
        
        # 生成方法函数 - 第二阶段：生成所有方法的方法体
        for method_info in method_info_list:
            method = method_info['method']
            function = method_info['function']
            return_type = method_info['return_type']
            param_types = method_info['param_types']
            class_type = method_info['class_type']
            
            print(f"DEBUG: Generating method body for {function.name}", file=sys.stderr, flush=True)
            
            # 创建入口基本块
            entry_block = function.append_basic_block(name="entry")
            builder = ir.IRBuilder(entry_block)
            
            # 保存当前状态
            old_function = self.current_function
            old_builder = self.current_basic_block
            old_builder_instance = self.builder
            old_symbols = self.symbols.copy()
            
            self.current_function = function
            self.current_basic_block = entry_block
            self.builder = builder
            
            # 添加 this 指针到符号表
            this_ptr = builder.alloca(ir.PointerType(class_type))
            builder.store(function.args[0], this_ptr)
            self.symbols['这'] = this_ptr
            
            # 添加参数到符号表
            for i, param in enumerate(method.parameters):
                param_ptr = builder.alloca(param_types[i + 1])
                builder.store(function.args[i + 1], param_ptr)
                self.symbols[param.name] = param_ptr
            
            # 生成方法体
            self._generate_statement(method.body)
            
            # 如果没有返回语句，添加隐式返回
            if not builder.block.is_terminated:
                if return_type == ir.VoidType():
                    builder.ret_void()
                else:
                    builder.ret(ir.Constant(return_type, 0))
            
            # 恢复状态
            self.current_function = old_function
            self.current_basic_block = old_builder
            self.builder = old_builder_instance
            self.symbols = old_symbols
        
        # 将类名添加到符号表（指向类信息）
        self.symbols[cls.name] = ('class', cls.name)
    
    def _generate_dll_function_declaration(self, decl: 'DLLFunctionDeclaration'):
        """生成DLL导出函数代码"""
        import sys
        
        # DLL函数与普通函数类似，但需要导出
        # 先生成普通函数（大部分逻辑复用）
        
        # 确定返回类型
        if decl.return_type:
            return_type = self._llvm_type(decl.return_type.type_name)
        else:
            # TODO: 根据函数体推断返回类型
            return_type = ir.IntType(32)
        print(f"DEBUG DLL func.return_type={return_type}", file=sys.stderr, flush=True)
        
        # 确定参数类型
        param_types = []
        for param in decl.parameters:
            if param.type_annotation:
                param_types.append(self._llvm_type(param.type_annotation.type_name))
            else:
                param_types.append(ir.IntType(32))  # 默认整数
        
        # 创建函数类型
        func_type = ir.FunctionType(return_type, param_types)
        
        # 创建新函数
        function = ir.Function(self.module, func_type, name=decl.name)
        
        # 设置为 dllexport（在 Windows 上导出）
        function.linkage = 'dllexport'
        
        # 将函数对象存储在符号表中
        self.symbols[decl.name] = function
        
        # 设置参数名
        for i, param in enumerate(decl.parameters):
            function.args[i].name = param.name
        
        # 创建入口基本块
        entry_block = function.append_basic_block(name="entry")
        builder = ir.IRBuilder(entry_block)
        
        # 保存当前状态
        old_function = self.current_function
        old_builder = self.current_basic_block
        old_builder_instance = self.builder
        old_symbols = self.symbols.copy()
        
        self.current_function = function
        self.current_basic_block = entry_block
        self.builder = builder
        
        # 添加参数到符号表
        for i, param in enumerate(decl.parameters):
            param_ptr = builder.alloca(param_types[i])
            builder.store(function.args[i], param_ptr)
            self.symbols[param.name] = param_ptr
        
        # 生成函数体
        self._generate_statement(decl.body)
        
        # 如果没有返回语句，添加隐式返回
        if not builder.block.is_terminated:
            if return_type == ir.VoidType():
                builder.ret_void()
            elif isinstance(return_type, ir.IntType):
                builder.ret(ir.Constant(return_type, 0))
            elif isinstance(return_type, ir.DoubleType):
                builder.ret(ir.Constant(return_type, 0.0))
            else:
                builder.ret(ir.Constant(ir.IntType(32), 0))
        
        # 恢复状态
        self.current_function = old_function
        self.current_basic_block = old_builder
        self.builder = old_builder_instance
        self.symbols = old_symbols
        
        # 记录导出的函数
        if not hasattr(self, 'dll_exports'):
            self.dll_exports = []
        self.dll_exports.append(decl.name)
    
    def _generate_dll_function_binding(self, stmt: 'DLLFunctionBinding'):
        """生成DLL函数绑定代码"""
        builder = self._get_builder()
        
        # 存储函数签名信息，用于后续调用
        if not hasattr(self, 'dll_bindings'):
            self.dll_bindings = {}
        
        key = f"{stmt.lib_name}.{stmt.func_name}"
        self.dll_bindings[key] = {
            'param_types': stmt.param_types,
            'return_type': stmt.return_type
        }
        
        # 将绑定信息存储到符号表（用于标记这是DLL函数）
        # 格式：dll_func_{lib_name}_{func_name}
        binding_name = f"dll_func_{stmt.lib_name}_{stmt.func_name}"
        # 标记这是一个DLL函数绑定
        self.symbols[binding_name] = ('dll_binding', stmt.lib_name, stmt.func_name)
    
    def _generate_return_statement(self, stmt: ReturnStatement):
        """生成返回语句代码"""
        print(f"DEBUG: current_basic_block={self.current_basic_block}, current_function={self.current_function}")
        builder = self._get_builder()
        
        # 如果是main函数，在返回前添加暂停
        if self.current_function and self.current_function.name == "main":
            self._add_pause_before_exit(builder)
        
        if stmt.value:
            value = self._generate_expression(stmt.value)
            
            # 检查返回类型是否匹配函数返回类型
            if self.current_function:
                expected_type = self.current_function.function_type.return_type
                if value.type != expected_type:
                    # 尝试进行类型转换
                    if isinstance(expected_type, ir.IntType) and isinstance(value.type, ir.PointerType):
                        # 指针转整数
                        value = builder.ptrtoint(value, expected_type)
                    elif isinstance(expected_type, ir.PointerType) and isinstance(value.type, ir.IntType):
                        # 整数转指针
                        value = builder.inttoptr(value, expected_type)
                    elif isinstance(expected_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                        # 整数转浮点
                        value = builder.sitofp(value, expected_type)
                    elif isinstance(expected_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                        # 浮点转整数
                        value = builder.fptosi(value, expected_type)
            
            builder.ret(value)
        else:
            # 没有返回值时，检查函数返回类型
            if self.current_function:
                expected_type = self.current_function.function_type.return_type
                if expected_type == ir.VoidType():
                    builder.ret_void()
                else:
                    # 返回该类型的默认值
                    if isinstance(expected_type, ir.IntType):
                        builder.ret(ir.Constant(expected_type, 0))
                    elif isinstance(expected_type, ir.DoubleType):
                        builder.ret(ir.Constant(expected_type, 0.0))
                    elif isinstance(expected_type, ir.PointerType):
                        builder.ret(ir.Constant(expected_type, None))
                    else:
                        builder.ret_void()
            else:
                builder.ret_void()
    
    def _generate_if_statement(self, stmt: IfStatement):
        """生成条件语句代码"""
        builder = self._get_builder()
        
        # 生成条件
        condition = self._generate_expression(stmt.condition)
        
        # 将条件转换为 i1 类型
        if isinstance(condition.type, ir.IntType):
            if condition.type.width != 1:
                # 整数转布尔：非零为真
                condition = builder.icmp_signed('!=', condition, ir.Constant(condition.type, 0))
        elif isinstance(condition.type, ir.DoubleType):
            # 浮点转布尔：非零为真
            condition = builder.fcmp_ordered('!=', condition, ir.Constant(ir.DoubleType(), 0.0))
        elif isinstance(condition.type, ir.PointerType):
            # 指针转布尔：非空为真
            null_ptr = ir.Constant(condition.type, None)
            condition = builder.icmp_signed('!=', condition, null_ptr)
        
        # 创建基本块
        then_block = self.current_function.append_basic_block(name="then")
        else_block = self.current_function.append_basic_block(name="else")
        merge_block = self.current_function.append_basic_block(name="merge")
        
        # 条件分支
        builder.cbranch(condition, then_block, else_block)
        
        # 生成then块
        builder.position_at_end(then_block)
        self._generate_statement(stmt.then_branch)
        if not builder.block.is_terminated:
            builder.branch(merge_block)
        
        # 生成else块
        builder.position_at_end(else_block)
        if stmt.else_branch:
            self._generate_statement(stmt.else_branch)
        if not builder.block.is_terminated:
            builder.branch(merge_block)
        
        # 继续在merge块生成
        builder.position_at_end(merge_block)
    
    def _generate_while_statement(self, stmt: WhileStatement):
        """生成循环语句代码"""
        builder = self._get_builder()
        
        # 创建基本块
        condition_block = self.current_function.append_basic_block(name="while.condition")
        body_block = self.current_function.append_basic_block(name="while.body")
        after_block = self.current_function.append_basic_block(name="while.after")
        
        # 跳转到条件块
        builder.branch(condition_block)
        
        # 生成条件块
        builder.position_at_end(condition_block)
        condition = self._generate_expression(stmt.condition)
        
        # 将条件转换为 i1 类型
        if isinstance(condition.type, ir.IntType):
            if condition.type.width != 1:
                condition = builder.icmp_signed('!=', condition, ir.Constant(condition.type, 0))
        elif isinstance(condition.type, ir.DoubleType):
            condition = builder.fcmp_ordered('!=', condition, ir.Constant(ir.DoubleType(), 0.0))
        elif isinstance(condition.type, ir.PointerType):
            null_ptr = ir.Constant(condition.type, None)
            condition = builder.icmp_signed('!=', condition, null_ptr)
        
        builder.cbranch(condition, body_block, after_block)
        
        # 生成循环体
        builder.position_at_end(body_block)
        self._generate_statement(stmt.body)
        if not builder.block.is_terminated:
            builder.branch(condition_block)
        
        # 继续在after块生成
        builder.position_at_end(after_block)
    
    def _generate_for_statement(self, stmt: ForStatement):
        """生成for循环语句代码"""
        builder = self._get_builder()
        
        # 解析可迭代对象（简化：只支持 范围(n) 或 范围(start, end)）
        start_value = ir.Constant(ir.IntType(32), 0)
        end_value = ir.Constant(ir.IntType(32), 10)  # 默认值
        
        if isinstance(stmt.iterable, CallExpression):
            if isinstance(stmt.iterable.callee, Identifier) and stmt.iterable.callee.name == '范围':
                args = stmt.iterable.arguments
                if len(args) == 1:
                    # 范围(n) -> 0 到 n-1
                    end_value = self._generate_expression(args[0])
                elif len(args) >= 2:
                    # 范围(start, end) -> start 到 end-1
                    start_value = self._generate_expression(args[0])
                    end_value = self._generate_expression(args[1])
        
        # 为循环变量分配内存（在入口块）
        var_ptr = builder.alloca(ir.IntType(32), name=stmt.variable)
        self.symbols[stmt.variable] = var_ptr
        
        # 初始化循环变量
        builder.store(start_value, var_ptr)
        
        # 创建基本块
        condition_block = self.current_function.append_basic_block(name="for.condition")
        body_block = self.current_function.append_basic_block(name="for.body")
        after_block = self.current_function.append_basic_block(name="for.after")
        
        # 跳转到条件块
        builder.branch(condition_block)
        
        # 生成条件块：检查 i < end
        builder.position_at_end(condition_block)
        current = builder.load(var_ptr)
        condition = builder.icmp_signed('<', current, end_value)
        builder.cbranch(condition, body_block, after_block)
        
        # 生成循环体
        builder.position_at_end(body_block)
        self._generate_statement(stmt.body)
        
        # 更新循环变量：i = i + 1
        current = builder.load(var_ptr)
        next_val = builder.add(current, ir.Constant(ir.IntType(32), 1))
        builder.store(next_val, var_ptr)
        
        if not builder.block.is_terminated:
            builder.branch(condition_block)
        
        # 继续在after块生成
        builder.position_at_end(after_block)
    
    def _generate_cstyle_for_statement(self, stmt: CStyleForStatement):
        """生成C风格for循环语句代码"""
        builder = self._get_builder()
        
        # 生成初始化语句
        if stmt.init:
            self._generate_statement(stmt.init)
        
        # 创建基本块
        condition_block = self.current_function.append_basic_block(name="cfor.condition")
        body_block = self.current_function.append_basic_block(name="cfor.body")
        update_block = self.current_function.append_basic_block(name="cfor.update")
        after_block = self.current_function.append_basic_block(name="cfor.after")
        
        # 跳转到条件块
        builder.branch(condition_block)
        
        # 生成条件块
        builder.position_at_end(condition_block)
        condition = self._generate_expression(stmt.condition)
        builder.cbranch(condition, body_block, after_block)
        
        # 生成循环体
        builder.position_at_end(body_block)
        self._generate_statement(stmt.body)
        if not builder.block.is_terminated:
            builder.branch(update_block)
        
        # 生成更新块
        builder.position_at_end(update_block)
        if stmt.update:
            self._generate_statement(stmt.update)
        if not builder.block.is_terminated:
            builder.branch(condition_block)
        
        # 继续在after块生成
        builder.position_at_end(after_block)
    
    def _generate_expression(self, expr: Expression) -> ir.Value:
        """生成表达式代码"""
        if isinstance(expr, Literal):
            return self._generate_literal(expr)
        elif isinstance(expr, StringInterpolation):
            return self._generate_string_interpolation(expr)
        elif isinstance(expr, Identifier):
            return self._generate_identifier(expr)
        elif isinstance(expr, ThisExpression):
            return self._generate_this_expression(expr)
        elif isinstance(expr, BinaryOperation):
            return self._generate_binary_operation(expr)
        elif isinstance(expr, UnaryOperation):
            return self._generate_unary_operation(expr)
        elif isinstance(expr, CallExpression):
            return self._generate_call_expression(expr)
        elif isinstance(expr, MemberAccess):
            return self._generate_member_access(expr)
        elif isinstance(expr, Assignment):
            return self._generate_assignment(expr)
        elif isinstance(expr, ListLiteral):
            return self._generate_list_literal(expr)
        elif isinstance(expr, ListComprehension):
            return self._generate_list_comprehension(expr)
        elif isinstance(expr, TupleExpression):
            return self._generate_tuple_expression(expr)
        elif isinstance(expr, SubscriptExpression):
            return self._generate_subscript_expression(expr)
        elif isinstance(expr, DictLiteral):
            return self._generate_dict_literal(expr)
        elif isinstance(expr, DLLLoadExpression):
            return self._generate_dll_load_expression(expr)
        elif isinstance(expr, DLLFunctionCall):
            return self._generate_dll_function_call(expr)
        elif isinstance(expr, ConsoleCreateExpression):
            return self._generate_console_create_expression(expr)
        elif isinstance(expr, ConsoleMemberAccess):
            return self._generate_console_member_access(expr)
        elif isinstance(expr, UpdateMemberAccess):
            return self._generate_update_member_access(expr)
        elif isinstance(expr, UpdateCallExpression):
            return self._generate_update_call_expression(expr)
        elif isinstance(expr, LambdaExpression):
            return self._generate_lambda_expression(expr)
        else:
            raise CodeGeneratorError(f"不支持的表达式类型: {type(expr).__name__}")
    
    def _generate_literal(self, lit: Literal) -> ir.Value:
        """生成字面量代码"""
        value = lit.value
        
        if isinstance(value, int):
            return ir.Constant(ir.IntType(32), value)
        elif isinstance(value, float):
            return ir.Constant(ir.DoubleType(), value)
        elif isinstance(value, str):
            # 创建全局字符串常量
            # 计算UTF-8编码的字节长度
            byte_len = len(value.encode('utf-8'))
            str_const = ir.Constant(ir.ArrayType(ir.IntType(8), byte_len + 1),
                                   bytearray(value.encode('utf-8') + b'\0'))
            global_str = ir.GlobalVariable(self.module, str_const.type, name=f"str.{self._str_counter}")
            global_str.linkage = 'internal'
            global_str.global_constant = True
            global_str.initializer = str_const
            self._str_counter += 1
            
            # 返回字符串指针
            builder = self._get_builder()
            return builder.gep(global_str, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
        elif isinstance(value, bool):
            return ir.Constant(ir.IntType(1), 1 if value else 0)
        elif value is None:
            # 空指针
            return ir.Constant(ir.PointerType(ir.IntType(8)), None)
        else:
            return ir.Constant(ir.IntType(32), 0)
    
    def _generate_string_interpolation(self, expr: StringInterpolation) -> ir.Value:
        """生成字符串插值代码，如 "你好{name}" """
        builder = self._get_builder()
        
        if not expr.parts:
            # 空字符串
            return self._create_string_constant("")
        
        # 处理每个部分，将结果拼接
        result = None
        
        for part in expr.parts:
            if isinstance(part, str):
                # 字符串字面量部分
                part_value = self._create_string_constant(part)
            elif isinstance(part, Expression):
                # 表达式部分，需要转换为字符串
                expr_value = self._generate_expression(part)
                part_value = self._value_to_string(expr_value, builder)
            else:
                continue
            
            if result is None:
                result = part_value
            else:
                # 拼接字符串
                result = self._concat_strings(result, part_value, builder)
        
        return result if result else self._create_string_constant("")
    
    def _value_to_string(self, value: ir.Value, builder: ir.IRBuilder) -> ir.Value:
        """将值转换为字符串"""
        # 检查值的类型
        if isinstance(value.type, ir.PointerType) and value.type.pointee == ir.IntType(8):
            # 已经是字符串指针
            return value
        elif isinstance(value.type, ir.IntType):
            # 整数转字符串
            buffer_size = ir.Constant(ir.IntType(64), 21)
            buffer = builder.call(self.malloc, [buffer_size])
            fmt_str = self._create_string_constant("%d")
            builder.call(self.sprintf, [buffer, buffer_size, fmt_str, value])
            return buffer
        elif isinstance(value.type, ir.DoubleType):
            # 浮点数转字符串
            buffer_size = ir.Constant(ir.IntType(64), 32)
            buffer = builder.call(self.malloc, [buffer_size])
            fmt_str = self._create_string_constant("%g")
            builder.call(self.sprintf, [buffer, buffer_size, fmt_str, value])
            return buffer
        else:
            # 默认：尝试作为字符串处理
            return value
    
    def _concat_strings(self, left: ir.Value, right: ir.Value, builder: ir.IRBuilder) -> ir.Value:
        """拼接两个字符串"""
        left_len = self._get_string_length(left)
        right_len = self._get_string_length(right)
        
        total_len = builder.add(left_len, right_len)
        total_len_with_null = builder.add(total_len, ir.Constant(ir.IntType(64), 1))
        result_buffer = builder.call(self.malloc, [total_len_with_null])
        
        # 复制左字符串
        self._copy_string(builder, result_buffer, left, 0)
        # 复制右字符串
        self._copy_string(builder, result_buffer, right, left_len)
        
        # 添加null终止符
        total_len_i32 = builder.trunc(total_len, ir.IntType(32))
        null_ptr = builder.gep(result_buffer, [total_len_i32])
        builder.store(ir.Constant(ir.IntType(8), 0), null_ptr)
        
        return result_buffer
    
    def _generate_identifier(self, ident: Identifier) -> ir.Value:
        """生成标识符代码"""
        import sys
        print(f"DEBUG _generate_identifier: name={ident.name}, symbols keys={list(self.symbols.keys())}", file=sys.stderr, flush=True)
        name = ident.name
        
        if name not in self.symbols:
            raise CodeGeneratorError(f"未定义的标识符: {name}")
        
        symbol = self.symbols[name]
        builder = self._get_builder()
        
        # 检查是否是类实例
        if isinstance(symbol, tuple) and symbol[0] == 'class_instance':
            # symbol = ('class_instance', ptr, class_name, var_type)
            ptr = symbol[1]
            print(f"DEBUG _generate_identifier: class_instance ptr={ptr}", file=sys.stderr, flush=True)
            result = builder.load(ptr)
            print(f"DEBUG _generate_identifier: result={result}", file=sys.stderr, flush=True)
            return result
        
        # 普通变量
        ptr = symbol
        print(f"DEBUG _generate_identifier: ptr={ptr}, builder.block={builder.block}", file=sys.stderr, flush=True)
        result = builder.load(ptr)
        print(f"DEBUG _generate_identifier: result={result}", file=sys.stderr, flush=True)
        return result
    
    def _generate_this_expression(self, expr: ThisExpression) -> ir.Value:
        """生成this表达式代码"""
        # "这" 关键字指向当前类实例
        # 查找符号表中的 "这" 变量
        if '这' not in self.symbols:
            raise CodeGeneratorError("在非类方法中使用 '这' 关键字")
        
        ptr = self.symbols['这']
        builder = self._get_builder()
        return builder.load(ptr)
    
    def _add_pause_before_exit(self, builder: ir.IRBuilder):
        """在程序退出前添加暂停功能（Windows下双击exe时防止闪退）"""
        # 检测环境变量 TAIHE_NO_PAUSE，如果设置则跳过暂停
        env_name = self._create_string_constant("TAIHE_NO_PAUSE")
        env_value = builder.call(self.getenv, [env_name])
        
        # 如果 getenv 返回非空指针，说明环境变量被设置，跳过暂停
        null_ptr = ir.Constant(ir.PointerType(ir.IntType(8)), None)
        should_pause = builder.icmp_signed('!=', env_value, null_ptr)
        
        # 创建条件分支
        skip_block = self.current_function.append_basic_block(name="skip_pause")
        pause_block = self.current_function.append_basic_block(name="do_pause")
        continue_block = self.current_function.append_basic_block(name="after_pause")
        
        builder.cbranch(should_pause, skip_block, pause_block)
        
        # pause_block: 执行暂停
        builder.position_at_end(pause_block)
        
        # 输出分隔线
        separator = "\n" + "-" * 50 + "\n"
        sep_str = self._create_string_constant(separator)
        
        # 输出"按任意键退出"
        pause_msg = "按任意键退出. . ."
        pause_str = self._create_string_constant(pause_msg)
        
        # 调用printf输出
        builder.call(self.printf, [sep_str])
        builder.call(self.printf, [pause_str])
        
        # 调用system("pause")等待用户按键
        cmd_str = self._create_string_constant("pause >nul")
        builder.call(self.system, [cmd_str])
        
        builder.branch(continue_block)
        
        # skip_block: 跳过暂停
        builder.position_at_end(skip_block)
        builder.branch(continue_block)
        
        # continue_block: 继续
        builder.position_at_end(continue_block)
    
    def _add_main_init(self, builder: ir.IRBuilder):
        """在main函数开始时添加初始化代码"""
        # 设置控制台代码页为UTF-8（解决中文乱码问题）
        chcp_cmd = self._create_string_constant("chcp 65001 >nul 2>&1")
        builder.call(self.system, [chcp_cmd])
    
    def _create_string_constant(self, string_value: str) -> ir.Value:
        """创建字符串常量并返回指针"""
        # 计算UTF-8编码的字节长度
        byte_len = len(string_value.encode('utf-8'))
        str_const = ir.Constant(ir.ArrayType(ir.IntType(8), byte_len + 1),
                               bytearray(string_value.encode('utf-8') + b'\0'))
        global_str = ir.GlobalVariable(self.module, str_const.type, name=f"str.{self._str_counter}")
        global_str.linkage = 'internal'
        global_str.global_constant = True
        global_str.initializer = str_const
        self._str_counter += 1
        
        # 返回字符串指针
        builder = self._get_builder()
        return builder.gep(global_str, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
    
    def _get_string_length(self, str_ptr: ir.Value) -> ir.Value:
        """计算以null结尾的字符串长度"""
        builder = self._get_builder()
        # 使用已声明的strlen函数
        return builder.call(self.strlen, [str_ptr])
    
    def _copy_string(self, builder: ir.IRBuilder, dest_ptr: ir.Value, src_ptr: ir.Value, offset: ir.Value) -> None:
        """复制字符串到目标缓冲区（带偏移量）"""
        # 获取源字符串长度（不包括null终止符）
        src_len = self._get_string_length(src_ptr)
        
        # 计算目标地址（dest_ptr + offset）
        # 处理offset：可能是ir.Value或Python整数
        if isinstance(offset, ir.Value):
            # 将offset从i64转换为i32（gep期望i32索引）
            offset_i32 = builder.trunc(offset, ir.IntType(32)) if offset.type != ir.IntType(32) else offset
        else:
            # offset是Python整数，创建常量
            offset_i32 = ir.Constant(ir.IntType(32), offset)
        
        dest_with_offset = builder.gep(dest_ptr, [offset_i32])
        
        # 调用已声明的memcpy函数
        builder.call(self.memcpy, [dest_with_offset, src_ptr, src_len])
    
    def _generate_binary_operation(self, op: BinaryOperation) -> ir.Value:
        """生成二元运算代码"""
        left = self._generate_expression(op.left)
        right = self._generate_expression(op.right)
        builder = self._get_builder()
        
        # 类型检查（简化）
        if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.IntType):
            if op.operator == '+':
                return builder.add(left, right)
            elif op.operator == '-':
                return builder.sub(left, right)
            elif op.operator == '*':
                return builder.mul(left, right)
            elif op.operator == '/':
                return builder.sdiv(left, right)
            elif op.operator == '%':
                return builder.srem(left, right)
            elif op.operator == '==':
                return builder.icmp_signed('==', left, right)
            elif op.operator == '!=':
                return builder.icmp_signed('!=', left, right)
            elif op.operator == '<':
                return builder.icmp_signed('<', left, right)
            elif op.operator == '<=':
                return builder.icmp_signed('<=', left, right)
            elif op.operator == '>':
                return builder.icmp_signed('>', left, right)
            elif op.operator == '>=':
                return builder.icmp_signed('>=', left, right)
            elif op.operator == '&&':
                # 逻辑与
                left_bool = builder.trunc(left, ir.IntType(1))
                right_bool = builder.trunc(right, ir.IntType(1))
                return builder.and_(left_bool, right_bool)
            elif op.operator == '||':
                # 逻辑或
                left_bool = builder.trunc(left, ir.IntType(1))
                right_bool = builder.trunc(right, ir.IntType(1))
                return builder.or_(left_bool, right_bool)
        
        # 浮点运算
        elif isinstance(left.type, ir.DoubleType) and isinstance(right.type, ir.DoubleType):
            if op.operator == '+':
                return builder.fadd(left, right)
            elif op.operator == '-':
                return builder.fsub(left, right)
            elif op.operator == '*':
                return builder.fmul(left, right)
            elif op.operator == '/':
                return builder.fdiv(left, right)
            elif op.operator == '==':
                return builder.fcmp_ordered('==', left, right)
            elif op.operator == '!=':
                return builder.fcmp_ordered('!=', left, right)
            elif op.operator == '<':
                return builder.fcmp_ordered('<', left, right)
            elif op.operator == '<=':
                return builder.fcmp_ordered('<=', left, right)
            elif op.operator == '>':
                return builder.fcmp_ordered('>', left, right)
            elif op.operator == '>=':
                return builder.fcmp_ordered('>=', left, right)
        
        # 混合类型运算：整数与浮点数
        left_is_int = isinstance(left.type, ir.IntType)
        right_is_int = isinstance(right.type, ir.IntType)
        left_is_double = isinstance(left.type, ir.DoubleType)
        right_is_double = isinstance(right.type, ir.DoubleType)
        
        if (left_is_int and right_is_double) or (left_is_double and right_is_int):
            # 将整数转换为浮点数
            if left_is_int:
                left = builder.sitofp(left, ir.DoubleType())
            if right_is_int:
                right = builder.sitofp(right, ir.DoubleType())
            
            # 现在两个都是 double，执行浮点运算
            if op.operator == '+':
                return builder.fadd(left, right)
            elif op.operator == '-':
                return builder.fsub(left, right)
            elif op.operator == '*':
                return builder.fmul(left, right)
            elif op.operator == '/':
                return builder.fdiv(left, right)
            elif op.operator == '==':
                return builder.fcmp_ordered('==', left, right)
            elif op.operator == '!=':
                return builder.fcmp_ordered('!=', left, right)
            elif op.operator == '<':
                return builder.fcmp_ordered('<', left, right)
            elif op.operator == '<=':
                return builder.fcmp_ordered('<=', left, right)
            elif op.operator == '>':
                return builder.fcmp_ordered('>', left, right)
            elif op.operator == '>=':
                return builder.fcmp_ordered('>=', left, right)
        
        # 字符串比较
        left_is_str = isinstance(left.type, ir.PointerType) and left.type.pointee == ir.IntType(8)
        right_is_str = isinstance(right.type, ir.PointerType) and right.type.pointee == ir.IntType(8)
        if left_is_str and right_is_str:
            if op.operator == '==':
                # 调用 strcmp 比较字符串
                result = builder.call(self.strcmp, [left, right])
                # strcmp 返回 0 表示相等
                return builder.icmp_signed('==', result, ir.Constant(ir.IntType(32), 0))
            elif op.operator == '!=':
                result = builder.call(self.strcmp, [left, right])
                return builder.icmp_signed('!=', result, ir.Constant(ir.IntType(32), 0))
        
        # 字符串拼接
        if op.operator == '+':
            # 检查是否涉及字符串
            left_is_str = isinstance(left.type, ir.PointerType) and left.type.pointee == ir.IntType(8)
            right_is_str = isinstance(right.type, ir.PointerType) and right.type.pointee == ir.IntType(8)
            
            # 如果左操作数是字符串，右操作数是整数，需要将整数转换为字符串
            if left_is_str and isinstance(right.type, ir.IntType):
                # 将整数转换为字符串
                # 首先分配缓冲区（足够容纳整数，最大约20位）
                builder = self._get_builder()
                # 分配21字节（20位数字 + 符号 + null终止符）
                buffer_size = ir.Constant(ir.IntType(64), 21)
                buffer = builder.call(self.malloc, [buffer_size])
                
                # 创建格式化字符串 "%d"
                fmt_str = self._create_string_constant("%d")
                
                # 调用 snprintf(buffer, 21, "%d", right)
                builder.call(self.sprintf, [buffer, buffer_size, fmt_str, right])
                
                # 现在拼接两个字符串
                # 计算左字符串长度
                left_len = self._get_string_length(left)
                right_len = self._get_string_length(buffer)
                
                # 分配新缓冲区（左长度 + 右长度 + 1）
                total_len = builder.add(left_len, right_len)
                total_len_with_null = builder.add(total_len, ir.Constant(ir.IntType(64), 1))
                result_buffer = builder.call(self.malloc, [total_len_with_null])
                
                # 复制左字符串
                self._copy_string(builder, result_buffer, left, 0)
                # 复制右字符串
                self._copy_string(builder, result_buffer, buffer, left_len)
                
                # 添加null终止符（位置是 total_len）
                total_len_i32 = builder.trunc(total_len, ir.IntType(32))
                null_ptr = builder.gep(result_buffer, [total_len_i32])
                builder.store(ir.Constant(ir.IntType(8), 0), null_ptr)
                
                # 释放临时缓冲区
                builder.call(self.free, [buffer])
                
                return result_buffer
            elif isinstance(left.type, ir.IntType) and right_is_str:
                # 整数在左边，字符串在右边，需要将整数转换为字符串
                builder = self._get_builder()
                # 分配21字节（20位数字 + 符号 + null终止符）
                buffer_size = ir.Constant(ir.IntType(64), 21)
                buffer = builder.call(self.malloc, [buffer_size])
                
                # 创建格式化字符串 "%d"
                fmt_str = self._create_string_constant("%d")
                
                # 调用 snprintf(buffer, 21, "%d", left)
                builder.call(self.sprintf, [buffer, buffer_size, fmt_str, left])
                
                # 现在拼接两个字符串
                left_len = self._get_string_length(buffer)
                right_len = self._get_string_length(right)
                
                # 分配新缓冲区（左长度 + 右长度 + 1）
                total_len = builder.add(left_len, right_len)
                total_len_with_null = builder.add(total_len, ir.Constant(ir.IntType(64), 1))
                result_buffer = builder.call(self.malloc, [total_len_with_null])
                
                # 复制左字符串（整数转后的字符串）
                self._copy_string(builder, result_buffer, buffer, 0)
                # 复制右字符串
                self._copy_string(builder, result_buffer, right, left_len)
                
                # 添加null终止符
                total_len_i32 = builder.trunc(total_len, ir.IntType(32))
                null_ptr = builder.gep(result_buffer, [total_len_i32])
                builder.store(ir.Constant(ir.IntType(8), 0), null_ptr)
                
                # 释放临时缓冲区
                builder.call(self.free, [buffer])
                
                return result_buffer
            elif left_is_str and right_is_str:
                # 两个都是字符串，直接拼接
                builder = self._get_builder()
                left_len = self._get_string_length(left)
                right_len = self._get_string_length(right)
                
                total_len = builder.add(left_len, right_len)
                total_len_with_null = builder.add(total_len, ir.Constant(ir.IntType(64), 1))
                result_buffer = builder.call(self.malloc, [total_len_with_null])
                
                # 复制左字符串
                self._copy_string(builder, result_buffer, left, 0)
                # 复制右字符串
                self._copy_string(builder, result_buffer, right, left_len)
                
                # 添加null终止符（位置是 total_len）
                total_len_i32 = builder.trunc(total_len, ir.IntType(32))
                null_ptr = builder.gep(result_buffer, [total_len_i32])
                builder.store(ir.Constant(ir.IntType(8), 0), null_ptr)
                
                return result_buffer

        # 处理 in 和 not in 运算符
        if op.operator in ('in', 'not in'):
            builder = self._get_builder()
            
            # 检查是否是字符串包含检查
            left_is_str = isinstance(left.type, ir.PointerType) and left.type.pointee == ir.IntType(8)
            right_is_str = isinstance(right.type, ir.PointerType) and right.type.pointee == ir.IntType(8)
            
            if left_is_str and right_is_str:
                # 字符串包含检查：strstr(haystack, needle) != null
                # 注意：left 是要查找的子串，right 是被查找的字符串
                # strstr(right, left) 返回指向第一次出现位置的指针，如果没找到返回 null
                result_ptr = builder.call(self.strstr, [right, left])
                null_ptr = ir.Constant(ir.PointerType(ir.IntType(8)), None)
                found = builder.icmp_signed('!=', result_ptr, null_ptr)
                
                if op.operator == 'not in':
                    return builder.not_(found)
                return found
            
            # 处理混合类型（整数占位符与字符串）
            left_is_int = isinstance(left.type, ir.IntType)
            right_is_int = isinstance(right.type, ir.IntType)
            
            if (left_is_int and right_is_str) or (left_is_str and right_is_int):
                # 混合类型，返回 False（或根据语义返回合理默认值）
                result = ir.Constant(ir.IntType(1), 0)  # False
                if op.operator == 'not in':
                    result = builder.not_(result)
                return result
            
            # 检查右边是否是列表类型
            if isinstance(right.type, ir.PointerType):
                # 对于列表，我们需要遍历元素
                # 这里简化处理：返回 False（需要更复杂的实现）
                result = ir.Constant(ir.IntType(1), 0)  # False (i1 type)
                if op.operator == 'not in':
                    result = builder.not_(result)
                return result  # 返回 i1 类型
            else:
                # 不支持的类型
                raise CodeGeneratorError(f"'in' 运算符不支持类型: {left.type}")

        # 处理混合类型比较（如整数占位符与字符串比较）
        if op.operator in ('==', '!=', '<', '<=', '>', '>='):
            # 对于混合类型比较，返回 False（类型不匹配）
            # 这主要用于 UI 组件属性访问返回占位符的情况
            left_is_int = isinstance(left.type, ir.IntType)
            right_is_int = isinstance(right.type, ir.IntType)
            left_is_ptr = isinstance(left.type, ir.PointerType)
            right_is_ptr = isinstance(right.type, ir.PointerType)
            
            if (left_is_int and right_is_ptr) or (left_is_ptr and right_is_int):
                # 混合类型比较，返回 False
                result = ir.Constant(ir.IntType(1), 0)  # False
                if op.operator == '!=':
                    result = builder.not_(result)
                return result
        
        raise CodeGeneratorError(f"不支持的二元运算符: {op.operator}")
    
    def _generate_unary_operation(self, op: UnaryOperation) -> ir.Value:
        """生成一元运算代码"""
        operand = self._generate_expression(op.operand)
        builder = self._get_builder()
        
        if op.operator == '-':
            if isinstance(operand.type, ir.IntType):
                return builder.neg(operand)
            elif isinstance(operand.type, ir.DoubleType):
                return builder.fneg(operand)
        elif op.operator == '!':
            # 逻辑非
            if isinstance(operand.type, ir.IntType):
                bool_val = builder.trunc(operand, ir.IntType(1))
                return builder.xor(bool_val, ir.Constant(ir.IntType(1), 1))
        
        raise CodeGeneratorError(f"不 supported 的一元运算符: {op.operator}")
    
    def _generate_call_expression(self, expr: CallExpression) -> ir.Value:
        """生成函数调用代码"""
        # 检查是否是 DLL 函数调用 (lib.func(...))
        if isinstance(expr.callee, MemberAccess):
            if isinstance(expr.callee.object, Identifier):
                lib_name = expr.callee.object.name
                # 检查是否是 DLL 库变量
                if lib_name in self.symbols:
                    symbol = self.symbols[lib_name]
                    if isinstance(symbol, tuple) and symbol[0] == 'dll_lib':
                        # 这是 DLL 函数调用
                        dll_call = DLLFunctionCall(
                            lib_name=lib_name,
                            func_name=expr.callee.member,
                            arguments=expr.arguments,
                            line=expr.line,
                            column=expr.column
                        )
                        return self._generate_dll_function_call(dll_call)
                
                # 检查是否是模块调用（如 ui.窗口(...)）
                if isinstance(symbol, tuple) and symbol[0] == 'module':
                    # 模块函数调用
                    return self._generate_module_call(
                        module_name=lib_name,
                        func_name=expr.callee.member,
                        arguments=expr.arguments,
                        named_arguments=expr.named_arguments,
                        line=expr.line,
                        column=expr.column
                    )
                
                # 检查是否是对象方法调用
                # 需要找到对象的类型，然后调用对应的方法
                return self._generate_method_call(expr)
            
            # 对于非Identifier的MemberAccess（如 这.方法()），也作为方法调用处理
            return self._generate_method_call(expr)
        
        # 查找函数
        if isinstance(expr.callee, Identifier):
            func_name = expr.callee.name
            
            # 内置函数特殊处理
            if func_name == "整数":
                # 整数(字符串) -> 将字符串转换为整数
                if len(expr.arguments) != 1:
                    raise CodeGeneratorError(f"函数'整数'需要1个参数")
                
                arg = self._generate_expression(expr.arguments[0])
                builder = self._get_builder()
                
                # 使用 atoi 函数
                if not hasattr(self, 'atoi'):
                    atoi_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))])
                    self.atoi = ir.Function(self.module, atoi_type, name="atoi")
                
                # 如果参数不是指针类型，尝试转换
                if isinstance(arg.type, ir.IntType):
                    arg = builder.inttoptr(arg, ir.PointerType(ir.IntType(8)))
                
                return builder.call(self.atoi, [arg])
            
            elif func_name == "浮点":
                # 浮点(字符串) -> 将字符串转换为浮点数
                if len(expr.arguments) != 1:
                    raise CodeGeneratorError(f"函数'浮点'需要1个参数")
                
                arg = self._generate_expression(expr.arguments[0])
                builder = self._get_builder()
                
                # 使用 atof 函数
                if not hasattr(self, 'atof'):
                    atof_type = ir.FunctionType(ir.DoubleType(), [ir.PointerType(ir.IntType(8))])
                    self.atof = ir.Function(self.module, atof_type, name="atof")
                
                # 如果参数不是指针类型，尝试转换
                if isinstance(arg.type, ir.IntType):
                    arg = builder.inttoptr(arg, ir.PointerType(ir.IntType(8)))
                
                return builder.call(self.atof, [arg])
            
            elif func_name == "字符串":
                # 字符串(数字) -> 将数字转换为字符串
                if len(expr.arguments) != 1:
                    raise CodeGeneratorError(f"函数'字符串'需要1个参数")
                
                arg = self._generate_expression(expr.arguments[0])
                builder = self._get_builder()
                
                # 分配缓冲区
                buffer_size = ir.Constant(ir.IntType(64), 32)
                buffer = builder.call(self.malloc, [buffer_size])
                
                # 根据参数类型选择格式
                if isinstance(arg.type, ir.DoubleType):
                    fmt_str = self._create_string_constant("%.6g")
                else:
                    fmt_str = self._create_string_constant("%d")
                
                # 调用 snprintf
                builder.call(self.sprintf, [buffer, buffer_size, fmt_str, arg])
                
                return buffer
            
            elif func_name == "输出":
                if len(expr.arguments) != 1:
                    raise CodeGeneratorError(f"函数'输出'需要1个参数，但传入了{len(expr.arguments)}个")
                
                # 先生成参数值，然后根据类型判断格式字符串
                arg = expr.arguments[0]
                arg_value = self._generate_expression(arg)
                
                # 判断是否是字符串类型（指针类型 i8* 或 i8**）
                # 字符串指针类型是 i8*，整数类型是 i32
                is_string = False
                if hasattr(arg_value, 'type'):
                    arg_type = arg_value.type
                    # 检查是否是 i8* 类型（字符串指针）
                    if isinstance(arg_type, ir.PointerType):
                        if isinstance(arg_type.pointee, ir.IntType) and arg_type.pointee.width == 8:
                            is_string = True
                
                # 根据类型选择格式字符串
                if is_string:
                    format_str = "%s\n"
                else:
                    format_str = "%d\n"
                
                byte_len = len(format_str.encode('utf-8'))
                str_const = ir.Constant(ir.ArrayType(ir.IntType(8), byte_len + 1),
                                       bytearray(format_str.encode('utf-8') + b'\0'))
                global_fmt = ir.GlobalVariable(self.module, str_const.type, name=f"fmt.{self._fmt_counter}")
                global_fmt.linkage = 'internal'
                global_fmt.global_constant = True
                global_fmt.initializer = str_const
                self._fmt_counter += 1
                
                builder = self._get_builder()
                fmt_ptr = builder.gep(global_fmt, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
                
                # 调用printf
                return builder.call(self.printf, [fmt_ptr, arg_value])
            
            elif func_name == "创建窗口":
                if len(expr.arguments) != 3:
                    raise CodeGeneratorError(f"函数'创建窗口'需要3个参数（标题，宽度，高度），但传入了{len(expr.arguments)}个")
                
                # 生成调试信息：输出窗口创建消息
                debug_msg = "创建窗口: 标题='%s', 宽度=%d, 高度=%d\n"
                byte_len = len(debug_msg.encode('utf-8'))
                str_const = ir.Constant(ir.ArrayType(ir.IntType(8), byte_len + 1),
                                       bytearray(debug_msg.encode('utf-8') + b'\0'))
                global_fmt = ir.GlobalVariable(self.module, str_const.type, name=f"fmt.{self._fmt_counter}")
                global_fmt.linkage = 'internal'
                global_fmt.global_constant = True
                global_fmt.initializer = str_const
                self._fmt_counter += 1
                
                builder = self._get_builder()
                fmt_ptr = builder.gep(global_fmt, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
                
                # 生成参数
                title_arg = self._generate_expression(expr.arguments[0])
                width_arg = self._generate_expression(expr.arguments[1])
                height_arg = self._generate_expression(expr.arguments[2])
                
                # 调用printf显示调试信息
                builder.call(self.printf, [fmt_ptr, title_arg, width_arg, height_arg])
                
                # 返回0（成功）
                return ir.Constant(ir.IntType(32), 0)
            
            elif func_name == "绑定事件":
                if len(expr.arguments) != 3:
                    raise CodeGeneratorError(f"函数'绑定事件'需要3个参数（组件名，事件类型，处理函数），但传入了{len(expr.arguments)}个")
                
                # 生成调试信息
                debug_msg = "绑定事件: 组件='%s', 事件类型='%s'\n"
                byte_len = len(debug_msg.encode('utf-8'))
                str_const = ir.Constant(ir.ArrayType(ir.IntType(8), byte_len + 1),
                                       bytearray(debug_msg.encode('utf-8') + b'\0'))
                global_fmt = ir.GlobalVariable(self.module, str_const.type, name=f"fmt.{self._fmt_counter}")
                global_fmt.linkage = 'internal'
                global_fmt.global_constant = True
                global_fmt.initializer = str_const
                self._fmt_counter += 1
                
                builder = self._get_builder()
                fmt_ptr = builder.gep(global_fmt, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
                
                # 生成参数
                component_arg = self._generate_expression(expr.arguments[0])
                event_type_arg = self._generate_expression(expr.arguments[1])
                # 第三个参数是函数，但我们只输出调试信息
                
                # 调用printf显示调试信息
                builder.call(self.printf, [fmt_ptr, component_arg, event_type_arg])
                
                # 返回0（成功）
                return ir.Constant(ir.IntType(32), 0)
            
            elif func_name == "关闭窗口":
                if len(expr.arguments) != 0:
                    raise CodeGeneratorError(f"函数'关闭窗口'不需要参数，但传入了{len(expr.arguments)}个")
                
                # 生成调试信息
                debug_msg = "关闭窗口\n"
                byte_len = len(debug_msg.encode('utf-8'))
                str_const = ir.Constant(ir.ArrayType(ir.IntType(8), byte_len + 1),
                                       bytearray(debug_msg.encode('utf-8') + b'\0'))
                global_fmt = ir.GlobalVariable(self.module, str_const.type, name=f"fmt.{self._fmt_counter}")
                global_fmt.linkage = 'internal'
                global_fmt.global_constant = True
                global_fmt.initializer = str_const
                self._fmt_counter += 1
                
                builder = self._get_builder()
                fmt_ptr = builder.gep(global_fmt, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
                
                # 调用printf显示调试信息
                builder.call(self.printf, [fmt_ptr])
                
                # 返回0（成功）
                return ir.Constant(ir.IntType(32), 0)
            
            # 检查是否是类名调用（构造函数）
            if func_name in self.symbols:
                symbol = self.symbols[func_name]
                if isinstance(symbol, tuple) and symbol[0] == 'class':
                    # 这是一个类名调用，创建类实例
                    return self._generate_class_instantiation(symbol[1], expr.arguments)
            
            # 普通函数查找
            # 首先检查符号表（用于处理重命名的"主"函数）
            if func_name in self.symbols and isinstance(self.symbols[func_name], ir.Function):
                func = self.symbols[func_name]
            else:
                try:
                    func = self.module.get_global(func_name)
                except KeyError:
                    func = None
                
                if not func:
                    # 函数尚未定义，创建前向声明
                    # 假设函数返回i32，参数默认为空
                    func_type = ir.FunctionType(ir.IntType(32), [])
                    func = ir.Function(self.module, func_type, name=func_name)
                    # 存入符号表以便后续使用
                    self.symbols[func_name] = func
                    print(f"DEBUG: 创建前向声明: {func_name}")
        else:
            # 复杂的callee表达式（暂不支持）
            raise CodeGeneratorError("复杂的函数调用表达式暂不支持")
        
        # 生成参数
        args = []
        for i, arg in enumerate(expr.arguments):
            arg_value = self._generate_expression(arg)
            
            # 获取期望的参数类型
            if i < len(func.function_type.args):
                expected_type = func.function_type.args[i]
                
                # 如果类型不匹配，尝试转换
                if arg_value.type != expected_type:
                    builder = self._get_builder()
                    if isinstance(expected_type, ir.PointerType) and isinstance(arg_value.type, ir.IntType):
                        # 整数转指针
                        arg_value = builder.inttoptr(arg_value, expected_type)
                    elif isinstance(expected_type, ir.IntType) and isinstance(arg_value.type, ir.PointerType):
                        # 指针转整数
                        arg_value = builder.ptrtoint(arg_value, expected_type)
                    elif isinstance(expected_type, ir.DoubleType) and isinstance(arg_value.type, ir.IntType):
                        # 整数转浮点
                        arg_value = builder.sitofp(arg_value, expected_type)
                    elif isinstance(expected_type, ir.IntType) and isinstance(arg_value.type, ir.DoubleType):
                        # 浮点转整数
                        arg_value = builder.fptosi(arg_value, expected_type)
            
            args.append(arg_value)
        
        # 调用函数
        builder = self._get_builder()
        return builder.call(func, args)
    
    def _generate_member_access(self, expr: MemberAccess) -> ir.Value:
        """生成成员访问代码"""
        import sys
        print(f"DEBUG _generate_member_access: object={expr.object}, member={expr.member}", file=sys.stderr, flush=True)
        
        builder = self._get_builder()
        
        # 检查是否是 this.成员 的访问
        if isinstance(expr.object, ThisExpression):
            # 访问类的成员变量
            class_name = None
            # 查找当前类名
            if '这' in self.symbols:
                # 通过符号表找到类信息
                for name, info in self.class_info.items():
                    if 'methods' in info:
                        class_name = name
                        break
            
            if class_name and class_name in self.class_info:
                class_info = self.class_info[class_name]
                member_name = expr.member
                
                # 查找成员变量索引
                if member_name in class_info['member_names']:
                    index = class_info['member_names'].index(member_name)
                    
                    # 获取 this 指针
                    this_ptr_ptr = self.symbols['这']
                    this_ptr = builder.load(this_ptr_ptr)
                    
                    # 访问成员变量
                    member_ptr = builder.gep(this_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), index)])
                    return builder.load(member_ptr)
                
                # 查找方法
                elif member_name in class_info['methods']:
                    method_info = class_info['methods'][member_name]
                    # 返回方法指针
                    func = method_info['function']
                    return builder.bitcast(func, ir.PointerType(ir.IntType(8)))
        
        # 检查是否是模块访问（如 ui.窗口）
        if isinstance(expr.object, Identifier):
            obj_name = expr.object.name
            # 检查是否是模块名
            if obj_name in self.symbols:
                symbol = self.symbols[obj_name]
                if isinstance(symbol, tuple) and symbol[0] == 'module':
                    # 模块成员访问，返回一个标记
                    return ('module_member', obj_name, expr.member)
                elif isinstance(symbol, tuple) and symbol[0] == 'class_instance':
                    # 类实例变量的成员访问
                    ptr = symbol[1]
                    class_name = symbol[2]
                    obj_ptr = builder.load(ptr)
                    
                    if hasattr(self, 'class_info') and class_name in self.class_info:
                        class_info = self.class_info[class_name]
                        member_name = expr.member
                        
                        if member_name in class_info['member_names']:
                            index = class_info['member_names'].index(member_name)
                            member_ptr = builder.gep(obj_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), index)])
                            return builder.load(member_ptr)
                    
                    # 外部对象属性访问，返回占位符
                    print(f"WARNING: 外部对象属性访问暂不完全支持: {obj_name}.{expr.member}", file=sys.stderr, flush=True)
                    return ir.Constant(ir.IntType(32), 0)
                else:
                    # 普通变量的成员访问（外部对象）
                    print(f"WARNING: 外部对象属性访问: {obj_name}.{expr.member}", file=sys.stderr, flush=True)
                    return ir.Constant(ir.IntType(32), 0)
        
        # 检查是否是成员访问的成员访问（如 a.b.c）
        if isinstance(expr.object, MemberAccess):
            # 递归处理多级成员访问
            obj_value = self._generate_member_access(expr.object)
            # 对于多级成员访问，暂时返回占位符
            print(f"WARNING: 多级成员访问暂不完全支持: {expr.object}.{expr.member}", file=sys.stderr, flush=True)
            return ir.Constant(ir.IntType(32), 0)
        
        # 普通成员访问（暂不支持）
        raise CodeGeneratorError(f"成员访问暂不支持: {expr.member}")
    
    def _generate_assignment(self, expr: Assignment) -> ir.Value:
        """生成赋值表达式代码"""
        import sys
        print(f"DEBUG _generate_assignment: target={expr.target}", file=sys.stderr, flush=True)
        
        # 生成值
        value = self._generate_expression(expr.value)
        
        # 目标可以是标识符或成员访问
        if isinstance(expr.target, Identifier):
            name = expr.target.name
            
            if name not in self.symbols:
                raise CodeGeneratorError(f"未定义的标识符: {name}")
            
            ptr = self.symbols[name]
            builder = self._get_builder()
            builder.store(value, ptr)
            
            return value
        
        elif isinstance(expr.target, MemberAccess):
            # 成员访问赋值（如 这.显示框 = ... 或 这.显示框.样式 = ...）
            builder = self._get_builder()
            
            # 处理多级成员访问
            target = expr.target
            
            # 收集成员访问链
            access_chain = []
            while isinstance(target, MemberAccess):
                access_chain.insert(0, target.member)
                target = target.object
            
            # 现在 target 是起始对象（如 ThisExpression 或 Identifier）
            access_chain.insert(0, target)  # 添加起始对象
            
            print(f"DEBUG access_chain: {access_chain}", file=sys.stderr, flush=True)
            
            # 处理 this 开头的访问
            if isinstance(access_chain[0], ThisExpression):
                # 查找类信息
                class_name = None
                for name, info in getattr(self, 'class_info', {}).items():
                    class_name = name
                    break
                
                if class_name and class_name in self.class_info:
                    class_info = self.class_info[class_name]
                    
                    # 获取 this 指针
                    this_ptr_ptr = self.symbols.get('这')
                    if this_ptr_ptr:
                        this_ptr = builder.load(this_ptr_ptr)
                        
                        # 遍历成员访问链
                        current_ptr = this_ptr
                        current_type = class_info['type']
                        
                        for i, member_name in enumerate(access_chain[1:], 1):
                            # 如果不是最后一个，获取成员指针
                            if i < len(access_chain) - 1:
                                # 中间成员访问
                                if hasattr(self, 'class_info') and class_name in self.class_info:
                                    if member_name in class_info['member_names']:
                                        index = class_info['member_names'].index(member_name)
                                        current_ptr = builder.gep(current_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), index)])
                                        current_ptr = builder.load(current_ptr)
                                        # 更新 class_name 和 class_info 以支持多级访问
                                        # 这里需要类型信息，暂时跳过
                                    else:
                                        # 成员不存在于类中，可能是动态属性
                                        pass
                                else:
                                    # 没有类信息，跳过
                                    pass
                            else:
                                # 最后一个成员，执行赋值
                                if hasattr(self, 'class_info') and class_name in self.class_info:
                                    if member_name in class_info['member_names']:
                                        index = class_info['member_names'].index(member_name)
                                        member_ptr = builder.gep(current_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), index)])
                                        
                                        # 获取成员期望的类型
                                        expected_type = class_info['member_types'][index]
                                        
                                        # 如果类型不匹配，进行转换
                                        if value.type != expected_type:
                                            if isinstance(expected_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                                                # 整数转浮点
                                                value = builder.sitofp(value, expected_type)
                                            elif isinstance(expected_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                                                # 浮点转整数
                                                value = builder.fptosi(value, expected_type)
                                            elif isinstance(expected_type, ir.PointerType) and isinstance(value.type, ir.IntType):
                                                # 整数转指针（不常见，但用于占位符）
                                                value = builder.inttoptr(value, expected_type)
                                            # 其他类型转换可以在这里添加
                                        
                                        builder.store(value, member_ptr)
                                        return value
                                    else:
                                        # 成员不在类中，可能是外部对象属性
                                        # 暂时忽略，返回值
                                        print(f"WARNING: 成员 '{member_name}' 不在类 '{class_name}' 中，忽略赋值", file=sys.stderr, flush=True)
                                        return value
                                else:
                                    # 没有类信息，返回值
                                    return value
            
            # 处理 Identifier 开头的成员访问赋值（如 变量.属性 = 值）
            elif isinstance(access_chain[0], Identifier):
                var_name = access_chain[0].name
                if var_name in self.symbols:
                    symbol = self.symbols[var_name]
                    # 获取变量值
                    if isinstance(symbol, tuple) and symbol[0] == 'class_instance':
                        # 类实例变量
                        ptr = symbol[1]
                        obj_ptr = builder.load(ptr)
                        # 对于外部对象属性赋值，暂时忽略
                        print(f"WARNING: 外部对象属性赋值暂不支持: {access_chain}", file=sys.stderr, flush=True)
                        return value
                    else:
                        # 普通变量
                        var_value = builder.load(symbol)
                        # 对于外部对象属性赋值，暂时忽略
                        print(f"WARNING: 外部对象属性赋值暂不支持: {access_chain}", file=sys.stderr, flush=True)
                        return value
                else:
                    # 变量不存在
                    print(f"WARNING: 变量 '{var_name}' 未定义，忽略赋值", file=sys.stderr, flush=True)
                    return value
            
            raise CodeGeneratorError(f"不支持的成员访问赋值: {access_chain}")
        
        else:
            raise CodeGeneratorError(f"复杂的赋值目标暂不支持: {type(expr.target).__name__}")
    
    def _generate_list_literal(self, expr: ListLiteral) -> ir.Value:
        """生成列表字面量代码"""
        import sys
        print(f"DEBUG _generate_list_literal: {expr.elements}", file=sys.stderr, flush=True)
        
        if not expr.elements:
            # 空列表
            # 创建一个空的i8*指针（简化处理）
            builder = self._get_builder()
            return ir.Constant(ir.PointerType(ir.IntType(8)), None)
        
        # 检查所有元素类型是否相同（简化：假设都是整数）
        # 生成所有元素值
        element_values = []
        for element in expr.elements:
            element_values.append(self._generate_expression(element))
        
        # 暂时简化：只返回第一个元素（待完善）
        # TODO: 实现真正的列表分配和存储
        return element_values[0] if element_values else ir.Constant(ir.IntType(32), 0)
    
    def _generate_list_comprehension(self, expr: ListComprehension) -> ir.Value:
        """生成列表推导式代码"""
        import sys
        print(f"DEBUG _generate_list_comprehension: expr={expr.expression}, variable={expr.variable}, iterable={expr.iterable}, condition={expr.condition}", file=sys.stderr, flush=True)
        
        builder = self._get_builder()
        
        # 解析范围参数
        start_value = ir.Constant(ir.IntType(32), 0)
        end_value = ir.Constant(ir.IntType(32), 10)  # 默认值
        
        if isinstance(expr.iterable, CallExpression):
            if isinstance(expr.iterable.callee, Identifier) and expr.iterable.callee.name == '范围':
                args = expr.iterable.arguments
                if len(args) == 1:
                    end_value = self._generate_expression(args[0])
                elif len(args) >= 2:
                    start_value = self._generate_expression(args[0])
                    end_value = self._generate_expression(args[1])
        
        # 计算元素数量：end - start
        count = builder.sub(end_value, start_value)
        
        # 简化：返回列表长度作为整数（用于调试）
        # TODO: 实现真正的列表类型和打印
        return count
    
    def _generate_tuple_expression(self, expr: TupleExpression) -> ir.Value:
        """生成元组表达式代码"""
        import sys
        print(f"DEBUG _generate_tuple_expression: elements={expr.elements}", file=sys.stderr, flush=True)
        # 简化：暂时不支持，抛出错误
        raise CodeGeneratorError("元组表达式暂不支持")
    
    def _generate_method_call(self, expr: CallExpression) -> ir.Value:
        """生成对象方法调用代码"""
        builder = self._get_builder()
        
        # 获取对象和方法名
        member_access = expr.callee  # MemberAccess 类型
        obj_expr = member_access.object
        method_name = member_access.member
        
        # 生成对象值（获取对象指针）
        obj_value = self._generate_expression(obj_expr)
        
        # 确定对象的类型
        class_name = None
        if isinstance(obj_expr, ThisExpression):
            # 从当前上下文获取类名
            if hasattr(self, 'class_info'):
                for cname, info in self.class_info.items():
                    # 检查当前是否在这个类的方法中
                    if 'methods' in info:
                        class_name = cname
                        break
        elif isinstance(obj_expr, Identifier):
            # 从符号表查找变量的类型
            var_name = obj_expr.name
            if var_name in self.symbols:
                symbol = self.symbols[var_name]
                # symbol 可能是 ('class_instance', ptr, class_name, type) 或其他形式
                if isinstance(symbol, tuple):
                    if symbol[0] == 'class_instance':
                        class_name = symbol[2]
                    elif symbol[0] == 'ui_component':
                        # UI 组件方法调用
                        ui_method = self._try_generate_ui_method_call(obj_value, method_name, expr.arguments, builder)
                        if ui_method is not None:
                            return ui_method
        
        # 如果符号表没有类型信息，尝试从 class_info 推断
        if not class_name and hasattr(self, 'class_info'):
            # 检查是否有类型推断信息
            pass
        
        # 构造方法函数名
        # 需要知道对象所属的类名
        # 暂时使用简单策略：尝试所有已注册的类
        if hasattr(self, 'class_info'):
            for cname, info in self.class_info.items():
                full_method_name = f"{cname}_{method_name}"
                try:
                    func = self.module.get_global(full_method_name)
                    if func:
                        class_name = cname
                        break
                except KeyError:
                    continue
        
        if not class_name:
            # 检查是否是 UI 组件的方法调用
            ui_method = self._try_generate_ui_method_call(obj_value, method_name, expr.arguments, builder)
            if ui_method is not None:
                return ui_method
            
            # 外部对象的方法调用，暂时生成占位符
            print(f"WARNING: 外部对象方法调用暂不完全支持: {method_name}", file=sys.stderr, flush=True)
            # 生成参数（用于副作用）
            for arg in expr.arguments:
                self._generate_expression(arg)
            # 返回占位符值
            return ir.Constant(ir.IntType(32), 0)
        
        full_method_name = f"{class_name}_{method_name}"
        
        # 获取方法函数
        try:
            func = self.module.get_global(full_method_name)
        except KeyError:
            raise CodeGeneratorError(f"未找到方法 '{full_method_name}'")
        
        # 生成参数（第一个参数是 this 指针）
        args = [obj_value]  # this 指针
        for arg in expr.arguments:
            args.append(self._generate_expression(arg))
        
        # 调用方法
        return builder.call(func, args)
    
    def _generate_class_instantiation(self, class_name: str, arguments: list) -> ir.Value:
        """生成类实例化代码"""
        import sys
        print(f"DEBUG _generate_class_instantiation: class={class_name}", file=sys.stderr, flush=True)
        
        builder = self._get_builder()
        
        # 获取类信息
        if not hasattr(self, 'class_info') or class_name not in self.class_info:
            raise CodeGeneratorError(f"未知的类: {class_name}")
        
        class_info = self.class_info[class_name]
        class_type = class_info['type']
        
        # 分配类实例内存
        instance_ptr = builder.alloca(class_type)
        
        # 初始化成员变量
        member_vars = class_info['member_vars']
        member_types = class_info['member_types']
        
        for i, (var, var_type) in enumerate(zip(member_vars, member_types)):
            # 获取成员指针
            member_ptr = builder.gep(instance_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)])
            
            # 初始化为默认值
            if isinstance(var_type, ir.IntType):
                default_value = ir.Constant(var_type, 0)
            elif isinstance(var_type, ir.DoubleType):
                default_value = ir.Constant(var_type, 0.0)
            elif isinstance(var_type, ir.PointerType):
                default_value = ir.Constant(var_type, None)  # null 指针
            else:
                default_value = ir.Constant(var_type, 0)
            
            builder.store(default_value, member_ptr)
        
        return instance_ptr
    
    def _generate_module_call(self, module_name: str, func_name: str, 
                               arguments: list, named_arguments: list,
                               line: int, column: int) -> ir.Value:
        """生成模块函数调用代码"""
        import sys
        print(f"DEBUG _generate_module_call: module={module_name}, func={func_name}, args={arguments}, named={named_arguments}", file=sys.stderr, flush=True)
        
        builder = self._get_builder()
        
        # 处理 UI 模块
        if module_name == "ui":
            return self._generate_ui_call(func_name, arguments, named_arguments, builder)
        
        # 处理命名参数：将其转换为位置参数
        # 例如：ui.窗口("计算器", 宽度=400, 高度=500)
        # 需要知道函数参数的顺序
        
        # 目前简化处理：生成调试输出
        debug_msg = f"调用模块函数: {module_name}.{func_name}()\n"
        debug_str = self._create_string_constant(debug_msg)
        builder.call(self.printf, [debug_str])
        
        # 生成普通参数
        for i, arg in enumerate(arguments):
            arg_value = self._generate_expression(arg)
            arg_debug = f"  参数 {i}: 类型={type(arg_value).__name__}\n"
            arg_str = self._create_string_constant(arg_debug)
            builder.call(self.printf, [arg_str])
        
        # 生成命名参数
        for named_arg in named_arguments:
            arg_value = self._generate_expression(named_arg.value)
            named_debug = f"  命名参数 {named_arg.name}: 类型={type(arg_value).__name__}\n"
            named_str = self._create_string_constant(named_debug)
            builder.call(self.printf, [named_str])
        
        # 返回默认值
        return ir.Constant(ir.IntType(32), 0)
    
    def _generate_ui_call(self, func_name: str, arguments: list, 
                          named_arguments: list, builder) -> ir.Value:
        """生成 UI 模块函数调用"""
        ptr_type = ir.PointerType(ir.IntType(8))
        
        # 映射中文函数名到内部名称
        func_map = {
            "窗口": "window_create",
            "按钮": "button_create",
            "文本框": "textbox_create",
            "标签": "label_create",
            "网格布局": "grid_create",
            "垂直布局": "vlayout_create",
        }
        
        internal_name = func_map.get(func_name, func_name)
        
        if internal_name == "window_create":
            # ui.窗口(title, 宽度=width, 高度=height)
            title = self._generate_expression(arguments[0]) if arguments else self._create_string_constant("")
            width = self._get_named_arg(named_arguments, "宽度", 400)
            height = self._get_named_arg(named_arguments, "高度", 300)
            return builder.call(self.taihe_window_create, [title, width, height])
        
        elif internal_name == "button_create":
            # ui.按钮(text)
            text = self._generate_expression(arguments[0]) if arguments else self._create_string_constant("")
            return builder.call(self.taihe_button_create, [text])
        
        elif internal_name == "textbox_create":
            # ui.文本框(text, 只读=readonly)
            text = self._generate_expression(arguments[0]) if arguments else self._create_string_constant("")
            readonly = self._get_named_arg(named_arguments, "只读", 0)
            return builder.call(self.taihe_textbox_create, [text, readonly])
        
        elif internal_name == "label_create":
            # ui.标签(text)
            text = self._generate_expression(arguments[0]) if arguments else self._create_string_constant("")
            return builder.call(self.taihe_label_create, [text])
        
        elif internal_name == "grid_create":
            # ui.网格布局(行数=rows, 列数=cols)
            rows = self._get_named_arg(named_arguments, "行数", 1)
            cols = self._get_named_arg(named_arguments, "列数", 1)
            return builder.call(self.taihe_grid_create, [rows, cols])
        
        elif internal_name == "vlayout_create":
            # ui.垂直布局()
            return builder.call(self.taihe_vlayout_create, [])
        
        else:
            # 未知的 UI 函数，返回空指针
            return ir.Constant(ptr_type, None)
    
    def _get_named_arg(self, named_arguments: list, name: str, default_value):
        """获取命名参数的值"""
        for named_arg in named_arguments:
            if named_arg.name == name:
                value = self._generate_expression(named_arg.value)
                # 如果是默认值（整数），直接返回生成的值
                if isinstance(default_value, int):
                    return value
                return value
        # 返回默认值
        if isinstance(default_value, int):
            return ir.Constant(ir.IntType(32), default_value)
        return default_value
    
    def _try_generate_ui_method_call(self, obj_value, method_name: str, arguments: list, builder) -> ir.Value:
        """尝试生成 UI 组件的方法调用，如果不是 UI 组件则返回 None"""
        ptr_type = ir.PointerType(ir.IntType(8))
        
        # UI 组件方法映射
        ui_methods = {
            # 窗口方法
            '显示': ('window_show', self.taihe_window_show),
            '设置布局': ('window_set_layout', self.taihe_window_set_layout),
            # 组件通用方法
            '设置文本': ('set_text', self.taihe_set_text),
            '获取文本': ('get_text', self.taihe_get_text),
            '设置样式': ('set_style', self.taihe_set_style),
            '设置点击事件': ('set_onclick', self.taihe_set_onclick),
            # 按钮方法
            '设置跨列': ('set_colspan', self.taihe_set_colspan),
            # 布局方法
            '添加': ('layout_add', self.taihe_layout_add),
            '获取组件': ('layout_get', None),  # 暂未实现
        }
        
        if method_name not in ui_methods:
            return None
        
        info = ui_methods[method_name]
        internal_name = info[0]
        func = info[1]
        
        if func is None:
            # 暂未实现的方法
            return ir.Constant(ir.IntType(32), 0)
        
        # 根据方法名生成调用
        if internal_name == 'window_show':
            # 窗口.显示()
            builder.call(func, [obj_value])
            return ir.Constant(ir.IntType(32), 0)
        
        elif internal_name == 'window_set_layout':
            # 窗口.设置布局(layout)
            if arguments:
                layout = self._generate_expression(arguments[0])
                builder.call(func, [obj_value, layout])
            return ir.Constant(ir.IntType(32), 0)
        
        elif internal_name == 'set_text':
            # 组件.设置文本(text)
            if arguments:
                text = self._generate_expression(arguments[0])
                builder.call(func, [obj_value, text])
            return ir.Constant(ir.IntType(32), 0)
        
        elif internal_name == 'get_text':
            # 组件.获取文本() -> char*
            return builder.call(func, [obj_value])
        
        elif internal_name == 'set_style':
            # 组件.设置样式(style)
            if arguments:
                style = self._generate_expression(arguments[0])
                builder.call(func, [obj_value, style])
            return ir.Constant(ir.IntType(32), 0)
        
        elif internal_name == 'set_onclick':
            # 组件.设置点击事件(callback)
            if arguments:
                callback = self._generate_expression(arguments[0])
                closure = ir.Constant(ptr_type, None)
                builder.call(func, [obj_value, callback, closure])
            return ir.Constant(ir.IntType(32), 0)
        
        elif internal_name == 'set_colspan':
            # 按钮.设置跨列(colspan)
            if arguments:
                colspan = self._generate_expression(arguments[0])
                builder.call(func, [obj_value, colspan])
            return ir.Constant(ir.IntType(32), 0)
        
        elif internal_name == 'layout_add':
            # 布局.添加(component, row, col)
            if len(arguments) >= 3:
                component = self._generate_expression(arguments[0])
                row = self._generate_expression(arguments[1])
                col = self._generate_expression(arguments[2])
                builder.call(func, [obj_value, component, row, col])
            return ir.Constant(ir.IntType(32), 0)
        
        return None
    
    def _generate_subscript_expression(self, expr: SubscriptExpression) -> ir.Value:
        """生成下标表达式代码（索引或切片）"""
        import sys
        print(f"DEBUG _generate_subscript_expression: value={expr.value}, slice={expr.slice}", file=sys.stderr, flush=True)
        
        builder = self._get_builder()
        
        # 生成被索引的值
        value_ptr = self._generate_expression(expr.value)
        slice_expr = expr.slice
        
        # 检查是否是切片（start、end、step中至少有一个不为None）
        if slice_expr.start is None and slice_expr.end is None and slice_expr.step is None:
            # 空切片（例如 list[:]），暂不支持
            raise CodeGeneratorError("空切片暂不支持")
        
        # 如果是索引（只有start，没有end和step）
        if slice_expr.start is not None and slice_expr.end is None and slice_expr.step is None:
            # 索引访问
            index = self._generate_expression(slice_expr.start)
            
            # 检查是否是列表类型（简化处理）
            # 对于多维数组访问，需要先加载前一维的值
            if isinstance(expr.value, SubscriptExpression):
                # 多维索引访问
                parent_value = self._generate_subscript_expression(expr.value)
                # 这里简化处理，假设是整数数组
                # 实际实现需要更复杂的类型系统
                return parent_value
            
            # 简化：假设value_ptr是列表第一个元素或指针
            # 对于列表字面量，我们返回对应索引的元素
            if isinstance(expr.value, ListLiteral):
                elements = expr.value.elements
                # 尝试获取常量索引
                if isinstance(slice_expr.start, Literal) and isinstance(slice_expr.start.value, int):
                    idx = slice_expr.start.value
                    if 0 <= idx < len(elements):
                        return self._generate_expression(elements[idx])
            
            # 对于运行时索引，需要更复杂的列表实现
            # 简化：返回第一个元素
            # TODO: 实现真正的动态列表索引
            return value_ptr
        else:
            # 切片操作，暂不支持
            raise CodeGeneratorError("切片操作暂不支持")
    
    def _generate_dict_literal(self, expr: DictLiteral) -> ir.Value:
        """生成字典字面量代码"""
        # 简化：暂时不实现
        raise CodeGeneratorError("字典字面量暂不支持")
    
    def _generate_dll_load_expression(self, expr: 'DLLLoadExpression') -> ir.Value:
        """生成DLL加载表达式代码"""
        builder = self._get_builder()
        
        # 生成DLL路径
        path_value = self._generate_expression(expr.path)
        
        # 调用 LoadLibraryA (已在 _declare_builtins 中声明)
        lib_handle = builder.call(self.LoadLibraryA, [path_value])
        
        return lib_handle
    
    def _generate_dll_function_call(self, expr: 'DLLFunctionCall') -> ir.Value:
        """生成DLL函数调用代码"""
        builder = self._get_builder()
        
        # 获取库句柄
        lib_name = expr.lib_name
        if lib_name in self.symbols:
            symbol = self.symbols[lib_name]
            # 检查是否是 DLL 库句柄元组
            if isinstance(symbol, tuple) and symbol[0] == 'dll_lib':
                # 元组格式: ('dll_lib', ptr, value)
                lib_handle = symbol[2]  # 使用实际的句柄值
            else:
                raise CodeGeneratorError(f"变量 {lib_name} 不是DLL库句柄")
        else:
            raise CodeGeneratorError(f"未找到DLL库: {lib_name}")
        
        # 获取函数签名
        key = f"{lib_name}.{expr.func_name}"
        if hasattr(self, 'dll_bindings') and key in self.dll_bindings:
            binding = self.dll_bindings[key]
            param_types = binding['param_types']
            return_type = binding['return_type']
        else:
            # 默认使用整数类型
            param_types = None
            return_type = None
        
        # 声明 GetProcAddress 函数 (已在 _declare_builtins 中声明)
        # 创建函数名字符串
        func_name_str = expr.func_name
        func_name_const = self._create_global_string(func_name_str, "dll_func_name")
        func_name_ptr = builder.gep(func_name_const, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
        
        # 获取函数地址
        func_ptr = builder.call(self.GetProcAddress, [lib_handle, func_name_ptr])
        
        # 生成参数
        args = [self._generate_expression(arg) for arg in expr.arguments]
        
        # 确定返回类型
        if return_type:
            ret_type = self._llvm_type(return_type.type_name)
        else:
            ret_type = ir.IntType(32)
        
        # 创建函数类型
        if param_types:
            param_llvm_types = [self._llvm_type(pt.type_name) for pt in param_types]
        else:
            param_llvm_types = [ir.IntType(32)] * len(args)
        
        func_type = ir.FunctionType(ret_type, param_llvm_types)
        
        # 将函数指针转换为正确的类型
        typed_func_ptr = builder.bitcast(func_ptr, ir.PointerType(func_type))
        
        # 调用函数
        result = builder.call(typed_func_ptr, args)
        
        return result
    
    def _create_global_string(self, value: str, prefix: str = "str") -> ir.GlobalVariable:
        """创建全局字符串常量"""
        byte_len = len(value.encode('utf-8'))
        str_const = ir.Constant(ir.ArrayType(ir.IntType(8), byte_len + 1),
                               bytearray(value.encode('utf-8') + b'\0'))
        global_str = ir.GlobalVariable(self.module, str_const.type, name=f"{prefix}.{self._str_counter}")
        global_str.linkage = 'internal'
        global_str.global_constant = True
        global_str.initializer = str_const
        self._str_counter += 1
        return global_str
    
    def _llvm_type(self, type_name: str) -> ir.Type:
        """将太和类型名转换为LLVM类型"""
        if type_name == '整数':
            return ir.IntType(32)
        elif type_name == '浮点':
            return ir.DoubleType()
        elif type_name == '布尔':
            return ir.IntType(1)
        elif type_name == '字符':
            return ir.IntType(8)
        elif type_name == '字符串':
            return ir.PointerType(ir.IntType(8))
        elif type_name == '空值':
            return ir.VoidType()
        else:
            # 默认为整数
            return ir.IntType(32)
    
    def _get_builder(self) -> ir.IRBuilder:
        """获取当前IRBuilder"""
        import sys
        print(f"DEBUG _get_builder: builder={self.builder}, current_basic_block={self.current_basic_block}, current_function={self.current_function}", file=sys.stderr, flush=True)
        if not self.builder:
            raise CodeGeneratorError("不在函数内部")
        
        return self.builder
    
    def _generate_update_statement(self, stmt: 'UpdateStatement'):
        """生成更新语句代码（定时器）"""
        builder = self._get_builder()
        
        # 解析执行次数和间隔时间
        count = self._generate_expression(stmt.count)
        interval = self._generate_expression(stmt.interval)
        
        # 如果有名称，存储更新循环的信息
        if stmt.name:
            if not hasattr(self, 'update_loops'):
                self.update_loops = {}
            self.update_loops[stmt.name] = {
                'count': count,
                'interval': interval
            }
        
        # 创建循环变量来计数
        counter_ptr = builder.alloca(ir.IntType(32), name="update_counter")
        builder.store(ir.Constant(ir.IntType(32), 0), counter_ptr)
        
        # 创建基本块
        condition_block = self.current_function.append_basic_block(name="update.condition")
        body_block = self.current_function.append_basic_block(name="update.body")
        sleep_block = self.current_function.append_basic_block(name="update.sleep")
        after_block = self.current_function.append_basic_block(name="update.after")
        
        # 如果有名称，存储控制块的信息
        if stmt.name:
            # 存储控制变量：是否暂停、是否销毁
            paused_ptr = builder.alloca(ir.IntType(1), name=f"update_{stmt.name}_paused")
            destroyed_ptr = builder.alloca(ir.IntType(1), name=f"update_{stmt.name}_destroyed")
            builder.store(ir.Constant(ir.IntType(1), 0), paused_ptr)  # 初始不暂停
            builder.store(ir.Constant(ir.IntType(1), 0), destroyed_ptr)  # 初始不销毁
            
            # 存储到符号表
            self.symbols[f"_update_{stmt.name}_paused"] = paused_ptr
            self.symbols[f"_update_{stmt.name}_destroyed"] = destroyed_ptr
            self.symbols[f"_update_{stmt.name}_counter"] = counter_ptr
            self.symbols[f"_update_{stmt.name}_interval"] = interval
        
        # 跳转到条件块
        builder.branch(condition_block)
        
        # 生成条件块
        builder.position_at_end(condition_block)
        
        # 检查是否已销毁
        if stmt.name:
            destroyed_ptr = self.symbols.get(f"_update_{stmt.name}_destroyed")
            if destroyed_ptr:
                is_destroyed = builder.load(destroyed_ptr)
                # 如果已销毁，跳转到after块
                check_not_destroyed_block = self.current_function.append_basic_block(name="update.check_not_destroyed")
                builder.cbranch(is_destroyed, after_block, check_not_destroyed_block)
                builder.position_at_end(check_not_destroyed_block)
        
        # 检查是否暂停
        if stmt.name:
            paused_ptr = self.symbols.get(f"_update_{stmt.name}_paused")
            if paused_ptr:
                is_paused = builder.load(paused_ptr)
                # 如果暂停，跳转到sleep块（不执行body但继续循环）
                check_not_paused_block = self.current_function.append_basic_block(name="update.check_not_paused")
                builder.cbranch(is_paused, sleep_block, check_not_paused_block)
                builder.position_at_end(check_not_paused_block)
        
        # 检查计数：count == 0 表示无限循环，否则检查 counter < count
        current_counter = builder.load(counter_ptr)
        
        # 检查 count == 0（无限循环）
        is_infinite = builder.icmp_signed('==', count, ir.Constant(ir.IntType(32), 0))
        
        # 检查 counter < count
        not_reached_limit = builder.icmp_signed('<', current_counter, count)
        
        # 如果是无限循环或者未达到限制，继续循环
        should_continue = builder.or_(is_infinite, not_reached_limit)
        builder.cbranch(should_continue, body_block, after_block)
        
        # 生成循环体
        builder.position_at_end(body_block)
        
        # 保存当前状态
        old_symbols = self.symbols.copy()
        
        # 生成更新体
        self._generate_statement(stmt.body)
        
        # 恢复状态
        self.symbols = old_symbols
        
        # 更新计数器
        current_counter = builder.load(counter_ptr)
        next_counter = builder.add(current_counter, ir.Constant(ir.IntType(32), 1))
        builder.store(next_counter, counter_ptr)
        
        # 跳转到sleep块
        builder.branch(sleep_block)
        
        # 生成sleep块
        builder.position_at_end(sleep_block)
        
        # 调用Sleep函数（间隔时间，毫秒）
        builder.call(self.sleep, [interval])
        
        # 跳回条件块
        builder.branch(condition_block)
        
        # 继续在after块生成
        builder.position_at_end(after_block)
    
    def _generate_console_create_expression(self, expr: 'ConsoleCreateExpression') -> ir.Value:
        """生成控制台创建表达式代码"""
        builder = self._get_builder()
        
        # 生成参数
        hidden = self._generate_expression(expr.hidden) if expr.hidden else ir.Constant(ir.IntType(32), 0)
        keep = self._generate_expression(expr.keep) if expr.keep else ir.Constant(ir.IntType(32), 0)
        command = self._generate_expression(expr.command) if expr.command else self._create_string_constant("")
        
        # 调用 _taihe_console_create
        console_handle = builder.call(self.console_create, [hidden, keep, command])
        
        return console_handle
    
    def _generate_console_member_access(self, expr: 'ConsoleMemberAccess') -> ir.Value:
        """生成控制台成员访问代码"""
        builder = self._get_builder()
        
        # 获取控制台句柄
        console_name = expr.console_name
        if console_name not in self.symbols:
            raise CodeGeneratorError(f"未定义的控制台变量: {console_name}")
        
        symbol = self.symbols[console_name]
        if isinstance(symbol, tuple) and symbol[0] == 'console':
            console_handle = symbol[2]  # 使用实际的句柄值
        else:
            # 加载控制台句柄
            console_handle = builder.load(symbol)
        
        member = expr.member
        
        if member == '内容':
            # 获取控制台内容
            content = builder.call(self.console_get_content, [console_handle])
            return content
        
        elif member == '执行':
            # 执行命令
            if expr.arguments and len(expr.arguments) > 0:
                command = self._generate_expression(expr.arguments[0])
            else:
                command = self._create_string_constant("")
            builder.call(self.console_execute, [console_handle, command])
            return ir.Constant(ir.IntType(32), 0)  # 返回0表示成功
        
        elif member == '销毁':
            # 销毁控制台
            builder.call(self.console_destroy, [console_handle])
            return ir.Constant(ir.IntType(32), 0)  # 返回0表示成功
        
        else:
            raise CodeGeneratorError(f"不支持的控制台成员: {member}")
    
    def _generate_update_member_access(self, expr: 'UpdateMemberAccess') -> ir.Value:
        """生成更新循环成员访问代码"""
        builder = self._get_builder()
        
        update_name = expr.update_name
        member = expr.member
        
        # 检查更新循环是否存在
        if f"_update_{update_name}_destroyed" not in self.symbols:
            raise CodeGeneratorError(f"未定义的更新循环: {update_name}")
        
        if member == '销毁':
            # 设置销毁标志
            destroyed_ptr = self.symbols.get(f"_update_{update_name}_destroyed")
            if destroyed_ptr:
                builder.store(ir.Constant(ir.IntType(1), 1), destroyed_ptr)
            return ir.Constant(ir.IntType(32), 0)
        
        elif member == '暂停':
            # 设置暂停标志
            paused_ptr = self.symbols.get(f"_update_{update_name}_paused")
            if paused_ptr:
                builder.store(ir.Constant(ir.IntType(1), 1), paused_ptr)
            return ir.Constant(ir.IntType(32), 0)
        
        elif member == '继续':
            # 清除暂停标志
            paused_ptr = self.symbols.get(f"_update_{update_name}_paused")
            if paused_ptr:
                builder.store(ir.Constant(ir.IntType(1), 0), paused_ptr)
            return ir.Constant(ir.IntType(32), 0)
        
        else:
            raise CodeGeneratorError(f"不支持的更新循环成员: {member}")
    
    def _generate_update_call_expression(self, expr: 'UpdateCallExpression') -> ir.Value:
        """生成更新循环调用代码（更新参数）"""
        builder = self._get_builder()
        
        update_name = expr.update_name
        
        # 检查更新循环是否存在
        if f"_update_{update_name}_interval" not in self.symbols:
            raise CodeGeneratorError(f"未定义的更新循环: {update_name}")
        
        # 更新间隔时间
        new_interval = self._generate_expression(expr.interval)
        interval_ptr = self.symbols.get(f"_update_{update_name}_interval")
        if interval_ptr:
            # 如果是指针，需要重新分配空间
            # 简化处理：直接更新符号表中的值
            self.symbols[f"_update_{update_name}_interval"] = new_interval
        
        # 更新计数（重置计数器）
        new_count = self._generate_expression(expr.count)
        counter_ptr = self.symbols.get(f"_update_{update_name}_counter")
        if counter_ptr:
            builder.store(ir.Constant(ir.IntType(32), 0), counter_ptr)  # 重置计数器
        
        return ir.Constant(ir.IntType(32), 0)
    
    def _generate_lambda_expression(self, expr: LambdaExpression) -> ir.Value:
        """生成Lambda表达式代码"""
        import sys
        print(f"DEBUG _generate_lambda_expression: parameters={expr.parameters}", file=sys.stderr, flush=True)
        
        # 创建匿名函数名
        if not hasattr(self, '_lambda_counter'):
            self._lambda_counter = 0
        self._lambda_counter += 1
        lambda_name = f"__lambda_{self._lambda_counter}"
        
        # 确定返回类型
        return_type = ir.IntType(32)  # 默认返回整数
        
        # 收集需要捕获的变量（从当前符号表中）
        captured_vars = {}
        captured_types = []
        captured_names = []
        
        # 保存当前符号表状态
        current_symbols = self.symbols.copy()
        
        # 找出需要捕获的变量（排除函数参数和局部变量定义中的临时变量）
        for name, symbol in current_symbols.items():
            # 跳过特殊变量和模块级别的符号
            if name in ('这', 'ui') or isinstance(symbol, tuple):
                continue
            # 跳过函数对象
            if isinstance(symbol, ir.Function):
                continue
            # 检查是否是 alloca 指令（局部变量）
            if isinstance(symbol, (ir.AllocaInstr, ir.GlobalVariable)):
                # 这是一个可能需要捕获的变量
                # 获取其类型
                if isinstance(symbol, ir.AllocaInstr):
                    var_type = symbol.allocated_type
                else:
                    var_type = symbol.type.pointee
                captured_vars[name] = symbol
                captured_types.append(var_type)
                captured_names.append(name)
        
        # 确定参数类型（显式参数 + 捕获的变量）
        param_types = []
        for param in expr.parameters:
            if param.type_annotation:
                param_types.append(self._llvm_type(param.type_annotation.type_name))
            else:
                param_types.append(ir.IntType(32))  # 默认整数
        
        # 添加捕获变量的类型
        param_types.extend(captured_types)
        
        # 创建函数类型
        func_type = ir.FunctionType(return_type, param_types)
        
        # 创建函数
        function = ir.Function(self.module, func_type, name=lambda_name)
        
        # 设置参数名
        for i, param in enumerate(expr.parameters):
            function.args[i].name = param.name
        
        # 设置捕获变量参数名
        for i, name in enumerate(captured_names):
            function.args[len(expr.parameters) + i].name = f"_captured_{name}"
        
        # 创建入口基本块
        entry_block = function.append_basic_block(name="entry")
        builder = ir.IRBuilder(entry_block)
        
        # 保存当前状态
        old_function = self.current_function
        old_builder = self.current_basic_block
        old_builder_instance = self.builder
        old_symbols = self.symbols.copy()
        
        self.current_function = function
        self.current_basic_block = entry_block
        self.builder = builder
        
        # 添加显式参数到符号表
        for i, param in enumerate(expr.parameters):
            param_ptr = builder.alloca(param_types[i])
            builder.store(function.args[i], param_ptr)
            self.symbols[param.name] = param_ptr
        
        # 添加捕获变量到符号表
        for i, name in enumerate(captured_names):
            param_idx = len(expr.parameters) + i
            var_ptr = builder.alloca(captured_types[i])
            builder.store(function.args[param_idx], var_ptr)
            self.symbols[name] = var_ptr
        
        # 生成函数体
        if isinstance(expr.body, Block):
            # 多行块
            self._generate_statement(expr.body)
            # 如果没有返回语句，添加隐式返回
            if not builder.block.is_terminated:
                builder.ret(ir.Constant(return_type, 0))
        else:
            # 单行表达式
            result = self._generate_expression(expr.body)
            builder.ret(result)
        
        # 恢复状态
        self.current_function = old_function
        self.current_basic_block = old_builder
        self.builder = old_builder_instance
        self.symbols = old_symbols
        
        # 返回函数指针
        # 在LLVM中，我们需要返回函数的地址
        builder = self._get_builder()
        func_ptr = builder.bitcast(function, ir.PointerType(ir.IntType(8)))
        return func_ptr


# ==================== 测试函数 ====================

if __name__ == '__main__':
    # 测试代码
    test_code = """
    函数 主():
        变量 x = 10
        变量 y = x + 20
        返回 y
    """
    
    print("测试代码生成器:")
    print("=" * 50)
    print("源代码:")
    print(test_code)
    print("=" * 50)
    
    from .lexer import tokenize_string
    from .parser import Parser
    
    tokens = tokenize_string(test_code)
    parser = Parser(tokens)
    ast = parser.parse()
    
    codegen = CodeGenerator()
    llvm_ir = codegen.generate(ast)
    
    print("生成的LLVM IR:")
    print(llvm_ir)
