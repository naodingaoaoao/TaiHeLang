"""TaiHeLang Python 解释器/运行时
支持 WinUI3 风格（默认）和 Win32 GUI"""
import sys
import math
import re
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .ast import Program, ClassDeclaration, FunctionDeclaration, VariableDeclaration


class TaiHeObject:
    """TaiHeLang 对象基类"""
    pass


# WinUI3 风格 UI（使用 tkinter 实现）
# 这个文件没有啥用 不能实现我的高性能目标，但是作为无法实现的代替，在未来会被解决


import tkinter as tk
from tkinter import ttk

class WinUIWindow(TaiHeObject):
    """WinUI3 风格窗口"""
    _instance = None
    
    def __init__(self, title: str = "窗口", 宽度: int = 800, 高度: int = 600):
        # 单例模式：只创建一个主窗口
        if WinUIWindow._instance is None:
            self.window = tk.Tk()
            WinUIWindow._instance = self
        else:
            self.window = WinUIWindow._instance.window
        
        self.window.title(title)
        self.window.geometry(f"{宽度}x{高度}")
        self.window.configure(bg='#f3f3f3')  # WinUI3 浅灰背景
        self.layout = None
        self.widgets = []
        self._title = title
        self._layout_obj = None
    
    def 设置布局(self, layout):
        self._layout_obj = layout
        # 延迟构建：在显示时才创建组件
    
    def _build_ui(self):
        """构建 UI 组件树"""
        if self._layout_obj is None:
            return
        
        layout = self._layout_obj
        
        if hasattr(layout, 'cells'):
            # 网格布局
            layout._create_frame(self)
            for (row, col), widget in layout.cells.items():
                if hasattr(widget, '_create_widget'):
                    widget._create_widget(self)
                    colspan = getattr(widget, '跨列', 1)
                    widget.widget.grid(row=row, column=col, columnspan=colspan, 
                                       sticky="nsew", padx=4, pady=4)
        
        elif hasattr(layout, 'children'):
            # 垂直布局
            layout._create_frame(self)
            for widget in layout.children:
                if hasattr(widget, '_create_widget'):
                    widget._create_widget(self)
                    widget.widget.pack(fill=tk.X, pady=4)
        
        elif hasattr(layout, 'frame'):
            layout.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def 显示(self):
        # 在显示前构建 UI
        self._build_ui()
        self.window.mainloop()
    
    def 关闭(self):
        self.window.quit()


class WinUITextBox(TaiHeObject):
    """WinUI3 风格文本框"""
    def __init__(self, text: str = "", 只读: bool = False, 多行: bool = False):
        self._parent = None
        self._text = text
        self._readonly = 只读
        self._multiline = 多行
        self.widget = None
        self._样式 = ""
    
    def _create_widget(self, parent):
        if self.widget:
            return
        
        self._parent = parent
        win = parent.window if isinstance(parent, WinUIWindow) else parent
        
        if self._multiline:
            self.widget = tk.Text(win, height=3, font=('Segoe UI', 11), 
                                  bg='white', relief='flat', borderwidth=1)
            self.widget.insert('1.0', self._text)
        else:
            self.widget = tk.Entry(win, font=('Segoe UI', 11), 
                                   bg='white', relief='flat', borderwidth=1)
            self.widget.insert(0, self._text)
        
        if self._readonly:
            self.widget.config(state='disabled' if self._multiline else 'readonly')
        
        # 应用样式
        if self._样式:
            self.样式 = self._样式
    
    @property
    def 文本(self) -> str:
        if self.widget is None:
            return self._text
        if self._multiline:
            return self.widget.get('1.0', 'end-1c')
        return self.widget.get()
    
    @文本.setter
    def 文本(self, value: str):
        self._text = str(value)
        if self.widget is None:
            return
        
        if self._multiline:
            state = self.widget.cget('state')
            if state == 'disabled':
                self.widget.config(state='normal')
                self.widget.delete('1.0', 'end')
                self.widget.insert('1.0', self._text)
                self.widget.config(state='disabled')
            else:
                self.widget.delete('1.0', 'end')
                self.widget.insert('1.0', self._text)
        else:
            state = self.widget.cget('state')
            if state == 'readonly':
                self.widget.config(state='normal')
                self.widget.delete(0, 'end')
                self.widget.insert(0, self._text)
                self.widget.config(state='readonly')
            else:
                self.widget.delete(0, 'end')
                self.widget.insert(0, self._text)
    
    @property
    def 样式(self) -> str:
        return self._样式
    
    @样式.setter
    def 样式(self, value: str):
        self._样式 = value
        if self.widget is None:
            return
        
        # WinUI3 风格解析
        if "字体大小" in value:
            match = re.search(r'字体大小:\s*(\d+)px', value)
            if match:
                size = int(match.group(1))
                self.widget.config(font=('Segoe UI', size))
        
        if "文本对齐: 右对齐" in value:
            if not self._multiline:
                self.widget.config(justify='right')
        
        if "背景:" in value:
            match = re.search(r'背景:\s*#?([a-fA-F0-9]{6})', value)
            if match:
                color = '#' + match.group(1)
                self.widget.config(bg=color)


