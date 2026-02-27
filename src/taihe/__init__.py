__version__ = "0.1.0"
__author__ = "太和语言开发团队"

# 导出主要API
from .lexer import Lexer, Token, tokenize_string
from .parser import Parser
from .codegen import CodeGenerator
from .compiler import compile_source, compile_file