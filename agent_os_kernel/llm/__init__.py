# LLM Provider Module - Multi-Model LLM Support

from .provider import LLMProvider, LLMConfig, ProviderType
from .factory import LLMProviderFactory

# Mock Provider (always available)
from .mock_provider import (
    MockProvider,
    MockErrorProvider,
    create_mock_provider,
    create_error_mock_provider
)

# Try to import real providers (optional)
try:
    from .openai_impl import OpenAIProvider, OpenAIConfig
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False
    OpenAIProvider = None
    OpenAIConfig = None

try:
    from .anthropic import AnthropicProvider
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False
    AnthropicProvider = None

try:
    from .deepseek import DeepSeekProvider
    _HAS_DEEPSEEK = True
except ImportError:
    _HAS_DEEPSEEK = False
    DeepSeekProvider = None

# Other providers (stubs for now)
try:
    from .kimi import KimiProvider
    _HAS_KIMI = True
except ImportError:
    _HAS_KIMI = False
    KimiProvider = None

try:
    from .minimax import MiniMaxProvider
    _HAS_MINIMAX = True
except ImportError:
    _HAS_MINIMAX = False
    MiniMaxProvider = None

try:
    from .qwen import QwenProvider
    _HAS_QWEN = True
except ImportError:
    _HAS_QWEN = False
    QwenProvider = None

try:
    from .ollama import OllamaProvider
    _HAS_OLLAMA = True
except ImportError:
    _HAS_OLLAMA = False
    OllamaProvider = None

try:
    from .vllm import VLLMProvider
    _HAS_VLLM = True
except ImportError:
    _HAS_VLLM = False
    VLLMProvider = None


__all__ = [
    # Core
    'LLMProvider',
    'LLMConfig',
    'ProviderType',
    'LLMProviderFactory',
    
    # Mock (always available)
    'MockProvider',
    'MockErrorProvider',
    'create_mock_provider',
    'create_error_mock_provider',
    
    # Providers (may be None if dependencies not installed)
    'OpenAIProvider',
    'OpenAIConfig',
    'AnthropicProvider',
    'DeepSeekProvider',
    'KimiProvider',
    'MiniMaxProvider',
    'QwenProvider',
    'OllamaProvider',
    'VLLMProvider',
]

# Provider availability info
PROVIDER_AVAILABILITY = {
    'openai': _HAS_OPENAI,
    'anthropic': _HAS_ANTHROPIC,
    'deepseek': _HAS_DEEPSEEK,
    'kimi': _HAS_KIMI,
    'minimax': _HAS_MINIMAX,
    'qwen': _HAS_QWEN,
    'ollama': _HAS_OLLAMA,
    'vllm': _HAS_VLLM,
    'mock': True,  # Always available
}
