"""语法分析器"""
from typing import List, Optional
from .lexer import Token, LexerError
from .ast import *
from .ast import CStyleForStatement, ThisExpression, NamedArgument


class ParserError(Exception):
    """语法分析错误"""
    def __init__(self, message, token: Token):
        super().__init__(f"语法错误 (行:{token.line}, 列:{token.column}): {message}")
        self.token = token


class Parser:
    """太和语言语法分析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.current_token = tokens[0] if tokens else None
        self.errors = []
    
    def parse(self) -> Program:
        """解析整个程序"""
        program = Program()
        
        while not self._is_at_end():
            stmt = self._parse_statement()
            if stmt:
                program.statements.append(stmt)
        
        return program
    
    # ==================== 辅助方法 ====================
    
    def _advance(self) -> Token:
        """前进到下一个token，跳过 NEWLINE 标记"""
        if not self._is_at_end():
            self.position += 1
            
            # 跳过 NEWLINE 标记（不影响缩进）
            while (self.position < len(self.tokens) and 
                   self.tokens[self.position].type == 'NEWLINE'):
                self.position += 1
            
            self.current_token = self.tokens[self.position] if self.position < len(self.tokens) else None
        return self.tokens[self.position - 1] if self.position > 0 else None
    
    def _peek(self) -> Token:
        """查看下一个token而不消耗它，跳过 NEWLINE 标记"""
        next_pos = self.position + 1
        # 跳过 NEWLINE 标记（不影响缩进）
        while (next_pos < len(self.tokens) and 
               self.tokens[next_pos].type == 'NEWLINE'):
            next_pos += 1
        
        if next_pos < len(self.tokens):
            return self.tokens[next_pos]
        return None
    
    def _peek_n(self, n: int) -> Token:
        """查看后面第 n 个 token 而不消耗它，跳过 NEWLINE 标记
        _peek_n(1) 相当于 _peek()，返回下一个 token
        _peek_n(2) 返回下下个 token
        """
        next_pos = self.position + 1
        count = 0
        while next_pos < len(self.tokens) and count < n:
            if self.tokens[next_pos].type != 'NEWLINE':
                count += 1
                if count == n:
                    # 找到第 n 个非 NEWLINE token，直接返回
                    return self.tokens[next_pos]
            next_pos += 1
        
        return None
    
    def _is_at_end(self) -> bool:
        """是否到达文件末尾"""
        if self.current_token is None:
            return True
        return self.position >= len(self.tokens) or self.current_token.type == 'EOF'
    
    def _check(self, token_type: str) -> bool:
        """检查当前token类型"""
        return not self._is_at_end() and self.current_token.type == token_type
    
    def _match(self, token_type: str) -> bool:
        """如果当前token匹配则消耗它"""
        if self._check(token_type):
            self._advance()
            return True
        return False
    
    def _error(self, message: str, token: Token) -> None:
        """记录语法错误"""
        # 基础错误信息
        error_msg = f"语法错误 (行:{token.line}, 列:{token.column}): {message} (当前 token: 类型={token.type}, 值='{token.value}')"
        
        # 添加额外提示
        hints = []
        
        # 检查是否可能是全角/半角标点问题
        if token.type == 'PUNCTUATION':
            hints.append("请检查是否使用了全角标点（如：，。：；）而不是半角标点（,.:;）")
        
        # 检查是否缺少分角标点（全角转半角映射）
        full_width_map = {'，': ',', '。': '.', '：': ':', '；': ';', '（': '(', '）': ')', '｛': '{', '｝': '}', '［': '[', '］': ']'}
        if token.value in full_width_map:
            hints.append(f"检测到全角标点 '{token.value}'，请使用半角标点 '{full_width_map[token.value]}'")
        
        # 检查是否缺少分号或冒号
        if '期望' in message and any(punct in message for punct in [':', ';', ',', '(', ')', '[', ']', '{', '}']):
            hints.append("请检查标点符号是否正确，注意全角/半角区别")
        
        # 检查是否缺少关键字
        if '期望' in message and 'KEYWORD' not in message:
            # 提取期望的内容
            import re
            match = re.search(r"期望 ['\"](.+?)['\"]", message)
            if match:
                expected = match.group(1)
                hints.append(f"请确保使用了正确的关键字或符号: '{expected}'")
        
        # 组合提示
        if hints:
            error_msg += "\n提示: " + "；".join(hints)
        
        self.errors.append(error_msg)
        print(f"警告: {error_msg}")
    
    def _synchronize(self) -> None:
        """同步恢复：跳过token直到遇到同步点"""
        # 同步点：换行、分号、关键字等
        while not self._is_at_end():
            token = self.current_token
            if token.type == 'NEWLINE':
                self._advance()
                return
            if token.type == 'DEDENT':
                # DEDENT表示块结束，是重要的同步点
                self._advance()
                return
            if token.type == 'PUNCTUATION' and token.value == ';':
                self._advance()
                return
            # 如果是语句开始的关键字，也停止
            if token.type == 'KEYWORD':
                keyword = token.value
                if keyword in ('函数', '变量', '类', '导入', '导出', '返回', '如果', '当', '对于'):
                    return
            # 遇到结束符号也停止：')', ']', '}'
            if token.type == 'PUNCTUATION' and token.value in (')', ']', '}'):
                return
            # 否则继续跳过
            self._advance()
    
    def _consume(self, token_type: str, message: str) -> Token:
        """消耗指定类型的token，如果类型不匹配则记录错误并尝试恢复"""
        if self._check(token_type):
            return self._advance()
        
        # 保存当前token用于错误报告
        error_token = self.current_token
        # 记录错误
        self._error(message, error_token)
        # 尝试同步恢复
        self._synchronize()
        
        # 返回一个占位token，防止调用者崩溃
        if error_token:
            return Token(type='ERROR', value='', line=error_token.line, column=error_token.column)
        else:
            # 如果没有当前token，使用默认值
            return Token(type='ERROR', value='', line=0, column=0)
    
    # ==================== 解析方法 ====================
    
    def _parse_statement(self) -> Statement:
        """解析语句"""
        # 跳过开始的 INDENT（可能在某些上下文中出现）
        if self._check('INDENT'):
            self._advance()
        
        if self._check('KEYWORD'):
            keyword = self.current_token.value
            
            if keyword == '函数':
                return self._parse_function_declaration()
            elif keyword == 'DLL':
                return self._parse_dll_function_declaration()
            elif keyword == '变量':
                return self._parse_variable_declaration()
            elif keyword == '常量':
                return self._parse_constant_declaration()
            elif keyword == '类':
                return self._parse_class_declaration()
            elif keyword == '从':
                return self._parse_from_import_statement()
            elif keyword == '导入':
                return self._parse_import_statement()
            elif keyword == '导出':
                return self._parse_export_statement()
            elif keyword == '返回':
                return self._parse_return_statement()
            elif keyword == '如果':
                return self._parse_if_statement()
            elif keyword == '当':
                return self._parse_while_statement()
            elif keyword == '对于':
                return self._parse_for_statement()
            elif keyword == '循环':
                return self._parse_cstyle_for_statement()
            elif keyword == '更新':
                return self._parse_update_statement()
            
            # 特殊处理：某些关键字可以作为变量名使用（如 内容、执行、销毁、暂停、继续）
            if keyword in ('内容', '执行', '销毁', '暂停', '继续'):
                next_token = self._peek()
                if next_token and next_token.type == 'OPERATOR' and next_token.value == '=':
                    # 作为变量名使用，解析为隐式变量声明
                    return self._parse_implicit_variable_declaration_with_keyword(keyword)
        
        # 检查是否是隐式变量声明（标识符后跟等号）
        if self._check('IDENTIFIER'):
            # 向前看下一个token是否是等号或点号
            next_token = self._peek()
            if next_token and next_token.type == 'OPERATOR' and next_token.value == '=':
                return self._parse_implicit_variable_declaration()
            # 检查是否是 DLL 函数绑定：lib.func = ([类型], 返回类型)
            # 需要 lookahead 检查是否是 lib.func = ( 的模式
            elif next_token and next_token.type == 'PUNCTUATION' and next_token.value == '.':
                # 再向前看 token，检查是否是标识符后面跟着 = 和 (
                next_next_token = self._peek_n(2)
                next_next_next_token = self._peek_n(3)
                next_next_next_next_token = self._peek_n(4)
                # DLL 函数绑定的模式：lib.func = ([...], 返回类型)
                # 检查：标识符 . 标识符/关键字 = (
                if (next_next_token and next_next_token.type in ('IDENTIFIER', 'KEYWORD') and
                    next_next_next_token and next_next_next_token.type == 'OPERATOR' and next_next_next_token.value == '=' and
                    next_next_next_next_token and next_next_next_next_token.type == 'PUNCTUATION' and next_next_next_next_token.value == '('):
                    return self._parse_dll_function_binding()
                # 否则，作为普通表达式语句处理（如 a.执行() 或 a.样式 = 值）
        
        # 表达式语句
        expr = self._parse_expression()
        if expr:
            # 消耗分号（如果有）
            self._match('PUNCTUATION')
            return ExpressionStatement(expression=expr)
        
        # 无法解析语句，跳过当前token以避免无限循环
        if not self._is_at_end() and self.current_token:
            self._error(f"无法解析的语句开始", self.current_token)
            self._advance()
        
        return None
    
    def _parse_function_declaration(self) -> FunctionDeclaration:
        """解析函数声明"""
        # 消耗 '函数' 关键字
        func_token = self._consume('KEYWORD', "期望 '函数'")
        
        # 函数名（可以是IDENTIFIER或某些关键字）
        if self._check('IDENTIFIER'):
            name_token = self._advance()
            name = name_token.value
        elif self._check('KEYWORD'):
            name_token = self._advance()
            name = name_token.value
        else:
            name_token = self._consume('IDENTIFIER', "期望函数名")
            name = name_token.value if name_token else ""
        
        # 参数列表
        self._consume('PUNCTUATION', "期望 '('")
        parameters = []
        
        if not self._check('PUNCTUATION') or self.current_token.value != ')':
            while True:
                # 参数名（可以是IDENTIFIER或某些关键字）
                if self._check('IDENTIFIER'):
                    param_name_token = self._advance()
                    param_name = param_name_token.value
                elif self._check('KEYWORD'):
                    param_name_token = self._advance()
                    param_name = param_name_token.value
                else:
                    param_name_token = self._consume('IDENTIFIER', "期望参数名")
                    param_name = param_name_token.value if param_name_token else ""
                
                # 类型注解（可选）
                type_annotation = None
                if self._check('PUNCTUATION') and self.current_token and self.current_token.value == ':':
                    self._advance()  # 消耗 ':'
                    type_annotation = self._parse_type_annotation()
                
                # 默认值（可选）
                default_value = None
                if self._check('OPERATOR') and self.current_token and self.current_token.value == '=':
                    self._advance()  # 消耗 '='
                    default_value = self._parse_expression()
                
                parameters.append(Parameter(
                    name=param_name,
                    type_annotation=type_annotation,
                    default_value=default_value,
                    line=param_name_token.line,
                    column=param_name_token.column
                ))
                
                # 检查是否有逗号（更多参数）
                if not (self._check('PUNCTUATION') and self.current_token.value == ','):
                    break
                self._advance()  # 消耗 ','
        
        self._consume('PUNCTUATION', "期望 ')'")
        
        # 返回类型（可选）
        return_type = None
        if self._check('OPERATOR') and self.current_token and self.current_token.value == '->':
            self._advance()  # 消耗 '->'
            return_type = self._parse_type_annotation()
        
        # 函数体
        self._consume('PUNCTUATION', "期望 ':'")
        body = self._parse_block()
        
        return FunctionDeclaration(
            name=name,
            parameters=parameters,
            return_type=return_type,
            body=body,
            line=func_token.line,
            column=func_token.column
        )
    
    def _parse_dll_function_declaration(self) -> 'DLLFunctionDeclaration':
        """解析DLL导出函数声明"""
        # 消耗 'DLL' 关键字
        dll_token = self._consume('KEYWORD', "期望 'DLL'")
        
        # 消耗 '函数' 关键字
        self._consume('KEYWORD', "期望 '函数'")
        
        # 函数名
        name_token = self._consume('IDENTIFIER', "期望函数名")
        name = name_token.value
        
        # 参数列表
        self._consume('PUNCTUATION', "期望 '('")
        parameters = []
        
        if not self._check('PUNCTUATION') or self.current_token.value != ')':
            while True:
                # 类型注解（可选但推荐）
                type_annotation = None
                if self._check('KEYWORD') and self.current_token.value in ['整数', '浮点', '字符', '字符串', '布尔']:
                    type_annotation = self._parse_type_annotation()
                
                # 参数名
                param_name_token = self._consume('IDENTIFIER', "期望参数名")
                param_name = param_name_token.value
                
                # 如果前面没有类型，检查后面是否有类型
                if type_annotation is None and self._check('KEYWORD') and self.current_token.value in ['整数', '浮点', '字符', '字符串', '布尔']:
                    type_annotation = self._parse_type_annotation()
                
                parameters.append(Parameter(
                    name=param_name,
                    type_annotation=type_annotation,
                    default_value=None,
                    line=param_name_token.line,
                    column=param_name_token.column
                ))
                
                # 检查是否有逗号（更多参数）
                if not (self._check('PUNCTUATION') and self.current_token.value == ','):
                    break
                self._advance()  # 消耗 ','
        
        self._consume('PUNCTUATION', "期望 ')'")
        
        # 返回类型（可选）
        return_type = None
        if self._check('KEYWORD') and self.current_token.value in ['整数', '浮点', '字符', '字符串', '布尔']:
            return_type = self._parse_type_annotation()
        
        # 函数体
        self._consume('PUNCTUATION', "期望 ':'")
        body = self._parse_block()
        
        return DLLFunctionDeclaration(
            name=name,
            parameters=parameters,
            return_type=return_type,
            body=body,
            line=dll_token.line,
            column=dll_token.column
        )
    
    def _parse_variable_declaration(self) -> Statement:
        """解析变量声明（支持解构：变量 x, y = 坐标）"""
        # 消耗 '变量' 关键字
        var_token = self._consume('KEYWORD', "期望 '变量'")
        
        # 解析第一个标识符（可以是IDENTIFIER或某些关键字）
        names = []
        if self._check('IDENTIFIER'):
            first_token = self._advance()
            names.append(first_token.value)
        elif self._check('KEYWORD'):
            # 某些关键字可以作为变量名
            first_token = self._advance()
            names.append(first_token.value)
        else:
            self._error("期望变量名", self.current_token)
            first_token = self.current_token
            names.append("")
        
        # 检查是否有逗号（解构）
        while self._check('PUNCTUATION') and self.current_token and self.current_token.value == ',':
            self._advance()  # 消耗 ','
            if self._check('IDENTIFIER'):
                next_token = self._advance()
                names.append(next_token.value)
            elif self._check('KEYWORD'):
                next_token = self._advance()
                names.append(next_token.value)
            else:
                self._error("期望变量名", self.current_token)
                names.append("")
        
        # 类型注解（可选）
        type_annotation = None
        if self._check('PUNCTUATION') and self.current_token and self.current_token.value == ':':
            self._advance()
            type_annotation = self._parse_type_annotation()
        
        # 初始值（可选）
        value = None
        if self._check('OPERATOR') and self.current_token and self.current_token.value == '=':
            self._advance()  # 消耗 '='
            value = self._parse_expression()
        
        # 消耗分号（如果有）
        self._match('PUNCTUATION')
        
        if len(names) == 1:
            # 单个变量
            return VariableDeclaration(
                name=names[0],
                type_annotation=type_annotation,
                value=value,
                line=var_token.line,
                column=var_token.column
            )
        else:
            # 解构变量
            return DestructuringVariableDeclaration(
                names=names,
                type_annotation=type_annotation,
                value=value,
                line=var_token.line,
                column=var_token.column
            )
    
    def _parse_constant_declaration(self) -> ConstantDeclaration:
        """解析常量声明"""
        # 消耗 '常量' 关键字
        const_token = self._consume('KEYWORD', "期望 '常量'")
        
        # 解析标识符
        name_token = self._consume('IDENTIFIER', "期望常量名")
        
        # 类型注解（可选）
        type_annotation = None
        if self._check('PUNCTUATION') and self.current_token and self.current_token.value == ':':
            self._advance()
            type_annotation = self._parse_type_annotation()
        
        # 初始值（必须）
        if not (self._check('OPERATOR') and self.current_token and self.current_token.value == '='):
            self._error("常量必须有初始值", self.current_token)
        self._advance()  # 消耗 '='
        value = self._parse_expression()
        
        # 消耗分号（如果有）
        self._match('PUNCTUATION')
        
        return ConstantDeclaration(
            name=name_token.value,
            type_annotation=type_annotation,
            value=value,
            line=const_token.line,
            column=const_token.column
        )
    
    def _parse_implicit_variable_declaration(self, consume_semicolon: bool = True) -> VariableDeclaration:
        """解析隐式变量声明（如：a = 1）"""
        # 获取标识符
        name_token = self._consume('IDENTIFIER', "期望变量名")
        
        # 消耗 '='
        self._consume('OPERATOR', "期望 '='")
        
        # 解析初始值
        value = self._parse_expression()
        
        # 消耗分号（如果有且需要）
        if consume_semicolon:
            self._match('PUNCTUATION')
        
        return VariableDeclaration(
            name=name_token.value,
            type_annotation=None,
            value=value,
            line=name_token.line,
            column=name_token.column
        )
    
    def _parse_implicit_variable_declaration_with_keyword(self, keyword: str) -> VariableDeclaration:
        """解析以关键字作为变量名的隐式变量声明（如：内容 = a.内容）"""
        # 消耗关键字
        keyword_token = self._advance()
        
        # 消耗 '='
        self._consume('OPERATOR', "期望 '='")
        
        # 解析初始值
        value = self._parse_expression()
        
        # 消耗分号（如果有）
        self._match('PUNCTUATION')
        
        return VariableDeclaration(
            name=keyword,
            type_annotation=None,
            value=value,
            line=keyword_token.line,
            column=keyword_token.column
        )
    
    def _parse_dll_function_binding(self) -> 'DLLFunctionBinding':
        """解析DLL函数绑定：lib.func = ([类型], 返回类型)"""
        # 获取 lib 变量名
        lib_token = self._consume('IDENTIFIER', "期望变量名")
        lib_name = lib_token.value
        
        # 消耗 '.'
        self._consume('PUNCTUATION', "期望 '.'")
        
        # 获取函数名（可以是标识符或某些关键字）
        if self._check('IDENTIFIER'):
            func_token = self._advance()
            func_name = func_token.value
        elif self._check('KEYWORD'):
            func_token = self._advance()
            func_name = func_token.value
        else:
            func_token = self._consume('IDENTIFIER', "期望函数名")
            func_name = func_token.value if func_token else ""
        
        # 消耗 '='
        self._consume('OPERATOR', "期望 '='")
        
        # 消耗 '('
        self._consume('PUNCTUATION', "期望 '('")
        
        # 消耗 '['
        self._consume('PUNCTUATION', "期望 '['")
        
        # 解析参数类型列表
        param_types = []
        while True:
            if self._check('KEYWORD') and self.current_token.value in ['整数', '浮点', '字符', '字符串', '布尔']:
                param_types.append(self._parse_type_annotation())
            else:
                break

            # 检查是否有逗号（更多参数）
            if self._check('PUNCTUATION') and self.current_token.value == ',':
                self._advance()  # 消耗 ','
            else:
                break
        
        # 消耗 ']'
        self._consume('PUNCTUATION', "期望 ']'")
        
        # 消耗 ','
        self._consume('PUNCTUATION', "期望 ','")
        
        # 解析返回类型
        return_type = None
        if self._check('KEYWORD') and self.current_token.value in ['整数', '浮点', '字符', '字符串', '布尔']:
            return_type = self._parse_type_annotation()
        
        # 消耗 ')'
        self._consume('PUNCTUATION', "期望 ')'")
        
        return DLLFunctionBinding(
            lib_name=lib_name,
            func_name=func_name,
            param_types=param_types,
            return_type=return_type,
            line=lib_token.line,
            column=lib_token.column
        )
    
    def _parse_class_declaration(self) -> ClassDeclaration:
        """解析类声明"""
        # 消耗 '类' 关键字
        class_token = self._consume('KEYWORD', "期望 '类'")
        
        # 类名
        name_token = self._consume('IDENTIFIER', "期望类名")
        name = name_token.value
        
        # 基类（可选）
        base_class = None
        if self._check('PUNCTUATION') and self.current_token and self.current_token.value == '(':
            self._advance()  # 消耗 '('
            base_token = self._consume('IDENTIFIER', "期望基类名")
            base_class = base_token.value
            self._consume('PUNCTUATION', "期望 ')'")
        
        # 类体
        self._consume('PUNCTUATION', "期望 ':'")
        
        # 检查是否有 INDENT
        if self._check('INDENT'):
            self._advance()  # 消耗 INDENT
        
        members = []
        while not self._is_at_end() and not self._check('EOF'):
            # 跳过 NEWLINE
            while self._check('NEWLINE'):
                self._advance()
            
            # 检查 DEDENT（类体结束）
            if self._check('DEDENT'):
                self._advance()  # 消耗 DEDENT
                break
            
            # 检查是否是类成员开始
            if self._check('KEYWORD'):
                keyword = self.current_token.value
                
                if keyword == '变量':
                    members.append(self._parse_variable_declaration())
                elif keyword == '函数':
                    members.append(self._parse_function_declaration())
                else:
                    break
            elif self._check('IDENTIFIER'):
                # 可能是隐式变量声明或其他
                break
            else:
                break
        
        return ClassDeclaration(
            name=name,
            base_class=base_class,
            members=members,
            line=class_token.line,
            column=class_token.column
        )
    
    def _parse_import_statement(self) -> ImportStatement:
        """解析导入语句"""
        # 消耗 '导入' 关键字
        import_token = self._consume('KEYWORD', "期望 '导入'")
        
        # 模块名（可以是标识符或字符串）
        module = ""
        if self._check('IDENTIFIER'):
            # 解析点分隔的模块名
            parts = []
            while self._check('IDENTIFIER'):
                token = self._advance()
                parts.append(token.value)
                if self._check('PUNCTUATION') and self.current_token.value == '.':
                    self._advance()  # 消耗 '.'
                else:
                    break
            module = '.'.join(parts)
        elif self._check('STRING'):
            token = self._advance()
            module = token.value.strip('"\'')
        else:
            self._error("期望模块名（标识符或字符串）", self.current_token)
            # 恢复
            self._synchronize()
            return ImportStatement(module="", line=import_token.line, column=import_token.column)
        
        # 别名（可选）
        alias = None
        if self._check('KEYWORD') and self.current_token and self.current_token.value == '作为':
            self._advance()  # 消耗 '作为'
            alias_token = self._consume('IDENTIFIER', "期望别名")
            alias = alias_token.value
        
        # 消耗分号（如果有）
        self._match('PUNCTUATION')
        
        return ImportStatement(
            module=module,
            alias=alias,
            line=import_token.line,
            column=import_token.column
        )
    
    def _parse_from_import_statement(self) -> FromImportStatement:
        """解析从...导入...语句"""
        # 消耗 '从' 关键字
        from_token = self._consume('KEYWORD', "期望 '从'")
        
        # 模块名（可以是标识符或字符串）
        module = ""
        if self._check('IDENTIFIER'):
            parts = []
            while self._check('IDENTIFIER'):
                token = self._advance()
                parts.append(token.value)
                if self._check('PUNCTUATION') and self.current_token.value == '.':
                    self._advance()  # 消耗 '.'
                else:
                    break
            module = '.'.join(parts)
        elif self._check('STRING'):
            token = self._advance()
            module = token.value.strip('"\'')
        else:
            self._error("期望模块名（标识符或字符串）", self.current_token)
            # 恢复
            self._synchronize()
            return FromImportStatement(module="", imported_names=[], line=from_token.line, column=from_token.column)
        
        # 消耗 '导入' 关键字
        self._consume('KEYWORD', "期望 '导入'")
        
        # 解析导入的标识符列表
        imported_names = []
        while True:
            if self._check('IDENTIFIER'):
                token = self._advance()
                imported_names.append(token.value)
            else:
                self._error("期望标识符", self.current_token)
                break
            
            # 检查是否有逗号（更多标识符）
            if self._check('PUNCTUATION') and self.current_token.value == ',':
                self._advance()  # 消耗 ','
            else:
                break
        
        # 消耗分号（如果有）
        self._match('PUNCTUATION')
        
        return FromImportStatement(
            module=module,
            imported_names=imported_names,
            line=from_token.line,
            column=from_token.column
        )

    def _parse_export_statement(self) -> ExportStatement:
        """解析导出语句"""
        # 消耗 '导出' 关键字
        export_token = self._consume('KEYWORD', "期望 '导出'")
        
        # 被导出的声明
        declaration = self._parse_statement()
        
        return ExportStatement(
            declaration=declaration,
            line=export_token.line,
            column=export_token.column
        )
    
    def _parse_return_statement(self) -> ReturnStatement:
        """解析返回语句"""
        # 消耗 '返回' 关键字
        return_token = self._consume('KEYWORD', "期望 '返回'")
        
        # 返回值（可选）
        value = None
        if not self._check('PUNCTUATION') or self.current_token.value != ';':
            value = self._parse_expression()
        
        # 消耗分号（如果有）
        self._match('PUNCTUATION')
        
        return ReturnStatement(
            value=value,
            line=return_token.line,
            column=return_token.column
        )
    
    def _parse_if_statement(self) -> IfStatement:
        """解析条件语句"""
        # 消耗 '如果' 关键字
        if_token = self._consume('KEYWORD', "期望 '如果'")

        # 条件
        condition = self._parse_expression()

        # then分支
        self._consume('PUNCTUATION', "期望 ':'")
        then_branch = self._parse_block()

        # else分支（可选）
        else_branch = None
        if self._check('KEYWORD') and self.current_token and self.current_token.value == '否则':
            self._advance()  # 消耗 '否则'

            # 检查是否是 '否则 如果' (elif)
            if self._check('KEYWORD') and self.current_token and self.current_token.value == '如果':
                # 递归解析 elif
                else_branch = self._parse_if_statement()
            else:
                # 普通 else
                self._consume('PUNCTUATION', "期望 ':'")
                else_branch = self._parse_block()

        return IfStatement(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=if_token.line,
            column=if_token.column
        )
    
    def _parse_while_statement(self) -> WhileStatement:
        """解析循环语句"""
        # 消耗 '当' 关键字
        while_token = self._consume('KEYWORD', "期望 '当'")
        
        # 条件
        condition = self._parse_expression()
        
        # 循环体
        self._consume('PUNCTUATION', "期望 ':'")
        body = self._parse_block()
        
        return WhileStatement(
            condition=condition,
            body=body,
            line=while_token.line,
            column=while_token.column
        )
    
    def _parse_for_statement(self) -> ForStatement:
        """解析for循环语句"""
        # 消耗 '对于' 关键字
        for_token = self._consume('KEYWORD', "期望 '对于'")
        
        # 循环变量
        variable_token = self._consume('IDENTIFIER', "期望循环变量名")
        variable = variable_token.value
        
        # '在' 关键字
        self._consume('KEYWORD', "期望 '在'")
        
        # 可迭代对象
        iterable = self._parse_expression()
        
        # 循环体
        self._consume('PUNCTUATION', "期望 ':'")
        body = self._parse_block()
        
        return ForStatement(
            variable=variable,
            iterable=iterable,
            body=body,
            line=for_token.line,
            column=for_token.column
        )
    
    def _parse_cstyle_for_statement(self) -> CStyleForStatement:
        """解析C风格for循环语句（循环 init; condition; update:）"""
        # 消耗 '循环' 关键字
        for_token = self._consume('KEYWORD', "期望 '循环'")
        
        # 初始化语句（可选）
        init = None
        if not self._check('PUNCTUATION') or self.current_token.value != ';':
            # 可能是变量声明或表达式
            if self._check('KEYWORD') and self.current_token.value == '变量':
                init = self._parse_variable_declaration()
            elif self._check('IDENTIFIER'):
                # 可能是隐式变量声明或表达式语句
                next_token = self._peek()
                if next_token and next_token.type == 'OPERATOR' and next_token.value == '=':
                    init = self._parse_implicit_variable_declaration(consume_semicolon=False)
                else:
                    # 表达式语句
                    expr = self._parse_expression()
                    if expr:
                        init = ExpressionStatement(expression=expr)
            else:
                # 表达式语句
                expr = self._parse_expression()
                if expr:
                    init = ExpressionStatement(expression=expr)
        
        # 分号
        self._consume('PUNCTUATION', "期望 ';'")
        
        # 条件表达式
        condition = self._parse_expression()
        
        # 分号
        self._consume('PUNCTUATION', "期望 ';'")
        
        # 更新语句（可选）
        update = None
        if not self._check('PUNCTUATION') or self.current_token.value != ':':
            # 表达式语句
            expr = self._parse_expression()
            if expr:
                update = ExpressionStatement(expression=expr)
        
        # 冒号
        self._consume('PUNCTUATION', "期望 ':'")
        
        # 循环体
        body = self._parse_block()
        
        return CStyleForStatement(
            init=init,
            condition=condition,
            update=update,
            body=body,
            line=for_token.line,
            column=for_token.column
        )
    
    def _parse_update_statement(self) -> 'UpdateStatement':
        """解析更新语句（定时器）：更新(次数, 间隔) -> 名称: ..."""
        # 消耗 '更新' 关键字
        update_token = self._consume('KEYWORD', "期望 '更新'")
        
        # 消耗 '('
        self._consume('PUNCTUATION', "期望 '('")
        
        # 解析执行次数
        count = self._parse_expression()
        
        # 消耗 ','
        self._consume('PUNCTUATION', "期望 ','")
        
        # 解析间隔时间（毫秒）
        interval = self._parse_expression()
        
        # 消耗 ')'
        self._consume('PUNCTUATION', "期望 ')'")
        
        # 可选的名称绑定 -> name
        name = None
        if self._check('ARROW') or (self._check('OPERATOR') and self.current_token.value == '->'):
            self._advance()  # 消耗 '->'
            name_token = self._consume('IDENTIFIER', "期望更新循环名称")
            name = name_token.value
        
        # 消耗 ':'
        self._consume('PUNCTUATION', "期望 ':'")
        
        # 解析循环体
        body = self._parse_block()
        
        return UpdateStatement(
            count=count,
            interval=interval,
            name=name,
            body=body,
            line=update_token.line,
            column=update_token.column
        )
    
    def _parse_block(self) -> Block:
        """解析代码块，支持多行缩进和单行语句"""
        block = Block()
        
        # 检查是否有 INDENT 标记（表示多行块）
        if self._check('INDENT'):
            # 消耗 INDENT 标记
            self._advance()
            
            # 解析块中的语句，直到遇到 DEDENT 标记
            while not self._is_at_end() and not self._check('DEDENT'):
                # 跳过 NEWLINE 标记
                while self._check('NEWLINE'):
                    self._advance()
                
                # 如果遇到 DEDENT，结束块
                if self._check('DEDENT'):
                    break
                
                # 如果遇到 EOF，结束块
                if self._is_at_end():
                    break
                    
                # 解析语句
                stmt = self._parse_statement()
                if stmt:
                    block.statements.append(stmt)
                else:
                    # 无法解析语句，跳过当前token以避免无限循环
                    if not self._is_at_end() and self.current_token:
                        self._error(f"无法解析的语句", self.current_token)
                        self._advance()
            
            # 消耗 DEDENT 标记（如果存在）
            if self._check('DEDENT'):
                self._advance()
        
        else:
            # 单行语句：解析一条语句
            if not self._is_at_end() and not self._check('EOF'):
                stmt = self._parse_statement()
                if stmt:
                    block.statements.append(stmt)
        
        return block
    
    def _parse_type_annotation(self) -> TypeAnnotation:
        """解析类型注解"""
        # 类型可以是关键字（整数、浮点等）或标识符或成员访问类型（ui.文本框）
        type_parts = []
        
        # 获取第一个类型部分
        if self._check('KEYWORD') and self.current_token.value in ['整数', '浮点', '字符', '字符串', '布尔', '空值', '数组', '列表', '字典', '元组']:
            type_token = self._advance()
            type_parts.append(type_token.value)
        elif self._check('IDENTIFIER'):
            type_token = self._advance()
            type_parts.append(type_token.value)
        elif self._check('KEYWORD'):
            # 关键字也可以作为类型名使用（如 窗口、布局 等）
            type_token = self._advance()
            type_parts.append(type_token.value)
        else:
            type_token = self._consume('IDENTIFIER', "期望类型名")
            if type_token:
                type_parts.append(type_token.value)
        
        # 检查是否有成员访问（ui.文本框）
        while self._check('PUNCTUATION') and self.current_token and self.current_token.value == '.':
            self._advance()  # 消耗 '.'
            if self._check('IDENTIFIER'):
                member_token = self._advance()
                type_parts.append(member_token.value)
            elif self._check('KEYWORD'):
                member_token = self._advance()
                type_parts.append(member_token.value)
            else:
                self._error("期望类型成员名", self.current_token)
                break
        
        # 组合类型名（用点连接）
        type_name = '.'.join(type_parts) if type_parts else "unknown"
        
        # 泛型参数（可选）
        generic_args = []
        if self._check('PUNCTUATION') and self.current_token and self.current_token.value == '<':
            self._advance()  # 消耗 '<'
            
            while True:
                generic_args.append(self._parse_type_annotation())
                
                if not (self._check('PUNCTUATION') and self.current_token.value == ','):
                    break
                self._advance()  # 消耗 ','
            
            self._consume('PUNCTUATION', "期望 '>'")
        
        return TypeAnnotation(
            type_name=type_name,
            generic_args=generic_args,
            line=type_token.line if type_token else 0,
            column=type_token.column if type_token else 0
        )
    
    # ==================== 表达式解析 ====================
    
    def _parse_expression(self) -> Optional[Expression]:
        """解析表达式"""
        return self._parse_assignment()
    
    def _parse_assignment(self) -> Optional[Expression]:
        """解析赋值表达式"""
        expr = self._parse_equality()
        
        if expr is None:
            return None
        
        if self._check('OPERATOR') and self.current_token and self.current_token.value == '=':
            operator_token = self.current_token
            operator = operator_token.value
            self._advance()  # 消耗运算符
            value = self._parse_assignment()
            if value is None:
                self._error("期望赋值表达式", self.current_token)
                return expr
            return Assignment(target=expr, value=value, line=expr.line, column=expr.column)
        
        # 处理复合赋值运算符 (+=, -=, *=, /=)
        if self._check('OPERATOR') and self.current_token and self.current_token.value in ('+=', '-=', '*=', '/='):
            op = self.current_token.value[0]  # 提取运算符
            self._advance()  # 消耗运算符
            value = self._parse_assignment()
            if value is None:
                self._error("期望赋值表达式", self.current_token)
                return expr
            # 将 a += b 转换为 a = a + b
            binary_op = BinaryOperation(left=expr, operator=op, right=value, line=expr.line, column=expr.column)
            return Assignment(target=expr, value=binary_op, line=expr.line, column=expr.column)
        
        return expr
    
    def _parse_equality(self) -> Optional[Expression]:
        """解析相等性比较"""
        expr = self._parse_comparison()
        
        while self._check('OPERATOR') and self.current_token and self.current_token.value in ('==', '!='):
            operator_token = self.current_token
            operator = operator_token.value
            self._advance()  # 消耗运算符
            right = self._parse_comparison()
            expr = BinaryOperation(
                left=expr,
                operator=operator,
                right=right,
                line=expr.line,
                column=expr.column
            )
        
        return expr
    
    def _parse_comparison(self) -> Optional[Expression]:
        """解析比较运算"""
        expr = self._parse_term()
        
        while self.current_token and (
            (self._check('OPERATOR') and self.current_token.value in ('<', '>', '<=', '>=', '==', '!=')) or
            (self._check('UI_TAG_OPEN') and self.current_token.value == '<') or
            (self._check('UI_TAG_CLOSE') and self.current_token.value == '>') or
            (self._check('KEYWORD') and self.current_token.value in ('在', '不在'))
        ):
            operator_token = self.current_token
            operator = operator_token.value
            # 将中文运算符转换为符号
            if operator == '在':
                operator = 'in'
            elif operator == '不在':
                operator = 'not in'
            self._advance()  # 消耗运算符
            right = self._parse_term()
            expr = BinaryOperation(
                left=expr,
                operator=operator,
                right=right,
                line=expr.line,
                column=expr.column
            )
        
        return expr
    
    def _parse_term(self) -> Optional[Expression]:
        """解析加减运算"""
        expr = self._parse_factor()
        
        while self._check('OPERATOR') and self.current_token and self.current_token.value in ('+', '-'):
            operator_token = self.current_token
            operator = operator_token.value
            self._advance()  # 消耗运算符
            right = self._parse_factor()
            expr = BinaryOperation(
                left=expr,
                operator=operator,
                right=right,
                line=expr.line,
                column=expr.column
            )
        
        return expr
    
    def _parse_factor(self) -> Optional[Expression]:
        """解析乘除运算"""
        expr = self._parse_unary()
        
        while self._check('OPERATOR') and self.current_token and self.current_token.value in ('*', '/', '%'):
            operator_token = self.current_token
            operator = operator_token.value
            self._advance()  # 消耗运算符
            right = self._parse_unary()
            expr = BinaryOperation(
                left=expr,
                operator=operator,
                right=right,
                line=expr.line,
                column=expr.column
            )
        
        return expr
    
    def _parse_unary(self) -> Optional[Expression]:
        """解析一元运算"""
        if self._check('OPERATOR') and self.current_token and self.current_token.value in ('+', '-', '!'):
            operator_token = self.current_token
            operator = operator_token.value
            self._advance()  # 消耗运算符
            operand = self._parse_unary()
            return UnaryOperation(
                operator=operator,
                operand=operand,
                line=operator_token.line,
                column=operator_token.column
            )
        
        return self._parse_postfix()
    
    def _parse_postfix(self) -> Optional[Expression]:
        """解析后缀操作（函数调用、下标、成员访问）"""
        expr = self._parse_primary()
        if expr is None:
            return None
        
        while True:
            # 函数调用
            if self._check('PUNCTUATION') and self.current_token.value == '(':
                expr = self._parse_call_expression(expr)
            # 下标操作（索引或切片）
            elif self._check('PUNCTUATION') and self.current_token.value == '[':
                expr = self._parse_subscript_expression(expr)
            # 成员访问（点操作符）
            elif self._check('PUNCTUATION') and self.current_token.value == '.':
                self._advance()  # 消耗 '.'
                
                # 获取成员名（可以是标识符或关键字）
                if self._check('IDENTIFIER'):
                    member_token = self._advance()
                    member_name = member_token.value
                elif self._check('KEYWORD'):
                    member_token = self._advance()
                    member_name = member_token.value
                else:
                    self._error("期望成员名", self.current_token)
                    break
                
                # 创建成员访问表达式
                expr = MemberAccess(
                    object=expr,
                    member=member_name,
                    line=expr.line,
                    column=expr.column
                )
            else:
                break
        
        return expr
    
    def _parse_subscript_expression(self, value: Expression) -> Expression:
        """解析下标表达式（索引或切片）"""
        # 消耗 '['
        start_token = self._consume('PUNCTUATION', "期望 '['")
        
        # 检查是否是切片表达式（包含 ':'）
        if self._check('PUNCTUATION') and self.current_token.value == ':':
            # 切片表达式
            self._advance()  # 消耗 ':'
            
            # 解析可选的end
            end = None
            if not (self._check('PUNCTUATION') and self.current_token.value in (':', ']')):
                end = self._parse_expression()
            
            # 解析可选的第二个 ':' 和 step
            step = None
            if self._check('PUNCTUATION') and self.current_token.value == ':':
                self._advance()  # 消耗第二个 ':'
                if not (self._check('PUNCTUATION') and self.current_token.value == ']'):
                    step = self._parse_expression()
            
            # 创建切片表达式（start为None）
            slice_expr = SliceExpression(start=None, end=end, step=step, 
                                         line=start_token.line, column=start_token.column)
        else:
            # 可能是单个索引表达式或切片表达式
            # 解析第一个表达式（可能是start）
            first_expr = self._parse_expression()
            
            if self._check('PUNCTUATION') and self.current_token.value == ':':
                # 切片表达式：first_expr是start
                self._advance()  # 消耗 ':'
                
                # 解析可选的end
                end = None
                if not (self._check('PUNCTUATION') and self.current_token.value in (':', ']')):
                    end = self._parse_expression()
                
                # 解析可选的第二个 ':' 和 step
                step = None
                if self._check('PUNCTUATION') and self.current_token.value == ':':
                    self._advance()  # 消耗第二个 ':'
                    if not (self._check('PUNCTUATION') and self.current_token.value == ']'):
                        step = self._parse_expression()
                
                # 创建切片表达式
                slice_expr = SliceExpression(start=first_expr, end=end, step=step,
                                             line=start_token.line, column=start_token.column)
            else:
                # 单个索引表达式：将整个表达式视为start，end和step为None
                slice_expr = SliceExpression(start=first_expr, end=None, step=None,
                                             line=start_token.line, column=start_token.column)
        
        # 消耗 ']'
        self._consume('PUNCTUATION', "期望 ']'")
        
        return SubscriptExpression(value=value, slice=slice_expr,
                                   line=start_token.line, column=start_token.column)
    
    def _parse_primary(self) -> Optional[Expression]:
        """解析基本表达式"""
        if self._is_at_end():
            return None
        
        token = self.current_token
        
        if token.type == 'INTEGER':
            self._advance()
            return Literal(value=int(token.value), line=token.line, column=token.column)
        
        elif token.type == 'FLOAT':
            self._advance()
            return Literal(value=float(token.value), line=token.line, column=token.column)
        
        elif token.type == 'STRING':
            self._advance()
            # 去掉引号
            value = token.value[1:-1]
            # 检查是否有插值表达式 {xxx}
            if '{' in value and '}' in value:
                return self._parse_string_interpolation(value, token.line, token.column)
            return Literal(value=value, line=token.line, column=token.column)
        
        elif token.type == 'FSTRING':
            self._advance()
            # 去掉 f 前缀和引号
            value = token.value[2:-1]
            # f-字符串总是解析为插值字符串
            return self._parse_string_interpolation(value, token.line, token.column)
        
        elif token.type == 'KEYWORD':
            if token.value in ('真', '假', '空'):
                self._advance()
                if token.value == '真':
                    value = True
                elif token.value == '假':
                    value = False
                else:  # '空'
                    value = None
                return Literal(value=value, line=token.line, column=token.column)
            elif token.value == '函数':
                # Lambda表达式：函数(参数): 表达式/块
                return self._parse_lambda_expression()
            elif token.value == '这':
                # this关键字，类似Python的self
                self._advance()
                return ThisExpression(line=token.line, column=token.column)
            # 这些关键字可以作为标识符使用（用于成员访问、函数调用等）
            elif token.value in ('窗口', '组件', '布局', '事件', '属性', '样式', '内容', '执行', '销毁', '暂停', '继续', '整数', '浮点', '字符', '字符串', '布尔', '数组', '列表', '字典', '元组', '范围'):
                self._advance()
                return Identifier(name=token.value, line=token.line, column=token.column)
            elif token.value == 'dll':
                # DLL加载表达式
                self._advance()
                self._consume('PUNCTUATION', "期望 '('")
                path = self._parse_expression()
                self._consume('PUNCTUATION', "期望 ')'")
                return DLLLoadExpression(path=path, line=token.line, column=token.column)
            elif token.value == '控制台':
                # 控制台创建表达式
                return self._parse_console_create_expression()
            elif token.value in ('内容', '执行', '销毁', '暂停', '继续'):
                # 这些关键字可以作为标识符使用
                self._advance()
                return Identifier(name=token.value, line=token.line, column=token.column)
            # 其他关键字不能作为表达式的开始，返回None
            return None
        
        elif token.type == 'IDENTIFIER':
            self._advance()
            ident = Identifier(name=token.value, line=token.line, column=token.column)
            return ident
        
        elif token.type == 'PUNCTUATION' and token.value == '(':
            self._advance()
            expr = self._parse_expression()
            self._consume('PUNCTUATION', "期望 ')'")
            return expr
        
        # 列表字面量
        elif token.type == 'PUNCTUATION' and token.value == '[':
            return self._parse_list_literal()
        
        # 字典字面量
        elif token.type == 'PUNCTUATION' and token.value == '{':
            return self._parse_dict_literal()
        
        # UI元素
        elif token.type == 'UI_TAG_OPEN':
            return self._parse_ui_element()
        
        # 如果没有匹配任何基本表达式，返回None
        return None
    
    def _parse_string_interpolation(self, value: str, line: int, column: int) -> StringInterpolation:
        """解析字符串插值，如 "你好{name}" """
        import re
        parts = []
        last_end = 0
        
        # 匹配 {xxx} 模式
        pattern = r'\{([^}]+)\}'
        
        for match in re.finditer(pattern, value):
            # 添加前面的字符串部分
            if match.start() > last_end:
                parts.append(value[last_end:match.start()])
            
            # 解析插值表达式
            expr_str = match.group(1).strip()
            # 简单标识符直接创建 Identifier
            if re.match(r'^[a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*$', expr_str):
                parts.append(Identifier(name=expr_str))
            else:
                # 复杂表达式需要重新词法分析和解析
                # 简化处理：只支持标识符
                parts.append(Identifier(name=expr_str))
            
            last_end = match.end()
        
        # 添加最后剩余的字符串
        if last_end < len(value):
            parts.append(value[last_end:])
        
        return StringInterpolation(parts=parts, line=line, column=column)
    
    def _parse_list_literal(self) -> Union[ListLiteral, ListComprehension]:
        """解析列表字面量或列表推导式"""
        # 消耗 '['
        start_token = self._consume('PUNCTUATION', "期望 '['")
        
        # 检查是否是空列表
        if self._check('PUNCTUATION') and self.current_token.value == ']':
            self._advance()  # 消耗 ']'
            return ListLiteral(
                elements=[],
                line=start_token.line,
                column=start_token.column
            )
        
        # 跳过 NEWLINE 和 INDENT（用于多行列表）
        while self._check('NEWLINE') or self._check('INDENT'):
            self._advance()
        
        # 解析第一个表达式
        first_expr = self._parse_expression()
        
        # 检查是否是列表推导式：表达式后跟着 '对于'
        if self._check('KEYWORD') and self.current_token.value == '对于':
            # 是列表推导式，解析剩余部分
            self._advance()  # 消耗 '对于'
            
            # 解析变量名
            if not self._check('IDENTIFIER'):
                self._error("期望变量名", self.current_token)
                # 尝试恢复
                variable_token = Token(type='ERROR', value='', line=self.current_token.line, column=self.current_token.column)
            else:
                variable_token = self._advance()
            variable_name = variable_token.value
            
            # 解析 '在' 关键字
            self._consume('KEYWORD', "期望 '在'")
            
            # 解析可迭代对象
            iterable = self._parse_expression()
            
            # 可选的条件子句
            condition = None
            if self._check('KEYWORD') and self.current_token.value == '如果':
                self._advance()  # 消耗 '如果'
                condition = self._parse_expression()
            
            # 跳过 DEDENT
            while self._check('DEDENT'):
                self._advance()
            
            # 消耗 ']'
            self._consume('PUNCTUATION', "期望 ']'")
            
            return ListComprehension(
                expression=first_expr,
                variable=variable_name,
                iterable=iterable,
                condition=condition,
                line=start_token.line,
                column=start_token.column
            )
        else:
            # 普通列表字面量
            elements = [first_expr]
            
            # 解析剩余元素（如果有）
            while True:
                # 跳过 NEWLINE 和 DEDENT（用于多行列表）
                while self._check('NEWLINE') or self._check('DEDENT'):
                    self._advance()
                
                # 检查是否是逗号
                if self._check('PUNCTUATION') and self.current_token.value == ',':
                    self._advance()  # 消耗 ','
                    # 跳过 NEWLINE 和 INDENT（用于多行列表）
                    while self._check('NEWLINE') or self._check('INDENT'):
                        self._advance()
                    elements.append(self._parse_expression())
                elif self._check('PUNCTUATION') and self.current_token.value == ']':
                    break
                else:
                    # 可能是结束，让下一个 consume 处理错误
                    break
            
            # 跳过 DEDENT
            while self._check('DEDENT'):
                self._advance()
            
            # 消耗 ']'
            self._consume('PUNCTUATION', "期望 ']'")
            
            return ListLiteral(
                elements=elements,
                line=start_token.line,
                column=start_token.column
            )
    
    def _parse_dict_literal(self) -> DictLiteral:
        """解析字典字面量"""
        # 消耗 '{'
        start_token = self._consume('PUNCTUATION', "期望 '{'")
        
        entries = []
        if not self._check('PUNCTUATION') or self.current_token.value != '}':
            while True:
                key = self._parse_expression()
                self._consume('PUNCTUATION', "期望 ':'")
                value = self._parse_expression()
                entries.append(DictEntry(key=key, value=value, line=key.line, column=key.column))
                
                if not self._match('PUNCTUATION') or self.current_token.value != ',':
                    break
        
        self._consume('PUNCTUATION', "期望 '}'")
        
        return DictLiteral(
            entries=entries,
            line=start_token.line,
            column=start_token.column
        )
    
    def _parse_call_expression(self, callee: Expression) -> CallExpression:
        """解析函数调用"""
        # 消耗 '('
        self._consume('PUNCTUATION', "期望 '('")
        
        arguments = []
        named_arguments = []
        
        if not self._check('PUNCTUATION') or self.current_token.value != ')':
            while True:
                # 检查是否是命名参数（标识符 = 表达式）
                if self._check('IDENTIFIER') or self._check('KEYWORD'):
                    # 向前看检查是否是命名参数
                    next_token = self._peek()
                    if next_token and next_token.type == 'OPERATOR' and next_token.value == '=':
                        # 命名参数
                        name_token = self._advance()  # 消耗参数名
                        self._advance()  # 消耗 '='
                        value = self._parse_expression()
                        named_arguments.append(NamedArgument(
                            name=name_token.value,
                            value=value,
                            line=name_token.line,
                            column=name_token.column
                        ))
                    else:
                        # 普通参数
                        arguments.append(self._parse_expression())
                else:
                    # 普通参数
                    arguments.append(self._parse_expression())
                
                # 检查是否有逗号（更多参数）
                if self._check('PUNCTUATION') and self.current_token.value == ',':
                    self._advance()  # 消耗逗号
                else:
                    break
        
        self._consume('PUNCTUATION', "期望 ')'")
        
        return CallExpression(
            callee=callee,
            arguments=arguments,
            named_arguments=named_arguments,
            line=callee.line,
            column=callee.column
        )
    
    def _parse_ui_element(self) -> UIElement:
        """解析UI元素"""
        # 消耗 '<'
        start_token = self._consume('UI_TAG_OPEN', "期望 '<'")
        
        # 检查是否是结束标签 '</'
        is_closing_tag = False
        if self._check('UI_TAG_SLASH'):
            self._advance()  # 消耗 '/'
            is_closing_tag = True
        
        # 标签名（可以是标识符或关键字）
        if not self._check('IDENTIFIER') and not self._check('KEYWORD'):
            self._error("期望UI标签名（标识符或关键字）", self.current_token)
            # 尝试恢复
            self._synchronize()
            return UIElement(tag="unknown", line=start_token.line, column=start_token.column)
        
        tag_name_token = self._advance()
        tag_name = tag_name_token.value
        
        # 如果是结束标签，只需要 '>'
        if is_closing_tag:
            self._consume('UI_TAG_CLOSE', "期望 '>'")
            # 返回一个特殊的结束标记？实际上，结束标签不应该作为表达式返回
            # 但为了简化，我们返回一个占位符UI元素，类型为'CLOSING_TAG'
            # 更好的方法是：结束标签不应该出现在表达式中，只出现在UI元素上下文中
            # 这里我们假设解析器会正确处理嵌套
            return UIElement(tag=tag_name, line=tag_name_token.line, column=tag_name_token.column)
        
        # 解析属性
        attributes = []
        while not self._is_at_end():
            # 检查是否遇到 '>' 或 '/>'
            if self._check('UI_TAG_CLOSE'):
                self._advance()  # 消耗 '>'
                break
            if self._check('UI_TAG_SELF_CLOSE'):
                self._advance()  # 消耗 '/>'
                # 自闭合标签，没有子元素
                children = []
                return UIElement(
                    tag=tag_name,
                    attributes=attributes,
                    children=children,
                    line=start_token.line,
                    column=start_token.column
                )
            
            # 解析属性名（可以是标识符或关键字）
            if not self._check('IDENTIFIER') and not self._check('KEYWORD'):
                self._error("期望属性名（标识符或关键字）", self.current_token)
                # 尝试恢复
                self._synchronize()
                attr_name_token = Token(type='ERROR', value='', line=self.current_token.line, column=self.current_token.column)
                attr_name = ''
            else:
                attr_name_token = self._advance()
                attr_name = attr_name_token.value
            
            # 属性值
            attr_value = None
            if self._check('OPERATOR') and self.current_token and self.current_token.value == '=':
                self._advance()  # 消耗 '='
                # 值可以是字符串、数字、标识符或表达式
                if self._check('STRING'):
                    token = self._advance()
                    attr_value = token.value[1:-1]  # 去掉引号
                elif self._check('INTEGER'):
                    token = self._advance()
                    attr_value = int(token.value)
                elif self._check('FLOAT'):
                    token = self._advance()
                    attr_value = float(token.value)
                elif self._check('IDENTIFIER') or self._check('KEYWORD'):
                    token = self._advance()
                    # 如果关键字是"真"、"假"、"空"，转换为相应的值
                    if token.type == 'KEYWORD':
                        if token.value == '真':
                            attr_value = True
                        elif token.value == '假':
                            attr_value = False
                        elif token.value == '空':
                            attr_value = None
                        else:
                            # 其他关键字作为标识符处理
                            attr_value = Identifier(name=token.value, line=token.line, column=token.column)
                    else:
                        attr_value = Identifier(name=token.value, line=token.line, column=token.column)
                else:
                    # 可能是表达式
                    expr = self._parse_expression()
                    if expr:
                        attr_value = expr
                    else:
                        self._error(f"无效的属性值", self.current_token)
            else:
                # 布尔属性（没有值）
                attr_value = True
            
            attributes.append(UIAttribute(
                name=attr_name,
                value=attr_value,
                line=attr_name_token.line,
                column=attr_name_token.column
            ))
        
        # 解析子元素（文本或嵌套UI元素）
        children = []
        while not self._is_at_end():
            # 跳过INDENT和DEDENT token
            if self._check('INDENT') or self._check('DEDENT'):
                self._advance()
                continue
            
            # 检查是否遇到结束标签
            if self._check('UI_TAG_OPEN'):
                # 检查是否是结束标签 '</'
                next_pos = self.position + 1
                if next_pos < len(self.tokens) and self.tokens[next_pos].type == 'UI_TAG_SLASH':
                    # 遇到结束标签，跳出循环
                    # 消耗 '</' 和标签名和 '>'
                    self._advance()  # 消耗 '<'
                    self._advance()  # 消耗 '/'
                    # 结束标签名（可以是标识符或关键字）
                    if not self._check('IDENTIFIER') and not self._check('KEYWORD'):
                        self._error("期望结束标签名（标识符或关键字）", self.current_token)
                        # 尝试恢复
                        self._synchronize()
                        end_tag_name_token = Token(type='ERROR', value='', line=self.current_token.line, column=self.current_token.column)
                    else:
                        end_tag_name_token = self._advance()
                    self._consume('UI_TAG_CLOSE', "期望 '>'")
                    # 验证标签名匹配
                    if end_tag_name_token.value != tag_name:
                        self._error(f"标签不匹配: 期望 '</{tag_name}>'，但得到 '</{end_tag_name_token.value}>'", end_tag_name_token)
                    break
                else:
                    # 嵌套UI元素
                    child = self._parse_ui_element()
                    children.append(child)
            elif self._check('STRING'):
                # 文本内容
                token = self._advance()
                text = token.value[1:-1]
                children.append(Literal(value=text, line=token.line, column=token.column))
            elif self._check('IDENTIFIER') or self._check('KEYWORD'):
                # 可能是表达式
                expr = self._parse_expression()
                if expr:
                    children.append(expr)
                else:
                    break
            else:
                # 其他内容，可能是表达式
                expr = self._parse_expression()
                if expr:
                    children.append(expr)
                else:
                    break
        
        return UIElement(
            tag=tag_name,
            attributes=attributes,
            children=children,
            line=start_token.line,
            column=start_token.column
        )
    
    def _parse_console_create_expression(self) -> 'ConsoleCreateExpression':
        """解析控制台创建表达式：控制台(隐藏, 保留, 命令)"""
        token = self.current_token
        
        # 消耗 '控制台' 关键字
        self._advance()
        
        # 消耗 '('
        self._consume('PUNCTUATION', "期望 '('")
        
        # 解析第一个参数：隐藏/显示
        hidden = self._parse_expression()
        
        # 消耗 ','
        self._consume('PUNCTUATION', "期望 ','")
        
        # 解析第二个参数：执行完销毁/保留
        keep = self._parse_expression()
        
        # 消耗 ','
        self._consume('PUNCTUATION', "期望 ','")
        
        # 解析第三个参数：执行的命令
        command = self._parse_expression()
        
        # 消耗 ')'
        self._consume('PUNCTUATION', "期望 ')'")
        
        return ConsoleCreateExpression(
            hidden=hidden,
            keep=keep,
            command=command,
            line=token.line,
            column=token.column
        )
    
    def _parse_console_member_call(self, console_name: str, member_name: str, line: int, column: int) -> 'ConsoleMemberAccess':
        """解析控制台成员调用：console.执行(...) 或 console.销毁()"""
        # 消耗 '('
        self._consume('PUNCTUATION', "期望 '('")
        
        # 解析参数
        arguments = []
        if not self._check('PUNCTUATION') or self.current_token.value != ')':
            while True:
                arguments.append(self._parse_expression())
                
                # 检查是否有逗号（更多参数）
                if self._check('PUNCTUATION') and self.current_token.value == ',':
                    self._advance()  # 消耗逗号
                else:
                    break
        
        # 消耗 ')'
        self._consume('PUNCTUATION', "期望 ')'")
        
        return ConsoleMemberAccess(
            console_name=console_name,
            member=member_name,
            arguments=arguments if arguments else None,
            line=line,
            column=column
        )
    
    def _parse_update_call_expression(self, update_name: str, line: int, column: int) -> 'UpdateCallExpression':
        """解析更新循环调用：b(0, 2000) 更新循环参数"""
        # 消耗 '('
        self._consume('PUNCTUATION', "期望 '('")
        
        # 解析第一个参数：执行次数
        count = self._parse_expression()
        
        # 消耗 ','
        self._consume('PUNCTUATION', "期望 ','")
        
        # 解析第二个参数：间隔时间
        interval = self._parse_expression()
        
        # 消耗 ')'
        self._consume('PUNCTUATION', "期望 ')'")
        
        return UpdateCallExpression(
            update_name=update_name,
            count=count,
            interval=interval,
            line=line,
            column=column
        )
    
    def _parse_lambda_expression(self) -> 'LambdaExpression':
        """解析Lambda表达式：函数(参数): 表达式/块"""
        # 消耗 '函数' 关键字
        func_token = self._consume('KEYWORD', "期望 '函数'")
        
        # 参数列表
        self._consume('PUNCTUATION', "期望 '('")
        parameters = []
        
        if not self._check('PUNCTUATION') or self.current_token.value != ')':
            while True:
                # 参数名（可以是标识符或关键字）
                if self._check('IDENTIFIER'):
                    param_name_token = self._advance()
                    param_name = param_name_token.value
                elif self._check('KEYWORD'):
                    param_name_token = self._advance()
                    param_name = param_name_token.value
                else:
                    param_name_token = self._consume('IDENTIFIER', "期望参数名")
                    param_name = param_name_token.value if param_name_token else ""
                
                # 类型注解（可选）
                type_annotation = None
                if self._check('PUNCTUATION') and self.current_token and self.current_token.value == ':':
                    self._advance()  # 消耗 ':'
                    type_annotation = self._parse_type_annotation()
                
                # 默认值（可选）
                default_value = None
                if self._check('OPERATOR') and self.current_token and self.current_token.value == '=':
                    self._advance()  # 消耗 '='
                    default_value = self._parse_expression()
                
                parameters.append(Parameter(
                    name=param_name,
                    type_annotation=type_annotation,
                    default_value=default_value,
                    line=param_name_token.line,
                    column=param_name_token.column
                ))
                
                # 检查是否有逗号（更多参数）
                if not (self._check('PUNCTUATION') and self.current_token.value == ','):
                    break
                self._advance()  # 消耗 ','
        
        self._consume('PUNCTUATION', "期望 ')'")
        
        # 消耗 ':'
        self._consume('PUNCTUATION', "期望 ':'")
        
        # 解析函数体（可以是单行表达式或多行块）
        if self._check('INDENT'):
            # 多行块
            body = self._parse_block()
        else:
            # 单行表达式
            body = self._parse_expression()
        
        return LambdaExpression(
            parameters=parameters,
            body=body,
            line=func_token.line,
            column=func_token.column
        )


# ==================== 测试函数 ====================

if __name__ == '__main__':
    # 测试代码
    test_code = """
    变量 x = 10
    变量 y = x + 20
    函数 相加(a, b):
        返回 a + b
    如果 y > 0:
        输出("正数")
    """
    
    print("测试语法分析器:")
    print("=" * 50)
    
    from .lexer import tokenize_string
    tokens = tokenize_string(test_code)
    
    parser = Parser(tokens)
    ast = parser.parse()
    
    print("生成的AST:")
    print(print_ast(ast))