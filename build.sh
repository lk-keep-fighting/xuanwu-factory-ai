#!/bin/bash

# 简单的Docker镜像构建脚本
# 参考 build-base.sh 保持简洁性

set -e

# 配置
REGISTRY="nexus.aimstek.cn/xuanwu"
IMAGE_NAME="xuanwu-factory-ai"
PLATFORM="linux/amd64"  # 默认平台
TIMESTAMP=$(date +%Y%m%d-%H%M)

# 简化的参数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        --push)
            PUSH="--push"
            shift
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  -p, --platform PLATFORM   构建平台 (默认: $PLATFORM)"
            echo "  --push                    构建后推送到仓库"
            echo "  -t, --tag TAG            自定义标签"
            echo "  -h, --help               显示此帮助信息"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 设置镜像标签
TAG=${TAG:-$TIMESTAMP}
FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$TAG"

echo "=========================================="
echo "Docker 镜像构建"
echo "=========================================="
echo "镜像名称: $FULL_IMAGE_NAME"
echo "构建平台: $PLATFORM"
if [[ "$PUSH" == "--push" ]]; then
    echo "推送: 是"
else
    echo "推送: 否"
fi
echo "=========================================="

# 开始构建
echo "开始构建镜像..."
docker buildx build \
    --platform "$PLATFORM" \
    -t "$FULL_IMAGE_NAME" \
    ${PUSH:-"--load"} \
    .

echo ""
echo "=========================================="
echo "构建完成!"
echo "镜像: $FULL_IMAGE_NAME"
echo "=========================================="

# 显示镜像信息
echo ""
echo "本地镜像信息:"
docker images | grep "$IMAGE_NAME" | head -3