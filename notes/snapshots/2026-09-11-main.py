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
