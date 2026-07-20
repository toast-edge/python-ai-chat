#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG功能测试脚本
"""

import os
import sys
import time

# 确保可以导入当前目录的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_chat_with_api import AIChatter

def test_rag_functionality():
    """
    测试RAG功能的完整流程
    """
    print("=" * 50)
    print("RAG功能测试开始")
    print("=" * 50)
    
    # 创建AIChatter实例
    print("\n1. 初始化AI对话系统")
    chatter = AIChatter()
    
    # 测试1: 检查RAG功能初始状态
    print("\n2. 检查RAG功能初始状态")
    print(f"   RAG功能状态: {'已启用' if chatter.rag_enabled else '已禁用'}")
    
    # 测试2: 启用RAG功能
    print("\n3. 启用RAG功能")
    chatter.rag_enabled = True
    # 直接创建RAGManager实例
    from rag_manager import RAGManager
    chatter.rag_manager = RAGManager()
    print(f"   RAG功能状态: {'已启用' if chatter.rag_enabled else '已禁用'}")
    
    # 测试3: 添加测试文档
    print("\n4. 添加测试文档")
    test_doc_path = os.path.join(os.path.dirname(__file__), "test_rag_document.txt")
    if os.path.exists(test_doc_path):
        result = chatter.rag_manager.add_document(test_doc_path)
        print(f"   添加结果: {result}")
    else:
        print(f"   测试文档不存在: {test_doc_path}")
        return False
    
    # 测试4: 测试RAG检索功能
    print("\n5. 测试RAG检索功能")
    test_query = "如何启用RAG功能？"
    retrieved_docs = chatter.rag_manager.retrieve_relevant_documents(test_query, k=3)
    print(f"   检索到的文档数量: {len(retrieved_docs)}")
    for i, doc in enumerate(retrieved_docs):
        print(f"   文档{i+1}内容: {doc.page_content[:100]}...")
    
    # 测试5: 测试增强提示词生成
    print("\n6. 测试增强提示词生成")
    enhanced_prompt = chatter.rag_manager.generate_enhanced_prompt(test_query)
    print(f"   原始查询: {test_query}")
    print(f"   增强提示词: {enhanced_prompt[:200]}...")
    
    # 测试6: 保存RAG索引
    print("\n7. 保存RAG索引")
    index_path = os.path.join(os.path.dirname(__file__), "rag_index")
    chatter.rag_manager.save_rag_index(index_path)
    print(f"   索引保存路径: {index_path}")
    
    # 测试7: 加载RAG索引
    print("\n8. 加载RAG索引")
    new_chatter = AIChatter()
    new_chatter.rag_enabled = True
    new_chatter.rag_manager = RAGManager()
    new_chatter.rag_manager.load_rag_index(index_path)
    print("   索引加载完成")
    
    # 测试8: 使用新索引进行检索
    print("\n9. 使用新索引进行检索")
    retrieved_docs2 = new_chatter.rag_manager.retrieve_relevant_documents("如何切换AI模型？", k=3)
    print(f"   检索到的文档数量: {len(retrieved_docs2)}")
    
    # 测试9: 清理测试数据
    print("\n10. 清理测试数据")
    if os.path.exists(index_path):
        import shutil
        shutil.rmtree(index_path)
        print(f"   已删除索引目录: {index_path}")
    
    print("\n" + "=" * 50)
    print("RAG功能测试完成")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_rag_functionality()
