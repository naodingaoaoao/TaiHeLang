# 太和编程语言 (TaiHe Language) 项目索引


## 项目结构

### 根目录

| 文件/目录 | 说明 |
|-----------|------|
| `README.md` | 项目简介、快速开始 |
| `INDEX.md` | 本索引文件，详细结构说明 |
| `setup.py` | Python 包安装配置 |
| `requirements.txt` | Python 依赖列表 |
| `Makefile` | 构建脚本（可选） |
| `spec.md` | 语言规范（最新版） |
| `spec_v0.2.md`, `spec_v0.3.md` | 历史版本规范 |
| `docs/` | 文档目录（目前为空） |
| `examples/` | 示例程序目录 |
| `install/` | 安装相关文件（目前为空） |
| `src/` | 编译器源代码 |
| `tests/` | 单元测试 |

### `src/` 目录

| 文件 | 功能 |
|------|------|
| `taihe/__init__.py` | 包初始化文件 |
| `taihe/lexer.py` | 词法分析器，将源代码转换为 token 流 |
| `taihe/parser.py` | 语法分析器，构建抽象语法树（AST） |
| `taihe/ast.py` | AST 节点定义与打印工具 |
| `taihe/codegen.py` | LLVM IR 代码生成器 |
| `taihe/compiler.py` | 编译器主入口，协调各阶段 |
| `taihe/cli.py` | 命令行界面（基于 Click） |

### `examples/` 目录

| 文件 | 说明 |
|------|------|
| `hello.th` | 简单的“你好，世界！”程序 |
| `fibonacci.th` | 斐波那契数列计算示例 |
| `dll.th` | 简单dll实现程序 |
| `calldll.th` | 简单dll调用程序 |


## 核心模块功能

### 词法分析 (`lexer.py`)
- 识别中文关键字（`变量`、`函数`、`返回` 等）
- 处理标识符、字面量（整数、字符串）
- 支持全角标点（如 `：`、`；`）的错误恢复

### 语法分析 (`parser.py`)
- 递归下降解析器，构建 AST
- 支持变量声明、赋值、函数定义、条件语句等
- 错误恢复与错误报告

### 抽象语法树 (`ast.py`)
- 定义 AST 节点类（`VariableDeclaration`、`FunctionDefinition` 等）
- 提供 AST 打印函数，用于调试

### 代码生成 (`codegen.py`)
- 使用 `llvmlite` 库生成 LLVM IR
- 支持整数运算、函数调用、条件分支等
- 生成优化后的 IR 并输出到文件

### 编译器主入口 (`compiler.py`)
- 读取源文件，调用词法、语法、代码生成各阶段
- 调用系统工具链（`clang`、`llc`、`lld`）生成可执行文件

### 命令行界面 (`cli.py`)
- 提供 `taihe` 命令，支持 `taihe <源文件>` 直接编译
- 子命令：`run`（编译并运行）、`ir`（仅生成 IR）、`asm`（生成汇编）

## 主要函数与API

### 词法分析模块 (`lexer.py`)

| 函数/方法 | 参数 | 返回值 | 功能 |
|-----------|------|--------|------|
| `Lexer(source_code: str)` | `source_code`: 源代码字符串 | `Lexer` 实例 | 构造函数，初始化词法分析器 |
| `tokenize() -> List[Token]` | 无 | `List[Token]` | 将源代码转换为词法单元列表 |
| `_next_token() -> Optional[Token]` | 无 | `Optional[Token]` | 读取下一个词法单元（内部方法） |
| `_update_position(text: str)` | `text`: 已处理的文本 | 无 | 更新行号和列号（内部方法） |
| `peek() -> Optional[Token]` | 无 | `Optional[Token]` | 查看下一个 token 而不消耗它 |
| `consume(expected_type: Optional[str] = None) -> Token` | `expected_type`: 期望的 token 类型 | `Token` | 消耗下一个 token，可选检查类型 |
| `tokenize_string(source_code: str) -> List[Token]` | `source_code`: 源代码字符串 | `List[Token]` | 快速词法分析的便捷函数 |

### 语法分析模块 (`parser.py`)

| 函数/方法 | 参数 | 返回值 | 功能 |
|-----------|------|--------|------|
| `Parser(tokens: List[Token])` | `tokens`: 词法单元列表 | `Parser` 实例 | 构造函数，初始化语法分析器 |
| `parse() -> Program` | 无 | `Program` | 解析整个程序，返回 AST 根节点 |
| `_parse_statement() -> Statement` | 无 | `Statement` | 解析单个语句（内部方法） |
| `_parse_function_declaration() -> FunctionDeclaration` | 无 | `FunctionDeclaration` | 解析函数声明 |
| `_parse_variable_declaration() -> VariableDeclaration` | 无 | `VariableDeclaration` | 解析变量声明 |
| `_parse_class_declaration() -> ClassDeclaration` | 无 | `ClassDeclaration` | 解析类声明 |
| `_parse_if_statement() -> IfStatement` | 无 | `IfStatement` | 解析条件语句 |
| `_parse_while_statement() -> WhileStatement` | 无 | `WhileStatement` | 解析循环语句 |
| `_parse_expression() -> Optional[Expression]` | 无 | `Optional[Expression]` | 解析表达式 |

### AST 节点模块 (`ast.py`)

