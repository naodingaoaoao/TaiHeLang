"""抽象语法树节点定义"""
"""看不懂问AI"""

from dataclasses import dataclass, field
from typing import List, Optional, Union


# 基础

@dataclass
class Node:
    # 坤类
    line: int = 0
    column: int = 0


@dataclass
class Program(Node):
    # ROOT
    statements: List['Statement'] = field(default_factory=list)


# 语句

@dataclass
class Statement(Node):
    # 坤类
    pass


@dataclass
class ExpressionStatement(Statement):
    # 表达式语句
    expression: Optional['Expression'] = None
    
    def __post_init__(self):
        if self.expression is None:
            raise ValueError("ExpressionStatement必须包含expression")


@dataclass
class VariableDeclaration(Statement):
    #变量声明
    name: Optional[str] = None
    type_annotation: Optional['TypeAnnotation'] = None
    value: Optional['Expression'] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("VariableDeclaration必须包含name")


@dataclass
class DestructuringVariableDeclaration(Statement):
    # 变量 x, y = 坐标
    names: Optional[List[str]] = None
    type_annotation: Optional['TypeAnnotation'] = None
    value: Optional['Expression'] = None
    
    def __post_init__(self):
        if self.names is None or len(self.names) == 0:
            raise ValueError("DestructuringVariableDeclaration必须包含至少一个名称")


@dataclass
class ConstantDeclaration(Statement):
    # 常量声明
    name: Optional[str] = None
    type_annotation: Optional['TypeAnnotation'] = None
    value: Optional['Expression'] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("ConstantDeclaration必须包含name")


@dataclass
class FunctionDeclaration(Statement):
    # 函数声明
    name: Optional[str] = None
    parameters: Optional[List['Parameter']] = None
    return_type: Optional['TypeAnnotation'] = None
    body: Optional['Block'] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("FunctionDeclaration必须包含name")
        if self.parameters is None:
            self.parameters = []
        if self.body is None:
            raise ValueError("FunctionDeclaration必须包含body")


@dataclass
class ClassDeclaration(Statement):
    # 类声明
    name: Optional[str] = None
    base_class: Optional[str] = None
    members: Optional[List[Union['VariableDeclaration', 'FunctionDeclaration']]] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("ClassDeclaration必须包含name")
        if self.members is None:
            self.members = []


@dataclass
class ReturnStatement(Statement):
    # 返回
    value: Optional['Expression'] = None


@dataclass
class IfStatement(Statement):
    # 条件语句
    condition: Optional['Expression'] = None
    then_branch: Optional['Block'] = None
    else_branch: Optional['Block'] = None
    
    def __post_init__(self):
        if self.condition is None:
            raise ValueError("IfStatement必须包含condition")
        if self.then_branch is None:
            raise ValueError("IfStatement必须包含then_branch")


@dataclass
class WhileStatement(Statement):
    # 循环语句
    condition: Optional['Expression'] = None
    body: Optional['Block'] = None
    
    def __post_init__(self):
        if self.condition is None:
            raise ValueError("WhileStatement必须包含condition")
        if self.body is None:
            raise ValueError("WhileStatement必须包含body")


@dataclass
class ForStatement(Statement):
    # For循环语句（对于 x 在 列表）
    variable: Optional[str] = None
    iterable: Optional['Expression'] = None
    body: Optional['Block'] = None
    
    def __post_init__(self):
        if self.variable is None:
            raise ValueError("ForStatement必须包含variable")
        if self.iterable is None:
            raise ValueError("ForStatement必须包含iterable")
        if self.body is None:
            raise ValueError("ForStatement必须包含body")


@dataclass
class CStyleForStatement(Statement):
    # For循环语句 类似C
    init: Optional['Statement'] = None
    condition: Optional['Expression'] = None
    update: Optional['Statement'] = None
    body: Optional['Block'] = None
    
    def __post_init__(self):
        if self.condition is None:
            raise ValueError("CStyleForStatement必须包含condition")
        if self.body is None:
            raise ValueError("CStyleForStatement必须包含body")


