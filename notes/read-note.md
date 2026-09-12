# read_note：文件读取、路径校验与异常处理

整理日期：2026-09-12。依据：当天完成的 [main.py](../main.py)、[文件读取练习](../tmp/test_read_file.py) 和真实运行记录。

配套笔记：[Agent Loop：循环、消息历史与多工具调用](agent-loop.md)。JSON 基础见 [Tool Calling](tool-calling.md)。本篇从文件 I/O 入门，复盘如何把本地读取函数接成模型工具。

## 1. 今天完成的读取工具

`read_note` 接收笔记名称，例如 `basics.md`，定位项目 `notes/` 下的 Markdown 文件，用 UTF-8 读取并返回完整正文。

| 环节 | 当前实现 |
| --- | --- |
| 输入 | 必填字符串参数 `note_name` |
| 定位 | 从脚本位置找到项目笔记目录 |
| 校验 | 路径范围、普通文件、`.md` 后缀 |
| 执行 | 本地 Python 打开并读取文件 |
| 日志 | 工具名、调用 ID、参数、读取字符数 |
| 回传 | 完整正文放进对应的 `tool` 消息 |
| 失败 | 保留具体错误原因并退出程序 |

模型负责提出读取请求和根据正文总结；本地工具负责读取实际文件。只把文件名告诉模型不等于模型已经读到了正文，文件对象也不能直接代替正文回传。

## 2. 文件 I/O：从文件路径到正文字符串

### 2.1 先分清三个对象

| 内容 | 是什么 |
| --- | --- |
| 文件路径 | 指定文件位置的字符串或 `Path` 对象 |
| 文件对象 | `open` 返回的对象，用来操作文件 |
| 正文字符串 | 文本文件对象的 `read` 返回的内容 |

你最初完成的练习是：

```python
with open("/home/shijun/Projects/simple-agent/notes/basics.md", "r", encoding="utf-8") as f:
    text = f.read()
print(text)
```

`"r"` 表示只读文本模式；`encoding="utf-8"` 指定把字节解码成文字的方式。`read()` 不指定大小时，从当前位置读到末尾，返回字符串。

文件对象会记住当前位置。读到末尾后再次 `read()`，通常得到空字符串，不会自动从头重读。

### 2.2 `with`、`as` 和自动关闭

`as f` 把打开的文件对象绑定到变量 `f`。进入缩进块后读取；离开时自动关闭文件，包括正常结束、`return` 或异常传播离开的情况。关闭文件后，已读入的正文字符串仍然存在。

参考：[Python 文本文件读写](https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files)。

当前函数把 `return note.read()` 放在 `with` 内部：先读出正文，离开 `with` 时关闭文件，再把返回值交给调用者。

### 2.3 定义函数、调用函数、使用结果

只写 `def` 是定义函数，不会执行函数体。最初练习文件前面有独立读取语句，所以即使后面的函数从未调用，也会打印正文。

后来改成：定义读取函数 → 调用它并传入路径 → 用变量接收正文 → 打印正文，才验证了函数调用的完整过程。

`print` 是显示到终端；`return` 是把值交给调用者。Agent 需要拿到正文并写入工具消息，所以读取函数应当返回正文，而不是只打印。

## 3. `Path`：根据项目位置定位笔记

### 3.1 当前目录结构与路径来源

```text
simple-agent/
├── main.py
├── notes/
│   ├── basics.md
│   ├── tool-calling.md
│   ├── agent-loop.md
│   └── read-note.md
└── tmp/
    └── test_read_file.py
```

| 部件 | 作用 |
| --- | --- |
| `__file__` | 当前脚本文件的路径；这里讨论普通脚本运行 |
| `Path(...)` | 创建路径对象 |
| `.resolve()` | 转成绝对路径，解析 `..` 和符号链接 |
| `.parent` | 上一层目录 |
| `/` | 路径对象的拼接操作 |
| `.suffix` | 扩展名属性，不加括号 |
| `.is_file()` | 检查是否为普通文件的方法，需要括号 |
| `.is_relative_to(...)` | 检查路径是否在给定路径之下；本身不访问文件系统 |

