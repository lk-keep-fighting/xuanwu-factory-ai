# GitLab 认证问题修复指南

## 问题描述

在 K8s 容器中执行时出现 Git 克隆认证失败：
```
Clone attempt 1/3 failed: Cmd('git') failed due to: exit code(128)
stderr: 'remote: HTTP Basic: Access denied...'
```

## 根本原因

GitLab Personal Access Token 的认证格式需要特定的用户名/密码组合。

## 已修复的代码

### 1. `git_manager.py` 中的认证格式

已将认证格式从 `oauth2:token` 改为 `gitlab-ci-token:token`，这是 GitLab 推荐的格式。

```python
# 修改前
auth_segment = f"oauth2:{api_token}"

# 修改后 (针对 GitLab)
auth_segment = f"gitlab-ci-token:{api_token}"
```

## 验证步骤

### 步骤 1: 本地测试

运行诊断脚本检查配置：

```bash
python test_gitlab_auth.py
```

### 步骤 2: 本地测试克隆

```bash
python test_clone.py
```

### 步骤 3: 检查 K8s 环境变量

在 K8s 中检查环境变量是否正确传递：

```bash
# 查看 Pod
kubectl get pods -n xuanwu-factory

# 检查环境变量
kubectl exec <pod-name> -n xuanwu-factory -- env | grep GITLAB

# 查看 Pod 日志
kubectl logs <pod-name> -n xuanwu-factory
```

### 步骤 4: 验证 Token 权限

登录 GitLab，检查 Personal Access Token 权限：

1. 访问: https://gitlab.aimstek.cn/-/profile/personal_access_tokens
2. 找到你的 token (glpat-vpsWCFiBN4JpY2LFcrdx)
3. 确认权限包含以下之一：
   - ✓ `read_repository` (读取仓库)
   - ✓ `write_repository` (写入仓库)  
   - ✓ `api` (完整 API 访问)

### 步骤 5: 测试 Token 有效性

使用 curl 测试 token 是否有效：

```bash
# 测试 API 访问
curl --header "PRIVATE-TOKEN: glpat-vpsWCFiBN4JpY2LFcrdx" \
  "https://gitlab.aimstek.cn/api/v4/projects/xuanwu%2Fbiz-simulation%2Flogic-test-group%2Flogic-test-jdk17"

# 测试克隆 (使用 gitlab-ci-token)
git clone https://gitlab-ci-token:glpat-vpsWCFiBN4JpY2LFcrdx@gitlab.aimstek.cn/xuanwu/biz-simulation/logic-test-group/logic-test-jdk17.git /tmp/test-clone
```

## 常见问题

### 问题 1: Token 权限不足

**症状**: `HTTP Basic: Access denied`

**解决方案**:
1. 创建新的 Personal Access Token
2. 确保勾选 `read_repository` 权限
3. 更新 K8s Secret 或环境变量

### 问题 2: Token 已过期

**症状**: `token was either incorrect, expired, or improperly scoped`

**解决方案**:
1. 在 GitLab 中创建新的 token
2. 设置更长的过期时间或不过期
3. 更新环境变量

### 问题 3: 环境变量未传递到容器

**症状**: 日志显示 `Token prefix: ***...` 为空

**解决方案**:

检查 K8s 部署配置：

```bash
# 方式 1: 使用 Secret (推荐)
kubectl create secret generic ai-coder-secrets \
  --from-literal=GITLAB_API_TOKEN=glpat-vpsWCFiBN4JpY2LFcrdx \
  -n xuanwu-factory

# 方式 2: 直接在 Job 中设置环境变量
kubectl run ai-coder-test \
  --image=your-image \
  --env="GITLAB_API_TOKEN=glpat-vpsWCFiBN4JpY2LFcrdx" \
  -n xuanwu-factory
```

### 问题 4: 分支名称错误

**症状**: `Remote branch master not found`

**解决方案**:

确认仓库的默认分支名称：

```bash
# 检查远程分支
git ls-remote https://gitlab.aimstek.cn/xuanwu/biz-simulation/logic-test-group/logic-test-jdk17.git

# 更新 .env 文件
REPO_BRANCH=master  # 或 main
```

## 重新部署

修复代码后，重新构建和部署：

```bash
# 1. 重新构建镜像
./build.sh

# 2. 推送到镜像仓库
docker push your-registry/ai-coder:latest

# 3. 重新部署到 K8s
./run-in-k8s.sh

# 4. 查看日志
kubectl logs -f <pod-name> -n xuanwu-factory
```

## 调试日志

修改后的代码会输出详细的诊断信息：

```
[GitManager] Cloning repository: https://gitlab.aimstek.cn/...
[GitManager] Branch: master
[GitManager] Credentials provided: ['api_token']
[GitManager] Token prefix: glpat-vpsW...
```

如果看到这些日志，说明配置正确传递。

## 其他认证方式

如果 `gitlab-ci-token` 方式仍然失败，可以尝试：

### 方式 1: 使用 Deploy Token

1. 在 GitLab 项目设置中创建 Deploy Token
2. 使用格式: `https://<deploy-token-username>:<deploy-token>@gitlab.com/...`

### 方式 2: 使用 SSH

1. 生成 SSH 密钥对
2. 将公钥添加到 GitLab
3. 使用 SSH URL: `git@gitlab.aimstek.cn:xuanwu/biz-simulation/logic-test-group/logic-test-jdk17.git`

## 联系支持

如果问题仍未解决，请提供以下信息：

1. 完整的错误日志
2. `kubectl describe pod <pod-name> -n xuanwu-factory` 输出
3. Token 权限截图（隐藏 token 值）
4. GitLab 版本信息
