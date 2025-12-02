#!/bin/bash
# 快速构建和部署脚本

set -e

echo "=========================================="
echo "快速构建和部署"
echo "=========================================="

# 1. 构建镜像
echo ""
echo "[1/3] 构建 Docker 镜像..."
./build.sh

# 2. 获取最新镜像标签
IMAGE_TAG=$(docker images nexus.aimstek.cn/xuanwu-factory/xuanwu-factory-ai --format "{{.Tag}}" | head -1)
IMAGE_NAME="nexus.aimstek.cn/xuanwu-factory/xuanwu-factory-ai:${IMAGE_TAG}"

echo "✓ 镜像构建完成: $IMAGE_NAME"

# 3. 更新 K8s Deployment
echo ""
echo "[2/3] 更新 K8s Deployment..."
kubectl set image deployment/xuanwu-factory-ai \
  xuanwu-factory-ai="$IMAGE_NAME" \
  -n xuanwu-factory

echo "✓ Deployment 已更新"

# 4. 等待 Pod 就绪
echo ""
echo "[3/3] 等待新 Pod 启动..."
kubectl rollout status deployment/xuanwu-factory-ai -n xuanwu-factory --timeout=120s

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="

# 显示 Pod 状态
echo ""
echo "Pod 状态:"
kubectl get pods -n xuanwu-factory -l app=xuanwu-factory-ai

# 显示日志命令
POD_NAME=$(kubectl get pods -n xuanwu-factory -l app=xuanwu-factory-ai -o jsonpath='{.items[0].metadata.name}')
echo ""
echo "查看日志:"
echo "  kubectl logs -f $POD_NAME -n xuanwu-factory"
