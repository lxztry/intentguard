"""
IntentGuard - LLM Provider Factory

统一接口，支持多个LLM提供商
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import os


class LLMProvider(ABC):
    """LLMProvider抽象基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成回复"""
        pass
    
    @abstractmethod
    def name(self) -> str:
        """提供商名称"""
        pass


class SiliconFlowProvider(LLMProvider):
    """硅基流动API提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-ai/DeepSeek-V3"):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY", "")
        self.model = model
        self.base_url = "https://api.siliconflow.cn/v1"
    
    def name(self) -> str:
        return "SiliconFlow"
    
    def generate(self, prompt: str, **kwargs) -> str:
        """调用硅基流动API"""
        try:
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 2048)
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            return f"[LLM Error] {str(e)}"


class DeepSeekProvider(LLMProvider):
    """DeepSeek官方API提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.model = model
        self.base_url = "https://api.deepseek.com/v1"
    
    def name(self) -> str:
        return "DeepSeek"
    
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 2048)
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            return f"[LLM Error] {str(e)}"


class OpenAIProvider(LLMProvider):
    """OpenAI API提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    def name(self) -> str:
        return "OpenAI"
    
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 2048)
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            return f"[LLM Error] {str(e)}"


class OllamaProvider(LLMProvider):
    """Ollama本地模型提供商"""
    
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def name(self) -> str:
        return f"Ollama ({self.model})"
    
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            import httpx
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
                
        except Exception as e:
            return f"[LLM Error] {str(e)}"


class LLMFactory:
    """LLM工厂类"""
    
    _providers: Dict[str, LLMProvider] = {}
    _default: Optional[str] = None
    
    @classmethod
    def register(cls, name: str, provider: LLMProvider):
        """注册提供商"""
        cls._providers[name] = provider
    
    @classmethod
    def get(cls, name: str = None) -> Optional[LLMProvider]:
        """获取提供商"""
        if name is None:
            name = cls._default or "siliconflow"
        return cls._providers.get(name)
    
    @classmethod
    def set_default(cls, name: str):
        """设置默认提供商"""
        cls._default = name
    
    @classmethod
    def auto_detect(cls) -> Optional[LLMProvider]:
        """自动检测可用的LLM提供商"""
        # 优先级：硅基流动 > DeepSeek > OpenAI > Ollama
        if os.getenv("SILICONFLOW_API_KEY"):
            provider = SiliconFlowProvider()
            cls.register("siliconflow", provider)
            cls.set_default("siliconflow")
            return provider
        
        if os.getenv("DEEPSEEK_API_KEY"):
            provider = DeepSeekProvider()
            cls.register("deepseek", provider)
            cls.set_default("deepseek")
            return provider
        
        if os.getenv("OPENAI_API_KEY"):
            provider = OpenAIProvider()
            cls.register("openai", provider)
            cls.set_default("openai")
            return provider
        
        # 尝试Ollama
        try:
            provider = OllamaProvider()
            cls.register("ollama", provider)
            cls.set_default("ollama")
            return provider
        except:
            pass
        
        return None
    
    @classmethod
    def list_providers(cls) -> list:
        """列出所有注册的提供商"""
        return list(cls._providers.keys())


# 便捷函数
def get_llm(name: str = None) -> Optional[LLMProvider]:
    """获取LLM实例"""
    return LLMFactory.get(name)


def setup_llm() -> Optional[LLMProvider]:
    """自动设置LLM"""
    return LLMFactory.auto_detect()


# 测试
if __name__ == "__main__":
    print("Testing LLM Factory...")
    
    # 尝试自动检测
    provider = setup_llm()
    
    if provider:
        print(f"Using provider: {provider.name()}")
        
        # 测试调用
        response = provider.generate("请用一句话解释什么是编程语言")
        print(f"Response: {response[:200]}...")
    else:
        print("No LLM provider available. Set environment variables:")
        print("  SILICONFLOW_API_KEY")
        print("  DEEPSEEK_API_KEY")
        print("  OPENAI_API_KEY")