"""词法分析器"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Token:
    """词法单元"""
    type: str
    value: str
    line: int
    column: int
    
    def __str__(self):
        return f"Token({self.type}, '{self.value}', 行:{self.line}, 列:{self.column})"


class LexerError(Exception):
    """词法分析错误"""
    def __init__(self, message, line, column):
        super().__init__(f"词法错误 (行:{line}, 列:{column}): {message}")
        self.line = line
        self.column = column


class Lexer:
    """太和语言词法分析器"""
    
    # 关键字定义
    KEYWORDS = {
        # 控制流
        '如果', '否则', '循环', '当', '对于', '在', '不在', '中断', '继续', '返回',
        # 类型系统
        '整数', '浮点', '字符', '字符串', '布尔', '空值', '数组', '列表', '字典', '元组',
        # 面向对象
        '类', '新建', '这', '继承', '重写', '接口', '抽象', '枚举',
        # 函数和变量
        '函数', '变量', '常量', '导入', '从', '作为', '导出',
        # DLL相关
        'DLL', 'dll',
        # 控制台相关
        '控制台', '内容', '执行', '销毁',
        # 更新/定时器相关
        '更新', '暂停', '继续',
        # UI相关
        '窗口', '组件', '布局', '事件', '属性', '样式',
        # 值
        '真', '假', '空',
    }
    
    # 运算符和标点符号
    OPERATORS = {
        '+', '-', '*', '/', '%', '=', '==', '!=', '<', '>', '<=', '>=',
        '&&', '||', '!', '&', '|', '^', '~', '<<', '>>',
        '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=',
    }
    
    PUNCTUATION = {
        '(', ')', '[', ']', '{', '}', ',', ':', ';', '.', '->', '=>', '@',
    }
    
    # 正则表达式模式
    PATTERNS = [
        # 空白字符（忽略空格、制表符、回车符、全角空格）
        (r'[ \t\r\u3000]+', None),
        # 换行符（用于缩进处理）
        (r'\n', 'NEWLINE'),
        # 注释（单行）
        (r'#[^\n]*', None),
        # 数字
        (r'\d+\.\d+', 'FLOAT'),      # 浮点数
        (r'\d+', 'INTEGER'),         # 整数
        # f-字符串（插值字符串，必须在普通字符串之前匹配）
        (r'f"[^"\\]*(?:\\.[^"\\]*)*"', 'FSTRING'),    # f"..." 字符串
        (r"f'[^'\\]*(?:\\.[^'\\]*)*'", 'FSTRING'),    # f'...' 字符串
        # 字符串
        (r'"[^"\\]*(?:\\.[^"\\]*)*"', 'STRING'),    # 双引号字符串
        (r"'[^'\\]*(?:\\.[^'\\]*)*'", 'STRING'),    # 单引号字符串
        # UI标签相关 - 需要优先匹配较长模式
        (r'</', 'UI_TAG_SLASH'),     # 结束标签的斜杠
        (r'/>', 'UI_TAG_SELF_CLOSE'), # 自闭合标签斜杠
        # 运算符和标点（必须在UI标签之前，以便单独的<和>作为运算符）
        (r'->', 'ARROW'),
        (r'=>', 'FAT_ARROW'),
        (r'==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|^=|<<=|>>=', 'OPERATOR'),
        (r'[+\-*/%=<>&|^!~]', 'OPERATOR'),
        # UI标签开始和结束（单独的<和>，但上面运算符已匹配，所以这里可能不会匹配到）
        (r'<', 'UI_TAG_OPEN'),       # 标签开始
        (r'>', 'UI_TAG_CLOSE'),      # 标签结束
        # 标识符和关键字（支持Unicode字符，包括中文）
        (r'[^\W\d]\w*', 'IDENTIFIER'),  # 以字母或下划线开头，后跟字母、数字或下划线
        # 标点符号（支持全角和半角）
        (r'[(),.:;{}\[\]@，。：；（）｛｝［］]', 'PUNCTUATION'),
    ]

    # 全角标点到半角标点的映射
    FULL_WIDTH_TO_HALF_WIDTH = {
        '，': ',',
        '。': '.',
        '：': ':',
        '；': ';',
        '（': '(',
        '）': ')',
        '｛': '{',
        '｝': '}',
        '［': '[',
        '］': ']',
    }

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.errors = []
        
        # 缩进处理相关
        self.indent_stack = [0]  # 缩进级别栈，栈底为0
        self.at_line_start = True
        self.current_indent = 0
        
        # 编译正则表达式（启用Unicode支持）
        self.regex_patterns = []
        for pattern, token_type in self.PATTERNS:
            self.regex_patterns.append((re.compile(pattern, re.UNICODE), token_type))
    
    def tokenize(self) -> List[Token]:
        """将源代码转换为词法单元列表"""
        self.tokens = []
        self.errors = []
        self.position = 0
        self.line = 1
        self.column = 1
        self.indent_stack = [0]
        self.at_line_start = True
        self.current_indent = 0
        
        # 预处理：将 "DLL函数" 替换为 "DLL 函数"（中间加空格）
        # 这样 lexer 就能正确识别为两个关键字
        source = self.source_code
        source = source.replace('DLL函数', 'DLL 函数')
        self.source_code = source
        
        while self.position < len(self.source_code):
            token = self._next_token()
            if token:
                self.tokens.append(token)
        
        # 文件结束时，关闭所有未闭合的缩进
        while self.indent_stack[-1] > 0:
            self.tokens.append(Token('DEDENT', '', self.line, self.column))
            self.indent_stack.pop()
        
        # 添加结束标记
        self.tokens.append(Token('EOF', '', self.line, self.column))
        return self.tokens
    
    def _next_token(self) -> Optional[Token]:
        """读取下一个词法单元"""
        if self.position >= len(self.source_code):
            return None
        
        # 处理行首缩进
        if self.at_line_start:
            # 计算当前行的缩进
            indent_level = 0
            i = self.position
            while i < len(self.source_code) and self.source_code[i] in ' \t':
                if self.source_code[i] == '\t':
                    indent_level += 4 - (indent_level % 4)  # 制表符对齐到4的倍数
                else:  # 空格
                    indent_level += 1
                i += 1
            
            # 检查是否为空行（缩进后是换行符或文件结束）
            if i >= len(self.source_code) or self.source_code[i] == '\n':
                # 空行，跳过缩进空格，不改变缩进栈
                # 如果有换行符，消耗它
                if i < len(self.source_code) and self.source_code[i] == '\n':
                    self._update_position('\n')
                else:
                    self.position = i
                    self.column = 1
                # 保持 at_line_start = True
                return self._next_token()
            
            # 与栈顶缩进比较
            top_indent = self.indent_stack[-1]
            
            if indent_level > top_indent:
                # 缩进增加
                self.indent_stack.append(indent_level)
                # 消耗缩进空格
                self.position += (i - self.position)
                self.column = indent_level + 1
                self.at_line_start = False
                return Token('INDENT', '', self.line, self.column - 1)
            
            elif indent_level < top_indent:
                # 缩进减少，生成一个或多个 DEDENT token
                # 消耗缩进空格
                self.position += (i - self.position)
                self.column = indent_level + 1
                self.at_line_start = False
                
                # 弹出栈顶直到找到匹配的缩进级别
                dedent_tokens = []
                while self.indent_stack[-1] > indent_level:
                    self.indent_stack.pop()
                    dedent_tokens.append(Token('DEDENT', '', self.line, self.column - 1))
                
                # 如果缩进级别不在栈中，记录错误并调整缩进栈
                if self.indent_stack[-1] != indent_level:
                    error_msg = f"缩进不一致：期望 {self.indent_stack[-1]} 个空格，得到 {indent_level}"
                    self.errors.append((error_msg, self.line, self.column))
                    print(f"词法警告: {error_msg}")
                    # 调整缩进栈：将当前缩进级别推入栈中（视为新的缩进级别）
                    self.indent_stack.append(indent_level)
                
                # 返回第一个 DEDENT token，剩余的将在后续调用中返回
                # 为此，我们需要存储待返回的 DEDENT tokens
                if not hasattr(self, '_pending_dedents'):
                    self._pending_dedents = []
                self._pending_dedents.extend(dedent_tokens[1:])
                return dedent_tokens[0]
            
            else:
                # 缩进级别相同，消耗缩进空格，继续处理
                self.position = i
                self.column = indent_level + 1
                self.at_line_start = False
        
        # 检查是否有待返回的 DEDENT tokens
        if hasattr(self, '_pending_dedents') and self._pending_dedents:
            token = self._pending_dedents.pop(0)
            return token
        
        # 尝试匹配所有模式
        for regex, token_type in self.regex_patterns:
            match = regex.match(self.source_code, self.position)
            if match:
                value = match.group(0)
                
                # 标准化标点符号（全角转半角）
                if token_type == 'PUNCTUATION' and value in self.FULL_WIDTH_TO_HALF_WIDTH:
                    value = self.FULL_WIDTH_TO_HALF_WIDTH[value]
                
                # 如果是忽略的token（空白或注释）
                if token_type is None:
                    # 更新行号和列号
                    self._update_position(value)
                    return self._next_token()
                
                # 如果是 NEWLINE token
                if token_type == 'NEWLINE':
                    # 更新位置（换行）
                    self._update_position(value)
                    # 设置行首标志
                    self.at_line_start = True
                    # 不返回 token，继续下一个 token
                    return self._next_token()
                
                # 创建token
                token = Token(token_type, value, self.line, self.column)
                
                # 更新位置
                self._update_position(value)
                
                # 如果是标识符，检查是否是关键字
                if token_type == 'IDENTIFIER' and value in self.KEYWORDS:
                    token.type = 'KEYWORD'
                
                return token
        
        # 没有匹配的模式，记录错误并跳过字符
        char = self.source_code[self.position]
        
        # 检查是否可能是全角标点
        half_width = self.FULL_WIDTH_TO_HALF_WIDTH.get(char)
        if half_width:
            error_msg = f"无法识别的字符: '{char}'（全角标点）。请使用半角标点 '{half_width}'"
        else:
            error_msg = f"无法识别的字符: '{char}'"
        
        self.errors.append((error_msg, self.line, self.column))
        print(f"词法警告: {error_msg}")
        # 跳过该字符
        self._update_position(char)
        # 继续尝试下一个字符
        return self._next_token()
    
    def _update_position(self, text: str):
        """更新当前位置（行号和列号）"""
        lines = text.split('\n')
        if len(lines) > 1:
            # 跨越多行
            self.line += len(lines) - 1
            self.column = len(lines[-1]) + 1
            # 遇到换行符，下一行开始
            self.at_line_start = True
        else:
            # 单行内
            self.column += len(text)
        self.position += len(text)
    
    def peek(self) -> Optional[Token]:
        """查看下一个token而不消耗它"""
        if not hasattr(self, '_peek_cache'):
            self._peek_cache = self._next_token()
        return self._peek_cache
    
    def consume(self, expected_type: Optional[str] = None) -> Token:
        """消耗下一个token，可选地检查类型"""
        token = self._next_token()
        if not token:
            raise LexerError("意外的文件结束", self.line, self.column)
        
        if expected_type and token.type != expected_type:
            raise LexerError(
                f"期望 {expected_type}，但得到 {token.type}",
                token.line, token.column
            )
        
        return token


def tokenize_string(source_code: str) -> List[Token]:
    """快速词法分析函数"""
    lexer = Lexer(source_code)
    return lexer.tokenize()


if __name__ == '__main__':
    # 测试代码
    test_code = """
    # 简单的测试程序
    函数 主():
        变量 x = 10
        变量 y = 3.14
        变量 姓名 = "张三"
        
        如果 x > 0:
            输出("正数")
        否则:
            输出("非正数")
        
        返回 0
    """
    
    print("测试词法分析器:")
    print("=" * 50)
    print("源代码:")
    print(test_code)
    print("=" * 50)
    
    lexer = Lexer(test_code)
    tokens = lexer.tokenize()
    
    print("词法单元:")
    for token in tokens:
        print(f"  {token}")