class WinUIButton(TaiHeObject):
    """WinUI3 风格按钮"""
    def __init__(self, text: str = ""):
        self._text = text
        self.widget = None
        self._样式 = ""
        self._点击事件 = None
    
    def _create_widget(self, parent):
        if self.widget:
            return
        
        win = parent.window if isinstance(parent, WinUIWindow) else parent
        self.widget = tk.Button(win, text=self._text, font=('Segoe UI', 11),
                                bg='#0078d4', fg='white',  # WinUI3 默认蓝色
                                activebackground='#106ebe',
                                relief='flat', borderwidth=0, 
                                padx=20, pady=8, cursor='hand2')
        
        # 应用样式
        if self._样式:
            self.样式 = self._样式
        
        # 绑定事件
        if self._点击事件:
            self.widget.config(command=self._点击事件)
    
    @property
    def 样式(self) -> str:
        return self._样式
    
    @样式.setter
    def 样式(self, value: str):
        self._样式 = value
        if self.widget is None:
            return
        
        if "背景:" in value:
            match = re.search(r'背景:\s*#?([a-fA-F0-9]{6})', value)
            if match:
                color = '#' + match.group(1)
                self.widget.config(bg=color, activebackground=color)
        
        if "颜色: 白色" in value:
            self.widget.config(fg='white')
        
        if "字体大小" in value:
            match = re.search(r'字体大小:\s*(\d+)px', value)
            if match:
                size = int(match.group(1))
                self.widget.config(font=('Segoe UI', size))
    
    @property
    def 跨列(self) -> int:
        return self.widget.cget('columnspan') if self.widget else 1
    
    @跨列.setter
    def 跨列(self, value: int):
        if self.widget:
            self.widget.config(columnspan=value)
    
    @property
    def 点击事件(self):
        return self._点击事件
    
    @点击事件.setter
    def 点击事件(self, handler):
        self._点击事件 = handler
        if self.widget and handler:
            self.widget.config(command=handler)


class WinUIGridLayout(TaiHeObject):
    """WinUI3 风格网格布局"""
    def __init__(self, 行数: int = 1, 列数: int = 1):
        self.行数 = 行数
        self.列数 = 列数
        self.frame = None
        self.cells: Dict[tuple, Any] = {}
    
    def _create_frame(self, parent):
        if self.frame:
            return
        
        win = parent.window if isinstance(parent, WinUIWindow) else parent
        self.frame = tk.Frame(win, bg='#f3f3f3')
        
        # 配置行列权重
        for i in range(self.列数):
            self.frame.grid_columnconfigure(i, weight=1)
        for i in range(self.行数):
            self.frame.grid_rowconfigure(i, weight=1)
    
    def 添加(self, widget, row: int, col: int, rowspan=1, colspan=1):
        self.cells[(row, col)] = widget
    
    def 获取组件(self, row: int, col: int):
        return self.cells.get((row, col))


class WinUIVerticalLayout(TaiHeObject):
    """WinUI3 风格垂直布局"""
    def __init__(self):
        self.frame = None
        self.children = []
    
    def _create_frame(self, parent):
        if self.frame:
            return
        
        win = parent.window if isinstance(parent, WinUIWindow) else parent
        self.frame = tk.Frame(win, bg='#f3f3f3')
    
    def 添加(self, widget, stretch=0):
        self.children.append(widget)


