#!/bin/bash

# 错误处理函数
die() {
    echo "ERROR: $*" >&2
    exit 1
}

# ====================== 核心优化1: 自动检测架构（x86/arm） ======================
detect_architecture() {
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)
            echo "x86"
            ;;
        aarch64|arm64)
            echo "arm"
            ;;
        *)
            die "不支持的架构: $arch，仅支持 x86_64/amd64 或 aarch64/arm64"
            ;;
    esac
}
ARCH=$(detect_architecture)
echo "🎉 自动检测到系统架构: $ARCH"

# ====================== 核心优化2: 机器人名称记忆（基于文件存储） ======================
ROBOT_TYPE_FILE="$HOME/.robodriver_robot_type"  # 记忆文件存储路径
KNOWN_ROBOT_TYPES=("aloha" "pika" "realman" "dexterous_hand" "so101" "galaxea" "galbot")

# 读取历史机器人名称（如果存在）
if [ -f "$ROBOT_TYPE_FILE" ]; then
    LAST_ROBOT_TYPE=$(cat "$ROBOT_TYPE_FILE")
    echo -e "\n检测到上次使用的机器人名称: $LAST_ROBOT_TYPE"
    read -p "是否继续使用该名称？(y/n，默认y): " confirm
    if [[ -z "$confirm" || "$confirm" == "y" || "$confirm" == "Y" ]]; then
        robot_type="$LAST_ROBOT_TYPE"
        echo "已确认使用机器人名称: $robot_type"
    else
        # 重新输入机器人名称
        while true; do
            read -p "请输入新的机器人名称（例如：aloha, pika, realman 等）: " robot_type
            if [[ -z "$robot_type" ]]; then
                echo "错误：机器人名称不能为空，请重新输入！"
                continue
            fi
            # 检查是否是已知名称
            is_known_type=false
            for type in "${KNOWN_ROBOT_TYPES[@]}"; do
                if [[ "$robot_type" == "$type" ]]; then
                    is_known_type=true
                    break
                fi
            done
            # 未知名称二次确认
            if [[ $is_known_type == false ]]; then
                echo "警告：'${robot_type}' 不是预定义的机器人名称"
                read -p "是否确认使用此名称？(y/n): " confirm_new
                if [[ "$confirm_new" != "y" && "$confirm_new" != "Y" ]]; then
                    continue
                fi
            fi
            # 保存新名称到记忆文件
            echo "$robot_type" > "$ROBOT_TYPE_FILE"
            echo "已保存机器人名称: $robot_type"
            break
        done
    fi
else
    # 首次运行，输入机器人名称
    while true; do
        read -p "请输入您的机器人名称（例如：aloha, pika, realman 等）: " robot_type
        if [[ -z "$robot_type" ]]; then
            echo "错误：机器人名称不能为空，请重新输入！"
            continue
        fi
        # 检查是否是已知名称
        is_known_type=false
        for type in "${KNOWN_ROBOT_TYPES[@]}"; do
            if [[ "$robot_type" == "$type" ]]; then
                is_known_type=true
                break
            fi
        done
        # 未知名称二次确认
        if [[ $is_known_type == false ]]; then
            echo "警告：'${robot_type}' 不是预定义的机器人名称"
            read -p "是否确认使用此名称？(y/n): " confirm_new
            if [[ "$confirm_new" != "y" && "$confirm_new" != "Y" ]]; then
                continue
            fi
        fi
        # 保存名称到记忆文件
        echo "$robot_type" > "$ROBOT_TYPE_FILE"
        echo "已保存机器人名称: $robot_type"
        break
    done
fi

# ====================== 初始配置 ======================
echo -e "\n请注意！！！该安装程序为开发者使用，适配 $ARCH 架构，安装采集平台所需的软件、服务"
read -p "按回车键继续..."

# 获取脚本所在目录（处理符号链接情况）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR" || die "无法进入脚本目录"

# 核心优化3: 按架构定义变量（无需用户干预）
if [[ "$ARCH" == "x86" ]]; then
    DOCKER_IMAGES=("baai-server-x86.tar")
    DOCKER_HUB_IMAGE="liuyou1103/wanx-server:tag"
    BACKEND_ARCH_DIR="x86"
    TEST_ACCESS_URL="http://localhost:5805/hmi"  # x86仅正式地址
