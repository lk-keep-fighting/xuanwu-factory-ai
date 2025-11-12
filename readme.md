# AI Coding 简化版实现说明文档

## 1. 项目概述

### 目标
实现一个最小可用的 AI 编码服务，包含四个核心闭环功能：
1. **代码下载** - 从 Git 仓库获取代码
2. **智能编码** - 根据需求修改代码
3. **代码提交** - 提交修改到 Git
4. **过程推送** - 实时推送任务状态

### 技术栈
- **语言**: Python 3.9+
- **AI 模型**: Qwen Code CLI（兼容 OpenAI API，可配置自定义服务 URL 和 Key）
- **Git 操作**: GitPython
- **Webhook**: aiohttp
- **容器**: Docker

## 2. 核心功能模块

### 2.1 代码下载模块 (`git_manager.py`)

```python
"""
功能: 管理 Git 仓库的克隆、分支操作
输入: repo_url, branch, credentials
输出: 本地代码路径
异常: 网络错误、认证失败、仓库不存在
"""

class GitManager:
    def clone_repository(self, repo_url: str, local_path: str, 
                        branch: str = "main", credentials: dict | None = None) -> bool:
        """克隆远程仓库到本地"""
        # 实现要点:
        # 1. 支持 HTTP/SSH 认证
        # 2. 支持 GitLab 通过 API Token 授权 (将 token 注入 HTTPS URL 或使用 header)
        #    例如: https://oauth2:{api_token}@gitlab.com/group/project.git
        # 3. 自动创建临时目录
        # 4. 指定分支克隆
        # 5. 错误重试机制
        # 6. 克隆后写入凭证信息到受控范围，任务结束需清理
        
    def create_feature_branch(self, branch_name: str) -> bool:
        """创建功能分支"""
        
    def get_repo_structure(self) -> dict:
        """获取代码库结构信息"""
```

### 2.2 智能编码模块 (`ai_coder.py`)

```python
"""
功能: 分析需求并执行代码修改
输入: 任务描述、代码路径
输出: 修改文件列表、变更摘要
过程: 分析->规划->执行->验证循环
"""

class AICoder:
    def __init__(self, api_key: str, model: str = "qwen-coder", base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        
    async def analyze_requirements(self, intent: str, code_context: dict) -> dict:
        """分析需求并生成执行计划"""
        # 实现要点:
        # 1. 读取代码结构
        # 2. 调用 Qwen Code CLI / 其他 OpenAI 兼容模型分析需求
        # 3. 生成修改计划 {files: [], changes: [], tests: []}
        
    async def execute_code_changes(self, plan: dict, repo_path: str) -> dict:
        """执行代码修改"""
        # 实现要点:
        # 1. 按计划修改文件
        # 2. 保持代码风格一致
        # 3. 记录所有变更
        
    async def validate_changes(self, repo_path: str) -> dict:
        """验证修改结果"""
        # 实现要点:
        # 1. 运行基础测试
        # 2. 语法检查
        # 3. 生成验证报告
```

### 2.3 代码提交模块 (`commit_manager.py`)

```python
"""
功能: 管理 Git 提交和推送
输入: 修改文件、提交信息
输出: 提交哈希、推送结果
"""

class CommitManager:
    def stage_changes(self, file_pattern: str = ".") -> bool:
        """暂存所有修改"""
        
    def create_commit(self, message: str) -> str:
        """创建提交并返回提交哈希"""
        # 实现要点:
        # 1. 生成结构化提交信息
        # 2. 验证提交内容
        # 3. 返回提交ID
        
    def push_changes(self, remote: str = "origin", branch: str = None) -> bool:
        """推送到远程仓库"""
        
    def create_pull_request(self, title: str, description: str) -> dict:
        """可选: 创建 Pull Request"""
```

### 2.4 过程推送模块 (`webhook_client.py`)

```python
"""
功能: 实时推送任务状态到 Webhook
输入: 状态数据、Webhook URL
输出: 推送成功/失败
"""

class WebhookClient:
    def __init__(self, webhook_url: str, secret: str = None):
        self.webhook_url = webhook_url
        self.secret = secret
        
    async def send_status_update(self, task_id: str, status: str, data: dict) -> bool:
        """发送状态更新"""
        # 实现要点:
        # 1. 结构化状态数据
        # 2. 支持 HMAC 签名
        # 3. 异步发送，超时处理
        # 4. 重试机制
        
    def generate_payload(self, task_id: str, status: str, data: dict) -> dict:
        """生成标准化的推送载荷"""
        return {
            "task_id": task_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
```

## 3. 主控流程 (`main_controller.py`)

