#!/bin/bash

file_hosts='deploy_hosts.txt'

# 检查是否有传入参数
if [ -n "$1" ]; then
    # 如果有参数，将第一个参数赋值给 file_hosts
    file_hosts="$1"
fi

FILE_TEMP_HOSTS='deploy_hosts.temp'

# 判断传入的 file_hosts 文件是否存在
if [ -f "$file_hosts" ]; then
    echo "当前处理的文件是 $file_hosts"
    echo "head $file_hosts"
    head $file_hosts
    wc -l $file_hosts
else
    echo "传入的参数不是文件[$file_hosts]，作为单个 host 执行"
    FILE_TEMP_HOSTS="deploy_hosts_$file_hosts.temp"
    echo $file_hosts > $FILE_TEMP_HOSTS
    file_hosts=$FILE_TEMP_HOSTS
fi

TOOLS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPT_DIR=$(dirname "$TOOLS_DIR")
cd $SCRIPT_DIR

echo "############################################################"
echo "Step 1 将文件拷贝到目标机器"
# for i in `cat $file_hosts` ; do echo "===========" [Step 1] $i "===========" ; rsync -auvzP $SCRIPT_DIR/ $i:~/monad_faucet/ ; done
for i in $(cat $file_hosts); do  
    echo "===========" [Step 1] $i "==========="  
    rsync -auvzP --exclude='.git/' --exclude='.gitignore' --exclude='.DS_Store' --exclude='README.md' --exclude='chrome_profile' --exclude='__pycache__'  --exclude='venv' --exclude='datas' --exclude='run.log' --exclude='tmp_img' --exclude='tools' --exclude='deploy_hosts_*' $SCRIPT_DIR/ $i:~/monad_faucet/
done

echo "############################################################"
echo "Step 2 安装 chrome"
for i in `cat $file_hosts`; do
    echo "===========" [Step 2] $i "===========";
    ssh $i "
        if ! dpkg -l | grep -qw google-chrome-stable; then
            if [ ! -f ~/monad_faucet/google-chrome-stable_current_amd64.deb ]; then
                echo 'Google Chrome deb package not found. Downloading...'
                mkdir -p ~/monad_faucet && cd ~/monad_faucet
                curl -O https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
            else
                echo 'Google Chrome deb package already exists.'
            fi
            sudo dpkg --configure -a;
            echo Y | sudo dpkg -i ~/monad_faucet/google-chrome-stable_current_amd64.deb;
            # Reinstall
            echo Y | sudo apt --fix-broken install;
            sudo dpkg --configure -a;
            echo Y | sudo dpkg -i ~/monad_faucet/google-chrome-stable_current_amd64.deb;
            # Remove the deb package after installation
            rm -f ~/monad_faucet/google-chrome-stable_current_amd64.deb
        else
            echo 'Google Chrome is already installed.';
        fi;
    ";
done


echo "############################################################"
echo "Step 3 安装 pip3"
for i in `cat $file_hosts`; do
    echo "===========" [Step 3] $i "===========";
    ssh $i "
        if ! dpkg -l | grep -qw python3-pip; then
            echo 'Installing python3-pip...';
            echo Y | sudo apt --fix-broken install
            echo Y | sudo apt install python3-pip;
            pip3 install --upgrade pip --break-system-packages;
            echo Y | sudo apt autoremove
        else
            echo 'python3-pip is already installed.';
        fi;
    ";
done

echo "############################################################"
echo "Step 4 安装 requirements 列表中的包"
for i in `cat $file_hosts`; do
    echo "===========" [Step 4] $i "===========";
    ssh $i "
        pip3 install -r monad_faucet/requirements.txt --break-system-packages --no-warn-script-location;
    ";
done

if [ -f "$FILE_TEMP_HOSTS" ]; then
    rm -f $FILE_TEMP_HOSTS
fi

echo "Deploy finished !"
