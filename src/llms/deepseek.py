"""
DeepSeek LLM实现
使用DeepSeek API进行文本生成
"""

import os
from typing import Optional, Dict, Any, List
from openai import OpenAI
from .base import BaseLLM, LLMResponse


class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM实现类"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """初始化DeepSeek客户端"""
        if api_key is None:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DeepSeek API Key未找到！请设置DEEPSEEK_API_KEY环境变量或在初始化时提供")
        
        super().__init__(api_key, model_name)
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
        
        self.default_model = model_name or self.get_default_model()
    
    def get_default_model(self) -> str:
        """获取默认模型名称"""
        return "deepseek-chat"
    
    def invoke(self, messages: List[Any], **kwargs) -> LLMResponse:
        """
        调用DeepSeek API生成回复
        
        Args:
            messages: 消息列表 (LangChain Message 对象或 dict)
            **kwargs: temperature, max_tokens, response_format 等
            
        Returns:
            LLMResponse 对象
        """
        normalized = self._normalize_messages(messages)
        
        params = {
            "model": self.default_model,
            "messages": normalized,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4000),
            "stream": False
        }
        
        # 支持 JSON Mode
        if kwargs.get("response_format", {}).get("type") == "json_object":
            params["response_format"] = {"type": "json_object"}
        
        try:
            response = self.client.chat.completions.create(**params)
            
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content or ""
                return LLMResponse(self.validate_response(content))
            else:
                return LLMResponse("")
                
        except Exception as e:
            print(f"DeepSeek API调用错误: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        return {
            "provider": "DeepSeek",
            "model": self.default_model,
            "api_base": "https://api.deepseek.com"
        }
