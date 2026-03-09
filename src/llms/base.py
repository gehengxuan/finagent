"""
LLM基类定义
为所有LLM实现提供统一接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union


class LLMResponse:
    """
    统一的 LLM 响应对象
    
    所有 LLM 实现的 invoke() 方法都返回此类型。
    兼容 LangChain 风格的 .content 属性访问。
    """
    
    def __init__(self, content: str):
        self.content = content
    
    def __str__(self) -> str:
        return self.content
    
    def __repr__(self) -> str:
        preview = self.content[:80] + "..." if len(self.content) > 80 else self.content
        return f"LLMResponse(content='{preview}')"


class BaseLLM(ABC):
    """
    LLM 基类 - 定义统一接口
    
    所有子类必须实现 invoke() 方法，签名为：
        invoke(messages: List, **kwargs) -> LLMResponse
    
    其中 messages 可以是：
        - LangChain Message 对象列表 (SystemMessage, HumanMessage 等)
        - dict 列表 ({"role": "system", "content": "..."})
    """
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name
    
    @abstractmethod
    def get_default_model(self) -> str:
        """获取默认模型名称"""
        pass
    
    @abstractmethod
    def invoke(self, messages: List[Any], **kwargs) -> LLMResponse:
        """
        调用 LLM 生成回复（统一接口）
        
        Args:
            messages: 消息列表，支持 LangChain Message 对象或 dict 格式
            **kwargs: 其他参数 (temperature, max_tokens, response_format 等)
            
        Returns:
            LLMResponse 对象，通过 .content 获取文本内容
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        pass
    
    def _normalize_messages(self, messages: List[Any]) -> List[Dict[str, str]]:
        """
        将各种格式的消息统一转换为 OpenAI API 格式
        
        支持：
        - LangChain Message 对象 (有 .content 和 .type 属性)
        - dict 格式 ({"role": "...", "content": "..."})
        """
        normalized = []
        for msg in messages:
            if isinstance(msg, dict):
                normalized.append(msg)
            elif hasattr(msg, 'content'):
                # LangChain Message 对象
                role = "user"
                msg_type = getattr(msg, 'type', '')
                if msg_type == 'system':
                    role = "system"
                elif msg_type == 'ai':
                    role = "assistant"
                elif msg_type == 'human':
                    role = "user"
                normalized.append({"role": role, "content": msg.content})
            else:
                # 兜底：当作 user message
                normalized.append({"role": "user", "content": str(msg)})
        return normalized
    
    def generate(self, prompt: str, temperature: float = 0.7, 
                 max_tokens: int = 4000, **kwargs) -> str:
        """
        简单的文本生成接口
        
        Args:
            prompt: 输入提示
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            生成的文本字符串
        """
        system_prompt = kwargs.get("system_prompt", "You are a helpful assistant.")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response = self.invoke(messages, temperature=temperature, max_tokens=max_tokens)
        return response.content
    
    def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]], 
                           temperature: float = 0.3, **kwargs) -> Dict[str, Any]:
        """
        使用工具调用生成（可选实现）
        """
        print(f"警告: {self.__class__.__name__} 未实现原生工具调用")
        return {"content": "", "tool_calls": []}
    
    def supports_native_tools(self) -> bool:
        """检查是否支持原生工具调用"""
        return False
    
    def validate_response(self, response: str) -> str:
        """验证和清理响应内容"""
        if response is None:
            return ""
        return response.strip()
    
    def __str__(self) -> str:
        info = self.get_model_info()
        return f"{info.get('provider', 'Unknown')} ({info.get('model', 'unknown')})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model_name}>"


# =================================================================
# 自定义异常
# =================================================================

class LLMError(Exception):
    """LLM相关错误的基类"""
    pass


class APIError(LLMError):
    """API调用错误"""
    pass


class RateLimitError(LLMError):
    """速率限制错误"""
    pass


class InvalidResponseError(LLMError):
    """无效响应错误"""
    pass
