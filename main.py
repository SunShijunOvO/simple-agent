import os
from openai import OpenAI

# 读取环境变量，获取 DeepSeek 的 API Key
api_key = os.environ.get("DEEPSEEK_API_KEY")

# 如果没有读取到密钥，则退出程序
if not api_key:
    raise SystemExit("未设置 DEEPSEEK_API_KEY，请先在终端中设置密钥。")

# 配置程序与 DeepSeek API 通信的客户端对象
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
        "content": "请用两句话解释什么是 Linux 进程。",
    },
]

# 调用 SDK，将信息发送给 DeepSeek，并接收模型的回复
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,
    stream=False,
    extra_body={"thinking": {"type": "disabled"}},
)

# 从返回对象中取出回答并打印
print(response.choices[0].message.content)

import os
from openai import OpenAI

# 读取环境变量，获取 DeepSeek 的 API Key
api_key = os.environ.get("DEEPSEEK_API_KEY")

# 如果没有读取到密钥，则退出程序
if not api_key:
    raise SystemExit("未设置 DEEPSEEK_API_KEY，请先在终端中设置密钥。")

# 配置程序与 DeepSeek API 通信的客户端对象
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
        "content": "请用两句话解释什么是 Linux 进程。",
    },
]

# 调用 SDK，将信息发送给 DeepSeek，并接收模型的回复
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,
    stream=False,
    extra_body={"thinking": {"type": "disabled"}},
)

# 从返回对象中取出回答并打印
print(response.choices[0].message.content)