| 类/函数 | 参数/属性 | 功能 |
|---------|-----------|------|
| `Node` | `line`, `column` | 所有 AST 节点的基类 |
| `Program` | `statements: List[Statement]` | 程序根节点 |
| `Statement` | (基类) | 所有语句节点的基类 |
| `VariableDeclaration` | `name`, `type_annotation`, `value` | 变量声明节点 |
| `FunctionDeclaration` | `name`, `parameters`, `return_type`, `body` | 函数声明节点 |
| `ClassDeclaration` | `name`, `base_class`, `members` | 类声明节点 |
| `Expression` | (基类) | 所有表达式节点的基类 |
| `Literal` | `value` | 字面量节点（整数、浮点、字符串、布尔值） |
| `Identifier` | `name` | 标识符节点 |
| `BinaryOperation` | `left`, `operator`, `right` | 二元运算节点 |
| `CallExpression` | `callee`, `arguments` | 函数调用节点 |
| `UIElement` | `tag`, `attributes`, `children` | UI 元素节点 |
| `print_ast(node: Node, indent: int = 0) -> str` | `node`: AST 节点 | 将 AST 格式化为字符串，用于调试 |

### 代码生成模块 (`codegen.py`)

| 函数/方法 | 参数 | 返回值 | 功能 |
|-----------|------|--------|------|
| `CodeGenerator()` | 无 | `CodeGenerator` 实例 | 构造函数，初始化 LLVM 模块 |
| `generate(ast: Program) -> str` | `ast`: AST 根节点 | `str` (LLVM IR 字符串) | 从 AST 生成 LLVM IR |
| `_generate_statement(stmt: Statement)` | `stmt`: 语句节点 | 无 | 生成语句的 LLVM IR（内部方法） |
| `_generate_expression(expr: Expression) -> ir.Value` | `expr`: 表达式节点 | `ir.Value` | 生成表达式的 LLVM IR（内部方法） |
| `_generate_function_declaration(func: FunctionDeclaration)` | `func`: 函数声明节点 | 无 | 生成函数声明的 LLVM IR |
| `_generate_variable_declaration(decl: VariableDeclaration)` | `decl`: 变量声明节点 | 无 | 生成变量声明的 LLVM IR |
| `_llvm_type(type_name: str) -> ir.Type` | `type_name`: 太和类型名 | `ir.Type` | 将太和类型名转换为 LLVM 类型 |

### 编译器便捷模块 (`compiler.py`)

| 函数 | 参数 | 返回值 | 功能 |
|------|------|--------|------|
| `compile_source(source_code: str, verbose: bool = False) -> str` | `source_code`: 源代码，`verbose`: 详细输出 | `str` (LLVM IR 字符串) | 编译太和源代码字符串 |
| `read_source_file(file_path: str, verbose: bool = False) -> str` | `file_path`: 文件路径，`verbose`: 详细输出 | `str` (源代码字符串) | 读取源代码文件，自动处理编码 |
| `compile_file(source_file: str, output_file: Optional[str] = None, verbose: bool = False) -> str` | `source_file`: 源文件路径，`output_file`: 输出路径，`verbose`: 详细输出 | `str` (LLVM IR 字符串) | 编译太和源文件 |
| `compile_and_execute(source_code: str)` | `source_code`: 源代码字符串 | `None` | 编译并执行太和程序（实验性） |

### 命令行接口 (`cli.py`)

| 命令 | 参数 | 选项 | 功能 |
|------|------|------|------|
| `taihe <源文件>` | `<源文件>`: 太和源文件 | 无 | 直接编译并执行太和程序（便捷模式） |
| `taihe run <源文件>` | `<源文件>`: 太和源文件 | 无 | 编译并执行太和程序 |
| `taihe compile <源文件>` | `<源文件>`: 太和源文件 | `-o, --output`: 输出文件路径<br>`-v, --verbose`: 详细输出 | 编译太和源文件为 LLVM IR |
| `taihe tokens <源文件>` | `<源文件>`: 太和源文件 | 无 | 显示词法分析结果 |
| `taihe ast <源文件>` | `<源文件>`: 太和源文件 | 无 | 显示抽象语法树 |
| `taihe version` | 无 | 无 | 显示编译器版本信息 |
| `find_executable(name)` | `name`: 可执行文件名 | 可执行文件路径或 `None` | 查找可执行文件，支持 Windows 常见路径（内部函数） |

## 使用方法

### 安装
```bash
pip install -e .
```

### 编译一个程序
```bash
taihe examples/hello.th
```
这会生成可执行文件 `hello`（Linux/macOS）或 `hello.exe`（Windows）。

### 仅生成 LLVM IR
```bash
taihe ir examples/hello.th
```

### 运行程序（编译后自动执行）
```bash
taihe run examples/hello.th
```

## 开发指南

### 运行测试
```bash
python -m pytest tests/
```

### 添加新语法
1. 在 `lexer.py` 中添加对应的 token 类型
2. 在 `parser.py` 中添加解析规则
3. 在 `ast.py` 中定义新的 AST 节点
4. 在 `codegen.py` 中实现 IR 生成逻辑
5. 添加测试用例

### 调试
- 使用 `python -m pdb -m taihe.cli run examples/hello.太和` 进行调试
- 查看生成的中间文件（`.ll`、`.s`、`.o`）

## 常见问题

### 找不到 `clang`/`llc` 等工具
- 确保 LLVM 工具链已安装并位于 `PATH` 中
- Windows 用户可安装 LLVM 官方发行版并不包含llc工具，需要自行编译，并添加到环境变量

### 编译时出现“全角冒号”错误
- 检查源代码是否误用了全角标点（`：`、`；`），应使用半角标点（`:`、`;`）
- 或使用支持全角标点的版本（若已实现）

### 如何添加新的 UI 组件？
- 参考 `spec.md` 中关于 UI 语法的描述
- 在 `parser.py` 中扩展 UI 解析规则
- 在 `codegen.py` 中实现对应的 UI 组件生成

## 贡献

欢迎提交 Issue 和 Pull Request。请先阅读 `spec.md` 了解语言设计，并确保测试通过

## 许可证

MIT 许可证
