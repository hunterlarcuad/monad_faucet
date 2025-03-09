#!/bin/bash

file_hosts='deploy_hosts.txt'

# 检查是否有传入参数
if [ -n "$1" ]; then
    # 如果有参数，将第一个参数赋值给 file_hosts
    file_hosts="$1"
fi

FILE_TEMP_HOSTS='deploy_hosts_temp.txt'

# 判断传入的 file_hosts 文件是否存在
if [ -f "$file_hosts" ]; then
    echo "当前处理的文件是 $file_hosts"
else
    echo "传入的参数不是文件[$file_hosts]，作为单个 host 执行"
    FILE_TEMP_HOSTS="deploy_hosts_temp.txt.$file_hosts"
    echo $file_hosts > $FILE_TEMP_HOSTS
    file_hosts=$FILE_TEMP_HOSTS
fi

TOOLS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPT_DIR=$(dirname "$TOOLS_DIR")
cd $SCRIPT_DIR


echo "############################################################"
echo "Stop python 脚本"

for i in `cat $file_hosts`; do
    echo "===========" [Step 5] $i "===========";
    ssh $i "
        if ! screen -list | grep -qw monad_faucet; then
            echo 'Screen session monad_faucet not exist.';
        else
            echo 'Screen session monad_faucet already exists, kill, quit the session.';
            screen -S monad_faucet -X quit
        fi;
    ";
done

echo "Finish !"
