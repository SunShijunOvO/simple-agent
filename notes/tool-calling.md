# Tool Calling：从模型请求到 Python 执行，再回传结果

整理日期：2026-09-11。依据：[当前 main.py](../main.py)。前置笔记：[第一次调用 API](basics.md)。

本文对应当前的学习版本：一个 `add` 工具、一次工具执行、最多两次模型请求，遇到参数错误就提示并结束。文末保留当前源码快照，方便以后改成循环时对照。

## 1. 我已经实现了什么

用户输入：“请调用 add 工具计算 137 加 289。”

程序先收到模型的工具调用请求，在本地计算出 `426`，再将结果发回模型，最终在终端得到：

```text
137 + 289 = **426**
```

`**426**` 是模型生成的 Markdown 文本；普通终端直接打印星号，不代表计算结果的类型发生了变化。

完整流程如下：

```text
Python：定义 add 函数、tools 工具说明、messages 消息列表
    │
    ├── 第一次 API 请求：发送 messages 和 tools
    │
    ▼
模型：返回 assistant 消息，里面有工具调用请求
      name = "add"
      arguments = '{"a": 137, "b": 289}'
      id = 本次调用的标识
    │
    ▼
Python：检查工具名 → 解析 JSON → 校验参数 → 执行 add
      result = 426
    │
    ▼
Python：向 messages 追加两条消息
      ① 模型刚才提出的调用请求
      ② 带有同一调用 ID 的工具结果
    │
    ├── 第二次 API 请求：发送更新后的 messages
    │
    ▼
模型：根据工具结果生成最终回答
    │
    ▼
Python：取出回答文本并打印
```

模型负责提出调用请求；本地程序负责实际执行函数。官方也明确说明，工具的具体功能由开发者实现，模型不会替你执行本地函数。[DeepSeek Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)

这次成功分支中有 **2 次模型请求、1 次本地函数执行**。模型也可能直接回答，此时当前代码只请求一次。

## 2. 先分清：函数、工具说明、调用请求

| 内容 | 当前代码或数据 | 谁提供 | 作用 |
|---|---|---|---|
| 实际函数 | `def add(a, b): return a + b` | 你 | 真正完成计算 |
| 工具说明 | `tools` 中的名称、用途和参数规则 | 你 | 告诉模型可以请求什么 |
| 调用请求 | `name='add'` 和具体的 `arguments` | 模型 | 表示这次希望怎样使用工具 |
| 执行结果 | `result = 426` | Python 执行后得到 | 供模型组织最终回答 |

写出 `"name": "add"` 不会自动把远端模型连接到本地函数。当前真正完成名称到函数对应关系的是：

```python
if tool_call.function.name == "add":
    # 此处省略参数解析与校验，完整实现见文末。
    result = add(arguments["a"], arguments["b"])
```

`"add"` 是字符串，`add` 是 Python 函数，`add(...)` 才是执行函数。三者的用途不同。

函数里的三引号字符串 `"""求两数之和"""` 是文档字符串，供阅读或程序查询；本例没有自动把它转换成工具说明。`tools` 中的 `description` 是你另外写给模型的描述。

## 3. JSON 从零理解

### 3.1 JSON 是一种数据文本格式

