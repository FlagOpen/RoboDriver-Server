#!/bin/bash
sudo mkdir -p /opt/RoboDriver-log/
sudo chown -R $USER:$USER /opt/RoboDriver-log/
sudo chmod -R 777 /opt/RoboDriver-log/

sudo mkdir -p /etc/ilogtail/users
sudo touch /etc/ilogtail/users/1560822971114422
echo "robot-test-any" | sudo tee /etc/ilogtail/user_defined_id > /dev/null

wget http://aliyun-observability-release-cn-beijing.oss-cn-beijing.aliyuncs.com/loongcollector/linux64/latest/loongcollector.sh -O loongcollector.sh
chmod 755 loongcollector.sh
sudo ./loongcollector.sh install cn-beijing-internet
