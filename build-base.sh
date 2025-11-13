#!/bin/bash

# 构建并推送基础镜像脚本

set -e

# 配置
BASE_REGISTRY="nexus.aimstek.cn/xuanwu"
BASE_IMAGE_NAME="xuanwu-factory-ai-base"
TAG="python3.11-nodejs20"
FULL_IMAGE_NAME="$BASE_REGISTRY/$BASE_IMAGE_NAME:$TAG"

echo "=========================================="
echo "基础镜像构建配置"
echo "=========================================="
echo "镜像名称: $FULL_IMAGE_NAME"
echo "基础镜像: python:3.11-slim"
echo "包含: Python 3.11 + Node.js 20.18.0"
echo "=========================================="

# 构建镜像
echo "开始构建基础镜像..."
docker build \
    --platform linux/amd64 \
    -f Dockerfile.base \
    -t "$FULL_IMAGE_NAME" \
    .

echo ""
echo "=========================================="
echo "基础镜像构建完成!"
echo "镜像: $FULL_IMAGE_NAME"
echo "=========================================="

# 询问是否推送到仓库
read -p "是否推送到私有仓库? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "推送镜像到仓库..."
    docker push "$FULL_IMAGE_NAME"
    echo "镜像已推送到仓库: $FULL_IMAGE_NAME"
fi

# 显示镜像信息
echo ""
echo "本地镜像信息:"
docker images | grep "$BASE_IMAGE_NAME" | head -3

echo ""
echo "使用方法:"
echo "在项目Dockerfile中使用: FROM $FULL_IMAGE_NAME"