JSON 的全称是 JavaScript Object Notation，但使用它不需要先学习 JavaScript。它约定了如何用文本表示对象、数组、字符串、数字、布尔值和空值，方便不同语言的程序交换数据。[JSON 格式说明](https://www.json.org/json-en.html)

本次参数的 JSON 文本是：

```json
{"a": 137, "b": 289}
```

拆开看：

- `{}` 包住一个 JSON 对象。
- `"a"`、`"b"` 是键，也可以理解为字段名。
- `:` 把键与对应的值连接起来。
- `137`、`289` 是数字值。
- `,` 分隔两个键值对。

因此，这段文本的含义是：“参数 a 的值为 137，参数 b 的值为 289。”它没有执行求和，也不包含 Python 函数体。

### 3.2 JSON 对象与 Python 字典长得像，但不是同一层东西

看这两行 Python：

```python
raw = '{"a": 137, "b": 289}'
arguments = {"a": 137, "b": 289}
```

| 变量 | Python 类型 | 存放的内容 | 如何使用 |
|---|---|---|---|
| `raw` | `str` | 一段符合 JSON 格式的文本 | 先解析，才能按参数名取值 |
| `arguments` | `dict` | 已在内存中建立的键值数据 | 可以用 `arguments["a"]` 取值 |

第一行最外面的单引号是 **Python 字符串的边界**，不属于字符串里面的 JSON 文本。字符串内部的双引号才是 JSON 语法的一部分。

例如，`raw[0]` 得到字符 `{`，而 `arguments["a"]` 得到整数 `137`。相同的中括号，在字符串上按位置取字符，在字典上按键取值。[Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)

### 3.3 常见类型如何对应

以下是本练习使用的默认 JSON 解析方式下的对应关系：

| JSON 类型 | JSON 示例 | `json.loads` 后的 Python 类型或值 |
|---|---|---|
| object | `{"a": 137}` | `dict` |
| array | `[137, 289]` | `list` |
| string | `"137"` | `str`，内容是文字 137 |
| number | `137`、`1.5` | 通常分别是 `int`、`float` |
| boolean | `true`、`false` | `True`、`False` |
| null | `null` | `None` |

特别注意 `137` 和 `"137"`：前者是数字，后者是字符串。解析 JSON 不会把所有“看起来像数字的字符串”自动变成数字。[Python JSON 转换说明](https://docs.python.org/3/library/json.html#encoders-and-decoders)

### 3.4 为什么我的 tools 里能写尾随逗号

`main.py` 中写的是 Python 列表与字典，不是直接编写 JSON 文件。Python 允许字典、列表最后一项后面保留逗号，也允许用单引号表示字符串。

标准 JSON 要求对象的键和字符串使用双引号，不支持尾随逗号或 `#` 注释。例如下面是合法 JSON：

```json
{"a": 137, "b": 289}
```

下面只作为错误文本展示：

```text
{'a': 137, 'b': 289}     ← 单引号不符合 JSON 字符串语法
{"a": 137, "b": 289,}   ← JSON 不允许最后这个逗号
```

JSON 布尔值与空值写成 `true`、`false`、`null`，Python 则写成 `True`、`False`、`None`。[JSON 语法](https://www.json.org/json-en.html)

## 4. json.loads、json.dumps 与 SDK 各自做什么

### 4.1 loads：把 JSON 文本变成 Python 数据

```python
import json

raw = '{"a": 137, "b": 289}'
arguments = json.loads(raw)

print(type(raw))         # <class 'str'>
print(type(arguments))   # <class 'dict'>
print(arguments["a"])   # 137
```

`json` 是 Python 标准库，无需用 pip 安装。`loads` 处理的是内存中的文本，`load` 则通常接收打开的文件对象。本项目收到的是字符串，所以用 `loads`。

解析成功只表示它能读懂这段 JSON。`json.loads('[]')` 得到列表，`json.loads('null')` 得到 `None`；并不保证解析结果恰好是你需要的参数字典。[Python json 模块](https://docs.python.org/3/library/json.html)

### 4.2 dumps：把 Python 数据变成 JSON 文本

反过来的操作是：

```python
data = {"a": 137, "b": 289}
text = json.dumps(data)
```

这叫序列化；`loads` 的反向过程叫反序列化。当前主程序没有手动调用 `dumps`，这里只是为了理解两个方向。[Python json.dumps](https://docs.python.org/3/library/json.html#json.dumps)

```text
Python 字典 ── json.dumps ──→ JSON 文本（Python str）
Python 字典 ←─ json.loads ─── JSON 文本（Python str）
```

这里画的是 JSON 对象这个例子；`loads` 也可以解析其他 JSON 类型。

### 4.3 为什么不先把 tools 和 messages 全部 dumps 一遍

你使用的是 SDK 的方法，给 `tools=` 和 `messages=` 传入本地列表、字典或支持的消息对象即可，网络请求的数据转换由 SDK 处理。给这些参数传入 `json.dumps(...)` 的字符串会改变它们的类型，并不符合当前调用方式。

返回后，SDK 已经把外层响应整理成便于访问的对象；但接口里的 `function.arguments` 本身就是一个包含 JSON 文本的字符串，所以仍需要你显式调用 `json.loads`。这是两层不同的转换。可以在 [Chat Completion 接口文档](https://api-docs.deepseek.com/api/create-chat-completion/) 中对照工具调用的返回字段。

```text
发出：本地 messages / tools → SDK → 网络请求
收到：网络响应 → SDK → message 对象
                          └── function.arguments 仍是 str
                                      ↓ json.loads
                                   参数字典
```

所以，终端里的 `ChatCompletionMessage(...)` 是 SDK 对象的显示形式；它本身不是一段可以整体交给 `json.loads` 的 JSON。

## 5. tools 和 JSON Schema：给参数写一份规则

### 5.1 当前工具说明的结构

```text
tools：列表
└── 工具字典
    ├── type: "function"
    └── function：字典
        ├── name: "add"
        ├── description: "计算两个数字的和"
        └── parameters：参数规则
            ├── type: "object"
            ├── properties
            │   ├── "a": {type: "number", description: "第一个加数"}
            │   └── "b": {type: "number", description: "第二个加数"}
            └── required: ["a", "b"]
```

这是结构示意，不是可直接执行的 Python 或 JSON。

`tools` 是列表，因为以后可以提供多个工具。当前只有一个元素。`function.name` 用于标识工具，`description` 说明用途，`parameters` 用 JSON Schema 描述参数应该长什么样。

### 5.2 JSON Schema 是数据的规则，不是这次的参数值

对本例来说：

| 内容 | 回答的问题 | 示例 |
|---|---|---|
| Schema | 参数应该是什么样 | a 和 b 都必须存在，且都是数字 |
| 实际参数 | 这次具体填什么 | `{"a": 137, "b": 289}` |

可以把 Schema 理解为表格的填写要求，把实际参数理解为一次填好的表格。

`properties` 说明字段的要求，`required` 单独列出必填字段。只在 `properties` 里声明字段，不会自动让它变成必填项。当前规则没有禁止额外字段，所以 `required` 也不表示“只能有 a 和 b”。[JSON Schema 对象规则](https://json-schema.org/understanding-json-schema/reference/object)

### 5.3 为什么出现了好几个 type

| 位置 | 值 | 描述谁 |
|---|---|---|
| 工具字典的 `type` | `"function"` | API 的工具类别 |
| `parameters.type` | `"object"` | 整组参数的结构 |
| `properties.a.type`、`properties.b.type` | `"number"` | 单个参数的值 |

外层 `object` 的意思是“整组参数采用键值结构”，不是说 a、b 的值也要是对象。`number` 允许整数和小数。

这些字典中的 `"type"` 是字符串键；你在校验代码里调用的 `type(...)` 则是 Python 内置函数。它们不是同一个东西。

### 5.4 为什么有了 Schema 还要手动校验

当前 Python 函数没有自动执行 Schema 校验。你写出的规则说明了希望收到什么；`json.loads` 只解析文本，也不会代替你检查这些规则。收到数据后仍要确认它适合交给函数。

例如 `{"a": "137", "b": "289"}` 是合法 JSON，却不满足当前数字参数要求。如果不检查，Python 的字符串加法会得到 `"137289"`。

## 6. 第一次请求：让模型提出工具调用

代码先读取密钥并创建客户端，再准备 `system` 和 `user` 消息，最后调用：

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    tools=tools,
    messages=messages,
    stream=False,
    extra_body={"thinking": {"type": "disabled"}},
)
```

| 配置 | 在本练习中的作用 |
|---|---|
| `api_key` | 访问 DeepSeek 的凭证，从环境变量读取 |
| `base_url` | 指定请求发往 DeepSeek |
| `model` | 选择模型 |
| `tools=tools` | 左边是方法参数名，右边是你定义的工具列表 |
| `messages=messages` | 提供目前的对话内容 |
| `stream=False` | 本例等待完整响应后再处理 |
| `extra_body` | 本例传入关闭思考模式的配置 |

密钥检查、客户端和普通消息的基础解释见 [basics.md](basics.md)。当前练习固定使用非思考模式；改变模式后应再核对接口的消息回传要求。

## 7. 读懂实际返回的工具调用

你运行时看到的关键数据，简化后是：

```text
message
├── role = 'assistant'
├── content = ''
└── tool_calls = [
      一个调用对象：
        id = 'call_00_QtLhNmauiqLkODcWazRR9327'
        type = 'function'
        function.name = 'add'
        function.arguments = '{"a": 137, "b": 289}'
    ]
```

这个 ID 来自你当时的实际输出，是那一次调用的标识，不应硬编码到下一次运行。

### 7.1 为什么保存 message

```python
message = response.choices[0].message
```

`response` 是完整返回对象，`choices[0]` 是第一个候选回答，`.message` 是其中的消息。变量 `message` 让后续访问更清楚，不会因此新增网络请求。

### 7.2 为什么判断 tool_calls

```python
if message.tool_calls:
    tool_call = message.tool_calls[0]
else:
    print(message.content)
```

有调用才进入执行分支；如果它是 `None` 或空列表，就直接打印正文，避免对不存在的调用取下标。当前取 `[0]` 表示只处理第一个调用，尚未覆盖一次多个调用。

`content=''` 在你这次输出中表示没有正文，不能据此判断请求失败。真正的调用要求在 `tool_calls` 中。

### 7.3 为什么有时用点，有时用中括号

| 表达式 | 当前对象类型 | 访问方式 |
|---|---|---|
| `message.tool_calls` | SDK 消息对象 | 用点访问属性 |
| `message.tool_calls[0]` | 调用列表 | 用整数下标取元素 |
| `tool_call.function.name` | SDK 调用对象及其嵌套对象 | 用点访问属性 |
| `arguments["a"]` | 解析后的 Python 字典 | 用键取值 |

不要因为它们都保存数据，就把字典访问和对象属性访问混用。例如本例中的 `arguments.a` 不能代替 `arguments["a"]`。

## 8. 解析、校验、执行：每一步在防止什么

### 8.1 先检查工具名

只有名称为 `"add"` 才进入对应分支。未知名称使用现有提示，不调用函数。模型传来的名字通过你写的分支得到处理；程序不需要执行名字字符串本身，也不需要使用 `eval`。

### 8.2 捕获 JSON 解析错误

```python
try:
    arguments = json.loads(tool_call.function.arguments)
except json.JSONDecodeError:
    raise SystemExit("工具参数不是有效的 JSON")
```

`try` 尝试解析，发生指定异常时进入 `except`。成功就继续后面的校验。这里只有解析语句放在 `try` 里，便于明确错误来自哪一步。

你曾经写过 `SystemExit("...")` 而没有 `raise`。前者只创建一个异常对象；加上 `raise` 才会抛出它，并在当前脚本中终止执行。它不是“打印后继续”。[Python 异常处理](https://docs.python.org/3/tutorial/errors.html)

### 8.3 检查解析结果是字典

```python
if not isinstance(arguments, dict):
    raise SystemExit("工具参数必须是对象")
```

合法 JSON 可以是 `null`、列表或一个数字。这个检查保证后面确实是在参数字典上查找键。

### 8.4 检查必填键

```python
if not ("a" in arguments and "b" in arguments):
    raise SystemExit("缺少参数 a 或 b")
```

`"a" in arguments` 检查字典是否包含键 a，不是检查值是否为真。a 的值为 `0` 也算已提供；值为 `None` 同样算键存在，但会在下一步类型检查被拒绝。

只有确认键存在后，才能放心用 `arguments["a"]` 取值，避免 `KeyError`。

### 8.5 检查两个值都是数字

当前代码的条件，换行后便于阅读：

```python
if not (
    type(arguments["a"]) in (int, float)
    and type(arguments["b"]) in (int, float)
):
    raise SystemExit("参数必须是数字")
```

`type(value)` 取得值的实际类型；`(int, float)` 是包含两个类型的元组。这里的 `in` 是判断类型是否属于允许的两个类型。

设 A 表示“a 是数字”，B 表示“b 是数字”：

| A | B | `A and B` | `not (A and B)`：是否拒绝 |
|---|---|---|---|
| 真 | 真 | 真 | 否 |
| 真 | 假 | 假 | 是 |
| 假 | 真 | 假 | 是 |
| 假 | 假 | 假 | 是 |

`not (A and B)` 等价于 `(not A) or (not B)`，不等价于 `(not A) and B`。括号决定这里否定的是整个“两个都合法”的条件。

此外，Python 的 `bool` 是 `int` 的子类，`isinstance(True, int)` 为真；当前的精确类型判断会排除它。JSON 的 `true` 被解析成 `True` 后，就会被这里拒绝，避免 `True + 289` 得到 `290`。

### 8.6 校验通过后执行函数

```python
result = add(arguments["a"], arguments["b"])
```

本次相当于执行 `add(137, 289)`。函数用 `return` 把 `426` 交给调用者，由变量 `result` 保存。

`print(result)` 只用于终端观察，不会把数字发送给模型。要让模型知道结果，必须继续构造下面的工具结果消息。

## 9. 回传结果：为什么要追加两条消息

### 9.1 先保存模型的原始调用消息

```python
messages.append(message)
```

`append` 在列表末尾加入一个元素，直接修改原列表；不要写成 `messages = messages.append(message)`，因为 `append` 的返回值是 `None`。[Python 列表方法](https://docs.python.org/3/tutorial/datastructures.html#more-on-lists)

当前加入的是 SDK 返回的完整消息对象，它包含 `role='assistant'` 和工具调用内容。即使正文为空，也要保留调用请求；只添加 `message.content` 会丢失函数名、参数和 ID。官方示例也直接把此消息对象追加到消息列表。[DeepSeek Tool Calls 示例](https://api-docs.deepseek.com/guides/tool_calls/)

### 9.2 再加入本地计算结果

```python
messages.append(
    {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": str(result),
    }
)
```

| 字段 | 当前的值 | 为什么需要 |
|---|---|---|
| `role` | `"tool"` | 区分工具结果和用户输入、助手回答 |
| `tool_call_id` | 从当前调用对象读取的 ID | 表明是在回答哪一次工具调用 |
| `content` | `"426"` | 提供可传递的文本结果 |

工具名回答“调用了哪种功能”，ID 回答“对应哪一次调用”。即使两次都调用 add，也需要用各自的 ID 对应结果。

### 9.3 为什么是 str(result)，不是直接放数字

当前工具结果消息的 `content` 使用文本。`result` 是整数 `426`，`str(result)` 得到字符串 `"426"`。

```text
result                   426         int，Python 的计算结果
str(result)              '426'       str，准备作为消息正文
工具结果消息              一个 dict    role / tool_call_id / content
整个请求                  由 SDK 编码后发送
```

工具结果正文不要求必须是一份 JSON 对象。本例一个数字转成文本就够了。

如果未来工具返回字典，例如 `{"sum": 426, "ok": True}`，希望用 JSON 组织正文，可以先 `json.dumps(...)`。`str(dict)` 只是 Python 字典的显示形式，不保证符合 JSON 语法。当前代码尚不需要做这项扩展。

### 9.4 对话记录的顺序

第二次请求前，列表从两条变成四条：

| 下标 | 角色 | 内容 |
|---|---|---|
| 0 | `system` | 你是一位编程老师，请用简洁的中文回答 |
| 1 | `user` | 请调用 add 工具计算 137 加 289 |
| 2 | `assistant` | 请求调用 add，携带参数和调用 ID |
| 3 | `tool` | 返回 426，携带对应调用 ID |

这四条消息让第二次请求能够了解任务、调用过程和结果。不能只把 `426` 孤立地发过去，也不能丢掉之前的调用消息。

## 10. 第二次请求：生成最终回答

```python
final_response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,
    stream=False,
    extra_body={"thinking": {"type": "disabled"}},
)
print(final_response.choices[0].message.content)
```

这是当前源码中的第二次请求：使用更新后的四条消息，没有再提供 `tools`，用于让模型根据已有结果完成回答。

`response` 与 `final_response` 是你给两个返回对象起的变量名，不是特殊关键字。分开命名便于区分“第一次的调用请求”和“第二次的最终回答”。

第二次回答目前只打印，没有追加回 `messages`，因为脚本随后就结束。如果以后继续接收用户输入，才需要补上持续保存对话的逻辑。

## 11. 所有关键变量的复盘表

| 名称 | 当前类型 | 谁产生 | 保存什么 |
|---|---|---|---|
| `add` | 函数 | 你定义 | 本地求和逻辑 |
| `tools` | `list`，元素是 `dict` | 你定义 | 可用工具及参数规则 |
| `messages` | `list` | 你维护 | 本次调用过程的对话记录 |
| `response` | SDK 响应对象 | 第一次 API 请求 | 第一次模型回复 |
| `message` | SDK 消息对象 | 从 response 取出 | 正文及工具调用列表 |
| `tool_call` | SDK 工具调用对象 | 从列表取出 | 一个调用的名称、参数文本和 ID |
| `tool_call.function.arguments` | `str` | 模型回复中的字段 | JSON 格式的参数文本 |
| `arguments` | 校验通过后是 `dict` | `json.loads` | 可按键读取的参数 |
| `result` | 本例是 `int` | 本地 add | 数值 426 |
| `final_response` | SDK 响应对象 | 第二次 API 请求 | 最终回答 |

特别容易混淆的两个词：`parameters` 是工具定义中的参数规则；`arguments` 是这次调用的实际参数。源码中的局部变量 `arguments` 是解析之后的字典，同名的返回字段在解析前则是字符串。

## 12. 已验证的行为与当前限制

### 12.1 已有证据

你已经完成真实 API 演示，并得到了 `137 + 289 = **426**`。后续参数校验的检查使用离线模拟，不产生新的模型请求。

最近一次离线检查的 12 个样例全部通过：

| 样例 | 参数文本 | 预期及已观察到的结果 |
|---|---|---|
| 整数 | `{"a":137,"b":289}` | 计算 426 并进入第二次请求的模拟 |
| 小数与负数 | `{"a":1.5,"b":-2}` | 计算 -0.5 并进入第二次请求的模拟 |
| 无效 JSON | `{` | 提示 JSON 无效并结束 |
| 空值 | `null` | 提示必须是对象并结束 |
| 列表 | `[]` | 提示必须是对象并结束 |
| 缺少 a | `{"b":1}` | 提示缺少参数并结束 |
| 缺少 b | `{"a":1}` | 提示缺少参数并结束 |
| 两个字符串 | `{"a":"137","b":"289"}` | 提示必须是数字并结束 |
| a 为字符串 | `{"a":"137","b":289}` | 提示必须是数字并结束 |
| b 为字符串 | `{"a":137,"b":"289"}` | 提示必须是数字并结束 |
| a 为布尔值 | `{"a":true,"b":289}` | 提示必须是数字并结束 |
| b 为布尔值 | `{"a":137,"b":false}` | 提示必须是数字并结束 |

失败样例均未继续求和或进入第二次请求。离线检查验证的是本地控制流程，不能代替服务可用性或任意模型输出的验证。

### 12.2 尚未实现

- **一次多个调用**：当前只处理 `tool_calls[0]`。若一次返回多个调用，完整助手消息中会保留全部调用，却只回传第一个结果。后续应遍历调用列表，每个调用提供对应结果，再请求模型。
- **多轮工具执行**：目前固定两次请求，没有 Agent Loop。下一阶段才改为“有工具就执行并回传，无工具就结束”的有上限循环。
- **错误回传与修正**：当前参数错误会结束程序，未知工具会打印提示，没有把错误作为工具结果发送给模型。
- **API 异常处理**：网络、认证、余额等失败还没有专门处理。不能把参数校验通过理解为所有异常都已覆盖。
- **更严格的数字与字段规则**：当前未拒绝额外字段，也未检查非有限浮点数及结果范围；现阶段验证范围是上表里的普通参数。

这些是当前版本的边界，不应在复盘时写成已经完成的功能。

## 13. 不看代码时，试着回答这些问题

1. 模型返回 `name='add'` 后，究竟是哪一行真正执行函数？
2. 工具说明中的 `parameters` 与返回的 `arguments` 有什么区别？
3. 为什么 `arguments` 看起来像字典，却还要调用 `json.loads`？
4. `json.loads` 成功后，为什么还要检查字典、键和数字类型？
5. `not (A and B)` 为什么能拒绝任意一个错误参数？
6. 为什么要写 `raise SystemExit(...)`，而不是只写 `SystemExit(...)`？
7. 为什么 `messages` 里要先放助手调用消息，再放工具结果？
8. 同一个 add 调用两次，为什么不能只靠名字对应结果？
9. 为什么终端打印 426 之后，模型还不知道结果？
10. 第一次和第二次 API 请求的输入、输出分别是什么？

可以用这段话自述当前实现：

> 我先用工具说明告诉模型可以调用 add。模型返回函数名、调用 ID 和 JSON 格式的参数字符串。Python 检查工具名，解析并校验参数后执行函数，再把原始调用消息和对应结果追加到对话记录。第二次请求携带更新后的记录，让模型生成最终回答。当前实现支持单次工具调用，参数错误会明确退出，还没有改成 Agent Loop。

## 14. 当前源码快照

以下为整理笔记时的 `main.py` 原样快照，不是另一份需要运行或维护的源码。前文的解释以此版本为准；后续修改源码不会自动更新这里。

```python
import os
from openai import OpenAI
import json


# 一个十分十分十分十分简单的求和函数，用于 Tool Calling
def add(a, b):
    """求两数之和"""
    return a + b


# 工具列表：告诉大模型都有什么工具，以及它们的用途、接收参数等
# 一个工具使用一个字典进行说明
tools = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "计算两个数字的和",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个加数"},
                    "b": {"type": "number", "description": "第二个加数"},
                },
                "required": ["a", "b"],
            },
        },
    }
]

# 读取环境变量，获取 DeepSeek 的 API Key
api_key = os.environ.get("DEEPSEEK_API_KEY")

# 如果没有读取到密钥，则退出程序
if not api_key:
    raise SystemExit("未设置 DEEPSEEK_API_KEY，请先在终端中设置密钥。")

# 程序与 DeepSeek API 通信的客户端对象
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

# 要发送给大模型的消息
messages = [
    {
        "role": "system",
        "content": "你是一位编程老师，请用简洁的中文回答。",
    },
    {
        "role": "user",
        # "content": "请用两句话解释什么是 Linux 进程。",
        "content": "请调用 add 工具计算 137 加 289。",
    },
]

# 调用 SDK，将信息发送给 DeepSeek，并接收模型的回复
response = client.chat.completions.create(
    model="deepseek-flash",
    tools=tools,
    messages=messages,
    stream=False,
    extra_body={"thinking": {"type": "disabled"}},
)

# # 从返回对象中取出回答并打印
# print(response.choices[0].message.content)
# # 从返回对象中取出完整消息并打印
# print(response.choices[0].message)

# 返回对象的完整消息
message = response.choices[0].message

if message.tool_calls:
    tool_call = message.tool_calls[0]
    if tool_call.function.name == "add":
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            raise SystemExit("工具参数不是有效的 JSON")
        if not isinstance(arguments, dict):
            raise SystemExit("工具参数必须是对象")
        if not ("a" in arguments and "b" in arguments):
            raise SystemExit("缺少参数 a 或 b")
        if not (type(arguments["a"]) in (int, float) and type(arguments["b"]) in (int, float)):
            raise SystemExit("参数必须是数字")
        result = add(arguments["a"], arguments["b"])
        # print(result)
        messages.append(message)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            }
        )
        final_response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
        print(final_response.choices[0].message.content)
    else:
        print("未知工具，避免执行错误的函数")