elif [[ "$ARCH" == "arm" ]]; then
    DOCKER_IMAGES=("baai-flask-server-arm.tar")
    DOCKER_HUB_IMAGE="liuyou1103/wanx-server-arm:latest"
    BACKEND_ARCH_DIR="arm"
    TEST_ACCESS_URL="http://localhost:5805/hmi"   # arm测试+正式地址
fi

NGINX_CONFS=("baai_server_release.conf")
INSTALL_DOCKER="y"  # 默认安装Docker
BACKEND_DIR="/opt/RoboDriver-Server"

# 检查必需文件是否存在
REQUIRED_FILES=("${NGINX_CONFS[@]}")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        die "错误：必需文件 $file 不存在，请确保它在脚本同级目录下"
    fi
done

# 检查是否为root用户
if [ "$(id -u)" -eq 0 ]; then
    die "请使用普通用户运行此脚本，避免权限问题"
fi

# ====================== 核心优化4: 无需确认，直接使用当前用户名 ======================
CURRENT_USER=$(whoami)
echo -e "\n======================"
echo "步骤2: 自动获取当前用户名 - $CURRENT_USER（无需手动确认）"

# ====================== 步骤3: 选择是否安装 Docker ======================
echo -e "\n======================"
while true; do
    read -p "是否需要安装 Docker？（后续镜像加载、服务容器运行依赖Docker，输入 y/n）: " INSTALL_DOCKER
    case "$INSTALL_DOCKER" in
        y|Y|n|N)
            break
            ;;
        *)
            echo "输入无效！请输入 y（安装）或 n（不安装）"
            ;;
    esac
done

# ====================== 步骤1: 网络配置 ======================
echo -e "\n======================"
echo "步骤1: 请手动配置网络（如使用 nmcli 或编辑 /etc/netplan/），确保优先使用 国际 网络"
echo "📌 提示：国际网络将用于 Docker 镜像拉取、依赖包安装等操作"
read -p "按回车键继续..."

# ====================== 步骤4: 安装 Docker（根据用户选择执行） ======================
if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo -e "\n======================"
    echo "步骤4: 检查并安装 Docker..."

    # 检查是否已安装 Docker
    if command -v docker &>/dev/null; then
        echo "Docker 已安装，版本信息如下："
        docker --version
        echo "将用户 $USER 加入 docker 组..."
        sudo usermod -aG docker "$USER"
        echo "跳过安装步骤，但会继续执行配置和验证..."
    else
        # 安装依赖
        echo "安装必要依赖（ca-certificates、curl等）..."
        sudo apt-get update || die "apt 更新失败，请检查网络连接"
        sudo apt-get install -y \
            ca-certificates \
            curl \
            gnupg \
            lsb-release \
            apt-transport-https \
            software-properties-common || die "依赖安装失败"

        # 添加 Docker 官方 GPG 密钥
        echo "添加 Docker 官方 GPG 密钥..."
        sudo mkdir -p /etc/apt/keyrings || die "创建密钥目录失败"
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg || die "下载 GPG 密钥失败"
        sudo chmod a+r /etc/apt/keyrings/docker.gpg || die "设置密钥文件权限失败"

        # 设置 Docker 稳定版仓库
        echo "配置 Docker 官方软件源..."
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
            $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null || die "配置软件源失败"

        # 安装 Docker 引擎
        echo "安装 Docker 引擎（docker-ce、docker-compose等）..."
        sudo apt-get update || die "apt 二次更新失败"
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || die "Docker 引擎安装失败"
        
        # 启动 Docker 并设置开机自启
        sudo systemctl enable docker || die "设置 Docker 开机自启失败"
        sudo systemctl start docker || die "启动 Docker 服务失败"

        # 将当前用户加入 docker 组
        echo "将用户 $USER 加入 docker 组（避免后续执行 docker 命令需要 sudo）..."
        sudo usermod -aG docker "$USER" || die "添加用户到 docker 组失败"
        echo "正在刷新组权限，部分系统需要重启终端才能生效"
        newgrp docker || true

        # 验证安装
        echo "验证 Docker 安装是否成功..."
        if ! sudo docker run --rm hello-world &>/dev/null; then
            echo "错误：Docker 安装验证失败！可能是网络问题或权限未生效"
            echo "建议：重启终端后重新运行脚本，或手动执行 'docker run --rm hello-world' 验证"
            exit 1
        fi

        echo "Docker 配置完成！版本信息："
        docker --version
    fi
