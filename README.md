# TaiHeLang
太和是一门面向对象的中文编程语言，旨在降低中国人的编程学习成本，他拥有接近C语言的性能和简洁的语法，将中文代码编译成LLVM中间表示（IR），并进一步生成本地机器码。
Taihe is an object-oriented Chinese programming language aimed at reducing the programming learning cost for Chinese people. It has performance similar to C language and concise syntax, compiles Chinese code into LLVM intermediate representation (IR), and further generates local machine code.

**详细项目索引请参阅 [INDEX.md](INDEX.md)**，其中包含完整的文件结构、模块说明和使用指南。

## 特性

- 中文关键字和语法，降低中文用户学习门槛
- 静态类型系统，支持类型推断
- 面向对象编程，支持类、继承、多态
- 编译到LLVM IR，享受LLVM优化和跨平台支持
- 可生成高性能本地机器码

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

- git最新的LLVM开源工程，然后将其添加到path中，如果安装的是官方预编译版本，则会因为缺少llc指令而降低体验

### 安装太和编译器（开发模式）

```bash
pip install -e .
```

### 编译示例

```bash
taihe examples/hello.th
```

## 集成开发环境 (IDE)

太和语言提供了专用的集成开发环境，基于Electron构建，包含代码编辑器、文件管理、编译调试、UI设计器等完整功能。

### 运行IDE（正在开发ing）

1. 进入IDE目录：
   ```bash
   cd ide
   ```

2. 安装Node.js依赖：
   ```bash
   npm install
   ```

3. 启动IDE：
   ```bash
   npm start
   ```

详细安装和使用指南请参阅 [ide/README.md](ide/README.md)。

## 核心目录

- `src/taihe/` – 编译器核心模块（词法、语法、代码生成等）
- `examples/` – 示例程序（`.太和` 文件）
- `tests/` – 单元测试
- `docs/` – 文档（规划中）

## 语言规范

详见 [spec.md](spec.md)。

## 开发

欢迎贡献！请先阅读 [INDEX.md](INDEX.md) 了解项目结构，然后运行测试：

```bash
python -m pytest tests/
```

## 许可证

MIT

## 贡献

希望得到各位大佬的修改，让这门语言早日完善
