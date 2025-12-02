# GitLab 认证问题修复总结

## 🔧 已修复的问题

### 1. Git 认证格式错误

**位置**: `git_manager.py` 的 `_prepare_repo_url` 方法

**问题**: 使用了 `oauth2:token` 格式，但 GitLab 更推荐使用 `gitlab-ci-token:token`

**修复**:
```python
# 针对 GitLab 使用专用格式
if "gitlab" in repo_url.lower():
    auth_segment = f"gitlab-ci-token:{api_token}"
else:
    auth_segment = f"oauth2:{api_token}"
```

### 2. 添加诊断日志

在克隆过程中添加了详细的日志输出，便于排查问题：
```python
print(f"[GitManager] Cloning repository: {repo_url}")
print(f"[GitManager] Branch: {branch}")
print(f"[GitManager] Credentials provided: {list(credentials.keys())}")
```

## 🧪 测试工具

创建了 3 个测试工具帮助诊断问题：

### 1. `test_gitlab_auth.py` - 配置诊断
检查环境变量配置是否正确：
```bash
python test_gitlab_auth.py
```

### 2. `test_clone.py` - 克隆测试
测试实际的 Git 克隆功能：
```bash
python test_clone.py
```

### 3. `quick_test.sh` - 快速测试（可在 K8s 中运行）
测试多种认证方式：
```bash
./quick_test.sh
```

## 📋 排查步骤

### 步骤 1: 本地验证

```bash
# 1. 确保环境变量已设置
cat .env | grep GITLAB

# 2. 运行配置诊断
python test_gitlab_auth.py

# 3. 测试克隆
python test_clone.py
```

### 步骤 2: K8s 环境检查

```bash
# 1. 查看 Pod 状态
kubectl get pods -n xuanwu-factory

# 2. 查看环境变量
kubectl exec <pod-name> -n xuanwu-factory -- env | grep GITLAB

# 3. 在 Pod 中运行快速测试
kubectl exec <pod-name> -n xuanwu-factory -- /app/quick_test.sh

# 4. 查看应用日志
kubectl logs -f <pod-name> -n xuanwu-factory
```

### 步骤 3: 验证 Token 权限

1. 登录 GitLab: https://gitlab.aimstek.cn/-/profile/personal_access_tokens
2. 检查 token `glpat-vpsWCFiBN4JpY2LFcrdx` 的权限
3. 确保包含以下权限之一：
   - ✅ `read_repository`
   - ✅ `write_repository`
   - ✅ `api`

### 步骤 4: 手动测试 Token

```bash
# 测试 API 访问
curl --header "PRIVATE-TOKEN: glpat-vpsWCFiBN4JpY2LFcrdx" \
  "https://gitlab.aimstek.cn/api/v4/projects/xuanwu%2Fbiz-simulation%2Flogic-test-group%2Flogic-test-jdk17"

# 测试 Git 克隆
git clone https://gitlab-ci-token:glpat-vpsWCFiBN4JpY2LFcrdx@gitlab.aimstek.cn/xuanwu/biz-simulation/logic-test-group/logic-test-jdk17.git /tmp/test
```

## 🚀 重新部署

修复后重新部署到 K8s：

```bash
# 1. 重新构建镜像
./build.sh

# 2. 推送镜像（如果需要）
docker push <your-registry>/ai-coder:latest

# 3. 重新部署
./run-in-k8s.sh

# 4. 监控日志
kubectl logs -f $(kubectl get pods -n xuanwu-factory -l app=xuanwu-factory-ai -o name | head -1) -n xuanwu-factory
```

## ⚠️ 常见问题

### 问题 1: "HTTP Basic: Access denied"

**原因**: Token 权限不足或已过期

**解决**:
1. 检查 Token 权限（需要 `read_repository`）
2. 检查 Token 是否过期
3. 重新创建 Token 并更新环境变量

### 问题 2: "Remote branch master not found"

**原因**: 分支名称错误

**解决**:
```bash
# 检查远程分支
git ls-remote https://gitlab.aimstek.cn/xuanwu/biz-simulation/logic-test-group/logic-test-jdk17.git

# 更新 .env
REPO_BRANCH=master  # 或 main
```

### 问题 3: 环境变量未传递到容器

**原因**: K8s Secret 或 ConfigMap 配置错误

**解决**:
```bash
# 创建或更新 Secret
kubectl create secret generic ai-coder-secrets \
  --from-literal=GITLAB_API_TOKEN=glpat-vpsWCFiBN4JpY2LFcrdx \
  --dry-run=client -o yaml | kubectl apply -n xuanwu-factory -f -

# 验证 Secret
kubectl get secret ai-coder-secrets -n xuanwu-factory -o yaml
```

### 问题 4: 网络连接问题

**原因**: K8s 集群无法访问 GitLab

**解决**:
```bash
# 在 Pod 中测试网络
kubectl exec <pod-name> -n xuanwu-factory -- curl -I https://gitlab.aimstek.cn

# 检查 DNS
kubectl exec <pod-name> -n xuanwu-factory -- nslookup gitlab.aimstek.cn
```

## 📝 预期日志输出

修复后，应该看到类似的日志：

```
[GitManager] Cloning repository: https://gitlab.aimstek.cn/xuanwu/biz-simulation/logic-test-group/logic-test-jdk17.git
[GitManager] Branch: master
[GitManager] Credentials provided: ['api_token']
[GitManager] Token prefix: glpat-vpsW...
Cloning into '/tmp/ai-coder-xxxxx'...
remote: Enumerating objects: 100, done.
remote: Counting objects: 100% (100/100), done.
remote: Compressing objects: 100% (80/80), done.
remote: Total 100 (delta 20), reused 100 (delta 20)
Receiving objects: 100% (100/100), done.
Resolving deltas: 100% (20/20), done.
```

## 📚 相关文档

- [GitLab Personal Access Tokens](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)
- [Git Credentials](https://git-scm.com/docs/gitcredentials)
- [GitLab CI/CD Variables](https://docs.gitlab.com/ee/ci/variables/)

## 💡 下一步

如果问题仍未解决：

1. 运行 `./quick_test.sh` 获取详细诊断信息
2. 检查完整的错误日志
3. 验证 Token 在 GitLab Web 界面中是否可用
4. 尝试创建新的 Personal Access Token
5. 考虑使用 Deploy Token 或 SSH 密钥作为替代方案
