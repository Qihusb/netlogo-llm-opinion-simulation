# diagnose_zhipuai.py
import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI
import json

load_dotenv()

# 初始化客户端
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

# 简单的测试消息
messages = [
    {"role": "system", "content": "你是一个专业的新闻记者"},
    {"role": "user", "content": "请提出一个关于台湾问题的简单问题。"}
]

print("诊断智谱AI API响应结构...")
print("="*60)

try:
    # 调用API
    response = client.chat.completions.create(
        model="glm-4.5-flash",
        messages=messages,
        temperature=0.7,
        max_tokens=100,
        stream=False
    )
    
    print("1. 响应对象类型:", type(response))
    print()
    
    print("2. 使用 model_dump() 查看完整结构:")
    print("-"*40)
    try:
        if hasattr(response, 'model_dump'):
            data = response.model_dump()
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("没有 model_dump 方法")
    except Exception as e:
        print(f"model_dump 失败: {e}")
    print()
    
    print("3. 直接查看 choices 结构:")
    print("-"*40)
    if hasattr(response, 'choices'):
        print(f"choices 数量: {len(response.choices)}")
        for i, choice in enumerate(response.choices):
            print(f"\nChoice {i}:")
            print(f"  类型: {type(choice)}")
            
            # 检查 choice 对象的所有属性
            if hasattr(choice, '__dict__'):
                print(f"  属性: {choice.__dict__.keys()}")
                for key, value in choice.__dict__.items():
                    print(f"    {key}: {type(value)} = {repr(value)[:100]}")
            else:
                print(f"  没有 __dict__ 属性")
                
            # 尝试获取 message
            if hasattr(choice, 'message'):
                msg = choice.message
                print(f"  message 类型: {type(msg)}")
                if hasattr(msg, '__dict__'):
                    print(f"  message 属性: {msg.__dict__.keys()}")
                    for key, value in msg.__dict__.items():
                        print(f"    {key}: {type(value)} = {repr(value)[:100]}")
                else:
                    print(f"  message 没有 __dict__ 属性")
    print()
    
    print("4. 查看 usage 信息:")
    print("-"*40)
    if hasattr(response, 'usage'):
        usage = response.usage
        if hasattr(usage, '__dict__'):
            print(f"usage: {usage.__dict__}")
        else:
            print(f"usage: {usage}")
    print()
    
    print("5. 尝试直接获取内容:")
    print("-"*40)
    # 多种方式尝试获取内容
    methods = [
        ("response.choices[0].message.content", 
         lambda: response.choices[0].message.content if hasattr(response.choices[0].message, 'content') else None),
        ("response.choices[0].message['content']", 
         lambda: response.choices[0].message['content'] if isinstance(response.choices[0].message, dict) and 'content' in response.choices[0].message else None),
        ("response.choices[0]['message']['content']", 
         lambda: response.choices[0]['message']['content'] if isinstance(response.choices[0], dict) and 'message' in response.choices[0] and 'content' in response.choices[0]['message'] else None),
    ]
    
    for method_name, method_func in methods:
        try:
            content = method_func()
            print(f"{method_name}: {content}")
        except Exception as e:
            print(f"{method_name}: 失败 - {e}")
            
except Exception as e:
    print(f"API调用失败: {e}")
    import traceback
    traceback.print_exc()