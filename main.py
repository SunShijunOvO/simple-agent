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

# 初始化要发送给大模型的消息
messages = [
    {
        "role": "system",
        "content": "你是一位编程老师，请用简洁的中文回答。",
    },
    {
        "role": "user",
        "content": "请先调用 add 计算 137＋289。收到工具返回结果后，再调用 add，将这个结果加 100。两步都必须使用工具，最后告诉我结果。",
    },
]

# 限制最多请求 5 轮
for i in range(5):
    # [LOG] 每轮请求调用 SDK 之前，先记录这是第几次调用、准备发送的消息数量是多少
    print(f"[LOG] 第 [{i + 1}] 次调用 SDK；待发送消息 [{len(messages)}] 条。")
    # 调用 SDK，将信息发送给 DeepSeek，并接收模型的回复
    # 每轮只保留一次模型请求
    response = client.chat.completions.create(
        model="deepseek-flash",
        tools=tools,
        messages=messages,
        stream=False,
        extra_body={"thinking": {"type": "disabled"}},
    )
    # 保存模型回复的消息
    response_message = response.choices[0].message

    # 检查模型的回复中是否包含 tool_calls
    if response_message.tool_calls:
        # [LOG] 如果有 tool_calls，则记录本轮有多少工具调用。
        print(
            f"[LOG] 接收到模型的第 [{i + 1}] 轮回复；"
            + f"本轮要调用 [{len(response_message.tool_calls)}] 个工具。"
        )
        # 如果有 tool_calls，则将模型回复的消息追加至 messages
        messages.append(response_message)
        # 然后依次调用所有工具
        for tool_call in response_message.tool_calls:
            # 如果模型所调用的工具是 "add"，则执行解析、校验、执行、追加消息操作
            if tool_call.function.name == "add":
                # 解析参数，模型给出的参数列表是 JSON 形式的，需要解析成 Python 的数据格式
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    raise SystemExit("工具参数不是有效的 JSON")
                # 校验参数的合法性
                # 校验参数列表是否是字典
                if not isinstance(arguments, dict):
                    raise SystemExit("工具参数列表必须是字典对象")
                # 校验参数是否缺失
                if not ("a" in arguments and "b" in arguments):
                    raise SystemExit("缺少参数 a 或 b")
                # 校验参数类型是否都是数字
                if not (
                    type(arguments["a"]) in (int, float)
                    and type(arguments["b"]) in (int, float)
                ):
                    raise SystemExit("参数必须是数字")
                # 执行 add 函数，计算结果
                result = add(arguments["a"], arguments["b"])
                # [LOG] 工具执行成功后，显示工具调用 ID、工具名、解析后的参数、执行结果
                print(
                    f"[LOG] 工具执行成功。\n"
                    + f"      工具调用 ID：[{tool_call.id}]；工具名：[{tool_call.function.name}]；\n"
                    + f"      解析后的参数：[{arguments}]；执行结果：[{result}]。"
                )
                # 将工具执行的结果追加至消息列表
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                )
            else:
                # 调用了未知的工具，退出程序
                raise SystemExit("未知工具，避免执行错误的函数")
    else:
        # [LOG] 如果没有 tool_calls，则记录本轮要调用 0 个工具
        # 没有工具调用的时候，tool_calls 为 None，无法使用 len 取个数
        print(f"[LOG] 接收到模型的第 [{i + 1}] 轮回复；本轮要调用 [0] 个工具。")
        # 如果没有 tool_calls，则直接打印模型的回复信息内容，然后结束循环
        # 即使在最后一轮循环中模型回复了不包含 tool_calls 的消息，程序依然可以正常 break
        # [LOG] 正常结束的提示和最终的回答
        print("[LOG] 正常结束，模型的最终回答为：")
        print(response_message.content)
        break
else:
    # [LOG] 循环自然结束，说明请求轮数已经耗尽，且尚未获得最终答案，此时显示次数耗尽的提示
    print("[LOG] 模型请求达到最大轮数，尚未获得最终答案")
