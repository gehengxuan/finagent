"""
LLM基类定义
为所有LLM实现提供统一接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class BaseLLM(ABC):
    """LLM基类 - 定义统一接口"""
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """
        初始化LLM
        
        Args:
            api_key: API密钥
            model_name: 模型名称
        """
        self.api_key = api_key
        self.model_name = model_name
    
    @abstractmethod
    def get_default_model(self) -> str:
        """
        获取默认模型名称
        
        Returns:
            模型名称字符串
        """
        pass
    
    @abstractmethod
    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        调用LLM生成回复（传统接口）
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数
            
        Returns:
            生成的回复文本
        """
        pass
    
    def generate(self, prompt: str, temperature: float = 0.7, 
                 max_tokens: int = 4000, **kwargs) -> str:
        """
        生成文本（新接口）
        
        Args:
            prompt: 输入提示
            temperature: 温度参数 (0-1)
            max_tokens: 最大生成token数
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        # 默认实现：调用invoke方法
        system_prompt = kwargs.get("system_prompt", "You are a helpful assistant.")
        return self.invoke(system_prompt, prompt, 
                          temperature=temperature, 
                          max_tokens=max_tokens)
    
    def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]], 
                           temperature: float = 0.3, **kwargs) -> Dict[str, Any]:
        """
        使用工具调用生成（可选实现）
        
        Args:
            prompt: 输入提示
            tools: 工具定义列表
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            包含工具调用信息的响应字典：
            {
                "content": str,  # 文本响应
                "tool_calls": [  # 工具调用列表
                    {
                        "id": str,
                        "type": "function",
                        "function": {
                            "name": str,
                            "arguments": str  # JSON字符串
                        }
                    }
                ]
            }
        """
        # 默认实现：不支持工具调用，返回空响应
        print(f"警告: {self.__class__.__name__} 未实现原生工具调用")
        return {
            "content": "",
            "tool_calls": []
        }
    
    def supports_native_tools(self) -> bool:
        """
        检查是否支持原生工具调用
        
        Returns:
            True表示支持，False表示不支持
        """
        return False
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前模型信息
        
        Returns:
            模型信息字典，包含provider、model等字段
        """
        pass
    
    def validate_response(self, response: str) -> str:
        """
        验证和清理响应内容
        
        Args:
            response: 原始响应
            
        Returns:
            清理后的响应
        """
        if response is None:
            return ""
        
        # 移除可能的空白字符
        response = response.strip()
        
        # 可以添加更多验证逻辑
        # 例如：检查是否包含有害内容、格式验证等
        
        return response
    
    def __str__(self) -> str:
        """字符串表示"""
        info = self.get_model_info()
        return f"{info.get('provider', 'Unknown')} ({info.get('model', 'unknown')})"
    
    def __repr__(self) -> str:
        """详细表示"""
        return f"<{self.__class__.__name__} model={self.model_name}>"


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