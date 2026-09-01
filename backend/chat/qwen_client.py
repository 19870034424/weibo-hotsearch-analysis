import os
import json
import logging
from typing import Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenClient:
    def __init__(self, api_key: str = None, api_url: str = None):
        self.api_key = self._load_api_key(api_key)
        self.api_url = api_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        if not self.api_key:
            logger.warning("未配置Qwen API密钥，请设置环境变量QWEN_API_KEY或配置文件")

    def _load_api_key(self, api_key: str = None) -> Optional[str]:
        """按优先级加载API密钥"""
        # 1. 传入的参数优先
        if api_key:
            return api_key
        
        # 2. 系统环境变量
        env_key = os.environ.get('QWEN_API_KEY')
        if env_key:
            return env_key
        
        # 3. 配置文件
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'api_keys.yaml')
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'qwen' in config and 'api_key' in config['qwen']:
                        return config['qwen']['api_key']
            except Exception as e:
                logger.warning(f"读取配置文件失败: {e}")
        
        return None

    def generate_response(
        self,
        messages: List[Dict],
        model: str = "qwen-plus",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.8
    ) -> Optional[str]:
        """
        调用Qwen大模型生成响应
        
        Args:
            messages: 对话历史，格式为 [{"role": "user/assistant", "content": "..."}]
            model: 模型名称，默认qwen-plus
            max_tokens: 最大生成token数
            temperature: 温度参数，控制随机性
            top_p: 核采样参数
        
        Returns:
            生成的响应文本，如果失败返回None
        """
        if not self.api_key:
            logger.error("API密钥未配置")
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            }
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if "output" in result and "text" in result["output"]:
                text = result["output"]["text"]
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                elif isinstance(text, str):
                    text = text.encode('utf-8').decode('utf-8')
                return text
            else:
                logger.error(f"API响应格式异常: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"调用Qwen API失败: {e}")
            return None

    def chat_with_context(
        self,
        user_query: str,
        context: str = "",
        model: str = "qwen-plus"
    ) -> Optional[str]:
        """
        带上下文的聊天
        
        Args:
            user_query: 用户查询
            context: 上下文信息（如热搜数据摘要）
            model: 模型名称
        
        Returns:
            生成的响应文本
        """
        messages = []
        
        if context:
            messages.append({
                "role": "system",
                "content": f"你是一个微博热搜数据分析助手。以下是当前热搜数据的上下文信息：\n{context}\n\n请基于这些信息回答用户问题。"
            })
        
        messages.append({
            "role": "user",
            "content": user_query
        })
        
        return self.generate_response(messages, model=model)


if __name__ == "__main__":
    # 测试
    client = QwenClient()
    
    test_context = """
    当前热搜TOP5：
    1. 某明星结婚 - 热度856721
    2. 世界杯开幕 - 热度723456
    3. 新iPhone发布 - 热度654321
    4. 天气预警 - 热度456789
    5. 股市大涨 - 热度345678
    """
    
    response = client.chat_with_context("今天有什么热门话题？", test_context)
    print(f"响应: {response}")