@dataclass
class Block(Statement):
    # 代码块
    statements: Optional[List[Statement]] = None
    
    def __post_init__(self):
        if self.statements is None:
            self.statements = []


@dataclass
class ImportStatement(Statement):
    # 导入
    module: Optional[str] = None
    alias: Optional[str] = None
    
    def __post_init__(self):
        if self.module is None:
            raise ValueError("ImportStatement必须包含module")


@dataclass
class ExportStatement(Statement):
    # 导出
    declaration: Optional[Statement] = None
    
    def __post_init__(self):
        if self.declaration is None:
            raise ValueError("ExportStatement必须包含declaration")


@dataclass
class FromImportStatement(Statement):
    #从...导入...
    module: Optional[str] = None
    imported_names: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.module is None:
            raise ValueError("FromImportStatement必须包含module")
        if self.imported_names is None or len(self.imported_names) == 0:
            raise ValueError("FromImportStatement必须包含至少一个导入名称")



@dataclass
class DLLFunctionDeclaration(Statement):
    # DLL导出函数声明语句 似乎弃用了
    name: Optional[str] = None
    parameters: Optional[List['Parameter']] = None
    return_type: Optional['TypeAnnotation'] = None
    body: Optional['Block'] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("DLLFunctionDeclaration必须包含name")
        if self.parameters is None:
            self.parameters = []
        if self.body is None:
            raise ValueError("DLLFunctionDeclaration必须包含body")


@dataclass
class ImportDLLStatement(Statement):
    # DLL导入
    pass  # 仅声明


@dataclass
class DLLFunctionBinding(Statement):
    # DLL函数绑定语句
    lib_name: Optional[str] = None  # lib变量名
    func_name: Optional[str] = None  # 函数名
    param_types: Optional[List['TypeAnnotation']] = None  # 参数类型列表
    return_type: Optional['TypeAnnotation'] = None  # 返回类型


@dataclass
class UpdateStatement(Statement):
    # 定时器
    count: Optional['Expression'] = None  # 执行次数（0为无穷）
    interval: Optional['Expression'] = None  # 间隔时间（毫秒）
    name: Optional[str] = None  # 循环名称（可选）
    body: Optional['Block'] = None  # 更新体
    
    def __post_init__(self):
        if self.count is None:
            raise ValueError("UpdateStatement必须包含count")
        if self.interval is None:
            raise ValueError("UpdateStatement必须包含interval")
        if self.body is None:
            raise ValueError("UpdateStatement必须包含body")


# 表达式节点

@dataclass
class Expression(Node):
    # 鸡肋
    pass


@dataclass
class Literal(Expression):
    # 字面量
    value: Optional[Union[int, float, str, bool, None]] = None


@dataclass
class StringInterpolation(Expression):
    # 字符串插值
    parts: Optional[List[Union[str, 'Expression']]] = None
    
    def __post_init__(self):
        if self.parts is None:
            self.parts = []


@dataclass
class Identifier(Expression):
    # 标识符
    name: Optional[str] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("Identifier必须包含name")


@dataclass
class ThisExpression(Expression):
    # 这.表达式（类实例自身引用）如果你们觉得此更合适，可以换掉啊
    pass


@dataclass
class BinaryOperation(Expression):
    # 二元运算
    left: Optional[Expression] = None
    operator: Optional[str] = None
    right: Optional[Expression] = None
    
    def __post_init__(self):
        if self.left is None:
            raise ValueError("BinaryOperation必须包含left")
        if self.operator is None:
            raise ValueError("BinaryOperation必须包含operator")
        if self.right is None:
            raise ValueError("BinaryOperation必须包含right")


@dataclass
class DLLLoadExpression(Expression):
    # DLL加载
    path: Optional['Expression'] = None


@dataclass
class DLLFunctionCall(Expression):
    # DLL函数调用
    lib_name: Optional[str] = None  # lib变量名
    func_name: Optional[str] = None  # 函数名
    arguments: Optional[List['Expression']] = None
    
    def __post_init__(self):
        if self.arguments is None:
            self.arguments = []


