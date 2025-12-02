#!/usr/bin/env python3
"""测试 GitLab 认证配置的诊断脚本"""

import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def test_gitlab_token():
    """测试 GitLab Token 配置"""
    
    token = os.getenv("GITLAB_API_TOKEN")
    repo_url = os.getenv("REPO_URL")
    
    print("=" * 60)
    print("GitLab 认证配置诊断")
    print("=" * 60)
    
    # 检查 Token
    if not token:
        print("❌ 错误: GITLAB_API_TOKEN 环境变量未设置")
        return False
    
    print(f"✓ GITLAB_API_TOKEN 已设置")
    print(f"  Token 前缀: {token[:10]}...")
    print(f"  Token 长度: {len(token)} 字符")
    
    # 检查 Token 格式
    if token.startswith("glpat-"):
        print("  ✓ Token 格式正确 (Personal Access Token)")
    elif token.startswith("gldt-"):
        print("  ⚠️  这是 Deploy Token (gldt-), 确保有 read_repository 权限")
    else:
        print("  ⚠️  Token 格式不标准，请确认是否为有效的 GitLab Token")
    
    # 检查仓库 URL
    if not repo_url:
        print("❌ 错误: REPO_URL 环境变量未设置")
        return False
    
    print(f"\n✓ REPO_URL 已设置")
    print(f"  URL: {repo_url}")
    
    parsed = urlparse(repo_url)
    if "gitlab" not in parsed.netloc.lower():
        print("  ⚠️  URL 不包含 'gitlab'，请确认是否为 GitLab 仓库")
    else:
        print(f"  ✓ GitLab 主机: {parsed.netloc}")
    
    # 生成测试 URL
    print("\n" + "=" * 60)
    print("生成的认证 URL 格式:")
    print("=" * 60)
    
    # 方式 1: gitlab-ci-token (推荐)
    scheme = parsed.scheme
    remainder = f"{parsed.netloc}{parsed.path}"
    auth_url_1 = f"{scheme}://gitlab-ci-token:{token}@{remainder}"
    print(f"\n方式 1 (gitlab-ci-token):")
    print(f"  {scheme}://gitlab-ci-token:{'*' * 10}@{remainder}")
    
    # 方式 2: oauth2
    auth_url_2 = f"{scheme}://oauth2:{token}@{remainder}"
    print(f"\n方式 2 (oauth2):")
    print(f"  {scheme}://oauth2:{'*' * 10}@{remainder}")
    
    # 方式 3: 直接使用 token 作为用户名
    auth_url_3 = f"{scheme}://{token}@{remainder}"
    print(f"\n方式 3 (token as username):")
    print(f"  {scheme}://{'*' * 10}@{remainder}")
    
    print("\n" + "=" * 60)
    print("建议检查项:")
    print("=" * 60)
    print("1. 确认 Token 权限包含以下之一:")
    print("   - read_repository (读取仓库)")
    print("   - write_repository (写入仓库)")
    print("   - api (完整 API 访问)")
    print("\n2. 确认 Token 未过期")
    print("\n3. 确认你的账号有访问该仓库的权限")
    print("\n4. 如果是私有 GitLab 实例，确认网络可达")
    
    print("\n" + "=" * 60)
    print("在 Kubernetes 中检查环境变量:")
    print("=" * 60)
    print("kubectl get secret ai-coder-secrets -n xuanwu-factory -o yaml")
    print("kubectl describe pod <pod-name> -n xuanwu-factory")
    print("kubectl exec <pod-name> -n xuanwu-factory -- env | grep GITLAB")
    
    return True


if __name__ == "__main__":
    success = test_gitlab_token()
    sys.exit(0 if success else 1)
