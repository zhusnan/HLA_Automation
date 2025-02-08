#!/usr/bin/env python3
import download
import fastq_processor
import subprocess
import sys
import os

def main():
    # ---------------- 下载模块 ----------------
    tos_code = input("请输入完整的tos码（例如：tos://skyseq-product-tos/0012v00002Df9dbAAB/HBBIO-20250125-L-01-2025-01-281900）：").strip()
    if not download.download_data(tos_code):
        print("下载失败，程序退出。")
        return

    # ---------------- FASTQ 文件处理模块 ----------------
    # 固定目标文件大小为 300 MB，不再提示用户输入
    target_mb = 300
    print("大小设为 300 MB")
    fastq_processor.process_fastq_files(target_mb)

    # ---------------- HLHAD 分析模块 ----------------
    print("正在运行 HLHAD  ...")
    result = subprocess.run(["/home/huben/hlahd.1.7.0/onepotscript/hlahd_analysis.sh"], shell=True)
    if result.returncode != 0:
        print("hlahd_analysis.sh 执行失败，退出码：", result.returncode)
        sys.exit(result.returncode)
    print("hlahd_analysis.sh 执行成功。")

    # ---------------- 报告生成模块 ----------------
    print("PDF报告生成中...")
    result = subprocess.run(["/home/huben/hlahd.1.7.0/onepotscript/run_pdf-excle-combine_date.sh"], shell=True)
    if result.returncode != 0:
        print("run_pdf-excle-combine_date.sh失败，退出码：", result.returncode)
        sys.exit(result.returncode)
    print("成功")

    # ---------------- 盖章 ----------------
    print("盖章中...")
    result = subprocess.run(["/home/huben/hlahd.1.7.0/onepotscript/run_sealadd.sh"], shell=True)
    if result.returncode != 0:
        print("run_sealadd.sh失败，退出码：", result.returncode)
        sys.exit(result.returncode)
    print("盖章成功")


if __name__ == "__main__":
    main()
