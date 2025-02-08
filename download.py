#!/usr/bin/env python3
import os
import subprocess

def download_data(tos_code):
    """
    根据输入的 tos 码执行下载操作  
    如果用户输入的 tos 码已包含 "tos://", 则直接使用；否则添加前缀 "tos://skyseq-product-tos/"
    """
    # 判断是否已经包含 "tos://" 前缀
    if not tos_code.startswith("tos://"):
        tos_code = "tos://skyseq-product-tos/" + tos_code

    download_command = f"./tosutil cp -r -j 4 -p 12 -u {tos_code} /home/huben/hlahd.1.7.0/sample"
    
    # 切换到 tos 工具所在目录
    os.chdir("/home/huben/tos_tools")
    print("正在执行下载命令：")
    print(download_command)
    
    result = subprocess.run(download_command, shell=True)
    if result.returncode != 0:
        print("下载命令执行失败。")
        return False
    else:
        print("下载完成！")
        return True
