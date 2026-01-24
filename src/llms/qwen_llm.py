"""
Qwen LLM实现 - 兼容 LangChain 接口与工具调用
"""

import os
import json
from typing import Optional, Dict, Any, List, Union
from openai import OpenAI
from .base import BaseLLM

class QwenLLM(BaseLLM):
    """Qwen LLM实现类 - 完整兼容版"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        初始化Qwen客户端
        """
        if api_key is None:
            api_key = os.getenv("QWEN_API_KEY")
            if not api_key:
                # 尝试从 config 读取
                try:
                    from ..utils import load_config
                    config = load_config()
                    api_key = config.dashscope_api_key
                except:
                    pass
            
            if not api_key:
                raise ValueError("Qwen API Key未找到！请设置QWEN_API_KEY环境变量")
        
        super().__init__(api_key, model_name)

        # 初始化OpenAI客户端（Qwen兼容OpenAI接口）
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

    # =========================================================
    # 核心修复 1: 补全 BaseLLM 要求的抽象方法
    # =========================================================
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

    # =========================================================
    # 核心修复 2: 统一 invoke 接口 (兼容 LangChain)
    # =========================================================
    def invoke(self, input_arg: Union[str, List[Any]], user_prompt: Optional[str] = None, **kwargs) -> Any:
        """
        统一调用接口，智能兼容两种模式：
        1. LangChain 风格: invoke(messages_list) -> 返回带 .content 的对象
        2. 旧版风格: invoke(system_prompt, user_prompt) -> 返回字符串
        """
        # --- 模式 1: LangChain 风格 (传入消息列表) ---
        if isinstance(input_arg, list):
            messages = []
            for msg in input_arg:
                # 处理 LangChain Message 对象
                if hasattr(msg, 'content'):
                    role = "user"
                    if getattr(msg, 'type', '') == 'system':
                        role = "system"
                    elif getattr(msg, 'type', '') == 'ai':
                        role = "assistant"
                    messages.append({"role": role, "content": msg.content})
                # 处理字典格式
                elif isinstance(msg, dict):
                    messages.append(msg)
            
            # 准备参数
            params = {
                "model": self.default_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
            }
            
            # 支持 JSON Mode
            if kwargs.get("response_format", {}).get("type") == "json_object":
                params["response_format"] = {"type": "json_object"}
            
            try:
                response = self.client.chat.completions.create(**params)
                content = response.choices[0].message.content
                
                # 返回一个伪造的 AIMessage 对象，以便调用者可以通过 .content 获取
                class SimpleAIMessage:
                    def __init__(self, content): self.content = content
                    def __str__(self): return self.content
                
                return SimpleAIMessage(content)
            except Exception as e:
                print(f"Qwen Invoke Error: {e}")
                raise e

        # --- 模式 2: 旧版风格 (传入 System + User Prompt) ---
        else:
            system_prompt = input_arg
            # 如果 user_prompt 为空，说明可能只传了一个 str，当做 user prompt 处理
            if user_prompt is None:
                messages = [{"role": "user", "content": system_prompt}]
            else:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            
            params = {
                "model": self.default_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.6),
                "max_tokens": kwargs.get("max_tokens", 8000),
            }
            
            try:
                response = self.client.chat.completions.create(**params)
                if response.choices and response.choices[0].message:
                    return response.choices[0].message.content
                return ""
            except Exception as e:
                print(f"Qwen API Error: {str(e)}")
                raise e

    def generate(self, prompt: str, temperature: float = 0.7, **kwargs) -> str:
        """生成文本（简单包装）"""
        return self.invoke(prompt, temperature=temperature, **kwargs)
    
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
            result = {"content": "", "tool_calls": []}
            
            if response.choices:
                msg = response.choices[0].message
                if msg.content: result["content"] = msg.content
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