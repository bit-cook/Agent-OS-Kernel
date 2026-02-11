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

try:
    from .ai21_provider import AI21Provider
    _HAS_AI21 = True
except ImportError:
    _HAS_AI21 = False
    AI21Provider = None

try:
    from .cerebras_provider import CerebrasProvider
    _HAS_CEREBRAS = True
except ImportError:
    _HAS_CEREBRAS = False
    CerebrasProvider = None

try:
    from .cloudflare_provider import CloudflareProvider
    _HAS_CLOUDFLARE = True
except ImportError:
    _HAS_CLOUDFLARE = False
    CloudflareProvider = None


__all__ = [
    # Core
    'LLMProvider',
    'LLMConfig',
    'ProviderType',
    'LLMProviderFactory',
    'LLMResponse',
    
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
    'AI21Provider',
    'CerebrasProvider',
    'CloudflareProvider',
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
    'ai21': _HAS_AI21,
    'cerebras': _HAS_CEREBRAS,
    'cloudflare': _HAS_CLOUDFLARE,
    'mock': True,  # Always available
}
