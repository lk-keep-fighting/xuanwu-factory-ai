# GitLab 认证问题检查清单

## ✅ 立即检查项

### 1. Token 配置
- [ ] 确认 `GITLAB_API_TOKEN` 环境变量已设置
- [ ] Token 格式正确（以 `glpat-` 开头）
- [ ] Token 长度正常（通常 20-26 个字符）

### 2. Token 权限
登录 GitLab 检查：https://gitlab.aimstek.cn/-/profile/personal_access_tokens

- [ ] Token 未过期
- [ ] Token 包含 `read_repository` 权限
- [ ] 或者包含 `write_repository` 权限
- [ ] 或者包含 `api` 权限

### 3. 仓库访问权限
- [ ] 你的账号是该仓库的成员
- [ ] 仓库不是归档状态
- [ ] 仓库 URL 正确

### 4. 分支名称
- [ ] 确认分支名称（master 或 main）
- [ ] 在 `.env` 中设置了正确的 `REPO_BRANCH`

## 🧪 测试步骤

### 本地测试

```bash
# 1. 检查配置
python test_gitlab_auth.py

# 2. 测试克隆
python test_clone.py

# 3. 如果失败，手动测试
git clone https://gitlab-ci-token:YOUR_TOKEN@gitlab.aimstek.cn/xuanwu/biz-simulation/logic-test-group/logic-test-jdk17.git /tmp/test
```

### K8s 测试

```bash
# 1. 找到 Pod
POD_NAME=$(kubectl get pods -n xuanwu-factory -l app=xuanwu-factory-ai -o jsonpath='{.items[0].metadata.name}')

# 2. 检查环境变量
kubectl exec $POD_NAME -n xuanwu-factory -- env | grep GITLAB

# 3. 运行快速测试
kubectl exec $POD_NAME -n xuanwu-factory -- bash /app/quick_test.sh

# 4. 查看日志
kubectl logs -f $POD_NAME -n xuanwu-factory
```

## 🔧 修复步骤

### 如果 Token 权限不足

1. 创建新的 Personal Access Token
2. 勾选 `read_repository` 和 `write_repository`
3. 设置过期时间（建议 90 天或更长）
4. 复制新 Token
5. 更新环境变量：

```bash
# 本地
# 编辑 .env 文件
GITLAB_API_TOKEN=新的token

# K8s
kubectl create secret generic ai-coder-secrets \
  --from-literal=GITLAB_API_TOKEN=新的token \
  --dry-run=client -o yaml | kubectl apply -n xuanwu-factory -f -
```

### 如果分支名称错误

```bash
# 1. 检查远程分支
git ls-remote https://gitlab.aimstek.cn/xuanwu/biz-simulation/logic-test-group/logic-test-jdk17.git

# 2. 更新配置
# 编辑 .env
REPO_BRANCH=master  # 或 main

# K8s 中更新
kubectl set env deployment/xuanwu-factory-ai REPO_BRANCH=master -n xuanwu-factory
```

### 如果环境变量未传递

```bash
# 检查 Secret 是否存在
kubectl get secret ai-coder-secrets -n xuanwu-factory

# 如果不存在，创建
kubectl create secret generic ai-coder-secrets \
  --from-literal=GITLAB_API_TOKEN=glpat-vpsWCFiBN4JpY2LFcrdx \
  -n xuanwu-factory

# 检查 Deployment 是否引用了 Secret
kubectl get deployment xuanwu-factory-ai -n xuanwu-factory -o yaml | grep -A 5 GITLAB_API_TOKEN
```

## 📊 预期结果

### 成功的日志输出

```
[GitManager] Cloning repository: https://gitlab.aimstek.cn/...
[GitManager] Branch: master
[GitManager] Credentials provided: ['api_token']
[GitManager] Token prefix: glpat-vpsW...
Cloning into '/tmp/ai-coder-xxxxx'...
remote: Enumerating objects: 100, done.
✓ 克隆成功!
```

### 失败的日志输出

```
Clone attempt 1/3 failed: Cmd('git') failed due to: exit code(128)
stderr: 'remote: HTTP Basic: Access denied...'
```

## 🚨 紧急修复

如果所有方法都失败，使用 Deploy Token：

1. 在 GitLab 项目设置中创建 Deploy Token
   - 项目 → Settings → Repository → Deploy Tokens
   - 名称: `ai-coder-deploy`
   - 勾选: `read_repository`
   - 创建并复制 username 和 token

2. 更新代码使用 Deploy Token：

```python
# 在 main.py 中
"git_username": os.getenv("DEPLOY_TOKEN_USERNAME"),
"git_password": os.getenv("DEPLOY_TOKEN"),
```

3. 更新环境变量：

```bash
DEPLOY_TOKEN_USERNAME=your-deploy-token-username
DEPLOY_TOKEN=your-deploy-token
```

## 📞 获取帮助

如果问题仍未解决，收集以下信息：

```bash
# 1. 完整错误日志
kubectl logs $POD_NAME -n xuanwu-factory > error.log

# 2. Pod 描述
kubectl describe pod $POD_NAME -n xuanwu-factory > pod-describe.txt

# 3. 环境变量（隐藏敏感信息）
kubectl exec $POD_NAME -n xuanwu-factory -- env | grep -E "(GITLAB|REPO|GIT)" > env-vars.txt

# 4. 快速测试结果
kubectl exec $POD_NAME -n xuanwu-factory -- bash /app/quick_test.sh > test-result.txt
```

然后提供这些文件以获取进一步帮助。
