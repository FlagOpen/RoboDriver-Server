# 🎉 欢迎安装 RoboDriver-Server 及配套服务！
<p align="center">
  <img src="ui/robodriver_struct_1.png" alt="RoboDriver 架构图" width="70%"/>
</p>

为快速部署并使用 RoboDriver-Server，以下为 **外部使用者**提供专属部署指南，**智源研究院内部开发者**请切换到baai分支，按需选择操作即可高效完成配置：

---

## 👤 外部使用者部署指南
具身一体化平台：https://roboxstudio.baai.ac.cn/

### 🚀 核心部署流程
#### 1. 克隆源码仓库, 执行一键安装脚本
首先拉取 RoboDriver-Server 源码至本地：
```bash
git clone https://github.com/FlagOpen/RoboDriver-Server.git
cd ./RoboDriver-Server
git checkout main
cd ./setup
bash setup.bash
```

#### 2. 跟随脚本完成关键配置
运行脚本后，按提示完成 4 项核心操作，其余步骤将自动执行：
1. 输入机器人类型（支持 aloha/pika/realman 等预定义类型，也可自定义）；
2. 确认或输入当前用户名（将自动同步到数据集存储路径 `/home/$CURRENT_USER/DoRobot/dataset/`）；
3. 选择是否安装 Docker：
   - 安装 Docker：选择从 Docker Hub 拉取镜像，并启动 RoboDriver-Server 容器；
   - 不安装 Docker：需后续手动完成运行环境部署（详见下方「环境部署」步骤）；
4. 注意：RoboDriver-Server 源码默认存放于 `/opt/` 目录，项目目录结构如下：
```
├── arm/                # arm架构相关文件
│   ├── docker/         # Docker配置目录
│   ├── environment.yml # 环境配置文件
│   ├── requirements.txt # 依赖清单
│   ├── setup.yaml      # 服务配置文件
│   ├── start_server_docker.sh # 容器启动脚本
│   └── operating_platform_server_test.py # 服务启动入口
├── logtail/            # 日志相关配置
├── setup/              # 安装脚本目录
├── ui/                 # 前端相关资源
├── update/             # 版本更新工具
└── x86/                # x86架构相关文件（结构同arm目录）
```

#### 3. 访问采集平台
安装完成后，通过以下地址直接访问本地采集平台：
```
http://localhost:5805/hmi/
```

### ❌ 常见问题排查
1. 若RoboDriver提示 `127.0.0.1:8088` 连接失败：RoboDriver-Server 服务未启动，需重新执行启动命令；
2. 访问 `http://localhost:5805/hmi/` 失败：重启 Nginx 服务，命令：
   ```bash
   sudo systemctl restart nginx
   ```
   or
   ```
    sudo systemctl start nginx
   ```
3. 数据集路径权限问题：重新设置目录权限：
   ```bash
   sudo chown -R $USER:$USER /home/$CURRENT_USER/DoRobot/dataset/
   sudo chmod -R 777 /home/$CURRENT_USER/DoRobot/dataset/
   ```

### 🛠️ 补充操作指南
#### （一）非 Docker 环境部署（未安装 Docker 时）
若选择不安装 Docker，需手动部署运行环境，步骤如下：
1. 基于 Conda 创建并激活虚拟环境（支持 Python 3.10/3.11）：
   ```bash
   conda create -n robodriverserver python=3.11  # 以Python 3.11为例
   conda activate robodriverserver
   ```
2. 进入对应架构的服务目录：
   ```bash
   # x86架构
   cd /opt/RoboDriver-Server/x86/
   ```
   ```
   # 或 arm架构
   cd /opt/RoboDriver-Server/arm/
   ```
3. 安装依赖并启动服务：
   ```bash
   pip install -r requirements.txt  # 安装Python依赖
   python operating_platform_server_test.py  # 启动RoboDriver-Server
   ```

#### （二）容器调试操作（Docker 部署时）
若通过一键容器部署，需调试服务可按以下步骤操作：
1. 查看并停止当前容器：
   ```bash
   docker ps -a  # 查看容器状态（容器名：robodriver_server）
   docker stop robodriver_server && docker rm robodriver_server  # 停止并删除容器
   ```
2. 进入对应架构目录，启动调试容器：
   ```bash
   # x86架构
   cd /opt/RoboDriver-Server/x86/
   ```
   ```
   # 或 arm架构
   cd /opt/RoboDriver-Server/arm/
   ```
   ```
   bash debug_server_docker.sh  # 启动调试容器并进入
   ```
