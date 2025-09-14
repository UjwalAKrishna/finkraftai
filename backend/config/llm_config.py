"""
LLM Configuration Management
Centralized configuration for LLM providers
"""

import os
from typing import Dict, Any, Optional
from backend.core.llm_provider import LLMConfig

class LLMConfigManager:
    """Manages LLM configuration and provider settings"""
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default LLM configuration from environment"""
        
        return {
            "provider": os.getenv('LLM_PROVIDER', 'gemini').lower(),
            "fallback_enabled": os.getenv('LLM_FALLBACK_ENABLED', 'true').lower() == 'true',
            "providers": {
                "gemini": {
                    "model": os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'),
                    "api_key": os.getenv('GEMINI_API_KEY'),
                    "temperature": float(os.getenv('GEMINI_TEMPERATURE', '0.7')),
                    "max_tokens": int(os.getenv('GEMINI_MAX_TOKENS', '1000'))
                },
                "openai": {
                    "model": os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                    "api_key": os.getenv('OPENAI_API_KEY'),
                    "temperature": float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
                    "max_tokens": int(os.getenv('OPENAI_MAX_TOKENS', '1000'))
                },
                "local": {
                    "model": os.getenv('LOCAL_MODEL', 'local-model'),
                    "base_url": os.getenv('LOCAL_LLM_URL', 'http://localhost:1234'),
                    "temperature": float(os.getenv('LOCAL_TEMPERATURE', '0.7')),
                    "max_tokens": int(os.getenv('LOCAL_MAX_TOKENS', '1000'))
                }
            }
        }
    
    @staticmethod
    def create_provider_config(provider_name: str, config_dict: Dict[str, Any]) -> LLMConfig:
        """Create LLMConfig from configuration dictionary"""
        
        return LLMConfig(
            provider=provider_name,
            model=config_dict.get('model', 'default-model'),
            api_key=config_dict.get('api_key'),
            base_url=config_dict.get('base_url'),
            temperature=config_dict.get('temperature', 0.7),
            max_tokens=config_dict.get('max_tokens', 1000)
        )
    
    @staticmethod
    def validate_config(provider_name: str, config_dict: Dict[str, Any]) -> bool:
        """Validate provider configuration"""
        
        if provider_name == 'gemini':
            return bool(config_dict.get('api_key')) and bool(config_dict.get('model'))
        elif provider_name == 'openai':
            return bool(config_dict.get('api_key')) and bool(config_dict.get('model'))
        elif provider_name == 'local':
            return bool(config_dict.get('base_url')) and bool(config_dict.get('model'))
        
        return False
    
    @staticmethod
    def get_provider_status() -> Dict[str, Any]:
        """Get status of all configured providers"""
        
        from backend.core.llm_provider import llm_manager
        
        config = LLMConfigManager.get_default_config()
        status = {
            "current_provider": llm_manager.get_current_provider(),
            "available_providers": llm_manager.get_available_providers(),
            "providers": {}
        }
        
        for provider_name, provider_config in config["providers"].items():
            is_configured = LLMConfigManager.validate_config(provider_name, provider_config)
            
            status["providers"][provider_name] = {
                "configured": is_configured,
                "model": provider_config.get("model"),
                "available": False  # Will be updated by checking actual availability
            }
            
            # Check if provider is actually available
            for available_provider in llm_manager.get_available_providers():
                if provider_name.lower() in available_provider.lower():
                    status["providers"][provider_name]["available"] = True
                    break
        
        return status

# Configuration examples for different setups
EXAMPLE_CONFIGS = {
    "gemini_only": {
        "LLM_PROVIDER": "gemini",
        "GEMINI_API_KEY": "your-gemini-api-key",
        "GEMINI_MODEL": "gemini-1.5-flash",
        "LLM_FALLBACK_ENABLED": "false"
    },
    
    "openai_primary": {
        "LLM_PROVIDER": "openai", 
        "OPENAI_API_KEY": "your-openai-api-key",
        "OPENAI_MODEL": "gpt-3.5-turbo",
        "GEMINI_API_KEY": "your-gemini-api-key",  # Fallback
        "LLM_FALLBACK_ENABLED": "true"
    },
    
    "local_llm": {
        "LLM_PROVIDER": "local",
        "LOCAL_LLM_URL": "http://localhost:1234",
        "LOCAL_MODEL": "llama-2-7b-chat",
        "GEMINI_API_KEY": "your-gemini-api-key",  # Fallback
        "LLM_FALLBACK_ENABLED": "true"
    },
    
    "production_setup": {
        "LLM_PROVIDER": "gemini",
        "GEMINI_API_KEY": "your-production-gemini-key",
        "GEMINI_MODEL": "gemini-1.5-pro",  # More powerful model
        "OPENAI_API_KEY": "your-production-openai-key",  # Fallback
        "LLM_FALLBACK_ENABLED": "true",
        "LLM_TEMPERATURE": "0.3",  # More deterministic for production
        "LLM_MAX_TOKENS": "2000"
    }
}