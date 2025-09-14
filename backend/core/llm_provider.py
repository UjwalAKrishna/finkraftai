"""
LLM Provider Abstraction Layer
Supports multiple LLM providers with easy switching
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 120

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM provider is available"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider"""
        pass

class GeminiProvider(LLMProvider):
    """Google Gemini LLM Provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client"""
        try:
            import google.generativeai as genai
            
            api_key = self.config.api_key or os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("Gemini API key not provided")
            
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.config.model)
            
        except ImportError:
            raise ImportError("google-generativeai package not installed")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini client: {e}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Gemini"""
        try:
            if not self.client:
                raise RuntimeError("Gemini client not initialized")
            
            response = self.client.generate_content(
                prompt,
                generation_config={
                    'temperature': kwargs.get('temperature', self.config.temperature),
                    'max_output_tokens': kwargs.get('max_tokens', self.config.max_tokens),
                }
            )
            
            return response.text if response.text else "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {e}")
    
    def is_available(self) -> bool:
        """Check if Gemini is available"""
        try:
            return self.client is not None and bool(os.getenv('GEMINI_API_KEY'))
        except:
            return False
    
    def get_provider_name(self) -> str:
        return f"Gemini ({self.config.model})"

class OpenAIProvider(LLMProvider):
    """OpenAI LLM Provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            
            api_key = self.config.api_key or os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key not provided")
            
            self.client = OpenAI(api_key=api_key)
            
        except ImportError:
            raise ImportError("openai package not installed")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI"""
        try:
            if not self.client:
                raise RuntimeError("OpenAI client not initialized")
            
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.config.temperature),
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                timeout=self.config.timeout
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {e}")
    
    def is_available(self) -> bool:
        """Check if OpenAI is available"""
        try:
            return self.client is not None and bool(os.getenv('OPENAI_API_KEY'))
        except:
            return False
    
    def get_provider_name(self) -> str:
        return f"OpenAI ({self.config.model})"

class LocalLLMProvider(LLMProvider):
    """Local LLM Provider (LM Studio, Ollama, etc.)"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize local LLM client"""
        try:
            import requests
            self.requests = requests
            
            # Validate base URL
            base_url = self.config.base_url or "http://localhost:1234"
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            
            self.base_url = base_url.rstrip('/')
            self.api_endpoint = f"{self.base_url}/v1/chat/completions"
            
        except ImportError:
            raise ImportError("requests package not installed")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using local LLM"""
        try:
            payload = {
                "model": self.config.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get('temperature', self.config.temperature),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
                "stream": False
            }
            
            response = self.requests.post(
                self.api_endpoint,
                json=payload,
                timeout=120  # Longer timeout for local LLMs
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                raise RuntimeError(f"Local LLM returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            raise RuntimeError(f"Local LLM generation failed: {e}")
    
    def is_available(self) -> bool:
        """Check if local LLM is available"""
        try:
            response = self.requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_provider_name(self) -> str:
        return f"Local LLM ({self.config.base_url}, {self.config.model})"

class LLMManager:
    """Manages multiple LLM providers with fallback support"""
    
    def __init__(self):
        self.providers: List[LLMProvider] = []
        self.current_provider: Optional[LLMProvider] = None
        self._load_config()
    
    def _load_config(self):
        """Load LLM configuration from environment/config"""
        
        # Load from environment variables
        provider_type = os.getenv('LLM_PROVIDER', 'gemini').lower()
        
        print(f"Primary LLM provider: {provider_type}")
        
        if provider_type == 'gemini':
            config = LLMConfig(
                provider='gemini',
                model=os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'),
                api_key=os.getenv('GEMINI_API_KEY'),
                temperature=float(os.getenv('LLM_TEMPERATURE', '0.7')),
                max_tokens=int(os.getenv('LLM_MAX_TOKENS', '1000'))
            )
            try:
                self.add_provider(GeminiProvider(config))
                print("Added Gemini as primary provider")
            except Exception as e:
                print(f"Warning: Could not initialize Gemini provider: {e}")
            
        elif provider_type == 'openai':
            config = LLMConfig(
                provider='openai',
                model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                api_key=os.getenv('OPENAI_API_KEY'),
                temperature=float(os.getenv('LLM_TEMPERATURE', '0.7')),
                max_tokens=int(os.getenv('LLM_MAX_TOKENS', '1000'))
            )
            try:
                self.add_provider(OpenAIProvider(config))
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI provider: {e}")
            
        elif provider_type == 'local':
            config = LLMConfig(
                provider='local',
                model=os.getenv('LOCAL_MODEL', 'local-model'),
                base_url=os.getenv('LOCAL_LLM_URL', 'http://localhost:1234'),
                temperature=float(os.getenv('LLM_TEMPERATURE', '0.7')),
                max_tokens=int(os.getenv('LLM_MAX_TOKENS', '1000'))
            )
            try:
                self.add_provider(LocalLLMProvider(config))
            except Exception as e:
                print(f"Warning: Could not initialize Local LLM provider: {e}")
        
        # Add Gemini as fallback only if fallback is enabled
        fallback_enabled = os.getenv('LLM_FALLBACK_ENABLED', 'true').lower() == 'true'
        if fallback_enabled and provider_type != 'gemini' and os.getenv('GEMINI_API_KEY'):
            fallback_config = LLMConfig(
                provider='gemini',
                model='gemini-1.5-flash',
                api_key=os.getenv('GEMINI_API_KEY')
            )
            try:
                self.add_provider(GeminiProvider(fallback_config))
                print("Added Gemini as fallback provider")
            except Exception as e:
                print(f"Warning: Could not initialize Gemini fallback provider: {e}")
        elif not fallback_enabled:
            print("Fallback disabled - only using primary provider")
    
    def add_provider(self, provider: LLMProvider):
        """Add a new LLM provider"""
        self.providers.append(provider)
        if not self.current_provider and provider.is_available():
            self.current_provider = provider
    
    def switch_provider(self, provider_name: str) -> bool:
        """Switch to a specific provider"""
        for provider in self.providers:
            if provider.config.provider == provider_name.lower():
                if provider.is_available():
                    self.current_provider = provider
                    return True
                else:
                    raise RuntimeError(f"Provider {provider_name} is not available")
        
        raise ValueError(f"Provider {provider_name} not found")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response with fallback support"""
        
        # If no providers are available, return helpful error message
        if not self.providers:
            return "I apologize, but no LLM providers are configured. Please set up at least one provider (Gemini, OpenAI, or Local LLM) in your environment variables."
        
        for provider in self.providers:
            if provider.is_available():
                try:
                    response = provider.generate_response(prompt, **kwargs)
                    self.current_provider = provider
                    return response
                except Exception as e:
                    print(f"Provider {provider.get_provider_name()} failed: {e}")
                    continue
        
        # All providers failed or unavailable
        provider_status = []
        for provider in self.providers:
            status = "available" if provider.is_available() else "unavailable"
            provider_status.append(f"{provider.get_provider_name()} ({status})")
        
        return f"I apologize, but I'm currently unable to process your request. LLM provider status: {', '.join(provider_status)}. Please check your API keys and configuration."
    
    def get_current_provider(self) -> Optional[str]:
        """Get the name of the current provider"""
        return self.current_provider.get_provider_name() if self.current_provider else None
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [p.get_provider_name() for p in self.providers if p.is_available()]
    
    def is_any_provider_available(self) -> bool:
        """Check if any provider is available"""
        return any(p.is_available() for p in self.providers)

# Global LLM manager instance
llm_manager = LLMManager()