@dataclass
class ConsoleCreateExpression(Expression):
    # 控制台创建cmd biaoda指令
    hidden: Optional['Expression'] = None  # 隐藏/显示（0=隐藏，1=显示）
    keep: Optional['Expression'] = None  # 执行完销毁/保留（0=销毁，1=保留）
    command: Optional['Expression'] = None  # 执行的命令
    
    def __post_init__(self):
        if self.command is None:
            raise ValueError("ConsoleCreateExpression必须包含command")


@dataclass
class ConsoleMemberAccess(Expression):
    # 控制台成员访问（内容、执行、销毁）
    console_name: Optional[str] = None  # 控制台变量名
    member: Optional[str] = None  # 成员名（内容、执行、销毁）
    arguments: Optional[List['Expression']] = None  # 参数（用于执行）
    
    def __post_init__(self):
        if self.console_name is None:
            raise ValueError("ConsoleMemberAccess必须包含console_name")
        if self.member is None:
            raise ValueError("ConsoleMemberAccess必须包含member")


@dataclass
class UpdateMemberAccess(Expression):
    # 更新循环成员访问
    update_name: Optional[str] = None  # 更新循环变量名
    member: Optional[str] = None  # 成员名（销毁、暂停、继续）
    
    def __post_init__(self):
        if self.update_name is None:
            raise ValueError("UpdateMemberAccess必须包含update_name")
        if self.member is None:
            raise ValueError("UpdateMemberAccess必须包含member")


@dataclass
class UpdateCallExpression(Expression):
    #更新循环调用表达式（更新参数）
    update_name: Optional[str] = None  # 更新循环变量名
    count: Optional['Expression'] = None  # 执行次数
    interval: Optional['Expression'] = None  # 间隔时间
    
    def __post_init__(self):
        if self.update_name is None:
            raise ValueError("UpdateCallExpression必须包含update_name")


@dataclass
class UnaryOperation(Expression):
    # 运算
    operator: Optional[str] = None
    operand: Optional[Expression] = None
    
    def __post_init__(self):
        if self.operator is None:
            raise ValueError("UnaryOperation必须包含operator")
        if self.operand is None:
            raise ValueError("UnaryOperation必须包含operand")


@dataclass
class CallExpression(Expression):
    # 调用函数
    callee: Optional[Expression] = None
    arguments: Optional[List[Expression]] = None
    named_arguments: Optional[List['NamedArgument']] = None  # 命名参数
    
    def __post_init__(self):
        if self.callee is None:
            raise ValueError("CallExpression必须包含callee")
        if self.arguments is None:
            self.arguments = []
        if self.named_arguments is None:
            self.named_arguments = []


@dataclass
class NamedArgument(Node):
    # 起名函数
    name: Optional[str] = None
    value: Optional[Expression] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("NamedArgument必须包含name")
        if self.value is None:
            raise ValueError("NamedArgument必须包含value")


@dataclass
class MemberAccess(Expression):
    # 拜亲戚 成员访问
    object: Optional[Expression] = None
    member: Optional[str] = None
    
    def __post_init__(self):
        if self.object is None:
            raise ValueError("MemberAccess必须包含object")
        if self.member is None:
            raise ValueError("MemberAccess必须包含member")


@dataclass
class Assignment(Expression):
    # 赋值打钱
    target: Optional[Expression] = None
    value: Optional[Expression] = None
    
    def __post_init__(self):
        if self.target is None:
            raise ValueError("Assignment必须包含target")
        if self.value is None:
            raise ValueError("Assignment必须包含value")


@dataclass
class ListLiteral(Expression):
    # 面子工程
    elements: Optional[List[Expression]] = None
    
    def __post_init__(self):
        if self.elements is None:
            self.elements = []


@dataclass
class TupleExpression(Expression):
    # 杂货铺子
    elements: Optional[List[Expression]] = None
    
    def __post_init__(self):
        if self.elements is None:
            self.elements = []


