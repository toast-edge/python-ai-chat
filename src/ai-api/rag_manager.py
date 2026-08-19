#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG（检索增强生成）功能模块
支持文档加载、向量存储和检索增强生成
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (TextLoader, PyPDFLoader, 
                                        Docx2txtLoader, UnstructuredMarkdownLoader)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class DocumentProcessor:
    """文档处理器，负责加载和分割文档"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 100):
        """
        初始化文档处理器
        
        Args:
            chunk_size: 每个文档块的大小
            chunk_overlap: 文档块之间的重叠大小
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", "", "."]
        )
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        加载文档
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            文档对象列表
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文档文件不存在: {file_path}")
        
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            # Get loader class based on extension
            document_type_loaders = {
                'txt': TextLoader,
                'pdf': PyPDFLoader,
                'docx': Docx2txtLoader,
                'doc': Docx2txtLoader,
                'md': UnstructuredMarkdownLoader,
                'default': TextLoader
            }
            
            loader_class = document_type_loaders.get(ext.lstrip('.'), document_type_loaders['default'])
            
            # Initialize loader with appropriate parameters
            if loader_class == TextLoader:
                loader = TextLoader(file_path, encoding='utf-8')
            else:
                loader = loader_class(file_path)
                
            return loader.load()
        except Exception as e:
            raise Exception(f"加载文档失败: {str(e)}")
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        将文档分割成小块
        
        Args:
            documents: 原始文档对象列表
            
        Returns:
            分割后的文档块列表
        """
        return self.text_splitter.split_documents(documents)
    
    def load_and_split(self, file_path: str) -> List[Document]:
        """
        加载并分割文档
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            分割后的文档块列表
        """
        documents = self.load_document(file_path)
        return self.split_documents(documents)


class VectorStoreManager:
    """向量存储管理器，负责文档向量的存储和检索"""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        初始化向量存储管理器
        
        Args:
            embedding_model: 嵌入模型名称
        """
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.vector_store: Optional[FAISS] = None
    
    def create_vector_store(self, documents: List[Document]):
        """
        创建向量存储
        
        Args:
            documents: 文档块列表
        """
        if not documents:
            raise ValueError("文档列表为空")
        
        self.vector_store = FAISS.from_documents(documents, self.embeddings)
    
    def add_documents(self, documents: List[Document]):
        """
        向向量存储添加文档
        
        Args:
            documents: 文档块列表
        """
        if not self.vector_store:
            self.create_vector_store(documents)
        else:
            self.vector_store.add_documents(documents)
    
    def search(self, query: str, k: int = 3) -> List[Tuple[Document, float]]:
        """
        搜索相关文档
        
        Args:
            query: 查询文本
            k: 返回的相关文档数量
            
        Returns:
            相关文档列表，每个元素是(文档, 相似度分数)
        """
        if not self.vector_store:
            raise ValueError("向量存储未初始化")
        
        return self.vector_store.similarity_search_with_score(query, k=k)
    
    def load_vector_store(self, path: str):
        """
        加载向量存储
        
        Args:
            path: 向量存储文件路径
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"向量存储文件不存在: {path}")
        
        # 设置allow_dangerous_deserialization=True以允许加载本地生成的索引
        self.vector_store = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
    
    def save_vector_store(self, path: str):
        """
        保存向量存储
        
        Args:
            path: 向量存储文件路径
        """
        if not self.vector_store:
            raise ValueError("向量存储未初始化")
        
        self.vector_store.save_local(path)


class RAGManager:
    """RAG管理器，整合文档处理和向量存储，提供检索增强生成功能"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化RAG管理器
        
        Args:
            config: RAG配置参数
        """
        config = config or {}   # ① 如果没传配置，给个空字典
        
        chunk_size = config.get("chunk_size", 512)                              # ② 读取分块大小
        chunk_overlap = config.get("chunk_overlap", 100)                        # ③ 读取分块重叠大小
        embedding_model = config.get("embedding_model", "all-MiniLM-L6-v2")     # ④ 读取嵌入模型名
        
        # ⑤ 创建文档处理器（专门负责切分文本）
        self.document_processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        # ⑥ 创建向量存储管理器（专门负责把文本变成向量并搜索）
        self.vector_store_manager = VectorStoreManager(embedding_model=embedding_model)

        # ⑦ 标记为未初始化（内存里还是空的）
        self.is_initialized = False
    
    def add_document(self, file_path: str):
        """
        添加文档到RAG系统
        
        Args:
            file_path: 文档文件路径
        """
        try:
            # 加载并分割文档
            documents = self.document_processor.load_and_split(file_path)
            
            # 添加到向量存储
            self.vector_store_manager.add_documents(documents)
            
            self.is_initialized = True
            
            return {
                "status": "success",
                "message": f"文档 '{os.path.basename(file_path)}' 已成功添加",
                "document_count": len(documents),
                "file_path": file_path
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"添加文档失败: {str(e)}",
                "file_path": file_path
            }
    
    def add_multiple_documents(self, file_paths: List[str]) -> List[Dict]:
        """
        批量添加文档
        
        Args:
            file_paths: 文档文件路径列表
            
        Returns:
            每个文档的添加结果列表
        """
        results = []
        for file_path in file_paths:
            result = self.add_document(file_path)
            results.append(result)
        return results
    
    def retrieve_relevant_documents(self, query: str, k: int = 3) -> List[Document]:
        """
        检索与查询相关的文档
        
        Args:
            query: 查询文本
            k: 返回的相关文档数量
            
        Returns:
            相关文档列表
        """
        if not self.is_initialized:
            raise ValueError("RAG系统未初始化，请先添加文档")
        
        results = self.vector_store_manager.search(query, k=k)
        return [doc for doc, score in results]
    
    def generate_enhanced_prompt(self, user_query: str, k: int = 3) -> str:
        """
        生成增强提示词，将相关文档内容添加到用户查询中
        
        Args:
            user_query: 用户原始查询
            k: 使用的相关文档数量
            
        Returns:
            增强后的提示词
        """
        if not self.is_initialized:
            # 如果RAG未初始化，直接返回原始查询
            return user_query
        
        # 检索相关文档
        relevant_docs = self.retrieve_relevant_documents(user_query, k=k)
        
        if not relevant_docs:
            return user_query
        
        # 构建增强提示词
        context = "\n".join([f"[文档片段 {i+1}]\n{doc.page_content}\n" for i, doc in enumerate(relevant_docs)])
        
        enhanced_prompt = f"请基于以下参考资料回答用户的问题。如果资料中没有相关信息，你可以根据自己的知识回答。\n\n"
        enhanced_prompt += f"参考资料：\n{context}\n\n"
        enhanced_prompt += f"用户问题：{user_query}"
        
        return enhanced_prompt
    
    def save_rag_index(self, path: str):
        """
        保存RAG索引
        
        Args:
            path: 索引保存路径
        """
        if not self.is_initialized:
            raise ValueError("RAG系统未初始化")
        
        self.vector_store_manager.save_vector_store(path)
    
    def load_rag_index(self, path: str):
        """
        加载RAG索引
        
        Args:
            path: 索引加载路径
        """
        self.vector_store_manager.load_vector_store(path)
        self.is_initialized = True
    
    def clear(self):
        """
        清除RAG索引
        """
        self.vector_store_manager = VectorStoreManager()
        self.is_initialized = False
    
    def get_status(self) -> Dict:
        """
        获取RAG系统状态
        
        Returns:
            状态信息
        """
        return {
            "initialized": self.is_initialized,
            "has_vector_store": hasattr(self.vector_store_manager, 'vector_store') and 
                               self.vector_store_manager.vector_store is not None
        }
