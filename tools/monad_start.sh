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
echo "准备 purse address ..."
PATH_DATAS="$SCRIPT_DIR/datas"
PATH_PURSE="$PATH_DATAS/purse"
PATH_STATUS="$PATH_DATAS/status"

for i in `cat $file_hosts`; do
    echo "===========" [Step 5] $i "===========";
    FILE_PURSE="$PATH_PURSE/purse_$i.csv"
    FILE_STATUS="$PATH_STATUS/status_$i.csv"

    ssh $i "
        mkdir -p ~/monad_faucet/datas/purse
        mkdir -p ~/monad_faucet/datas/status
    ";

    if [ ! -f $FILE_PURSE ]; then
        echo 'Error! Purse file is not exist. Exit !'
        exit 1
    else
        echo "FILE_PURSE: $FILE_PURSE"
        cat $FILE_PURSE
        rsync -avuzP $FILE_PURSE $i:~/monad_faucet/datas/purse/purse.csv
    fi
    if [ ! -f $FILE_STATUS ]; then
        echo 'Warning! Status file is not exist.'
        # exit 1
    else
        echo "FILE_STATUS: $FILE_STATUS"
        cat $FILE_STATUS
        rsync -avuzP $FILE_STATUS $i:~/monad_faucet/datas/status/status.csv
    fi
done

echo "############################################################"
echo "启动 python 脚本"

for i in `cat $file_hosts`; do
    echo "===========" [Step 5] $i "===========";
    ssh $i "
        if ! screen -list | grep -qw monad_faucet; then
            echo 'Screen session monad_faucet not exist.';
        else
            echo 'Screen session monad_faucet already exists, kill, quit the session.';
            screen -S monad_faucet -X quit
            sleep 3
        fi;
        echo 'Creating new screen session for monad_faucet...';
        screen -dmS monad_faucet || { echo 'Failed to create screen session.'; exit 1; }
        screen -S monad_faucet -X stuff \"cd monad_faucet/ && python3 monad_faucet.py --sleep_sec_min=600 --sleep_sec_max=1800 --loop_interval=60\n\" || { echo 'Failed to send commands to screen session.'; exit 1; }
    ";
done

if [ -f "$FILE_TEMP_HOSTS" ]; then
    rm -f $FILE_TEMP_HOSTS
fi

echo "Finish !"
