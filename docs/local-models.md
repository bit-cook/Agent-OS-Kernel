# 本地模型配置指南

## 概述

Agent OS Kernel 支持多种本地大语言模型，无需 API Key 即可运行。

## 支持的本地模型

### 1. Ollama (推荐)

#### 安装
```bash
# Linux/macOS
curl -fsSL https://ollama.ai | sh

# Windows
# 下载安装包: https://ollama.ai/download
```

#### 下载模型
```bash
# 推荐模型
ollama pull qwen2.5:7b      # 通义千问 (推荐，中文效果好)
ollama pull llama3          # Meta Llama 3
ollama pull llama3.1:8b     # Llama 3.1 8B
ollama pull mistral        # Mistral 7B
ollama pull deepseek-coder  # 代码生成
ollama pull codellama      # Code Llama
```

#### 配置
```yaml
# config.yaml
llm:
  default_provider: "ollama"
  models:
    - name: "qwen2.5:7b"
      provider: "ollama"
      temperature: 0.7
      max_tokens: 4096
```

#### Python 使用
```python
from agent_os_kernel.llm import LLMProviderFactory, LLMConfig

factory = LLMProviderFactory()
provider = factory.create(LLMConfig(
    provider="ollama",
    model="qwen2.5:7b",
    base_url="http://localhost:11434"
))
```

---

### 2. vLLM (高性能)

#### 安装
```bash
pip install vllm
```

#### 启动服务器
```bash
# 单 GPU
vllm serve meta-llama/Llama-3.1-8B-Instruct

# 多 GPU
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --tensor-parallel-size 4 \
    --quantization awq
```

#### 配置
```yaml
# config.yaml
llm:
  providers:
    - name: "vllm-llama"
      provider: "vllm"
      model: "meta-llama/Llama-3.1-8B-Instruct"
      base_url: "http://localhost:8000/v1"
```

---

### 3. LM Studio (桌面应用)

#### 安装
1. 下载: https://lmstudio.ai
2. 下载模型 (GGUF 格式)
3. 启动本地服务器

#### 配置
```yaml
llm:
  provider: "openai"  # LM Studio 兼容 OpenAI API
  base_url: "http://localhost:1234/v1"
  model: "你的模型名称"
```

---

### 4. LocalAI (Docker)

#### Docker 部署
```bash
# 启动 LocalAI
docker run -d -p 8080:8080 \
  -v ./models:/models \
  mudler/localai:latest \
  --models-path /models \
  --context-size 2048 \
  "llama-3.2-vision:latest"

# 或使用 docker-compose
curl -o docker-compose.yml https://raw.githubusercontent.com/mudler/LocalAI/master/docker-compose.yml
docker-compose up -d
```

#### 下载模型
```bash
# 下载 GGUF 模型到 models/ 目录
# 支持格式: .gguf, .bin
```

#### 配置
```yaml
llm:
  provider: "openai"
  base_url: "http://localhost:8080/v1"
  model: "llama-3.2-vision:latest"
```

---

### 5. HuggingFace Transformers (直接使用)

#### 安装
```bash
pip install transformers accelerate torch
```

#### Python 使用
```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "meta-llama/Llama-3.1-8B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype="auto"
)

# 使用
inputs = tokenizer("Hello, I am", return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=100)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

---

## 模型推荐

### 中文场景
| 模型 | 大小 | 推荐场景 |
|-----|------|---------|
| Qwen2.5:7b | ~5GB | 通用对话 |
| Qwen2.5:14b | ~10GB | 复杂推理 |
| Yi-1.5-9B-Chat | ~9GB | 中文优化 |

### 英文场景
| 模型 | 大小 | 推荐场景 |
|-----|------|---------|
| Llama 3.1:8B | ~7GB | 通用对话 |
| Mistral 7B | ~7GB | 指令遵循 |
| Gemma 2:9B | ~9GB | 轻量高效 |

### 代码场景
| 模型 | 大小 | 推荐场景 |
|-----|------|---------|
| DeepSeek Coder | ~7GB | 代码生成 |
| CodeLlama | ~8GB | 代码补全 |

---

## 性能优化

### GPU 配置
```python
# 设置 GPU 内存管理
import torch
torch.cuda.set_per_process_memory_fraction(0.8)

# 使用半精度
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)
```

### 量化
```bash
# 使用量化模型减少显存
# 推荐: AWQ, GPTQ, GGUF (Q4_K_M)
```

---

## 故障排除

### Ollama 问题
```bash
# 查看日志
journalctl -u ollama

# 重启服务
sudo systemctl restart ollama

# 检查端口
netstat -tlnp | grep 11434
```

### vLLM 问题
```bash
# 检查 GPU
nvidia-smi

# 查看日志
vllm serve --verbose ...
```

### 内存不足
```yaml
# 减少上下文长度
llm:
  models:
    - name: "qwen2.5:7b"
      context_size: 2048  # 减少到 2K

# 使用量化模型
ollama pull qwen2.5:7b-instruct-q4_0
```

---

## 快速开始

### 步骤 1: 安装 Ollama
```bash
curl -fsSL https://ollama.ai | sh
```

### 步骤 2: 下载模型
```bash
ollama pull qwen2.5:7b
```

### 步骤 3: 配置项目
```yaml
# config.yaml
kernel:
  max_agents: 10

llm:
  default_provider: "ollama"
  models:
    - name: "qwen2.5:7b"
      provider: "ollama"
      temperature: 0.7
```

### 步骤 4: 运行
```bash
python -c "
from agent_os_kernel import AgentOSKernel

kernel = AgentOSKernel()
print('✅ 本地模型配置成功!')
"
```

---

## 总结

| 方案 | 难度 | 性能 | 推荐场景 |
|-----|------|------|---------|
| Ollama | ⭐ | ⭐⭐⭐ | 开发测试 |
| vLLM | ⭐⭐ | ⭐⭐⭐⭐ | 生产部署 |
| LM Studio | ⭐ | ⭐⭐ | 桌面应用 |
| LocalAI | ⭐⭐ | ⭐⭐⭐ | Docker 部署 |

**推荐**: 开发使用 Ollama，生产使用 vLLM
