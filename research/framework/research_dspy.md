# DSPy 研究

## 基本信息
- 项目名称: DSPy
- GitHub: https://github.com/stanfordnlp/dspy
- 机构: Stanford NLP
- 特点: 程序化 Prompt 工程

## 核心理念

### 程序化设计
- 将 Prompt 工程转化为程序
- 模块化、可测试、可复用
- 自动优化 Prompt

### 声明式接口
```python
class RAG(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        context = self.retrieve(question).passages
        return self.generate(context=context, question=question)
```

## 主要特性

### 1. 签名系统
```python
class GenerateAnswer(dspy.Signature):
    question: str = dspy.InputField()
    context: List[str] = dspy.InputField()
    answer: str = dspy.OutputField()
```

### 2. 优化器
```python
from dspy.teleprompt import BootstrapFewShot

teleprompter = BootstrapFewShot(metric=metric)
optimized_rag = teleprompter.compile(RAG(), trainset=trainset)
```

### 3. 内置模块
- Retriever (检索器)
- ChainOfThought (思维链)
- ReAct (推理+行动)
- ProgramOfThought (思考程序)

## 可借鉴点

1. **声明式签名设计**
2. **自动 Prompt 优化**
3. **模块化组合**
4. **评估驱动开发**

## 项目地址
https://github.com/stanfordnlp/dspy
