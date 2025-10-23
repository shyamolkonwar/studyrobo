"""
Dynamic LLM Factory
Supports multiple LLM providers (OpenAI, GLM-4.5, Gemini, Mistral) based on configuration
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from app.core.config import settings

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def create_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Create a completion with the LLM"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name"""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI LLM Provider"""

    def __init__(self):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.available = True
        except ImportError:
            self.client = None
            self.available = False

    async def create_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if not self.available or not self.client:
            raise ValueError("OpenAI client not available")

        tools = kwargs.get('tools', [])
        tool_choice = kwargs.get('tool_choice', 'auto')

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=tools if tools else None,
            tool_choice=tool_choice if tools else None,
            max_tokens=kwargs.get('max_tokens', 1000),
            temperature=kwargs.get('temperature', 0.3)
        )

        return {
            'choices': [{
                'message': {
                    'content': response.choices[0].message.content,
                    'tool_calls': response.choices[0].message.tool_calls
                }
            }]
        }

    def get_model_name(self) -> str:
        return settings.OPENAI_MODEL

class GLMProvider(LLMProvider):
    """GLM-4.5 LLM Provider"""

    def __init__(self):
        try:
            import requests
            self.requests = requests
            self.api_key = settings.GLM_API_KEY
            self.base_url = "https://api.z.ai/api/paas/v4/chat/completions"
            self.available = bool(self.api_key)
        except ImportError:
            self.requests = None
            self.available = False

    async def create_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if not self.available or not self.requests:
            raise ValueError("GLM client not available")

        # Prepare the payload
        payload = {
            "model": settings.GLM_MODEL,
            "messages": messages,
            "temperature": kwargs.get('temperature', 0.3),
            "max_tokens": kwargs.get('max_tokens', 1000)
        }

        # Add tools if provided
        tools = kwargs.get('tools', [])
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = kwargs.get('tool_choice', 'auto')

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Make the API call
        response = self.requests.post(self.base_url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()

        # Convert GLM response to OpenAI-like format
        return {
            'choices': [{
                'message': {
                    'content': data['choices'][0]['message'].get('content', ''),
                    'tool_calls': data['choices'][0]['message'].get('tool_calls')
                }
            }]
        }

    def get_model_name(self) -> str:
        return settings.GLM_MODEL

class GeminiProvider(LLMProvider):
    """Google Gemini LLM Provider"""

    def __init__(self):
        try:
            from google import genai
            from google.genai import types
            self.genai = genai
            self.types = types
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self.available = bool(settings.GEMINI_API_KEY)
        except ImportError:
            self.genai = None
            self.types = None
            self.client = None
            self.available = False

    async def create_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if not self.available or not self.client:
            raise ValueError("Gemini client not available")

        # Convert OpenAI format messages to Gemini format
        contents = []
        for msg in messages:
            if msg['role'] == 'system':
                # Gemini doesn't have system role, add as user message
                contents.append(f"System: {msg['content']}")
            elif msg['role'] == 'user':
                contents.append(msg['content'])
            elif msg['role'] == 'assistant':
                # For now, we'll skip assistant messages in the content
                # In a full implementation, you'd handle conversation history properly
                pass

        # Convert tools to Gemini format
        tools = kwargs.get('tools', [])
        gemini_tools = []
        if tools:
            for tool in tools:
                if 'function' in tool:
                    func = tool['function']
                    gemini_function = {
                        "name": func['name'],
                        "description": func['description'],
                        "parameters": func['parameters']
                    }
                    gemini_tools.append(self.types.Tool(function_declarations=[gemini_function]))

        # Create config
        config_kwargs = {
            "temperature": kwargs.get('temperature', 0.3),
            "max_output_tokens": kwargs.get('max_tokens', 1000)
        }
        if gemini_tools:
            config_kwargs["tools"] = gemini_tools

        config = self.types.GenerateContentConfig(**config_kwargs)

        # Make the API call
        response = self.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=config,
        )

        # Convert Gemini response to OpenAI-like format
        gemini_content = response.candidates[0].content

        # Check for function calls
        tool_calls = []
        content_text = ""

        for part in gemini_content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                # Convert Gemini function call to OpenAI format
                func_call = part.function_call
                tool_calls.append({
                    'id': f'call_{len(tool_calls)}',
                    'function': {
                        'name': func_call.name,
                        'arguments': str(func_call.args) if func_call.args else '{}'
                    }
                })
            elif hasattr(part, 'text') and part.text:
                content_text = part.text

        return {
            'choices': [{
                'message': {
                    'content': content_text,
                    'tool_calls': tool_calls if tool_calls else None
                }
            }]
        }

    def get_model_name(self) -> str:
        return settings.GEMINI_MODEL

class MistralProvider(LLMProvider):
    """Mistral AI LLM Provider"""

    def __init__(self):
        try:
            from mistralai import Mistral
            self.client = Mistral(api_key=settings.MISTRAL_API_KEY)
            self.available = bool(settings.MISTRAL_API_KEY)
        except ImportError:
            self.client = None
            self.available = False

    async def create_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if not self.available or not self.client:
            raise ValueError("Mistral client not available")

        # Convert OpenAI format messages to Mistral format
        mistral_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                mistral_messages.append({"role": "system", "content": msg['content']})
            elif msg['role'] == 'user':
                mistral_messages.append({"role": "user", "content": msg['content']})
            elif msg['role'] == 'assistant':
                mistral_messages.append({"role": "assistant", "content": msg['content']})
            elif msg['role'] == 'tool':
                # Handle tool messages
                mistral_messages.append({"role": "tool", "content": msg['content']})

        # Prepare tools for Mistral format
        tools = kwargs.get('tools', [])
        tool_choice = kwargs.get('tool_choice', 'auto')

        # Make the API call
        response = self.client.chat.complete(
            model=settings.MISTRAL_MODEL,
            messages=mistral_messages,
            tools=tools if tools else None,
            tool_choice=tool_choice if tools else None,
            max_tokens=kwargs.get('max_tokens', 1000),
            temperature=kwargs.get('temperature', 0.3)
        )

        # Convert Mistral response to OpenAI-like format
        return {
            'choices': [{
                'message': {
                    'content': response.choices[0].message.content,
                    'tool_calls': response.choices[0].message.tool_calls
                }
            }]
        }

    def get_model_name(self) -> str:
        return settings.MISTRAL_MODEL

class OpenRouterProvider(LLMProvider):
    """OpenRouter LLM Provider"""

    def __init__(self):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY
            )
            self.available = bool(settings.OPENROUTER_API_KEY)
        except ImportError:
            self.client = None
            self.available = False

    async def create_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if not self.available or not self.client:
            raise ValueError("OpenRouter client not available")

        tools = kwargs.get('tools', [])
        tool_choice = kwargs.get('tool_choice', 'auto')

        # Prepare extra headers as mentioned in OpenRouter docs
        extra_headers = {
            "HTTP-Referer": "https://studyrobo.com",  # Optional. Site URL for rankings
            "X-Title": "StudyRobo",  # Optional. Site title for rankings
        }

        response = await self.client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=messages,
            tools=tools if tools else None,
            tool_choice=tool_choice if tools else None,
            max_tokens=kwargs.get('max_tokens', 1000),
            temperature=kwargs.get('temperature', 0.3),
            extra_headers=extra_headers
        )

        return {
            'choices': [{
                'message': {
                    'content': response.choices[0].message.content,
                    'tool_calls': response.choices[0].message.tool_calls
                }
            }]
        }

    def get_model_name(self) -> str:
        return settings.OPENROUTER_MODEL

class LLMFactory:
    """Factory for creating LLM providers"""

    def __init__(self):
        self.providers = {
            'openai': OpenAIProvider(),
            'glm': GLMProvider(),
            'gemini': GeminiProvider(),
            'mistral': MistralProvider(),
            'openrouter': OpenRouterProvider()
        }

    def get_provider(self, provider_name: Optional[str] = None) -> LLMProvider:
        """Get LLM provider by name"""
        provider_name = provider_name or settings.LLM_PROVIDER

        if provider_name not in self.providers:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

        provider = self.providers[provider_name]
        if not provider.available:
            raise ValueError(f"LLM provider {provider_name} is not available (missing dependencies or API key)")

        return provider

# Global LLM factory instance
llm_factory = LLMFactory()

def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """Get LLM provider (convenience function)"""
    return llm_factory.get_provider(provider_name)