```python
"""
功能: 协调所有模块，实现完整工作流
输入: 任务配置
输出: 任务执行结果
状态: pending -> cloning -> analyzing -> coding -> testing -> committing -> completed/failed
"""

class MainController:
    def __init__(self, config: dict):
        self.git_mgr = GitManager()
        self.ai_coder = AICoder(
            api_key=config['api_key'],
            model=config.get('model', 'qwen-coder'),
            base_url=config.get('base_url')
        )
        self.commit_mgr = CommitManager()
        self.webhook = WebhookClient(config['webhook_url'], config.get('webhook_secret'))
        
    async def execute_task(self, task_config: dict) -> dict:
        """执行完整AI编码任务"""
        task_id = task_config['task_id']
        
        try:
            # 1. 推送开始状态
            await self.webhook.send_status_update(task_id, "started", {})
            
            # 2. 下载代码 (支持 GitLab API Token 授权)
            await self.webhook.send_status_update(task_id, "cloning", {"repo": task_config['repo_url']})
            repo_path = await self.git_mgr.clone_repository(
                task_config['repo_url'],
                credentials={"api_token": task_config.get('gitlab_api_token')}
            )
            
            # 3. AI分析规划
            await self.webhook.send_status_update(task_id, "analyzing", {})
            plan = await self.ai_coder.analyze_requirements(task_config['intent'], repo_path)
            
            # 4. 执行编码
            await self.webhook.send_status_update(task_id, "coding", {"plan": plan})
            changes = await self.ai_coder.execute_code_changes(plan, repo_path)
            
            # 5. 验证修改
            await self.webhook.send_status_update(task_id, "testing", {"changes": changes})
            test_results = await self.ai_coder.validate_changes(repo_path)
            
            # 6. 提交代码
            await self.webhook.send_status_update(task_id, "committing", {"test_results": test_results})
            commit_hash = self.commit_mgr.create_commit(f"AI: {task_config['intent']}")
            push_result = self.commit_mgr.push_changes()
            
            # 7. 任务完成
            result = {
                "task_id": task_id,
                "status": "completed",
                "commit_hash": commit_hash,
                "changes": changes,
                "test_results": test_results,
                "push_result": push_result
            }
            await self.webhook.send_status_update(task_id, "completed", result)
            return result
            
        except Exception as e:
            error_result = {
                "task_id": task_id,
                "status": "failed",
                "error": str(e)
            }
            await self.webhook.send_status_update(task_id, "failed", error_result)
            return error_result
```

## 4. 配置和入口点

### 4.1 配置文件 (`config.py`)

```python
"""
环境配置和常量定义
"""

import os
from typing import Dict, Any

class Config:
    # AI 配置
    API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL")  # OpenAI 兼容大模型服务地址
    MODEL_NAME = os.getenv("OPENAI_MODEL", "qwen-coder")
    
    # Git 配置
    GIT_USERNAME = os.getenv("GIT_USERNAME", "ai-coder-bot")
    GIT_EMAIL = os.getenv("GIT_EMAIL", "ai-coder@example.com")
    GITLAB_API_TOKEN = os.getenv("GITLAB_API_TOKEN")  # GitLab 下载源码时的 API Token
    
    # Webhook 配置
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    
    # 执行配置
    WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/workspace")
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
    
    @classmethod
    def validate(cls) -> bool:
        """验证必要配置"""
        if not cls.API_KEY:
            raise ValueError("OPENAI_API_KEY 或 LLM_API_KEY 必须设置")
        if cls.WEBHOOK_URL is None:
            raise ValueError("WEBHOOK_URL is required for status reporting")
        return True
```

### 4.2 主程序 (`main.py`)

```python
"""
程序入口点，支持命令行和模块调用
"""

import asyncio
import json
import os
import sys
from main_controller import MainController
from config import Config

async def main():
    # 从命令行参数或环境变量读取配置
    if len(sys.argv) > 1:
        task_config = json.loads(sys.argv[1])
    else:
        task_config = {
            "task_id": os.getenv("TASK_ID", "task_001"),
            "repo_url": os.getenv("REPO_URL"),
            "intent": os.getenv("TASK_INTENT"),
            "webhook_url": Config.WEBHOOK_URL,
            "gitlab_api_token": Config.GITLAB_API_TOKEN
        }
    
    # 验证配置
    Config.validate()
    
    # 执行任务
    controller = MainController({
        "api_key": Config.API_KEY,
        "model": Config.MODEL_NAME,
        "base_url": Config.BASE_URL,
        "webhook_url": Config.WEBHOOK_URL,
        "webhook_secret": Config.WEBHOOK_SECRET
    })
    
    result = await controller.execute_task(task_config)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. Docker 部署

### 5.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制代码
COPY requirements.txt .
COPY . .

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 设置工作目录
WORKDIR /workspace

# 启动命令
CMD ["python", "/app/main.py"]
```

