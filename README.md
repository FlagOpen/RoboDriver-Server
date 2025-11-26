# 🚀 一键安装脚本仓库

**一键部署RoboDriver-Server所需的基础软件和服务，简化开发者和用户的安装流程。**

---

## 📁 仓库目录结构

```bash
├── setup/developer/          # 开发者专用脚本和配置
│   ├── baai_server_ceshi.conf    # 测试环境服务器配置
│   ├── baai_server_demo.conf    # demo环境服务器配置
│   ├── baai_server_release.conf # 生产环境服务器配置
│   ├── developer_x86_setup.bash # 开发者版 x86 架构一键安装脚本
│   └── developer_arm_setup.bash # 开发者版 arm 架构一键安装脚本
├── setup/user/                # 用户专用脚本和配置
│   ├── baai_server_release.conf # 生产环境服务器配置
│   ├── user_x86_setup.bash # 用户版 x86 架构一键安装脚本
│   └── user_arm_setup.bash # 用户版 arm 架构一键安装脚本
└── README.md            # 本说明文件
```
---

## 🛠️ 用户安装指南
```bash
git clone git@github.com:FlagOpen/RoboDriver-Server.git
cd RoboDriver-Server/setup/user/
./user_x86_setup.bash 
or
./user_arm_setup.bash
```
---
## 🛠️ 开发者安装指南
```bash
git clone git@github.com:FlagOpen/RoboDriver-Server.git
cd RoboDriver-Server/setup/developer/
./developer_x86_setup.bash
or
./developer_arm_setup.bash
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




