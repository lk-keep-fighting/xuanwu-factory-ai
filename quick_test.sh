#!/bin/bash
# 快速测试脚本 - 可在 K8s Pod 中运行

echo "=========================================="
echo "GitLab 认证快速测试"
echo "=========================================="

# 检查环境变量
echo ""
echo "1. 检查环境变量..."
if [ -z "$GITLAB_API_TOKEN" ]; then
    echo "❌ GITLAB_API_TOKEN 未设置"
    exit 1
else
    echo "✓ GITLAB_API_TOKEN 已设置"
    echo "  Token 前缀: ${GITLAB_API_TOKEN:0:10}..."
    echo "  Token 长度: ${#GITLAB_API_TOKEN}"
fi

if [ -z "$REPO_URL" ]; then
    echo "❌ REPO_URL 未设置"
    exit 1
else
    echo "✓ REPO_URL 已设置"
    echo "  URL: $REPO_URL"
fi

BRANCH="${REPO_BRANCH:-master}"
echo "✓ 分支: $BRANCH"

# 测试 GitLab API
echo ""
echo "2. 测试 GitLab API 访问..."
PROJECT_PATH=$(echo "$REPO_URL" | sed -E 's|https?://[^/]+/(.+)\.git|\1|')
PROJECT_PATH_ENCODED=$(echo "$PROJECT_PATH" | sed 's|/|%2F|g')
GITLAB_HOST=$(echo "$REPO_URL" | sed -E 's|(https?://[^/]+)/.*|\1|')

API_URL="${GITLAB_HOST}/api/v4/projects/${PROJECT_PATH_ENCODED}"
echo "  API URL: $API_URL"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --header "PRIVATE-TOKEN: $GITLAB_API_TOKEN" \
    "$API_URL")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ API 访问成功 (HTTP $HTTP_CODE)"
else
    echo "❌ API 访问失败 (HTTP $HTTP_CODE)"
    echo "  可能原因:"
    echo "  - Token 权限不足"
    echo "  - Token 已过期"
    echo "  - 项目路径错误"
fi

# 测试 Git 克隆 (方式 1: gitlab-ci-token)
echo ""
echo "3. 测试 Git 克隆 (gitlab-ci-token)..."
CLONE_URL_1=$(echo "$REPO_URL" | sed -E "s|https://|https://gitlab-ci-token:${GITLAB_API_TOKEN}@|")
TEST_DIR_1="/tmp/test-clone-1-$$"

if git clone --branch "$BRANCH" "$CLONE_URL_1" "$TEST_DIR_1" 2>&1; then
    echo "✓ 克隆成功 (gitlab-ci-token)"
    rm -rf "$TEST_DIR_1"
    exit 0
else
    echo "❌ 克隆失败 (gitlab-ci-token)"
fi

# 测试 Git 克隆 (方式 2: oauth2)
echo ""
echo "4. 测试 Git 克隆 (oauth2)..."
CLONE_URL_2=$(echo "$REPO_URL" | sed -E "s|https://|https://oauth2:${GITLAB_API_TOKEN}@|")
TEST_DIR_2="/tmp/test-clone-2-$$"

if git clone --branch "$BRANCH" "$CLONE_URL_2" "$TEST_DIR_2" 2>&1; then
    echo "✓ 克隆成功 (oauth2)"
    rm -rf "$TEST_DIR_2"
    exit 0
else
    echo "❌ 克隆失败 (oauth2)"
fi

# 测试 Git 克隆 (方式 3: token as username)
echo ""
echo "5. 测试 Git 克隆 (token as username)..."
CLONE_URL_3=$(echo "$REPO_URL" | sed -E "s|https://|https://${GITLAB_API_TOKEN}:@|")
TEST_DIR_3="/tmp/test-clone-3-$$"

if git clone --branch "$BRANCH" "$CLONE_URL_3" "$TEST_DIR_3" 2>&1; then
    echo "✓ 克隆成功 (token as username)"
    rm -rf "$TEST_DIR_3"
    exit 0
else
    echo "❌ 克隆失败 (token as username)"
fi

echo ""
echo "=========================================="
echo "所有克隆方式都失败了"
echo "=========================================="
echo "请检查:"
echo "1. Token 权限 (需要 read_repository)"
echo "2. Token 是否过期"
echo "3. 账号是否有仓库访问权限"
echo "4. 分支名称是否正确: $BRANCH"
echo "5. 网络连接是否正常"

exit 1
