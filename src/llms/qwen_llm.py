"""
Qwen LLM实现 - 兼容统一接口与工具调用
"""

import os
import json
from typing import Optional, Dict, Any, List
from openai import OpenAI
from .base import BaseLLM, LLMResponse


class QwenLLM(BaseLLM):
    """Qwen LLM实现类"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """初始化Qwen客户端"""
        if api_key is None:
            api_key = os.getenv("QWEN_API_KEY")
            if not api_key:
                try:
                    from ..utils import load_config
                    config = load_config()
                    api_key = config.dashscope_api_key
                except Exception:
                    pass
            
            if not api_key:
                raise ValueError("Qwen API Key未找到！请设置QWEN_API_KEY环境变量")
        
        super().__init__(api_key, model_name)

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        self.default_model = model_name or "qwen-plus"
        
        # Qwen支持工具调用的模型列表
        self.tool_capable_models = [
            "qwen-plus",
            "qwen-turbo", 
            "qwen-max",
            "qwen2.5-72b-instruct"
        ]

    def get_default_model(self) -> str:
        """获取默认模型名称"""
        return self.default_model

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "Qwen",
            "model": self.default_model,
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "supports_tools": self.supports_native_tools()
        }

    def supports_native_tools(self) -> bool:
        """检查是否支持原生工具调用"""
        return self.default_model in self.tool_capable_models

    def invoke(self, messages: List[Any], **kwargs) -> LLMResponse:
        """
        调用 Qwen API 生成回复
        
        Args:
            messages: 消息列表 (LangChain Message 对象或 dict)
            **kwargs: temperature, response_format 等
            
        Returns:
            LLMResponse 对象
        """
        normalized = self._normalize_messages(messages)
        
        params = {
            "model": self.default_model,
            "messages": normalized,
            "temperature": kwargs.get("temperature", 0.7),
        }
        
        # 支持 JSON Mode
        if kwargs.get("response_format", {}).get("type") == "json_object":
            params["response_format"] = {"type": "json_object"}
        
        if "max_tokens" in kwargs:
            params["max_tokens"] = kwargs["max_tokens"]
        
        try:
            response = self.client.chat.completions.create(**params)
            content = response.choices[0].message.content or ""
            return LLMResponse(content)
        except Exception as e:
            print(f"Qwen API Error: {e}")
            raise

    def generate(self, prompt: str, temperature: float = 0.7, **kwargs) -> str:
        """生成文本（简单包装）"""
        messages = [{"role": "user", "content": prompt}]
        if "system_prompt" in kwargs:
            messages.insert(0, {"role": "system", "content": kwargs.pop("system_prompt")})
        response = self.invoke(messages, temperature=temperature, **kwargs)
        return response.content
    
    def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]], 
                           temperature: float = 0.3, **kwargs) -> Dict[str, Any]:
        """使用工具调用生成"""
        messages = [{"role": "user", "content": prompt}]
        
        qwen_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                qwen_tools.append({
                    "type": "function",
                    "function": tool["function"]
                })
        
        params = {
            "model": self.default_model,
            "messages": messages,
            "tools": qwen_tools,
            "temperature": temperature,
        }
        
        try:
            response = self.client.chat.completions.create(**params)
            result: Dict[str, Any] = {"content": "", "tool_calls": []}
            
            if response.choices:
                msg = response.choices[0].message
                if msg.content:
                    result["content"] = msg.content
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        result["tool_calls"].append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
            return result
        except Exception as e:
            print(f"Tool Gen Error: {e}")
            return {"content": "", "tool_calls": []}
