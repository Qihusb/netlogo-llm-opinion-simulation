#!/usr/bin/env python3
"""
NetLogo文件轮询HTTP客户端
持续检查temp_request.txt文件，处理请求并返回结果
"""
import os
import json
import time
import requests
from pathlib import Path

def process_request(request_file="temp_request.txt"):
    """处理单个请求文件"""
    try:
        # 读取请求文件
        with open(request_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]
        
        if len(lines) < 3:
            return False, "请求文件格式错误"
        
        method = lines[0]  # GET 或 POST
        url = lines[1]     # API地址
        json_str = lines[2]  # JSON数据
        
        # 发送HTTP请求
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        else:  # POST
            headers = {"Content-Type": "application/json"}
            try:
                json_data = json.loads(json_str) if json_str else {}
                response = requests.post(url, json=json_data, headers=headers, timeout=30)
            except json.JSONDecodeError:
                return False, "JSON数据格式错误"
        
        # 写入响应文件
        if response.status_code == 200:
            with open("temp_response.txt", "w", encoding="utf-8") as f:
                f.write(f"200|{response.text}")
            print(f"✓ 请求成功: {method} {url}")
            return True, "成功"
        else:
            with open("temp_error.txt", "w", encoding="utf-8") as f:
                f.write(f"error|HTTP {response.status_code}: {response.text[:100]}")
            print(f"✗ 请求失败: HTTP {response.status_code}")
            return False, f"HTTP {response.status_code}"
            
    except Exception as e:
        # 写入错误文件
        with open("temp_error.txt", "w", encoding="utf-8") as f:
            f.write(f"error|{str(e)}")
        print(f"✗ 处理异常: {str(e)}")
        return False, str(e)

def main():
    """主函数 - 持续轮询"""
    print("=== NetLogo文件轮询HTTP客户端 ===")
    print("正在监听请求文件...")
    print("按 Ctrl+C 停止")
    
    # 清理旧文件
    for file in ["temp_request.txt", "temp_response.txt", "temp_error.txt"]:
        if os.path.exists(file):
            os.remove(file)
    
    try:
        while True:
            # 检查是否有请求文件
            if os.path.exists("temp_request.txt"):
                print(f"\n[{time.strftime('%H:%M:%S')}] 检测到请求文件")
                
                # 处理请求
                success, message = process_request()
                
                # 删除请求文件（避免重复处理）
                os.remove("temp_request.txt")
                
                if success:
                    print(f"  响应已写入 temp_response.txt")
                else:
                    print(f"  错误: {message}")
            
            # 等待0.5秒再检查
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\n客户端已停止")
    except Exception as e:
        print(f"\n客户端异常: {str(e)}")

if __name__ == "__main__":
    # 检查依赖
    try:
        import requests
        main()
    except ImportError:
        print("错误：需要安装requests库")
        print("请运行: pip install requests")