@dataclass
class DictLiteral(Expression):
    # 字典字面量
    entries: Optional[List['DictEntry']] = None
    
    def __post_init__(self):
        if self.entries is None:
            self.entries = []


@dataclass
class LambdaExpression(Expression):
    # Lambda表达
    parameters: Optional[List['Parameter']] = None
    body: Optional['Expression'] = None  # 表达式或块
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.body is None:
            raise ValueError("LambdaExpression必须包含body")


@dataclass
class ListComprehension(Expression):
    # 列表推导
    expression: Optional[Expression] = None
    variable: Optional[str] = None
    iterable: Optional[Expression] = None
    condition: Optional[Expression] = None
    
    def __post_init__(self):
        if self.expression is None:
            raise ValueError("ListComprehension必须包含expression")
        if self.variable is None:
            raise ValueError("ListComprehension必须包含variable")
        if self.iterable is None:
            raise ValueError("ListComprehension必须包含iterable")


@dataclass
class SubscriptExpression(Expression):
    # 初步实现的下标表达式
    value: Optional[Expression] = None
    slice: Optional['SliceExpression'] = None
    
    def __post_init__(self):
        if self.value is None:
            raise ValueError("SubscriptExpression必须包含value")
        if self.slice is None:
            raise ValueError("SubscriptExpression必须包含slice")


@dataclass
class SliceExpression(Expression):
    # 切片表达式
    start: Optional[Expression] = None
    end: Optional[Expression] = None
    step: Optional[Expression] = None
    
    def __post_init__(self):
        if self.start is None and self.end is None and self.step is None:
            raise ValueError("SliceExpression至少需要start、end、step中的一个")


# 类型

@dataclass
class TypeAnnotation(Node):
    #类型注解
    type_name: Optional[str] = None
    generic_args: Optional[List['TypeAnnotation']] = None
    
    def __post_init__(self):
        if self.type_name is None:
            raise ValueError("TypeAnnotation必须包含type_name")
        if self.generic_args is None:
            self.generic_args = []


@dataclass
class Parameter(Node):
    # 函数参数
    name: Optional[str] = None
    type_annotation: Optional[TypeAnnotation] = None
    default_value: Optional[Expression] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("Parameter必须包含name")


@dataclass
class DictEntry(Node):
    # 字典
    key: Optional[Expression] = None
    value: Optional[Expression] = None
    
    def __post_init__(self):
        if self.key is None:
            raise ValueError("DictEntry必须包含key")
        if self.value is None:
            raise ValueError("DictEntry必须包含value")


# UI相关节点 很shi，还不能用
@dataclass
class UIElement(Node):
    # UI元素基类 
    tag: Optional[str] = None
    attributes: Optional[List['UIAttribute']] = None
    children: Optional[List[Union['UIElement', Expression]]] = None
    
    def __post_init__(self):
        if self.tag is None:
            raise ValueError("UIElement必须包含tag")
        if self.attributes is None:
            self.attributes = []
        if self.children is None:
            self.children = []


@dataclass
class UIAttribute(Node):
    # UI属性 
    name: Optional[str] = None
    value: Optional[Union[str, int, float, bool, 'Expression']] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("UIAttribute必须包含name")
        if self.value is None:
            raise ValueError("UIAttribute必须包含value")


@dataclass
class StyleRule(Node):
    # 样式规则 
    selector: Optional[str] = None
    properties: Optional[List['StyleProperty']] = None
    
    def __post_init__(self):
        if self.selector is None:
            raise ValueError("StyleRule必须包含selector")
        if self.properties is None:
            self.properties = []


@dataclass
class StyleProperty(Node):
    # 样式属性 
    name: Optional[str] = None
    value: Optional[str] = None
    
    def __post_init__(self):
        if self.name is None:
            raise ValueError("StyleProperty必须包含name")
        if self.value is None:
            raise ValueError("StyleProperty必须包含value")


@dataclass
class EventHandler(Node):
    # 事件处理器
    event_type: Optional[str] = None
    handler: Optional[Expression] = None
    
    def __post_init__(self):
        if self.event_type is None:
            raise ValueError("EventHandler必须包含event_type")
        if self.handler is None:
            raise ValueError("EventHandler必须包含handler")


