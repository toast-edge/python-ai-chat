#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对话程序启动器
"""

import os
import sys
import subprocess

def main():
    """启动AI对话程序"""
    print("🚀 正在启动AI对话程序...")
    
    # 检查主程序文件是否存在
    main_file = "ai_chat_with_api.py"
    if not os.path.exists(main_file):
        print(f"❌ 错误：找不到文件 {main_file}")
        print("请确保 ai_chat_with_api.py 文件在当前目录中")
        return
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 如果有额外参数，直接传递给主程序
        args = ' '.join(sys.argv[1:])
        print(f"🎯 使用参数: {args}")
        try:
            subprocess.run([sys.executable, main_file] + sys.argv[1:])
        except KeyboardInterrupt:
            print("\n👋 程序已退出")
        except Exception as e:
            print(f"❌ 运行错误: {e}")
    else:
        # 交互式选择AI服务和响应模式
        print("\n🤖 选择要使用的AI服务:")
        print("="*40)
        print("1. openai  - OpenAI GPT (GPT-3.5/GPT-4)")
        print("2. claude  - Anthropic Claude")
        print("3. qwen    - 阿里云Qwen")
        print("4. local   - 本地模型 (Ollama)")
        print("5. config  - 使用配置文件中的设置")
        print("="*40)
        
        choice = input("请选择 (1-5): ").strip()
        
        print("\n🎭 选择响应模式:")
        print("="*30)
        print("1. 流式响应 (默认，更流畅的体验)")
        print("2. 传统响应 (一次性显示完整回复)")
        print("="*30)
        
        streaming_choice = input("请选择响应模式 (1-2，默认1): ").strip()
        
        # 处理流式响应参数
        streaming_param = "--streaming true"
        if streaming_choice == "2":
            streaming_param = "--streaming false"
        
        service_map = {
            "1": "--service openai",
            "2": "--service claude", 
            "3": "--service qwen",
            "4": "--service local",
            "5": ""
        }
        
        if choice in service_map:
            service_cmd = service_map[choice]
            if service_cmd:
                print(f"✅ 将启动服务: {service_cmd.split()[-1]}")
                # 构建完整的命令行参数
                full_cmd = service_cmd.split() + streaming_param.split()
                try:
                    subprocess.run([sys.executable, main_file] + full_cmd)
                except KeyboardInterrupt:
                    print("\n👋 程序已退出")
                except Exception as e:
                    print(f"❌ 运行错误: {e}")
            else:
                print("✅ 将使用配置文件中的设置")
                print("✅ 使用流式响应模式")
                try:
                    subprocess.run([sys.executable, main_file, streaming_param])
                except KeyboardInterrupt:
                    print("\n👋 程序已退出")
                except Exception as e:
                    print(f"❌ 运行错误: {e}")
        else:
            print("❌ 无效选择，启动默认配置")
            print("✅ 使用流式响应模式")
            try:
                subprocess.run([sys.executable, main_file, streaming_param])
            except KeyboardInterrupt:
                print("\n👋 程序已退出")
            except Exception as e:
                print(f"❌ 运行错误: {e}")

if __name__ == "__main__":
    main()