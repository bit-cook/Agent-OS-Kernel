#!/usr/bin/env python3
"""LLM Provider 使用示例"""

from agent_os_kernel.llm.provider import (
    LLMConfig, LLMProvider, ProviderType
)


def main():
    print("="*50)
    print("LLM Provider 示例")
    print("="*50)
    
    # 1. 创建配置
    print("\n1. 创建 LLM 配置")
    
    config = LLMConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4",
        api_key="sk-xxx",
        temperature=0.7,
        max_tokens=4096
    )
    
    print(f"   Provider: {config.provider.value}")
    print(f"   Model: {config.model}")
    print(f"   Temperature: {config.temperature}")
    print(f"   Max Tokens: {config.max_tokens}")
    
    # 2. 配置转字典
    print("\n2. 配置转字典")
    
    data = config.to_dict()
    print(f"   Provider: {data['provider']}")
    print(f"   Model: {data['model']}")
    
    # 3. 从字典创建
    print("\n3. 从字典创建配置")
    
    config2 = LLMConfig.from_dict({
        'provider': 'anthropic',
        'model': 'claude-3',
        'temperature': 0.5
    })
    
    print(f"   Provider: {config2.provider.value}")
    print(f"   Model: {config2.model}")
    
    # 4. Provider 类型
    print("\n4. Provider 类型")
    
    for pt in [ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.DEEPSEEK,
               ProviderType.OLLAMA, ProviderType.VLLM]:
        print(f"   - {pt.value}")
    
    # 5. 从字符串创建
    print("\n5. 从字符串创建 ProviderType")
    
    pt = ProviderType.from_string("openai")
    print(f"   'openai' -> {pt.value}")
    
    pt = ProviderType.from_string("unknown")
    print(f"   'unknown' -> {pt.value}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    main()
