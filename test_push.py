#!/usr/bin/env python3
"""测试 Git push 功能"""

import asyncio
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from commit_manager import CommitManager
from git_manager import GitManager

load_dotenv()


async def test_push():
    """测试完整的克隆、提交、推送流程"""
    
    repo_url = os.getenv("REPO_URL")
    token = os.getenv("GITLAB_API_TOKEN")
    branch = os.getenv("REPO_BRANCH", "master")
    username = os.getenv("GIT_USERNAME", "xuanwu-factory-ai")
    email = os.getenv("GIT_EMAIL", "ai-coder@example.com")
    
    if not repo_url or not token:
        print("❌ 错误: REPO_URL 或 GITLAB_API_TOKEN 未设置")
        return False
    
    print("=" * 60)
    print("测试 Git Push 功能")
    print("=" * 60)
    print(f"仓库: {repo_url}")
    print(f"分支: {branch}")
    print(f"Token: {token[:10]}...")
    print("=" * 60)
    
    git_mgr = GitManager()
    commit_mgr = CommitManager()
    
    try:
        # 1. 克隆仓库
        print("\n[1/5] 克隆仓库...")
        repo_path = await git_mgr.clone_repository(
            repo_url,
            branch=branch,
            credentials={"api_token": token},
            retries=1,
        )
        print(f"✓ 克隆成功: {repo_path}")
        
        # 2. 创建测试分支
        print("\n[2/5] 创建测试分支...")
        test_branch = "test-push-fix"
        git_mgr.create_feature_branch(test_branch)
        print(f"✓ 分支创建成功: {test_branch}")
        
        # 3. 创建测试文件
        print("\n[3/5] 创建测试文件...")
        test_file = Path(repo_path) / "test_push.txt"
        test_file.write_text("This is a test file for push functionality\n")
        print(f"✓ 文件创建成功: {test_file}")
        
        # 4. 提交更改
        print("\n[4/5] 提交更改...")
        commit_mgr.attach_repo(git_mgr.repo)
        commit_mgr.stage_changes()
        
        # 配置 Git 用户信息
        git_mgr.repo.config_writer().set_value("user", "name", username).release()
        git_mgr.repo.config_writer().set_value("user", "email", email).release()
        
        commit_hash = commit_mgr.create_commit("Test: Push functionality test")
        print(f"✓ 提交成功: {commit_hash[:8]}")
        
        # 5. 推送到远程
        print("\n[5/5] 推送到远程...")
        push_result = commit_mgr.push_changes(
            branch=test_branch,
            credentials={"api_token": token},
        )
        
        if push_result:
            print(f"✓ 推送成功!")
            print(f"\n查看分支: {repo_url.replace('.git', '')}/tree/{test_branch}")
            print(f"\n⚠️  记得删除测试分支:")
            print(f"   git push origin --delete {test_branch}")
            return True
        else:
            print("❌ 推送失败")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = asyncio.run(test_push())
    sys.exit(0 if success else 1)
