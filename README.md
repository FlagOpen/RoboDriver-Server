# 🚀 一键安装脚本仓库

**一键部署RoboDriver-Server所需的基础软件和服务，简化外部使用者和智源院内开发者的安装流程。**

---

## 📁 仓库目录结构

```bash
├── setup/developer/          # 院内开发者专用脚本和配置
│   ├── baai_server_ceshi.conf    # 测试环境服务器配置
│   ├── baai_server_demo.conf    # demo环境服务器配置
│   ├── baai_server_release.conf # 生产环境服务器配置
│   ├── developer_x86_setup.bash # 开发者版 x86 架构一键安装脚本
│   └── developer_arm_setup.bash # 开发者版 arm 架构一键安装脚本

├── setup/user/                # 使用者专用脚本和配置
│   ├── baai_server_release.conf # 生产环境服务器配置
│   ├── user_x86_setup.bash # 使用者 x86 架构一键安装脚本
│   └── user_arm_setup.bash # 使用者 arm 架构一键安装脚本
└── README.md            # 本说明文件
```
---

### 🛠️ 使用者（用户）安装指南
```bash
git clone https://github.com/FlagOpen/RoboDriver-Server.git
cd RoboDriver-Server/setup/user/
```
```
bash ./user_x86_setup.bash 
```
or
```
bash ./user_arm_setup.bash
```

### 访问真机采集平台地址
- 本地采集平台：`http://localhost:5805/hmi/`；

### ❌ 问题排查
1. 数据集路径权限问题：重新设置目录权限（脚本已自动配置，异常时手动执行）：
   ```bash
   sudo chown -R $USER:$USER /home/$CURRENT_USER/DoRobot/dataset/
   sudo chmod -R 777 /home/$CURRENT_USER/DoRobot/dataset/
   ```
2. 提示 `127.0.0.1:8088` 连接失败：RoboDriver-Server 服务未启动，需重新执行启动命令；
3. 访问 `http://localhost:5805/hmi` 失败：重启 Nginx 服务，命令：
   ```bash
   sudo systemctl restart nginx
   ```
   or
   ```bash
   sudo systemctl start nginx
   ```

## 🛠️ 院内开发者安装指南
```bash
git clone https://github.com/FlagOpen/RoboDriver-Server.git
cd RoboDriver-Server/setup/developer/
```
```
bash ./developer_x86_setup.bash
```
or
```
bash ./developer_arm_setup.bash
```
## 🛠️ 开发者切换服务版本指南
```bash
# 1. 进入工作目录
cd /opt/RoboDriver-Server/x86/
or
cd /opt/RoboDriver-Server/arm/
 
# 2. 停止 Docker 容器（确保无冲突）
sudo docker stop baai_flask_server
 
# 3. 修改配置文件（选择 dev 或 release 模式）
#    - 使用 gedit 编辑 setup.yaml，修改 device_server_type 的值
#    - 示例（手动操作）：
#       device_server_type: dev   # 开发模式
#       或
#       device_server_type: release  # 发布模式
sudo gedit setup.yaml
 
# 4. 重启容器使配置生效
sudo docker restart baai_flask_server
```