class WinUIRadioButton(TaiHeObject):
    """WinUI3 风格单选按钮"""
    def __init__(self, text: str = "", 组: str = ""):
        self._text = text
        self._group = 组
        self.widget = None
        self._选中 = False
    
    def _create_widget(self, parent):
        win = parent.window if isinstance(parent, WinUIWindow) else parent
        self.widget = tk.Radiobutton(win, text=self._text, font=('Segoe UI', 11),
                                     bg='#f3f3f3', selectcolor='#0078d4')
    
    @property
    def 选中(self) -> bool:
        if self.widget:
            return self.widget.cget('selectcolor') == '#0078d4'
        return self._选中
    
    @选中.setter
    def 选中(self, value: bool):
        self._选中 = value


class WinUICheckBox(TaiHeObject):
    """WinUI3 风格复选框"""
    def __init__(self, text: str = ""):
        self._text = text
        self.widget = None
        self.var = None
    
    def _create_widget(self, parent):
        win = parent.window if isinstance(parent, WinUIWindow) else parent
        self.var = tk.BooleanVar()
        self.widget = tk.Checkbutton(win, text=self._text, variable=self.var,
                                     font=('Segoe UI', 11), bg='#f3f3f3',
                                     selectcolor='#0078d4')
    
    @property
    def 选中(self) -> bool:
        return self.var.get() if self.var else False
    
    @选中.setter
    def 选中(self, value: bool):
        if self.var:
            self.var.set(value)


class WinUILabel(TaiHeObject):
    """WinUI3 风格标签"""
    def __init__(self, text: str = ""):
        self._text = text
        self.widget = None
    
    def _create_widget(self, parent):
        win = parent.window if isinstance(parent, WinUIWindow) else parent
        self.widget = tk.Label(win, text=self._text, font=('Segoe UI', 11),
                               bg='#f3f3f3', fg='#1a1a1a')
    
    @property
    def 文本(self) -> str:
        return self._text
    
    @文本.setter
    def 文本(self, value: str):
        self._text = str(value)
        if self.widget:
            self.widget.config(text=self._text)


class WinUIComboBox(TaiHeObject):
    """WinUI3 风格下拉框"""
    def __init__(self, 选项列表=None):
        self._options = 选项列表 or []
        self.widget = None
        self.var = None
    
    def _create_widget(self, parent):
        win = parent.window if isinstance(parent, WinUIWindow) else parent
        self.var = tk.StringVar()
        self.widget = ttk.Combobox(win, textvariable=self.var, 
                                   values=self._options, font=('Segoe UI', 11))
        if self._options:
            self.var.set(self._options[0])
    
    @property
    def 当前选项(self) -> str:
        return self.var.get() if self.var else ""
    
    @当前选项.setter
    def 当前选项(self, value: str):
        if self.var:
            self.var.set(value)


# ============================================
# Win32 GUI 模块（使用 ctypes）
# ============================================