else:
    print(message.content)
```


<a id="response-archive"></a>

## 15. 完整工具调用响应样例归档

归档日期：2026-09-13。来源：原 `tmp/example_大模型返回消息示例.txt`。这是一份之前保存的 SDK 对象文本，归档时没有重新请求模型；原文件没有注明对应的执行命令，因此不据此补造一次新的实验记录。

下面保留完整样例。`ChatCompletion(...)` 是对象的文本表示，不是 JSON，也不是可直接运行的 Python 脚本。

```text
# 大模型返回消息的样子：
ChatCompletion(
    id="eeab60f7-742e-4cd5-bcf1-976d5967ec9c",
    choices=[
        Choice(
            finish_reason="tool_calls",
            index=0,
            logprobs=None,
            message=ChatCompletionMessage(
                content="",
                refusal=None,
                role="assistant",
                annotations=None,
                audio=None,
                function_call=None,
                tool_calls=[
                    ChatCompletionMessageFunctionToolCall(
                        id="call_00_jJhI4vmQRMD7ywkkzo2S3932",
                        function=Function(arguments='{"a": 137, "b": 289}', name="add"),
                        type="function",
                        index=0,
                    )
                ],
            ),
        )
    ],
    created=1789202287,
    model="deepseek-flash",
    object="chat.completion",
    moderation=None,
    service_tier=None,
    system_fingerprint="aeb56401ca74e127821c4f9126dcb669",
    usage=CompletionUsage(
        completion_tokens=52,
        prompt_tokens=313,
        total_tokens=365,
        completion_tokens_details=None,
        prompt_tokens_details=PromptTokensDetails(
            audio_tokens=None, cache_write_tokens=None, cached_tokens=128
        ),
        prompt_cache_hit_tokens=128,
        prompt_cache_miss_tokens=185,
    ),
)
```

读这份样例时，按层次定位：

| 字段或访问位置 | 这份样例的内容 | 用途 |
| --- | --- | --- |
| `response.id` | `eeab60f7-742e-4cd5-bcf1-976d5967ec9c` | 完整响应的标识，不是工具调用 ID |
| `response.choices[0].finish_reason` | `tool_calls` | 本次响应以提出工具调用结束，不等于用户任务已完成 |
| `response.choices[0].message.content` | 空字符串 | 本次主要返回工具调用；只打印正文会漏掉要执行的动作 |
| `message.tool_calls[0].id` | `call_00_jJhI4vmQRMD7ywkkzo2S3932` | 回传该工具结果时使用的 `tool_call_id` |
| `message.tool_calls[0].function.name` | `add` | 选择本地求和函数 |
| `message.tool_calls[0].function.arguments` | `'{"a": 137, "b": 289}'` | JSON 文本，先解析并校验，再执行工具 |
| `response.usage` | 输入 313、输出 52、合计 365 tokens | 该次响应中的用量记录，不是文件字符数 |

表中的 `message` 指 `response.choices[0].message`。当前主程序实际使用 `response_message.tool_calls` 判断是否需要执行工具；不会因为看到空 `content` 就认定任务已经完成。

样例还保存了模型名、生成时间字段、缓存用量和服务端附加字段。这些值属于该份响应，不保证下一次相同，也不表明控制程序对它们都进行了处理。普通文本回答的消息样例见 [basics.md 第 6 节](basics.md#6-记录的消息对象及字段说明)。