else
    echo -e "\n======================"
    echo "步骤4: 您选择不安装 Docker，跳过 Docker 相关配置"
    echo "⚠️  提示：后续需手动部署运行环境（conda虚拟环境+依赖安装）"
fi

# ====================== 步骤5: 安装 Git ======================
echo -e "\n======================"
echo "步骤5: 检查并安装 Git..."
if ! command -v git &>/dev/null; then
    echo "Git 未安装，开始安装..."
    sudo apt install -y git || die "Git 安装失败"
    echo "Git 安装完成，版本信息："
    git --version
else
    echo "Git 已安装（版本：$(git --version | awk '{print $3}')），跳过安装"
fi

# ====================== 步骤6: 安装并配置 Nginx + Logtail（开发者专属） ======================
echo -e "\n======================"
echo "步骤6: 检查并安装 Nginx（采集平台前端反向代理依赖）..."
if ! command -v nginx &>/dev/null; then
    echo "Nginx 未安装，开始安装..."
    sudo apt install -y nginx || die "Nginx 安装失败"
    echo "Nginx 安装完成"
else
    echo "Nginx 已安装（版本：$(nginx -v 2>&1 | awk '{print $3}' | cut -d '/' -f2)），跳过安装"
fi

# 配置 Nginx
echo "配置 Nginx 反向代理（替换默认用户为当前用户 $CURRENT_USER）..."
for conf in "${NGINX_CONFS[@]}"; do
    sed "s|/home/agilex/|/home/$CURRENT_USER/|g" "$SCRIPT_DIR/$conf" | sudo tee "/etc/nginx/conf.d/$conf" >/dev/null || die "配置 $conf 失败"
    echo "已成功配置 $conf，用户路径已替换为 /home/$CURRENT_USER/"
done

# 修复 Nginx 启动依赖（部分系统默认缺少 WantedBy 配置）
echo "修复 Nginx 启动依赖配置..."
if ! grep -q "WantedBy=multi-user.target" "/usr/lib/systemd/system/nginx.service"; then
    sudo mkdir -p /etc/systemd/system/nginx.service.d || die "创建 Nginx 配置覆盖目录失败"
    echo "[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/nginx.service.d/override.conf >/dev/null || die "创建 Nginx 覆盖配置失败"
    sudo systemctl daemon-reload || die "重载 systemd 配置失败"
    echo "Nginx 启动依赖修复完成"
else
    echo "Nginx 启动依赖配置已存在，跳过修复"
fi

# 启动 Nginx 并设置开机自启
echo "启动 Nginx 服务并设置开机自启..."
sudo systemctl start nginx || die "启动 Nginx 服务失败"
sudo systemctl enable nginx || die "设置 Nginx 开机自启失败"
echo "测试 Nginx 配置文件语法是否正确..."
sudo nginx -t || die "Nginx 配置测试失败，请检查 /etc/nginx/conf.d/ 下的配置文件"
sudo systemctl reload nginx || die "Nginx 服务重载失败"
echo "Nginx 配置完成，服务已启动"

# 配置 Logtail（开发者专属，日志采集功能）
echo -e "\n======================"
echo "步骤6.1: 配置 Logtail（开发者专属日志采集工具）..."
LOGTAIL_DIR="/usr/local/ilogtail"
APP_INFO_FILE="${LOGTAIL_DIR}/app_info.json"

if [ -f "$APP_INFO_FILE" ] && grep -q "loongcollector_version" "$APP_INFO_FILE"; then
    echo "Logtail 已安装，版本信息："
    sudo cat "$APP_INFO_FILE" | grep "loongcollector_version"
