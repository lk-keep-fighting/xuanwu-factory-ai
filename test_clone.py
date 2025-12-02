#!/usr/bin/env python3
"""快速测试 Git 克隆功能"""

import asyncio
import os
import sys

from dotenv import load_dotenv

from git_manager import GitManager

load_dotenv()


async def test_clone():
    """测试克隆功能"""
    
    repo_url = os.getenv("REPO_URL")
    token = os.getenv("GITLAB_API_TOKEN")
    branch = os.getenv("REPO_BRANCH", "master")
    
    if not repo_url:
        print("❌ 错误: REPO_URL 未设置")
        return False
    
    if not token:
        print("❌ 错误: GITLAB_API_TOKEN 未设置")
        return False
    
    print("=" * 60)
    print("测试 Git 克隆")
    print("=" * 60)
    print(f"仓库: {repo_url}")
    print(f"分支: {branch}")
    print(f"Token: {token[:10]}... (长度: {len(token)})")
    print("=" * 60)
    
    git_mgr = GitManager()
    
    try:
        print("\n开始克隆...")
        repo_path = await git_mgr.clone_repository(
            repo_url,
            branch=branch,
            credentials={"api_token": token},
            retries=1,  # 只尝试一次，快速失败
        )
        print(f"\n✓ 克隆成功!")
        print(f"  路径: {repo_path}")
        return True
    except Exception as e:
        print(f"\n❌ 克隆失败:")
        print(f"  错误: {e}")
        print("\n可能的原因:")
        print("  1. Token 权限不足 (需要 read_repository 或 write_repository)")
        print("  2. Token 已过期")
        print("  3. 账号无权访问该仓库")
        print("  4. 网络连接问题")
        print("  5. 分支名称错误")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_clone())
    sys.exit(0 if success else 1)