# 辅助函数

def print_ast(node: Node, indent: int = 0) -> str:
    if isinstance(node, Program):
        result = "Program:\n"
        for stmt in node.statements:
            result += print_ast(stmt, indent + 1)
        return result
    
    elif isinstance(node, Block):
        result = "  " * indent + "Block:\n"
        for stmt in node.statements:
            result += print_ast(stmt, indent + 1)
        return result
    
    elif isinstance(node, VariableDeclaration):
        result = "  " * indent + f"VariableDeclaration({node.name}"
        if node.type_annotation:
            result += f": {node.type_annotation.type_name}"
        if node.value:
            result += f" = ..."
        result += ")\n"
        if node.value:
            result += print_ast(node.value, indent + 1)
        return result
    
    elif isinstance(node, ExpressionStatement):
        result = "  " * indent + "ExpressionStatement:\n"
        if node.expression:
            result += print_ast(node.expression, indent + 1)
        return result
    
    elif isinstance(node, FunctionDeclaration):
        result = "  " * indent + f"FunctionDeclaration({node.name})"
        if node.return_type:
            result += f" -> {node.return_type.type_name}"
        result += "\n"
        result += print_ast(node.body, indent + 1)
        return result
    
    elif isinstance(node, IfStatement):
        result = "  " * indent + "IfStatement:\n"
        result += "  " * (indent + 1) + "条件:\n"
        result += print_ast(node.condition, indent + 2)
        result += "  " * (indent + 1) + "Then:\n"
        result += print_ast(node.then_branch, indent + 2)
        if node.else_branch:
            result += "  " * (indent + 1) + "Else:\n"
            result += print_ast(node.else_branch, indent + 2)
        return result
    
    elif isinstance(node, Literal):
        return "  " * indent + f"Literal({node.value!r})\n"
    
    elif isinstance(node, Identifier):
        return "  " * indent + f"Identifier({node.name!r})\n"
    
    elif isinstance(node, BinaryOperation):
        result = "  " * indent + f"BinaryOperation({node.operator})\n"
        result += print_ast(node.left, indent + 1)
        result += print_ast(node.right, indent + 1)
        return result
    
    elif isinstance(node, CallExpression):
        result = "  " * indent + f"CallExpression:\n"
        result += print_ast(node.callee, indent + 1)
        if node.arguments:
            result += "  " * (indent + 1) + "参数:\n"
            for arg in node.arguments:
                result += print_ast(arg, indent + 2)
        return result
    
    elif isinstance(node, UIElement):
        result = "  " * indent + f"UIElement(tag={node.tag!r}, 属性={len(node.attributes)}, 子元素={len(node.children)}):\n"
        if node.attributes:
            result += "  " * (indent + 1) + "属性:\n"
            for attr in node.attributes:
                result += print_ast(attr, indent + 2)
        if node.children:
            result += "  " * (indent + 1) + "子元素:\n"
            for child in node.children:
                result += print_ast(child, indent + 2)
        return result
    
    elif isinstance(node, UIAttribute):
        if isinstance(node.value, (str, int, float, bool)) or node.value is None:
            value_str = repr(node.value)
        else:
            value_str = "..."
        return "  " * indent + f"UIAttribute(name={node.name!r}, value={value_str})\n"
    
    elif isinstance(node, StyleRule):
        result = "  " * indent + f"StyleRule(selector={node.selector!r}):\n"
        if node.properties:
            result += "  " * (indent + 1) + "属性:\n"
            for prop in node.properties:
                result += print_ast(prop, indent + 2)
        return result
    
    elif isinstance(node, StyleProperty):
        return "  " * indent + f"StyleProperty(name={node.name!r}, value={node.value!r})\n"
    
    elif isinstance(node, EventHandler):
        return "  " * indent + f"EventHandler(event_type={node.event_type!r}, handler=...)\n"
    
    else:
        return "  " * indent + f"{node.__class__.__name__}(...)\n"