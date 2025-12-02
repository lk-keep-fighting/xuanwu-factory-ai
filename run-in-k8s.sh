#!/bin/bash

# Xuanwu Factory AI - Kubernetes 一键执行脚本
# 基于 .env 配置文件和 k8s_runner.py 实现 K8s 中的任务运行

set -e

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
K8S_RUNNER="${SCRIPT_DIR}/k8s_runner.py"
IMAGE_REGISTRY="nexus.aimstek.cn/xuanwu/xuanwu-factory-ai:20251114-1326"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "环境配置文件不存在: $ENV_FILE"
        exit 1
    fi

    if [[ ! -f "$K8S_RUNNER" ]]; then
        log_error "K8s运行器不存在: $K8S_RUNNER"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装或不在 PATH 中"
        exit 1
    fi

    if ! python3 -c "import kubernetes" 2>/dev/null; then
        log_error "Kubernetes Python 客户端未安装，请运行: pip install kubernetes"
        exit 1
    fi

    log_success "依赖检查通过"
}

# 加载环境变量
load_env_vars() {
    log_info "加载环境变量配置..."

    # 临时设置环境变量
    while IFS='=' read -r key value; do
        # 跳过注释和空行
        [[ $key =~ ^[[:space:]]*# ]] && continue
        [[ -z $key ]] && continue

        # 移除值中的引号
        value=$(echo "$value" | sed 's/^["\x27]//' | sed 's/["\x27]$//')

        # 导出环境变量
        export "$key"="$value"
        log_info "  $key=${value:0:20}..."
    done < "$ENV_FILE"

    log_success "环境变量加载完成"
}

# 验证必需的环境变量
validate_env_vars() {
    log_info "验证必需的环境变量..."

    local required_vars=(
        "OPENAI_API_KEY"
        "REPO_URL"
        "TASK_INTENT"
        "WEBHOOK_URL"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "缺少必需的环境变量: ${missing_vars[*]}"
        exit 1
    fi

    log_success "环境变量验证通过"
}

# 获取镜像标签
get_image_tag() {
    local tag="latest"

    # 如果有 Git 仓库，尝试获取最新的提交哈希
    if [[ -d "${SCRIPT_DIR}/.git" ]]; then
        local git_hash
        git_hash=$(cd "$SCRIPT_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "")
        if [[ -n "$git_hash" ]]; then
            tag="$git_hash"
        fi
    fi

    # 也可以使用当前时间
    # tag=$(date +%Y%m%d-%H%M%S)

    echo "$tag"
}

# 构建 k8s_runner.py 命令参数
build_k8s_command() {
    local image_tag="$1"
    local image="${IMAGE_REGISTRY}:${image_tag}"

    # 基础参数数组
    local cmd=(
        "python3"
        "$K8S_RUNNER"
        "--namespace" "xuanwu-ai"
        "--name" "xuanwu-factory-ai-task"
        "--auto-clean"
        "--request-cpu" "1000m"
        "--request-memory" "1Gi"
        "--limit-cpu" "2000m"
        "--limit-memory" "2Gi"
        "--timeout" "3600"
        "--backoff-limit" "2"
    )

    # 添加环境变量
    local env_vars=(
        "OPENAI_API_KEY=${OPENAI_API_KEY}"
        "OPENAI_BASE_URL=${OPENAI_BASE_URL:-}"
        "OPENAI_MODEL=${OPENAI_MODEL:-qwen-coder}"
        "REPO_URL=${REPO_URL}"
        "TASK_INTENT=${TASK_INTENT}"
        "WEBHOOK_URL=${WEBHOOK_URL}"
        "WEBHOOK_SECRET=${WEBHOOK_SECRET:-}"
        "GITLAB_API_TOKEN=${GITLAB_API_TOKEN:-}"
        "GIT_USERNAME=${GIT_USERNAME:-xuanwu-factory-ai}"
        "GIT_EMAIL=${GIT_EMAIL:-ai-coder@example.com}"
        "REPO_BRANCH=${REPO_BRANCH:-main}"
        "MAX_ITERATIONS=${MAX_ITERATIONS:-3}"
        "WORKSPACE_DIR=/workspace"
    )

    for env_var in "${env_vars[@]}"; do
        if [[ "$env_var" == *"="* ]]; then
            key="${env_var%%=*}"
            value="${env_var#*=}"
            if [[ -n "$value" ]]; then
                cmd+=("--env" "$env_var")
            fi
        fi
    done

    # 添加镜像和命令
    cmd+=("$image" "--" "python" "/app/main.py")

    # 输出命令字符串
    printf '%s ' "${cmd[@]}"
}

# 执行 K8s 任务
run_k8s_job() {
    local image_tag="$1"

    log_info "准备在 Kubernetes 中运行任务..."
    log_info "镜像: ${IMAGE_REGISTRY}:${image_tag}"
    log_info "命名空间: xuanwu-ai"
    log_info "任务描述: ${TASK_INTENT}"
    log_info "仓库地址: ${REPO_URL}"

    # 构建命令
    local k8s_cmd
    k8s_cmd=$(build_k8s_command "$image_tag")

    log_info "执行的命令:"
    echo "$k8s_cmd"
    echo

    # 执行命令
    log_info "启动 Kubernetes Job..."
    eval "$k8s_cmd"

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "任务执行完成!"
    else
        log_error "任务执行失败，退出码: $exit_code"
        exit $exit_code
    fi
}

# 显示帮助信息
show_help() {
    cat << 'EOF'
Xuanwu Factory AI - Kubernetes 一键执行脚本

用法:
    ./run-in-k8s.sh [选项] [镜像标签]

选项:
    -h, --help          显示此帮助信息
    -e, --env FILE      指定环境配置文件 (默认: .env)
    -t, --tag TAG       指定镜像标签 (默认: latest 或 git hash)
    -n, --namespace NS  指定K8s命名空间 (默认: xuanwu-ai)
    --dry-run           仅显示将要执行的命令，不实际运行
    --keep              任务完成后保留 K8s 资源（默认自动清理）

示例:
    ./run-in-k8s.sh                                      # 使用默认配置运行
    ./run-in-k8s.sh -t latest                           # 指定镜像标签
    ./run-in-k8s.sh -n my-namespace                     # 指定命名空间
    ./run-in-k8s.sh --dry-run                           # 预览命令
    ./run-in-k8s.sh --keep                              # 保留资源

环境配置文件 (.env) 必须包含以下必需变量:
    - OPENAI_API_KEY: AI 模型 API 密钥
    - REPO_URL: Git 仓库地址
    - TASK_INTENT: 任务描述
    - WEBHOOK_URL: Webhook 推送地址

可选变量:
    - OPENAI_BASE_URL: AI 模型服务地址
    - OPENAI_MODEL: 模型名称 (默认: qwen-coder)
    - GITLAB_API_TOKEN: GitLab API Token
    - GIT_USERNAME: Git 用户名 (默认: xuanwu-factory-ai)
    - GIT_EMAIL: Git 邮箱 (默认: ai-coder@example.com)
    - REPO_BRANCH: Git 分支 (默认: main)
    - MAX_ITERATIONS: 最大迭代次数 (默认: 3)
    - WEBHOOK_SECRET: Webhook 签名密钥

EOF
}

# 主函数
main() {
    local env_file="$ENV_FILE"
    local image_tag=""
    local namespace="xuanwu-ai"
    local dry_run=false
    local auto_clean=true

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -e|--env)
                env_file="$2"
                shift 2
                ;;
            -t|--tag)
                image_tag="$2"
                shift 2
                ;;
            -n|--namespace)
                namespace="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --keep)
                auto_clean=false
                shift
                ;;
            -*)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$image_tag" ]]; then
                    image_tag="$1"
                else
                    log_error "多余的参数: $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # 设置环境变量文件路径
    ENV_FILE="$env_file"

    # 如果未指定镜像标签，自动获取
    if [[ -z "$image_tag" ]]; then
        image_tag=$(get_image_tag)
    fi

    log_info "Xuanwu Factory AI - Kubernetes 运行器"
    log_info "======================================"

    # 检查依赖
    check_dependencies

    # 加载环境变量
    load_env_vars

    # 验证环境变量
    validate_env_vars

    # 如果只是预览，显示命令并退出
    if [[ "$dry_run" == true ]]; then
        log_info "将要执行的命令:"
        build_k8s_command "$image_tag"
        exit 0
    fi

    # 运行 K8s 任务
    run_k8s_job "$image_tag"

    log_success "脚本执行完成!"
}

# 信号处理
trap 'log_warning "脚本被中断"; exit 130' INT TERM

# 执行主函数
main "$@"