else
    echo "Logtail 未安装，开始配置和安装..."

    # 配置日志目录权限（确保 Logtail 可读写日志）
    echo "创建日志目录并配置权限..."
    sudo mkdir -p /opt/RoboDriver-log/ || die "创建日志目录 /opt/RoboDriver-log/ 失败"
    sudo chown -R "$USER":"$USER" /opt/RoboDriver-log/ || die "设置日志目录所有者失败"
    sudo chmod -R 777 /opt/RoboDriver-log/ || die "设置日志目录权限失败"

    # 创建 Logtail 用户标识文件
    echo "创建 Logtail 必要配置文件..."
    sudo mkdir -p /etc/ilogtail/users || die "创建 Logtail 用户目录失败"
    sudo touch /etc/ilogtail/users/1560822971114422 || die "创建用户标识文件失败"
    echo "robot-baai-any" | sudo tee /etc/ilogtail/user_defined_id > /dev/null || die "设置用户自定义 ID 失败"

    # 下载并安装 Logtail
    LOGTAIL_SCRIPT="loongcollector.sh"
    if [ ! -f "$LOGTAIL_SCRIPT" ]; then
        echo "本地未找到 Logtail 安装脚本，开始下载..."
        wget http://aliyun-observability-release-cn-beijing.oss-cn-beijing.aliyuncs.com/loongcollector/linux64/latest/loongcollector.sh -O "$LOGTAIL_SCRIPT" || die "下载 Logtail 安装脚本失败"
        chmod 755 "$LOGTAIL_SCRIPT" || die "设置安装脚本执行权限失败"
    else
        echo "检测到已下载的 Logtail 安装脚本（$LOGTAIL_SCRIPT），跳过下载"
    fi

    echo "执行 Logtail 安装（地域：cn-beijing-internet）..."
    sudo ./"$LOGTAIL_SCRIPT" install cn-beijing-internet || die "Logtail 安装失败"

    # 验证安装
    if [ -f "$APP_INFO_FILE" ] && grep -q "loongcollector_version" "$APP_INFO_FILE"; then
        echo "Logtail 安装成功！版本信息："
        sudo cat "$APP_INFO_FILE" | grep "loongcollector_version"
    else
        echo "错误：Logtail 安装失败，未找到版本信息文件 $APP_INFO_FILE"
        exit 1
    fi
fi

# ====================== 步骤6.2: 安装 ffmpeg 和 portaudio19-dev ======================
echo -e "\n======================"
echo "步骤6.2: 检查并安装 ffmpeg（视频编码）和 portaudio19-dev（音频采集依赖）..."

# 安装 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "ffmpeg 未安装，开始安装..."
    sudo apt update && sudo apt install -y ffmpeg || die "ffmpeg 安装失败"
    echo "ffmpeg 安装完成，版本信息："
    ffmpeg -version | head -n 1
else
    echo "ffmpeg 已安装，版本信息："
    ffmpeg -version | head -n 1
    echo "跳过 ffmpeg 安装"
fi

# 安装 portaudio19-dev
if ! dpkg -l | grep -q "portaudio19-dev"; then
    echo "portaudio19-dev 未安装，开始安装..."
    sudo apt install -y portaudio19-dev || die "portaudio19-dev 安装失败"
    echo "portaudio19-dev 安装完成"
else
    echo "portaudio19-dev 已安装，跳过安装"
fi

# ====================== 步骤7: 部署代码（覆盖现有目录） ======================
echo -e "\n======================"
echo "步骤8: 部署代码（覆盖现有目录）..."
# 获取代码源目录（脚本所在目录的父目录）
CODE_DIR=$(dirname "$SCRIPT_DIR")
if [ -z "$CODE_DIR" ] || [ "$CODE_DIR" = "/" ] || [ "$CODE_DIR" = "." ]; then
    die "无法获取有效代码源目录！请确保脚本在项目正确目录下执行"
fi
echo "代码源目录：$CODE_DIR"
# 新增：判断脚本是否已在目标目录下运行（无需拷贝）
if [ "$CODE_DIR" = "$BACKEND_DIR" ]; then
    echo "✅ 检测到代码源目录 $CODE_DIR 与目标目录 $BACKEND_DIR 一致"
    echo "无需拷贝代码，直接使用当前目录作为部署目录"
    # 确保目录权限正确（避免权限问题）
    sudo chown -R $USER:$USER "$BACKEND_DIR" || die "设置目录所有者失败"
    sudo chmod -R 777 "$BACKEND_DIR" || die "设置目录权限失败"