### 5.2 依赖文件 (`requirements.txt`)

```txt
GitPython>=3.1.40
aiohttp>=3.9.0
pydantic>=2.0.0
python-dotenv>=1.0.0
kubernetes>=28.1.0
```

## 6. 使用方式

### 6.1 环境变量配置

```bash
# 必需配置
export OPENAI_API_KEY="your-qwen-api-key"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 如使用第三方 OpenAI 兼容服务
export REPO_URL="https://github.com/username/repo.git"
export TASK_INTENT="添加用户登录功能"
export WEBHOOK_URL="https://your-webhook.com/endpoint"

# Git 认证 (GitLab 通过 API Token 下载源码)
export GITLAB_API_TOKEN="glpat-xxxxxxxxxxxx"
export GIT_USERNAME="ai-coder-bot"
export GIT_EMAIL="ai-coder@company.com"

# 可选配置
export OPENAI_MODEL="qwen-coder"
export WEBHOOK_SECRET="your-secret"
export TASK_ID="task_001"
export MAX_ITERATIONS=3
```

### 6.2 运行命令

```bash
# 方式1: 环境变量
docker run \
  -e OPENAI_API_KEY=xxx \
  -e OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \
  -e OPENAI_MODEL=qwen-coder \
  -e REPO_URL=xxx \
  -e TASK_INTENT="添加登录功能" \
  -e WEBHOOK_URL=https://hook.example.com \
  -e GITLAB_API_TOKEN=glpat-xxx \
  ai-coder

# 方式2: 命令行参数
docker run ai-coder '{
  "task_id": "task_001", 
  "repo_url": "https://gitlab.com/xxx/project.git",
  "intent": "添加登录功能",
  "webhook_url": "https://hook.example.com",
  "gitlab_api_token": "glpat-xxxxxxxx"
}'
```

## 7. Webhook 数据格式

### 状态推送示例

```json
{
  "task_id": "task_001",
  "status": "coding",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "changes": [
      "modified: src/auth.py",
      "created: tests/test_auth.py"
    ],
    "progress": 60
  }
}
```

## 8. 错误处理

### 主要错误类型
1. **网络错误**: Git 克隆失败、API 调用失败
2. **认证错误**: API 密钥无效、Git 权限不足（包含 GitLab API Token 失效）
3. **代码错误**: 语法错误、测试失败
4. **系统错误**: 磁盘空间不足、内存不足

### 重试策略
- Git 操作: 最多重试 3 次
- API 调用: 指数退避重试
- Webhook: 最多重试 5 次

这个文档提供了完整的实现指导，AI 可以根据这个结构生成可工作的代码。每个模块的职责明确，接口清晰，可以并行开发。

## 9. 在 Kubernetes 中运行

当前仓库默认提供 Docker 运行方式，如果希望在 Kubernetes 集群中运行（作为长驻服务或按需执行的任务），可以参考以下步骤。

### 9.1 构建并推送镜像
```
docker build -t your-registry.example.com/ai-coder:latest .
docker push your-registry.example.com/ai-coder:latest
```

确保集群节点能够访问镜像仓库，如有需要请配置 `imagePullSecrets`。

### 9.2 配置密钥与环境变量
敏感信息建议存放在 Secret 中，常规配置可存放在 ConfigMap 中。

**Secret (`ai-coder-secrets.yaml`)**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai-coder-secrets
type: Opaque
stringData:
  OPENAI_API_KEY: "sk-xxxxxxxx"
  OPENAI_BASE_URL: "https://dashscope.aliyuncs.com/compatible-mode/v1" # 可选
  WEBHOOK_URL: "https://hook.example.com"
  WEBHOOK_SECRET: "optional-secret"
  GITLAB_API_TOKEN: "glpat-xxxxxxxx"
```

**ConfigMap (`ai-coder-config.yaml`)**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-coder-config
data:
  REPO_URL: "https://gitlab.com/xxx/project.git"
  TASK_INTENT: "添加用户登录功能"
  TASK_ID: "task-001"
  GIT_USERNAME: "ai-coder-bot"
  GIT_EMAIL: "ai-coder@company.com"
  OPENAI_MODEL: "qwen-coder"
  MAX_ITERATIONS: "3"
```

创建资源：

```
kubectl apply -f ai-coder-secrets.yaml
kubectl apply -f ai-coder-config.yaml
```

