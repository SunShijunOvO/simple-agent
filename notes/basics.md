# Agent 基础：第一次调用 DeepSeek API

本笔记整理自 `main.py` 中的代码、注释和返回值记录。
当前已完成一次普通对话请求：发送问题，接收模型回答，在终端打印文本。

## 1. 请求流程

读取环境变量中的密钥 → 检查密钥 → 创建客户端 → 准备消息 → 发送请求 → 取出并打印回答。

## 2. 读取密钥并创建客户端

```python
import os
from openai import OpenAI

api_key = os.environ.get("DEEPSEEK_API_KEY")

if not api_key:
    raise SystemExit("未设置 DEEPSEEK_API_KEY，请先在终端中设置密钥。")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)
```

- `os.environ.get(...)` 从当前进程的环境变量中读取密钥；变量不存在时返回 `None`。
- `if not api_key` 检查密钥是否缺失或为空，`raise SystemExit(...)` 给出提示并结束程序。
- `OpenAI` 是 SDK 提供的客户端类。这里通过 `base_url` 指定 DeepSeek 服务器，并使用 DeepSeek 的密钥。
- `client` 是配置好的客户端对象。创建它时尚未向模型提问，后续通过它的方法发送请求。

## 3. 消息列表与角色

```python
messages = [
    {
        "role": "system",
        "content": "你是一位编程老师，请用简洁的中文回答。",
    },
    {
        "role": "user",
        "content": "请用两句话解释什么是 Linux 进程。",
    },
]
```

`messages` 是一个 Python 列表，其中每个字典表示一条消息。
本例用 `role` 表示消息角色，用 `content` 表示消息内容。

| 角色 | 用途 | 本次是否使用 |
|---|---|---|
| `system` | 设置对模型的整体要求，例如用中文、简洁回答 | 是 |
| `user` | 发送用户的问题 | 是 |
| `assistant` | 在对话记录中保存模型之前的回答 | 否 |
| `tool` | 向模型提供工具执行结果，后续学习工具调用时使用 | 否 |

原注释中的 `{"role": "assistant"}` 和 `{"role": "tool"}` 只是角色示意，不是完整的可发送消息。

## 4. 发送请求并接收回复

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,
    stream=False,
    extra_body={"thinking": {"type": "disabled"}},
)
```

调用 `client.chat.completions.create(...)` 时，SDK 才真正向 DeepSeek 发送请求。
返回的对象保存在变量 `response` 中。

| 参数 | 本次取值 | 作用 |
|---|---|---|
| `model` | `"deepseek-flash"` | 指定使用的模型 |
| `messages` | 前面定义的消息列表 | 提供本次请求的消息 |
| `stream` | `False` | 等完整回答生成后返回，即非流式输出 |
| `extra_body` | `{"thinking": {"type": "disabled"}}` | 传入 DeepSeek 扩展参数，本次关闭思考模式 |

## 5. 从返回对象中取出文本

```python
print(response.choices[0].message.content)
```

这条表达式的访问顺序是：返回结果 → 第一个候选回答 → 消息 → 文本内容。

| 表达式 | 含义 |
|---|---|
| `response` | 本次请求返回的完整对象 |
| `response.choices` | 候选回答列表 |
| `response.choices[0]` | 第一个候选回答，Python 下标从 0 开始 |
| `response.choices[0].message` | 该候选回答中的消息对象 |
| `response.choices[0].message.content` | 消息中的正文文本 |

`print(...)` 将取出的正文显示在终端。

## 6. 记录的消息对象及字段说明

源码注释中记录了以下消息对象示例。它对应 `response.choices[0].message` 这一层，而不是完整的 `response`，也不是最终打印的 `.content` 字符串：

```text
ChatCompletionMessage(content='进程是正在运行的程序的实例，拥有独立的内存空间和系统资源。Linux 通过进程来管理程序的执行、调度和资源分配。', refusal=None, role='assistant', annotations=None, audio=None, function_call=None, tool_calls=None)
```

| 字段 | 含义 | 记录中的值说明什么 |
|---|---|---|
| `content` | 模型回复的正文 | 就是解释 Linux 进程的文字 |
| `refusal` | 专门存放拒绝回答的说明 | `None` 表示这里没有提供拒绝说明 |
| `role` | 消息的角色 | `assistant` 表示这条消息来自模型助手 |
| `annotations` | 正文的附加标注，例如引用来源 | `None` 表示没有提供标注 |
| `audio` | 生成的音频相关信息 | `None` 表示没有提供音频信息 |
| `function_call` | 旧版函数调用字段，已被 `tool_calls` 取代 | 这次没有提供旧版函数调用 |
| `tool_calls` | 模型请求调用的工具列表，包含工具名称、参数等 | `None` 表示这条消息没有请求调用工具 |

`None` 表示该字段没有值。以上是本次记录中出现的 SDK 消息对象字段，不代表每次请求都会返回音频、标注或工具调用。

## 7. 当前练习的边界

当前代码完成的是一次提问和回答，还没有声明工具、执行工具或回传工具结果。
消息列表中也没有加入之前的回答，因此每次重新运行程序都会从代码中定义的消息开始。

## 参考资料

- [DeepSeek Chat Completion 接口文档](https://api-docs.deepseek.com/api/create-chat-completion/)（原代码中的参考链接）
- [DeepSeek 首次调用 API](https://api-docs.deepseek.com/zh-cn/)
- [DeepSeek 思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)