else
    # 检查本地代码是否存在
    if [ ! -d "$CODE_DIR" ]; then
        die "本地代码文件夹 $CODE_DIR 不存在！请确保该路径下有完整的后端代码"
    fi
    # 强制删除目标目录（如果存在），确保完全覆盖
    if [ -d "$BACKEND_DIR" ]; then
        echo "目标目录 $BACKEND_DIR 已存在，正在删除..."
        sudo rm -rf "$BACKEND_DIR" || die "删除现有目录 $BACKEND_DIR 失败（权限不足）"
    fi
    # 重新创建目标目录并拷贝代码
    sudo mkdir -p /opt || die "无法创建 /opt 目录（权限不足）"
    echo "正在将本地代码从 $CODE_DIR 复制到 $BACKEND_DIR..."
    sudo cp -a "$CODE_DIR/." "$BACKEND_DIR/" || die "拷贝代码失败（目标目录无写入权限或源文件损坏）"
    # 设置目录权限
    sudo chown -R $USER:$USER "$BACKEND_DIR" || die "设置目录所有者失败"
    sudo chmod -R 777 "$BACKEND_DIR" || die "设置目录权限失败"
    echo "代码拷入完成！目标目录：$BACKEND_DIR"
fi

# ====================== 核心优化5: 调整Docker镜像拉取顺序（先Hub后本地，优化日志） ======================
if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo -e "\n======================"
    echo "步骤8: 加载 Docker 镜像（优先从 Docker Hub 拉取，失败则加载本地镜像）..."

    for img in "${DOCKER_IMAGES[@]}"; do
        img_name="baai-flask-server"
        pull_image="n"
        load_image="n"

        # 第一步：询问是否从 Docker Hub 拉取（优先）
        while true; do
            read -p "是否从 Docker Hub 拉取镜像 ${img_name}（镜像地址：${DOCKER_HUB_IMAGE}）？(y/n) " pull_image
            case "$pull_image" in
                y|Y)
                    echo "正在从 Docker Hub 拉取镜像 ${DOCKER_HUB_IMAGE} ..."
                    if sudo docker pull "$DOCKER_HUB_IMAGE"; then
                        echo "✅ 成功拉取镜像 ${DOCKER_HUB_IMAGE}"
                        echo "正在将镜像重命名为 ${img_name}:latest（适配服务启动脚本）..."
                        if sudo docker tag "$DOCKER_HUB_IMAGE" "${img_name}:latest"; then
                            echo "✅ 成功重命名为 ${img_name}:latest"
                        else
                            die "错误：镜像重命名失败（${DOCKER_HUB_IMAGE} -> ${img_name}:latest）"
                        fi
                    else
                        echo "❌ 从 Docker Hub 拉取镜像 ${DOCKER_HUB_IMAGE} 失败（可能是网络问题）"
                        # 拉取失败，询问是否加载本地镜像
                        read -p "是否尝试加载本地镜像文件 ${img}？(y/n) " load_image
                        if [[ "$load_image" == "y" || "$load_image" == "Y" ]]; then
                            local_img_path="$SCRIPT_DIR/$img"
                            if [[ ! -f "$local_img_path" ]]; then
                                echo "⚠️  本地镜像文件 $local_img_path 不存在，跳过本地加载"
                            else
                                echo "正在加载本地镜像文件 $local_img_path ..."
                                if sudo docker load -i "$local_img_path"; then
                                    echo "✅ 成功加载本地镜像 $img"
                                else
                                    die "错误：加载本地镜像 $img 失败（文件可能损坏）"
                                fi
                            fi
                        fi
                    fi
                    break 2  # 跳出两层循环，处理下一个镜像
                    ;;
                n|N)
                    # 跳过Hub拉取，询问是否加载本地镜像
                    read -p "是否加载本地镜像文件 ${img}？(y/n) " load_image
                    case "$load_image" in
                        y|Y)
                            local_img_path="$SCRIPT_DIR/$img"
                            if [[ ! -f "$local_img_path" ]]; then
                                echo "⚠️  本地镜像文件 $local_img_path 不存在，跳过加载"
                                continue 3  # 跳出三层循环，跳过当前镜像
                            fi
                            echo "正在加载本地镜像文件 $local_img_path ..."
                            if sudo docker load -i "$local_img_path"; then
                                echo "✅ 成功加载本地镜像 $img"
                            else
                                die "错误：加载本地镜像 $img 失败（文件可能损坏）"
                            fi
                            break 2  # 跳出两层循环
                            ;;
                        n|N)
                            echo "⚠️  跳过镜像 ${img_name} 加载/拉取，后续服务启动可能失败"
                            continue 3  # 跳出三层循环
                            ;;
                        *)
                            echo "输入无效！请输入 y 或 n"
                            ;;
                    esac
                    ;;
                *)
                    echo "输入无效！请输入 y 或 n"
                    ;;
            esac
        done
    done
