#!/bin/bash

# ====================== 配置参数（可修改） ======================
CONTAINER_NAME="baai_flask_server"      # 容器名称
IMAGE_NAME="baai-flask-server"  # 镜像名称
#PORTS="-p 8088:8088"                    # 端口映射
ENCODE="-e PYTHONIOENCODING=utf-8"
PORTS="--network host"
PRIVILEGED="--privileged=true"          # 特权模式（谨慎使用）
RESTART_POLICY="--restart unless-stopped" # 重启策略

# 动态获取当前用户名
CURRENT_USER=$(whoami)

# 动态构建卷挂载路径
VOLUMES="-v /home/${CURRENT_USER}/DoRobot/dataset/:/home/robot/dataset/"
VOLUMES2="-v /opt/RoboDriver-Server/arm/:/app/code/"
VOLUMES3="-v /opt/RoboDriver-log/:/home/machine/"

# ====================== 逻辑部分（增强版） ======================

# 检查容器是否存在
if sudo docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # 容器存在，检查是否正在运行
    if sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "容器 '${CONTAINER_NAME}' 正在运行。"
        
        # 询问用户是否要重启容器
        read -p "容器正在运行，是否要重启它？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "正在重启容器..."
            sudo docker restart ${CONTAINER_NAME}
        else
            echo "保持容器运行，不执行重启操作。"
        fi
    else
        # 容器存在但未运行，尝试启动
        echo "启动已存在的容器 '${CONTAINER_NAME}'..."
        sudo docker start ${CONTAINER_NAME}
    fi
else
    # 容器不存在，创建并运行
    echo "创建并启动新容器 '${CONTAINER_NAME}'..."
    sudo docker run -d \
        --name ${CONTAINER_NAME} \
        --gpus all \
        -e LANG=C.UTF-8 \
        -e LC_ALL=C.UTF-8 \
        -e NVIDIA_DRIVER_CAPABILITIES=all \
        -v /usr/lib/x86_64-linux-gnu/libnvidia-encode.so.535.230.02:/usr/lib/x86_64-linux-gnu/libnvidia-encode.so.1 \
        ${ENCODE} \
        ${PRIVILEGED} \
        ${RESTART_POLICY} \
        ${PORTS} \
        ${VOLUMES} \
        ${VOLUMES2} \
        ${VOLUMES3} \
        ${IMAGE_NAME}
fi

# 检查容器状态
echo -e "\n当前容器状态："
sudo docker ps -a --filter "name=${CONTAINER_NAME}" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# 检查日志（最后10行）
echo -e "\n容器日志（最近10行）："
sudo docker logs --tail 10 ${CONTAINER_NAME}

# 提示如何进入容器
echo -e "\n进入容器命令："
echo "sudo docker exec -it ${CONTAINER_NAME} bash"