> 提示：如果某些配置不需要（例如未使用 WEBHOOK_SECRET 或 OPENAI_BASE_URL），请同时从 Secret/ConfigMap 以及 Deployment 的 `env` 中移除对应条目，以避免引用不存在的键。

### 9.3 部署应用
以下示例使用 Deployment，如果希望只运行一次，可改用 Job 或 CronJob。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-coder
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-coder
  template:
    metadata:
      labels:
        app: ai-coder
    spec:
      containers:
        - name: ai-coder
          image: your-registry.example.com/ai-coder:latest
          imagePullPolicy: IfNotPresent
          command: ["python"]
          args: ["/app/main.py"]
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: ai-coder-secrets
                  key: OPENAI_API_KEY
            - name: OPENAI_BASE_URL
              valueFrom:
                secretKeyRef:
                  name: ai-coder-secrets
                  key: OPENAI_BASE_URL
            - name: OPENAI_MODEL
              valueFrom:
                configMapKeyRef:
                  name: ai-coder-config
                  key: OPENAI_MODEL
            - name: WEBHOOK_URL
              valueFrom:
                secretKeyRef:
                  name: ai-coder-secrets
                  key: WEBHOOK_URL
            - name: WEBHOOK_SECRET
              valueFrom:
                secretKeyRef:
                  name: ai-coder-secrets
                  key: WEBHOOK_SECRET
            - name: GITLAB_API_TOKEN
              valueFrom:
                secretKeyRef:
                  name: ai-coder-secrets
                  key: GITLAB_API_TOKEN
            - name: REPO_URL
              valueFrom:
                configMapKeyRef:
                  name: ai-coder-config
                  key: REPO_URL
            - name: TASK_INTENT
              valueFrom:
                configMapKeyRef:
                  name: ai-coder-config
                  key: TASK_INTENT
            - name: TASK_ID
              valueFrom:
                configMapKeyRef:
                  name: ai-coder-config
                  key: TASK_ID
            - name: GIT_USERNAME
              valueFrom:
                configMapKeyRef:
                  name: ai-coder-config
                  key: GIT_USERNAME
            - name: GIT_EMAIL
              valueFrom:
                configMapKeyRef:
                  name: ai-coder-config
                  key: GIT_EMAIL
            - name: MODEL_NAME
              valueFrom:
                configMapKeyRef:
                  name: ai-coder-config
                  key: MODEL_NAME
            - name: MAX_ITERATIONS
              valueFrom:
                configMapKeyRef:
                  name: ai-coder-config
                  key: MAX_ITERATIONS
          volumeMounts:
            - name: workspace
              mountPath: /workspace
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
      volumes:
        - name: workspace
          emptyDir: {}
```

应用部署：

```
kubectl apply -f ai-coder-deployment.yaml
```

### 9.4 运行与排障
- 查看实时日志：`kubectl logs -f deploy/ai-coder`
- 更新配置后滚动重启：`kubectl rollout restart deploy/ai-coder`
- 临时进入容器排查：`kubectl exec -it deploy/ai-coder -- /bin/bash`
- 如果希望任务一次性执行，可改用 Job，并在任务完成后让 Pod 自动清理。

### 9.5 docker run 风格的一键执行

为了在 Kubernetes 中也能像 `docker run` 一样快速执行任务，仓库提供了 `k8s_runner.py` 脚本。该脚本会临时创建一个 Job、实时跟踪日志，并根据你的选择自动清理或保留资源。

#### 基本用法

```
python k8s_runner.py \
  --namespace ai-coder \
  --env OPENAI_API_KEY=sk-xxxxxxxx \
  --env OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --env OPENAI_MODEL=qwen-coder \
  --env WEBHOOK_URL=https://hook.example.com \
  --env TASK_INTENT="添加登录功能" \
  your-registry.example.com/ai-coder:latest -- python /app/main.py
```

`command` 部分使用 `--` 与运行参数分隔（与 `docker run` 习惯一致），可以传递任意命令、脚本或参数。

#### 自动销毁或保留

- 默认启用 `--auto-clean`，任务结束后会删除 Job / Pod（含挂载的 `emptyDir`）。
- 如需保留以便排查，可添加 `--keep`，脚本会输出后续手动删除的命令。

#### 其他常用参数

- `--entrypoint`：覆盖镜像内的入口命令。
- `--request-cpu` / `--request-memory`：为容器声明资源请求，`--limit-cpu` / `--limit-memory` 则限制上限。
- `--workspace-mount` / `--no-workspace`：控制是否挂载默认的临时工作目录。
- `--image-pull-secret` / `--service-account`：指定镜像拉取凭据或 ServiceAccount。
- `--context`：选择 kubeconfig 上下文，若未指定则自动读取当前上下文，或在集群内使用 service account。