else
    echo -e "\n======================"
    echo "步骤8: 您选择不安装 Docker，跳过镜像加载/拉取步骤"
fi

# ====================== 步骤9: 配置免密 sudo（优化提示信息） ======================
echo -e "\n======================"
echo "步骤9: 配置免密 sudo（仅允许指定命令，提升安全性）..."
sudoers_file="/etc/sudoers.d/baai_nopasswd_$CURRENT_USER"
echo "$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/ip, /sbin/modprobe, /usr/sbin/ethtool" | sudo tee "$sudoers_file" >/dev/null || die "配置免密 sudo 失败"
sudo chmod 440 "$sudoers_file" || die "设置 sudoers 文件权限失败"  # 增强安全性
echo "已配置免密命令：/sbin/ip（网络配置）、/sbin/modprobe（内核模块）、/usr/sbin/ethtool（网卡配置）"
echo "配置文件路径：$sudoers_file"

# ====================== 步骤10: 测试启动服务（优化容器清理、配置验证） ======================
echo -e "\n======================"
echo "步骤10: 服务启动配置..."

# 定义默认运行版本和配置文件路径
device_server_type="release"
SETUP_FILE="$BACKEND_DIR/$BACKEND_ARCH_DIR/setup.yaml"

if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo "正在通过 Docker 启动服务（默认运行 release 版本）..."
    if [ -d "$BACKEND_DIR/$BACKEND_ARCH_DIR" ]; then
        cd "$BACKEND_DIR/$BACKEND_ARCH_DIR" || die "无法进入后端服务目录 $BACKEND_DIR/$BACKEND_ARCH_DIR"
        echo "正在配置后台服务参数..."

        # 检查配置文件是否存在
        if [ ! -f "$SETUP_FILE" ]; then
            die "错误: setup.yaml 配置文件不存在于 $SETUP_FILE，请确保代码部署完整"
        fi

        # 选择上传方式（nas/ks3）
        while true; do
            read -p "请选择数据上传方式（支持 nas/ks3）: " upload_type
            if [ "$upload_type" = "nas" ] || [ "$upload_type" = "ks3" ]; then
                break
            else
                echo "无效输入！仅支持 nas 或 ks3，请重新输入"
            fi
        done

        # 更新配置文件（机器人名称、运行版本、上传方式、数据集路径）
        echo "正在更新 setup.yaml 配置文件..."
        # 机器人名称
        sed -i "s/^robot_type:.*/robot_type: $robot_type/" "$SETUP_FILE" || die "更新 robot_type 配置失败"
        # 运行版本
        sed -i "s/^device_server_type:.*/device_server_type: $device_server_type/" "$SETUP_FILE" || die "更新 device_server_type 配置失败"
        # 上传方式
        sed -i "s/^upload_type:.*/upload_type: $upload_type/" "$SETUP_FILE" || die "更新 upload_type 配置失败"
        # 数据集路径（替换为当前用户路径）
        sed -i "s|^device_data_path: /home/[^/]*/DoRobot/dataset/|device_data_path: /home/$CURRENT_USER/DoRobot/dataset/|" "$SETUP_FILE"
        
        # 验证数据集路径更新成功，失败则追加
        if grep -q "device_data_path: /home/$CURRENT_USER/DoRobot/dataset/" "$SETUP_FILE"; then
            echo "✅ dataset 路径已更新为：/home/$CURRENT_USER/DoRobot/dataset/"
        else
            echo "⚠️  未找到原有 dataset 路径格式，尝试追加配置到 setup.yaml"
            echo "device_data_path: /home/$CURRENT_USER/DoRobot/dataset/" >> "$SETUP_FILE" || die "追加 dataset 路径配置失败"
            echo "✅ dataset 路径已追加为：/home/$CURRENT_USER/DoRobot/dataset/"
        fi

        # 新增：检查并停止已有 robodriver_server 容器（避免端口/名称冲突）
        echo "检查是否存在已运行的 robodriver_server 容器..."
        if sudo docker ps -a --filter "name=^/robodriver_server$" --format "{{.Names}}" | grep -q "robodriver_server"; then
            echo "发现已有 robodriver_server 容器，正在停止并删除..."
            # 停止容器（忽略已停止的情况）
            sudo docker stop robodriver_server || echo "容器 robodriver_server 已处于停止状态"
            # 删除容器（确保彻底清理）
            sudo docker rm robodriver_server || die "删除已有 robodriver_server 容器失败，请手动执行：sudo docker rm robodriver_server"
        else
            echo "未发现 robodriver_server 容器，直接启动新容器..."
        fi

        # 2. 检查并清理 baai_flask_server 容器
        echo -e "\n检查是否存在名为 baai_flask_server 的容器..."
        if sudo docker ps -a --filter "name=^/baai_flask_server$" --format "{{.Names}}" | grep -q "baai_flask_server"; then
            echo "发现已有 baai_flask_server 容器，正在停止并删除..."
            # 停止容器（忽略停止失败，避免容器已退出的情况）
            sudo docker stop baai_flask_server || echo "容器 baai_flask_server 已停止"
            # 删除容器（确保彻底清理）
            sudo docker rm baai_flask_server || die "删除已有 baai_flask_server 容器失败，请手动执行：sudo docker rm baai_flask_server"
        else
            echo "未发现 baai_flask_server 容器"
        fi

        # 创建数据集目录（避免启动时目录不存在）
        echo "正在创建数据集存储目录..."
        mkdir -p "/home/$CURRENT_USER/DoRobot/dataset/" || die "创建数据集目录 /home/$CURRENT_USER/DoRobot/dataset/ 失败"

        # 启动服务
        echo "正在启动后端服务容器..."
        bash start_server_docker.sh || die "启动后端服务失败，请检查 start_server_docker.sh 脚本或容器日志"
        echo "✅ 后端服务容器启动成功！"
    else
        echo "警告: 后端服务目录 $BACKEND_DIR/$BACKEND_ARCH_DIR 不存在，跳过服务启动"
    fi
