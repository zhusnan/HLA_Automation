#!/bin/bash
# ===============================
# hlahd_analysis.sh
# 用于执行 HLHAD 分析流程
# ===============================

# --- 1. 激活 conda 环境 ---
# 根据你的 conda 安装路径调整下面的 source 语句
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
else
    echo "未找到 conda 配置文件，请检查 conda 安装路径。"
    exit 1
fi

conda activate hlahd
if [ $? -ne 0 ]; then
    echo "无法激活名为 'hlahd' 的 conda 环境，请检查环境名称或安装情况。"
    exit 1
fi

# --- 3. 动态设置输入目录 ---
# 获取 /home/huben/hlahd.1.7.0/sample 下的唯一子目录作为输入目录
input_dir=$(find /home/huben/hlahd.1.7.0/sample -maxdepth 1 -mindepth 1 -type d)

if [ -z "$input_dir" ]; then
    echo "在 /home/huben/hlahd.1.7.0/sample 中未找到子目录，退出程序。"
    exit 1
fi

# 输出输入目录
echo "找到输入目录: ${input_dir}"

# --- 4. 创建结果输出目录 ---
result_dir="${input_dir}/result"
mkdir -p "$result_dir"

echo "当前工作目录: $(pwd)"
echo "输入目录: ${input_dir}"
echo "结果目录: ${result_dir}"

# --- 5. 遍历每个样本文件夹 ---
# 遍历 input_dir 下所有以 Sample_ 开头的文件夹
for sample_dir in "${input_dir}"/Sample_*; do
    if [ -d "$sample_dir" ]; then
        # 获取样本名称（例如 Sample_JZ25020604-009C250124-009C25012401）
        sample_name=$(basename "$sample_dir")
        # 去除前缀 "Sample_" 得到样本 ID
        sample_id="${sample_name#Sample_}"

        # 构造 fastq 文件路径
        file_r1="${sample_dir}/${sample_id}_subset_R1.fastq"
        file_r2="${sample_dir}/${sample_id}_subset_R2.fastq"

        if [ ! -f "$file_r1" ] || [ ! -f "$file_r2" ]; then
            echo "样本 ${sample_id} 对应的文件未找到："
            echo "  ${file_r1}"
            echo "  ${file_r2}"
            echo "跳过该样本。"
            continue
        fi

        echo "正在处理样本: ${sample_id}"
        echo "  R1 文件: ${file_r1}"
        echo "  R2 文件: ${file_r2}"

        # 调用 /home/huben/hlahd.1.7.0/hlahd.sh 脚本进行分析
        # 绝对路径来确保正确调用
        /home/huben/hlahd.1.7.0/bin/hlahd.sh -t 130 -m 100 -c 0.95 -f freq_data/ \
            "$file_r1" "$file_r2" \
            /home/huben/hlahd.1.7.0/HLA_gene.split.txt /home/huben/hlahd.1.7.0/dictionary/ \
            "$sample_id" "$result_dir/"
    else
        echo "${sample_dir} 不是一个目录，跳过。"
    fi
done
cd /home/huben/hlahd.1.7.0/onepotscript