相对路径通常根据进程工作目录解释。当前实现从 `__file__` 定位，因此在不同工作目录启动也能找到项目笔记。

练习脚本在 `tmp/` 下，要取两次 `.parent` 到达项目根目录；迁移到根目录里的 `main.py` 后只取一次。这个调整已经通过本地读取验证。

### 3.2 当前代码中的两步构造

```python
notes_dir = (Path(__file__).resolve().parent / "notes").resolve()
note_path = (notes_dir / note_name).resolve()
```

先确定笔记根目录，再将传入名称拼接并解析为最终路径。`open` 能直接接收 `Path`，不必先转成字符串。

### 3.3 今天遇到的括号问题

错误写法是把 `.resolve()` 紧接在 `"notes"` 或 `file_name` 后面。例如，`notes_dir / file_name.resolve()` 会先尝试调用字符串的方法，而字符串没有 `.resolve()`。

正确思路：**先用括号把拼接表达式括起来，再对结果调用 `.resolve()`。**

这与“路径存在不存在”无关，是方法调用对象错误。通常表现为 `AttributeError`。

路径拼接和上述 API 的规则参考：[Python pathlib](https://docs.python.org/3/library/pathlib.html)。

## 4. 为什么拼接之后还要检查路径

把 `notes` 写在前面，并不保证最终位置在里面。

| 输入 | 拼接与解析的结果 |
| --- | --- |
| `basics.md` | 项目 `notes/basics.md` |
| `../main.py` | 先进入 `notes`，再回上一级，最终到项目 `main.py` |
| `/tmp/example.md` | 绝对路径会覆盖拼接前面的部分，最终到 `/tmp/example.md` |

符号链接也可能指向其他目录。因此先对根目录和目标路径进行 `resolve`，再比较路径层级，而不是只检查字符串里有没有 `notes`。

### 4.1 当前函数的检查顺序

| 顺序 | 判断 | 失败时 |
| --- | --- | --- |
| 1 | 目标路径在解析后的 `notes_dir` 内 | `ValueError`：只能读取 notes 目录下的笔记 |
| 2 | 目标是存在的普通文件 | `FileNotFoundError`：文件不存在或不是普通文件 |
| 3 | 解析后路径的扩展名等于 `.md` | `ValueError`：笔记扩展名必须是 .md |
| 4 | UTF-8 打开并读取 | 可能出现文件系统或解码异常 |

`.is_file()` 不保证有读取权限，也不保证文件编码正确，最终 `open` 和 `read` 仍可能失败。

当前后缀比较区分大小写，所以 `.MD` 不会通过；判断后缀也不等于验证正文一定符合 Markdown 语法。

当前实现允许 `notes/` 中的子目录笔记，以及解析后仍在范围内的绝对路径；并未强制输入只能是没有目录成分的单一文件名。符号链接指向目录外时会被范围检查拒绝。

这是本地学习工具的路径限制，不应当把检查后再打开文件的实现视为应对恶意并发文件替换的完整隔离机制。

## 5. `is` 与 `==`：今天踩过的第二个坑

曾用 `file_path.suffix is not ".md"` 判断后缀，导致真实 `.md` 文件也被拒绝，Python 还给出了 `SyntaxWarning`。

| 运算符 | 比较内容 | 今天的用途 |
| --- | --- | --- |
| `==`、`!=` | 值是否相等 | 扩展名文字是否为 `.md` |
| `is`、`is not` | 是否为同一个对象 | 判断 `None`，或比较具体类型对象 |

扩展名比较使用 `note_path.suffix != ".md"`。两个字符串内容相同，并不意味着它们是同一个对象，不能依赖字符串复用行为。

`type(arguments["note_name"]) is str` 则有效，因为这里比较的是 `type` 返回的类型对象和 `str` 类型本身。

也可以用 `isinstance` 做类型判断。当前 `add` 使用精确的 `int`、`float` 类型检查，会拒绝布尔值；这是因为 Python 中布尔类型与整数类型有继承关系，不能把 `True` 当成本次加法工具期望的普通数字输入。

## 6. JSON 参数与工具分发

模型给出的 `function.arguments` 是 JSON 文本，要先用 `json.loads` 转成 Python 数据。

读取笔记的参数示例：

```json
{"note_name": "basics.md"}
```

工具说明声明了 `note_name` 为 `string` 且必填，但本地仍然检查实际收到的参数：

1. 是有效 JSON。
2. 解析结果是字典。
3. 包含 `note_name`。
4. `note_name` 的值是字符串。
5. 调用读取函数，再做路径与文件检查。

原因是 JSON 不只可以表示对象，也可以表示列表、数字等；解析成功并不保证符合工具要求。

`read_note(note_name: str)` 的 `str` 是类型提示，不会自动执行运行时类型检查。当前分支里的 `type(arguments["note_name"]) is str` 才是实际判断。

工具分发就是根据 `tool_call.function.name` 选择动作。当前通过 `if / elif` 选择 `add` 或 `read_note`，未知名称退出程序。

## 7. 异常传播、捕获与具体错误提示

### 7.1 `raise` 不等于处理完错误

读取函数发现文件不存在时抛出异常，中断自身执行，并把异常传给调用者。调用者没有处理时，异常继续向外传播。

`try` 包住可能失败的调用，`except` 捕获匹配类型；`as exc` 给异常对象起名，f-string 中的 `{exc}` 会显示它的具体说明。

捕获父类也能匹配子类；`FileNotFoundError`、`PermissionError` 都属于 `OSError`。参考：[Python 异常处理](https://docs.python.org/3/tutorial/errors.html#handling-exceptions)。

当前实现片段：

```python
try:
    result = read_note(arguments["note_name"])
except ValueError as exc:
    raise SystemExit(f"读取笔记失败：{exc}")
except OSError as exc:
    raise SystemExit(f"文件操作错误：{exc}")
```

两个分支显示的前缀不同，但都会保留具体原因。解码失败的 `UnicodeDecodeError` 也属于 `ValueError` 的继承体系，会进入第一个分支；今天没有对损坏编码专门做实验。

### 7.2 为什么不能捕获后只打印，然后继续

赋值先执行右侧函数，成功返回后才更新左侧 `result`。如果函数抛出异常，本次赋值未完成。

在循环中，这可能意味着 `result` 仍保存上一次工具的结果。因此失败后继续走成功日志和回传，会把旧结果误当成新结果。

当前代码通过 `SystemExit` 结束程序，避免进入成功路径。本地检查特意预置了旧结果，确认文件失败时没有成功日志，也没有结果消息追加。

### 7.3 目前采用哪一种错误策略

目前是“报错并退出整个程序”。没有把失败作为 `tool` 消息发回模型，也没有自动要求模型换一个文件名重试。

因此一轮多个调用时，如果前面某个成功、后面某个失败，整个程序仍然退出，不会继续下一轮请求。这是当前学习版本的行为。

`raise SystemExit(...)` 才会抛出退出异常；单独创建 `SystemExit(...)` 对象并不会退出。

## 8. 从本地函数接入 Agent

接入分为三个层次：

1. 定义 `read_note` 函数，让它能独立读取并返回正文。
2. 在 `tools` 列表声明工具名、用途和参数；名称、属性与必填项保持一致。
3. 在控制程序中增加执行分支：解析参数 → 校验 → 调用函数 → 成功日志 → 回传正文。

### 8.1 完整执行链

```text
用户：读取 basics.md 并总结
  ↓
模型：请求 read_note，参数 note_name = basics.md，带调用 ID
  ↓
控制程序：保存完整 assistant 调用消息，选择 read_note 分支
  ↓
解析 JSON → 校验字典、参数名和类型
  ↓
read_note：定位路径 → 检查范围/文件/后缀 → 打开并返回正文
  ├─ 失败：捕获异常 → 输出具体原因 → SystemExit
  └─ 成功：记录读取字符数 → 追加带对应 ID 的 tool 结果消息
                                       ↓
下一轮请求：累积历史连同正文发给模型
  ↓
模型总结正文 → 控制程序打印回答并正常停止
```

### 8.2 工具说明与执行分支片段

以下片段从当天已完成源码中提取，用于复盘；它们依赖主程序的变量和上下文，不是独立脚本。

```python
{
    "type": "function",
    "function": {
        "name": "read_note",
        "description": "读取项目 notes/ 目录下的 Markdown 笔记正文",
        "parameters": {
            "type": "object",
            "properties": {
                "note_name": {"type": "string", "description": "待读取的笔记文件名"}
            },
            "required": ["note_name"],
        },
    },
}
```

声明参数为 `note_name`，实际解析时也按同名键读取。工具 Schema 中的 `string` 对应本地期望的 Python `str`。

```python
try:
    arguments = json.loads(tool_call.function.arguments)
except json.JSONDecodeError:
    raise SystemExit("工具参数不是有效的 JSON")
# 校验参数的合法性
# 校验参数列表是否是字典
if not isinstance(arguments, dict):
    raise SystemExit("工具参数列表必须是字典对象")
# 校验参数是否缺失
if not "note_name" in arguments:
    raise SystemExit("缺少参数 note_name")
# 校验参数类型是否是字符串
if not type(arguments["note_name"]) is str:
    raise SystemExit("参数必须是字符串")
# 执行 read_note 函数，获取笔记内容
try:
    result = read_note(arguments["note_name"])
except ValueError as exc:
    raise SystemExit(f"读取笔记失败：{exc}")
except OSError as exc:
    raise SystemExit(f"文件操作错误：{exc}")
# [LOG] 工具执行成功后，显示工具调用 ID、工具名、解析后的参数、执行结果（只打印字符数）
print(
    f"[LOG] 工具执行成功。\n"
    + f"      工具调用 ID：[{tool_call.id}]；工具名：[{tool_call.function.name}]；\n"
    + f"      解析后的参数：[{arguments}]；读取字符数：[{len(result)}]。"
)
# 将工具执行的结果追加至消息列表
messages.append(
    {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": str(result),
    }
)
```

`tool_call_id` 必须对应模型提出的这次请求。`content` 放完整正文，不是文件对象、文件路径或字符数。`result` 已是字符串，因此再次 `str(result)` 多余但无害。

一条包含所有调用的 `assistant` 消息由外层逻辑保存一次；每个执行分支只追加自己的 `tool` 结果。具体循环结构见 [Agent Loop 笔记](agent-loop.md)。

### 8.3 日志打印多少，回传多少

读取日志打印 `len(result)`，避免整篇正文刷屏。回传的 `content` 仍是完整正文。

`len(result)` 是 Python 字符串长度，不是文件字节数，也不是模型 token 数。3260 是当时 `basics.md` 的字符数，内容修改后会变化。

## 9. 真实实验与本地检查

以下为用户实际运行 API 后提供的记录。较长回答做了节选，省略处用“……”标识；调用 ID 是当次生成的。

### 9.1 读取笔记并总结

输入：“请调用 read_note 读取 basics.md，根据实际正文，用三点总结这份笔记的主要内容。”

```text
[LOG] 第 [1] 次调用 SDK；待发送消息 [2] 条。
[LOG] 接收到模型的第 [1] 轮回复；本轮要调用 [1] 个工具。
[LOG] 工具执行成功。
      工具调用 ID：[call_00_YtlR9579I9gelAfB5cGg2871]；工具名：[read_note]；
      解析后的参数：[{'note_name': 'basics.md'}]；读取字符数：[3260]。
[LOG] 第 [2] 次调用 SDK；待发送消息 [4] 条。
[LOG] 接收到模型的第 [2] 轮回复；本轮要调用 [0] 个工具。
[LOG] 正常结束，模型的最终回答为：
……
```

实际回答概括了首次 API 调用流程、消息与参数、回复取值与字段，并指出旧笔记还处于单次问答阶段。

这里“尚未涉及工具调用”说的是旧笔记覆盖范围。模型只读取了 `basics.md`，没有检查当天 `main.py`，所以不能据此判断项目现在没有工具调用。

验证：真实请求了读取工具，正文回传后生成回答，消息数为 2 → 4。模型回答仍需要人工核对；工具执行成功不自动保证总结的每一句都准确。

### 9.2 读取不存在的文件

输入：“请调用 read_note 读取 missing-note-test.md。”

```text
[LOG] 第 [1] 次调用 SDK；待发送消息 [2] 条。
[LOG] 接收到模型的第 [1] 轮回复；本轮要调用 [1] 个工具。
文件操作错误：文件不存在或不是普通文件
```

验证：没有成功日志，没有第 2 轮请求，也没有错误地进入正常结束分支。

### 9.3 本地验证

- `basics.md` 和 `tool-calling.md` 的返回正文与文件内容一致。
- 从 `/tmp` 工作目录运行练习，仍能找到项目笔记。
- 越界相对路径、目录外绝对路径被拒绝。
- 不存在的文件、目录和临时 `.txt` 文件按预期被拒绝，临时文件已清理。
- 无效 JSON、非字典、缺少 `note_name`、错误参数类型被拦截。
- 读取失败时即使预置旧 `result`，也没有成功日志和旧结果消息。

以上离线检查未调用 API；不能与用户提供的真实模型调用记录混为一谈。

## 10. 当前边界

- 失败时退出整个程序，没有给模型回传错误并重试。
- 只按路径和后缀限定读取范围，没有验证正文是否符合 Markdown 语法。
- 全文读入并回传，没有大小限制和正文截断，长文件会增加内存与上下文占用。
- 读取权限和编码问题在真正读取时仍可能出现；今天没有专门验证权限拒绝和损坏编码。
- 笔记正文是待总结的数据，不能把正文中的指令自动当成控制程序应遵循的命令。
- 模型的总结需要人工核对；读取成功不代表每一句总结都准确。

旧的 `basics.md` 只记录了首次 API 调用阶段。模型依据它说“尚未涉及工具调用”描述的是旧笔记的范围，不能据此判断现在的项目没有工具调用。

## 11. 复盘自测

1. 文件路径、文件对象、正文字符串分别是什么？
2. `open` 与 `read` 各自返回什么？
3. 只定义函数为什么不会执行读取？
4. `with` 内 `return` 会不会漏掉关闭文件？
5. 为什么练习中的两次 `.parent` 迁移后要变成一次？
6. 为什么 `notes / 文件名` 不一定指向 `notes` 内部？
7. `.resolve()` 前为什么要给完整拼接表达式加括号？
8. `.suffix` 和 `.is_file()` 为什么一个不加括号，一个加括号？
9. 后缀比较为什么用 `!=`，类型判断却可以用 `is str`？
10. `read_note` 抛出异常时，本次 `result` 赋值是否完成？
11. 为什么捕获错误后只打印再继续，可能回传旧结果？
12. `as exc` 与 f-string 怎样显示具体错误？
13. 日志中的读取字符数和模型收到的内容有何区别？

要点：1 位置、操作对象、文本数据；2 文件对象与字符串；3 `def` 仅定义；4 不会；5 脚本层级不同；6 `..`、绝对路径和符号链接；7 先拼接后解析；8 属性与方法；9 值与身份；10 没有；11 变量可能仍绑定旧值；12 捕获异常对象并显示说明；13 日志显示长度，工具消息发送完整正文。

## 12. 当天读取函数快照

以下为当天 `main.py` 中的原函数。它的单次 `.parent` 是根据函数位于项目根目录脚本设计的。

```python
def read_note(note_name: str):
    notes_dir = (Path(__file__).resolve().parent / "notes").resolve()
    note_path = (notes_dir / note_name).resolve()
    # 三个判断：第一个是判断待读取的文件是否在 notes 目录下
    if not note_path.is_relative_to(notes_dir):
        raise ValueError("只能读取 notes 目录下的笔记")
    # 第二个是判断文件是否存在且是普通文件
    if not note_path.is_file():
        raise FileNotFoundError("文件不存在或不是普通文件")
    # 第三个是判断文件是否是 Markdown 文档
    if note_path.suffix != ".md":
        raise ValueError("笔记扩展名必须是 .md")
    with open(note_path, "r", encoding="utf-8") as note:
        return note.read()
```

完整工具声明、调用分支和 Agent Loop 见 [2026-09-12 完整源码快照](snapshots/2026-09-12-main.py)。快照独立于当前源码保存，仅供阅读；不要将位于笔记子目录的快照当作项目入口运行。