else
    echo "您选择不安装 Docker，需手动启动服务（开发者模式）..."
    if [ -d "$BACKEND_DIR/$BACKEND_ARCH_DIR" ]; then
        cd "$BACKEND_DIR/$BACKEND_ARCH_DIR" || die "无法进入后端服务目录 $BACKEND_DIR/$BACKEND_ARCH_DIR"

        # 检查配置文件是否存在
        if [ ! -f "$SETUP_FILE" ]; then
            die "错误: setup.yaml 配置文件不存在于 $SETUP_FILE，请确保代码部署完整"
        fi
        # 选择上传方式（nas/ks3）
        while true; do
            read -p "请选择数据上传方式（支持 nas/ks3）: " upload_type
            if [ "$upload_type" = "nas" ] || [ "$upload_type" = "ks3" ]; then
                break
            else
                echo "无效输入！仅支持 nas 或 ks3，请重新输入"
            fi
        done

        # 更新配置文件
        echo "正在更新 setup.yaml 配置文件..."
        sed -i "s/^robot_type:.*/robot_type: $robot_type/" "$SETUP_FILE" || die "更新 robot_type 配置失败"
        sed -i "s/^device_server_type:.*/device_server_type: $device_server_type/" "$SETUP_FILE" || die "更新 device_server_type 配置失败"
        sed -i "s/^upload_type:.*/upload_type: $upload_type/" "$SETUP_FILE" || die "更新 upload_type 配置失败"
    else
        echo "警告: 后端服务目录 $BACKEND_DIR/$BACKEND_ARCH_DIR 不存在，跳过服务启动"
    fi
fi

# ====================== 步骤11: 开机后操作（优化提示信息，补充关键信息） ======================
echo -e "\n======================"
echo "步骤11: 开机后操作指引（开发者模式）..."

# 最终提示（区分 Docker 模式和手动模式）
if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo -e "\n⚠️  重要提示："
    echo "请按当前版本安装对应机器控制程序 Robodriver 后再开始采集"
    echo "🌐 采集平台访问地址: $TEST_ACCESS_URL"
else
    echo -e "\n⚠️  重要提示："
    echo "1. 您未安装 Docker，需按readme中 '手动启动服务步骤' 部署运行环境"
    echo "2. 运行版本：$device_server_type，上传方式：$upload_type"
    echo "3. 请按当前版本安装对应机器控制程序 Robodriver 后再开始采集"
    echo "🌐 采集平台访问地址: $TEST_ACCESS_URL"
fi