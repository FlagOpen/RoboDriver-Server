# ====================== 步骤11: 测试启动服务（仅Docker模式） ======================
if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo -e "\n======================"
    echo "步骤11: 测试启动服务（运行版本：$device_server_type，上传方式：$upload_type）..."
    if [ -d "$BACKEND_DIR/$BACKEND_ARCH_DIR" ]; then
        cd "$BACKEND_DIR/$BACKEND_ARCH_DIR" || die "无法进入后端服务目录"
        echo "配置后台服务..."
        # 定义配置文件路径
        SETUP_FILE="$BACKEND_DIR/$BACKEND_ARCH_DIR/setup.yaml"
        # 检查配置文件是否存在
        if [ ! -f "$SETUP_FILE" ]; then
            die "错误: setup.yaml 配置文件不存在于 $SETUP_FILE"
        fi
        # 更新配置文件（机器人名称、运行版本、上传方式、数据集路径）
        echo "正在更新配置文件..."
        sed -i "s/^robot_type:.*/robot_type: $robot_type/" "$SETUP_FILE"
        sed -i "s/^device_server_type:.*/device_server_type: $device_server_type/" "$SETUP_FILE"
        sed -i "s/^upload_type:.*/upload_type: $upload_type/" "$SETUP_FILE"
        sed -i "s|^device_data_path: /home/[^/]*/DoRobot/dataset/|device_data_path: /home/$CURRENT_USER/DoRobot/dataset/|" "$SETUP_FILE"
        # 验证数据集路径更新成功
        if grep -q "device_data_path: /home/$CURRENT_USER/DoRobot/dataset/" "$SETUP_FILE"; then
            echo "dataset 路径已更新为：/home/$CURRENT_USER/DoRobot/dataset/"
        else
            echo "警告：未找到原有 dataset 路径格式，尝试追加配置..."
            echo "device_data_path: /home/$CURRENT_USER/DoRobot/dataset/" >> "$SETUP_FILE"
        fi
        
        # 新增：检查并停止已有 robodriver_server 容器
        echo "检查是否存在名为 robodriver_server 的容器..."
        if sudo docker ps -a --filter "name=^/robodriver_server$" --format "{{.Names}}" | grep -q "robodriver_server"; then
            echo "发现已有 robodriver_server 容器，正在停止并删除..."
            # 停止容器（忽略停止失败，避免容器已退出的情况）
            sudo docker stop robodriver_server || echo "容器 robodriver_server 已停止"
            # 删除容器（确保彻底清理）
            sudo docker rm robodriver_server || die "删除已有 robodriver_server 容器失败，请手动执行：sudo docker rm robodriver_server"
        else
            echo "未发现 robodriver_server 容器，直接启动新容器..."
        fi
        
        # 启动服务
        bash start_server_docker.sh || die "启动后端服务失败"
    else
        echo "警告: 后端服务目录 $BACKEND_DIR/$BACKEND_ARCH_DIR 不存在，跳过启动"
    fi
else
    echo -e "\n======================"
    echo "步骤11: 您选择不安装 Docker，跳过服务容器启动步骤"
fi