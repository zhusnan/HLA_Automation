#!/bin/bash
# run_combine.sh
# 这个脚本用于激活 conda 环境 huben 后运行 combine.py

# 根据你的 conda 安装位置调整下面的 source 语句
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
else
    echo "未找到 conda 配置文件，请检查 conda 安装路径。"
    exit 1
fi

# 激活 conda 环境 huben
conda activate huben
if [ $? -ne 0 ]; then
    echo "无法激活 conda 环境 huben，请检查环境名称。"
    exit 1
fi

# 运行 combine.py
cd /home/huben/hlahd.1.7.0/onepotscript
python3 combine.py