3. 容器内启动服务并查看日志：
   ```bash
   python operating_platform_server_test.py  # 查看服务实时输出
   ```
4. 调试完成后退出并重启正式服务：
   ```bash
   exit  # 退出调试容器（按提示选择N删除容器）
   ```
   ```
   bash start_server_docker.sh  # 重启正式服务容器
   ```
5. 日志查看路径：`/opt/RoboDriver-log/log/server/`

#### （三）上传配置与 GPU 编码说明
采集数据的上传规则与视频编码可通过 `setup.yaml` 配置，核心参数说明如下：
```yaml
# 机器人类型配置
robot_type: franka  # 已通过脚本自动设置，可手动修改
# 服务端地址配置
device_server_ip: http://localhost:8088 # 本地服务地址配置
device_server_port: 8088  # 端口号
# 上传开关与模式
is_upload: True  # 是否开启自动上传
upload_immadiately_gpu: False  # 开启GPU实时编码上传（需NVIDIA显卡）
is_collect_upload_at_sametime: False  # 采集与上传异步执行（默认False,开启GPU实时编码上传时，需改成True）
# 上传类型与时间（外部用户仅支持ks3）
upload_type: ks3  # 固定为ks3，无需修改
upload_time: '20:00'  # 定时上传时间（仅is_upload=True时生效）
```

1. 当RoboDriver `use_video=False` 时，采集的相机数据将以图片形式存储；触发上传操作后，系统会自动将图片编码为视频文件，并存入指定的 `video` 目录。

2. 若需实现**采集、编码、上传同步完成**（实时处理流程），需同时满足以下所有条件：
   - **硬件要求**：主机必须配备 NVIDIA 显卡（需支持 NVENC 视频编码功能，主流 Kepler 架构及以上显卡均支持）；
   - **依赖安装**：需在主机安装 NVIDIA 容器运行时依赖 `nvidia-container-runtime`；
     - 安装方式（Ubuntu 系统示例）：
       1. 配置 NVIDIA 软件源：
          ```bash
          distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
          curl -s -L https://nvidia.github.io/nvidia-container-runtime/$distribution/nvidia-container-runtime.list | sudo tee /etc/apt/sources.list.d/nvidia-container-runtime.list
          ```
       2. 更新并安装：
          ```bash
          sudo apt update && sudo apt install -y nvidia-container-runtime
          ```
       3. 重启 Docker 服务使配置生效：
          ```bash
          sudo systemctl restart docker
          ```
   - **配置要求**：在配置文件中设置 `upload_immadiately_gpu: True` **并且** `is_collect_upload_at_sametime: True`；
   - **启动方式**：通过 `start_server_docker_gpu.sh` 脚本启动容器；
   - **关键配置修正**：`start_server_docker_gpu.sh` 脚本中存在 NVIDIA 编码库的挂载配置，需根据主机实际安装的 NVIDIA 驱动版本修改文件路径中的版本号：
      - 原始配置示例：
         ```bash
         -v /usr/lib/x86_64-linux-gnu/libnvidia-encode.so.535.230.02:/usr/lib/x86_64-linux-gnu/libnvidia-encode.so.1 \
         ```
      - 修改说明：将路径中的 `535.230.02` 替换为主机实际的 NVIDIA 驱动对应版本号（需确保主机 `/usr/lib/x86_64-linux-gnu/` 目录下存在 `libnvidia-encode.so.XXX.XX` 格式的文件）；
      - 版本查询方法：在主机终端执行命令 `nvidia-smi`，输出结果中「Driver Version」字段对应的数值即为需替换的版本号（例如驱动版本为 550.54.14，则替换为 `libnvidia-encode.so.550.54.14`）。

      - **补充说明**
      - 若未安装 `nvidia-container-runtime`，容器将无法识别主机 GPU 及挂载的编码库，同步处理流程会直接失效，需优先完成该依赖安装；
      - 若未正确匹配 NVIDIA 驱动版本号，会导致容器内无法加载 `libnvidia-encode.so.1` 编码库，进而出现编码失败、程序报错或同步流程卡死；
      - 若主机无 NVIDIA 显卡、不支持 NVENC 编码，或未按上述要求安装依赖/配置/启动，将无法使用同步处理流程，仅支持「先采集图片→触发上传时编码视频」的异步模式（即 `use_video=False` 对应的基础功能）；

---