class Win32Module:
    """Win32 GUI 模块"""
    
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.gdi32 = ctypes.windll.gdi32
        
        # 定义常用类型
        self.HWND = wintypes.HWND
        self.LPARAM = wintypes.LPARAM
        self.WPARAM = wintypes.WPARAM
        self.LRESULT = wintypes.LPARAM
        
        # MessageBox
        self.MessageBoxW = self.user32.MessageBoxW
        self.MessageBoxW.argtypes = [self.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
        self.MessageBoxW.restype = ctypes.c_int
        
        # 常量
        self.MB_OK = 0x00000000
        self.MB_OKCANCEL = 0x00000001
        self.MB_YESNO = 0x00000004
        self.MB_ICONINFORMATION = 0x00000040
        self.MB_ICONWARNING = 0x00000030
        self.MB_ICONERROR = 0x00000010
        self.IDOK = 1
        self.IDCANCEL = 2
        self.IDYES = 6
        self.IDNO = 7
    
    def 消息框(self, 文本: str, 标题: str = "提示", 类型: str = "信息") -> str:
        """显示消息框"""
        flags = self.MB_OK
        if 类型 == "警告":
            flags |= self.MB_ICONWARNING
        elif 类型 == "错误":
            flags |= self.MB_ICONERROR
        else:
            flags |= self.MB_ICONINFORMATION
        
        result = self.MessageBoxW(None, 文本, 标题, flags)
        return "确定" if result == self.IDOK else "取消"
    
    def 确认框(self, 文本: str, 标题: str = "确认") -> bool:
        """显示确认框"""
        result = self.MessageBoxW(None, 文本, 标题, self.MB_YESNO | self.MB_ICONQUESTION)
        return result == self.IDYES
    
    def 输入框(self, 提示: str, 标题: str = "输入", 默认值: str = "") -> str:
        """显示输入框（使用简单对话框）"""
        import tkinter.simpledialog as sd
        root = tk.Tk()
        root.withdraw()
        result = sd.askstring(标题, 提示, initialvalue=默认值)
        root.destroy()
        return result or ""


# ============================================
# UI 模块（默认 WinUI3 风格）
# ============================================

class UIModule:
    """UI 模块 - WinUI3 风格"""
    
    @staticmethod
    def 窗口(title: str = "窗口", 宽度: int = 800, 高度: int = 600) -> WinUIWindow:
        return WinUIWindow(title, 宽度, 高度)
    
    @staticmethod
    def 文本框(text: str = "", 只读: bool = False, 多行: bool = False) -> WinUITextBox:
        return WinUITextBox(text, 只读, 多行)
    
    @staticmethod
    def 按钮(text: str = "") -> WinUIButton:
        return WinUIButton(text)
    
    @staticmethod
    def 网格布局(行数: int = 1, 列数: int = 1) -> WinUIGridLayout:
        return WinUIGridLayout(行数, 列数)
    
    @staticmethod
    def 垂直布局() -> WinUIVerticalLayout:
        return WinUIVerticalLayout()
    
    @staticmethod
    def 标签(text: str = "") -> WinUILabel:
        return WinUILabel(text)
    
    @staticmethod
    def 单选按钮(text: str = "", 组: str = "") -> WinUIRadioButton:
        return WinUIRadioButton(text, 组)
    
    @staticmethod
    def 复选框(text: str = "") -> WinUICheckBox:
        return WinUICheckBox(text)
    
    @staticmethod
    def 下拉框(选项列表=None) -> WinUIComboBox:
        return WinUIComboBox(选项列表)


# 内置函数
def 整数(value) -> int:
    return int(value)

def 浮点(value) -> float:
    return float(value)

def 字符串(value) -> str:
    return str(value)

def 范围(n: int):
    return range(n)

def 输出(*args):
    print(*args)


class TaiHeInterpreter:
    """TaiHeLang 解释器"""
    
    def __init__(self):
        self.global_scope: Dict[str, Any] = {
            'ui': UIModule(),
            '整数': 整数,
            '浮点': 浮点,
            '字符串': 字符串,
            '范围': 范围,
            '输出': 输出,
        }
        self.classes: Dict[str, type] = {}
        self._win32_module = None
    
    def _get_win32(self):
        """延迟加载 Win32 模块"""
        if self._win32_module is None:
            self._win32_module = Win32Module()
        return self._win32_module
    
    def run(self, source: str):
        """运行 TaiHeLang 源代码"""
        from .lexer import tokenize_string
        from .parser import Parser
        
        tokens = tokenize_string(source)
        parser = Parser(tokens)
        ast = parser.parse()
        
        self.execute_program(ast)
    
    def execute_program(self, ast: 'Program'):
        """执行程序"""
        from .ast import ClassDeclaration, FunctionDeclaration, ImportStatement
        
        # 第一遍：处理导入
        for stmt in ast.statements:
            if isinstance(stmt, ImportStatement):
                module_name = stmt.module
                if module_name == 'Win32' or module_name == 'win32':
                    self.global_scope['Win32'] = self._get_win32()
        
        # 第二遍：收集类定义
        for stmt in ast.statements:
            if isinstance(stmt, ClassDeclaration):
                self.define_class(stmt)
        
        # 第三遍：收集全局函数
        for stmt in ast.statements:
            if isinstance(stmt, FunctionDeclaration):
                self.define_function(stmt)
        
        # 调用主函数
        if '主' in self.global_scope:
            self.global_scope['主']()
    
    def define_class(self, cls: 'ClassDeclaration'):
        """定义类"""
        from .ast import VariableDeclaration, FunctionDeclaration
        class_dict = {
            '__init__': None,
            'methods': {},
            'members': [],
        }
        
        # 收集成员变量和方法
        for member in cls.members:
            if isinstance(member, VariableDeclaration):
                class_dict['members'].append(member.name)
            elif isinstance(member, FunctionDeclaration):
                if member.name == '__新建__':
                    class_dict['__init__'] = member
                else:
                    class_dict['methods'][member.name] = member
        
        self.classes[cls.name] = class_dict
        self.global_scope[cls.name] = lambda: self.create_instance(cls.name)
    
    def create_instance(self, class_name: str):
        """创建类实例"""
        class_dict = self.classes[class_name]
        instance = TaiHeObject()
        instance.__class__.__name__ = class_name
        
        # 初始化成员变量
        for member in class_dict['members']:
            setattr(instance, member, None)
        
        # 调用构造函数
        if class_dict['__init__']:
            self.execute_method(instance, class_dict['__init__'], [])
        
        return instance
    
    def execute_method(self, instance, method, args):
        """执行方法"""
        local_scope = {
            '这': instance,
            **self.global_scope
        }
        
        # 绑定参数
        for i, param in enumerate(method.parameters):
            if i < len(args):
                local_scope[param.name] = args[i]
        
        # 执行方法体
        return self.execute_block(method.body, local_scope)
    
    def define_function(self, func: 'FunctionDeclaration'):
        """定义函数"""
        def function_wrapper(*args):
            local_scope = {**self.global_scope}
            for i, param in enumerate(func.parameters):
                if i < len(args):
                    local_scope[param.name] = args[i]
            return self.execute_block(func.body, local_scope)
        
        self.global_scope[func.name] = function_wrapper
    
    def execute_block(self, block, local_scope: dict) -> Any:
        """执行代码块"""
        from .ast import (
            VariableDeclaration, ExpressionStatement, ReturnStatement,
            IfStatement, WhileStatement, ForStatement,
            ListLiteral, LambdaExpression, Block
        )
        
        result = None
        
        # 处理 else if 链
        if isinstance(block, IfStatement):
            condition = self.evaluate(block.condition, local_scope)
            if condition:
                return self.execute_block(block.then_branch, local_scope)
            elif block.else_branch:
                return self.execute_block(block.else_branch, local_scope)
            return None
        
        # 正常 Block 处理
        for stmt in block.statements:
            if isinstance(stmt, VariableDeclaration):
                value = self.evaluate(stmt.value, local_scope) if stmt.value else None
                local_scope[stmt.name] = value
            
            elif isinstance(stmt, ExpressionStatement):
                self.evaluate(stmt.expression, local_scope)
            
            elif isinstance(stmt, ReturnStatement):
                return self.evaluate(stmt.value, local_scope) if stmt.value else None
            
            elif isinstance(stmt, IfStatement):
                condition = self.evaluate(stmt.condition, local_scope)
                if condition:
                    result = self.execute_block(stmt.then_branch, local_scope)
                elif stmt.else_branch:
                    result = self.execute_block(stmt.else_branch, local_scope)
            
            elif isinstance(stmt, WhileStatement):
                while self.evaluate(stmt.condition, local_scope):
                    result = self.execute_block(stmt.body, local_scope)
            
            elif isinstance(stmt, ForStatement):
                iterable = self.evaluate(stmt.iterable, local_scope)
                for item in iterable:
                    local_scope[stmt.variable] = item
                    result = self.execute_block(stmt.body, local_scope)
        
        return result
    
    def evaluate(self, expr, local_scope: dict) -> Any:
        """求值表达式"""
        from .ast import (
            Literal, StringInterpolation, Identifier, BinaryOperation,
            CallExpression, MemberAccess, Assignment, ListLiteral,
            LambdaExpression, SubscriptExpression, ThisExpression
        )
        
        if expr is None:
            return None
        
        if isinstance(expr, Literal):
            return expr.value
        
        # 处理 this/这 表达式
        if isinstance(expr, ThisExpression):
            if '这' in local_scope:
                return local_scope['这']
            raise NameError("this/这 不在当前作用域中")
        
        if isinstance(expr, StringInterpolation):
            parts = []
            for part in expr.parts:
                if isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(str(self.evaluate(part, local_scope)))
            return ''.join(parts)
        
        if isinstance(expr, Identifier):
            name = expr.name
            if name in local_scope:
                return local_scope[name]
            if name in self.global_scope:
                return self.global_scope[name]
            raise NameError(f"未定义的变量: {name}")
        
        if isinstance(expr, BinaryOperation):
            left = self.evaluate(expr.left, local_scope)
            right = self.evaluate(expr.right, local_scope)
            op = expr.operator
            
            if op == '+': return left + right
            if op == '-': return left - right
            if op == '*': return left * right
            if op == '/': return left / right
            if op == '%': return left % right
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '<': return left < right
            if op == '>': return left > right
            if op == '<=': return left <= right
            if op == '>=': return left >= right
            if op == '在': return left in right
            if op == '不在': return left not in right
            if op == '和': return left and right
            if op == '或': return left or right
            return None
        
        if isinstance(expr, CallExpression):
            callee = expr.callee
            args = [self.evaluate(arg, local_scope) for arg in expr.arguments]
            
            # 处理命名参数
            named_args = {}
            for na in expr.named_arguments:
                named_args[na.name] = self.evaluate(na.value, local_scope)
            
            # 模块函数调用 ui.窗口(...)
            if isinstance(callee, MemberAccess):
                obj = self.evaluate(callee.object, local_scope)
                
                # 处理 UI 组件创建
                if hasattr(obj, callee.member):
                    method = getattr(obj, callee.member)
                    result = method(*args, **named_args)
                    return result
                
                # 处理实例方法调用
                if isinstance(obj, TaiHeObject):
                    class_name = obj.__class__.__name__
                    if class_name in self.classes:
                        class_dict = self.classes[class_name]
                        if callee.member in class_dict['methods']:
                            method = class_dict['methods'][callee.member]
                            return self.execute_method(obj, method, args)
            
            # 普通函数调用
            if callable(callee):
                return callee(*args, **named_args)
            
            # 从作用域获取函数
            func = self.evaluate(callee, local_scope)
            if callable(func):
                return func(*args)
        
        if isinstance(expr, MemberAccess):
            obj = self.evaluate(expr.object, local_scope)
            
            # 首先检查实例是否有该属性
            if hasattr(obj, expr.member):
                return getattr(obj, expr.member)
            
            # 检查是否是类实例，并查找类方法
            if isinstance(obj, TaiHeObject):
                class_name = obj.__class__.__name__
                if class_name in self.classes:
                    class_dict = self.classes[class_name]
                    if expr.member in class_dict['methods']:
                        method = class_dict['methods'][expr.member]
                        def bound_method(*args, method=method, instance=obj):
                            return self.execute_method(instance, method, list(args))
                        return bound_method
            
            # 字典访问
            if isinstance(obj, dict):
                return obj.get(expr.member)
            
            raise AttributeError(f"{type(obj).__name__} 没有属性 {expr.member}")
        
        if isinstance(expr, Assignment):
            value = self.evaluate(expr.value, local_scope)
            if isinstance(expr.target, Identifier):
                local_scope[expr.target.name] = value
            elif isinstance(expr.target, MemberAccess):
                # 处理属性赋值，如 这.值 = 42
                obj = self.evaluate(expr.target.object, local_scope)
                setattr(obj, expr.target.member, value)
            return value
        
        if isinstance(expr, ListLiteral):
            return [self.evaluate(e, local_scope) for e in expr.elements]
        
        if isinstance(expr, LambdaExpression):
            def lambda_func(*args):
                lambda_scope = {**local_scope}
                for i, param in enumerate(expr.parameters):
                    lambda_scope[param.name] = args[i] if i < len(args) else None
                return self.execute_block(expr.body, lambda_scope)
            return lambda_func
        
        if isinstance(expr, SubscriptExpression):
            value = self.evaluate(expr.value, local_scope)
            slice_expr = expr.slice
            
            if slice_expr.start is not None and slice_expr.end is None and slice_expr.step is None:
                index = self.evaluate(slice_expr.start, local_scope)
                return value[index]
            else:
                start = self.evaluate(slice_expr.start, local_scope) if slice_expr.start else None
                end = self.evaluate(slice_expr.end, local_scope) if slice_expr.end else None
                step = self.evaluate(slice_expr.step, local_scope) if slice_expr.step else None
                return value[slice(start, end, step)]
        
        return None
    
    def _build_ui(self, window, layout):
        """构建 UI 组件树"""
        if hasattr(layout, 'cells'):
            # 网格布局
            layout._create_frame(window)
            for (row, col), widget in layout.cells.items():
                if hasattr(widget, '_create_widget'):
                    widget._create_widget(window)
                    colspan = getattr(widget, '跨列', 1)
                    widget.widget.grid(row=row, column=col, columnspan=colspan, 
                                       sticky="nsew", padx=4, pady=4)
        
        elif hasattr(layout, 'children'):
            # 垂直布局
            layout._create_frame(window)
            for widget in layout.children:
                if hasattr(widget, '_create_widget'):
                    widget._create_widget(window)
                    widget.widget.pack(fill=tk.X, pady=4)


def interpret_file(filepath: str):
    """解释执行文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    interpreter = TaiHeInterpreter()
    interpreter.run(source)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        interpret_file(sys.argv[1])
