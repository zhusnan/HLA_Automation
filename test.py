#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import io
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# =============================
# 第一部分：确定输入文件路径
# =============================

# 基础目录（根据你原来的脚本）
BASE_SAMPLE_DIR = "/home/huben/hlahd.1.7.0/sample"

# 找到包含 '-' 的目录
download_folders = [d for d in os.listdir(BASE_SAMPLE_DIR)
                    if os.path.isdir(os.path.join(BASE_SAMPLE_DIR, d)) and "-" in d]

if not download_folders:
    print("未找到符合格式的下载文件夹！")
    sys.exit(1)

# 选择第一个符合条件的目录，并解析名称获取 excel_base
download_folder = os.path.join(BASE_SAMPLE_DIR, download_folders[0])
folder_parts = os.path.basename(download_folder).split("-")
if len(folder_parts) < 2:
    print("下载文件夹名称格式异常！")
    sys.exit(1)
excel_base = folder_parts[1]

# summary_seal PDF（你上一个脚本生成的文件）
summary_pdf_path = os.path.join(BASE_SAMPLE_DIR, excel_base + "_summary_seal.pdf")
if not os.path.exists(summary_pdf_path):
    print(f"未找到 summary_seal PDF 文件：{summary_pdf_path}")
    sys.exit(1)

# 模板 PDF 路径
template_pdf_path = "/home/huben/hlahd.1.7.0/sample_info/HLA-typing.pdf"
if not os.path.exists(template_pdf_path):
    print(f"未找到模板 PDF 文件：{template_pdf_path}")
    sys.exit(1)

# 合并后生成的最终 PDF 路径
final_pdf_path = os.path.join(BASE_SAMPLE_DIR, excel_base + "_final.pdf")

# ============================================
# 第二部分：读取PDF、调整页面尺寸并合并
# ============================================

def adjust_page_size(page, target_width, target_height):
    """
    尝试将 page 调整到目标尺寸（target_width x target_height）。
    如果当前页面尺寸与目标一致，则直接返回。
    否则尝试调用 scale_to()（新版 PyPDF2 支持），如果不可用则用 scale_by() 近似缩放。
    """
    current_width = float(page.mediabox.width)
    current_height = float(page.mediabox.height)
    if current_width == target_width and current_height == target_height:
        return page

    # 计算缩放因子（这里取横向和纵向的比例，可能会导致内容边缘有空白）
    scale_x = target_width / current_width
    scale_y = target_height / current_height

    try:
        # 新版本 PyPDF2 提供 scale_to 方法，直接调整页面尺寸
        page.scale_to(target_width, target_height)
    except AttributeError:
        # 如果没有 scale_to 方法，则选择按比例缩放（取较小因子，以保证整个内容能显示在目标页面内）
        factor = min(scale_x, scale_y)
        page.scale_by(factor)
    return page

def create_footer_overlay(page_width, page_height, current_page, total_pages):
    """
    利用 ReportLab 动态生成一个 PDF 页面，页面尺寸为 page_width x page_height，
    并在底部居中绘制页脚文本：本次报告仅供科研使用    页码 current_page/total_pages
    返回生成的 PDF 页作为 PyPDF2 的 PageObject，用于后续覆盖合并。
    """
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    footer_text = f"本次报告仅供科研使用    页码 {current_page}/{total_pages}"
    c.setFont("Helvetica", 10)
    text_width = c.stringWidth(footer_text, "Helvetica", 10)
    x = (page_width - text_width) / 2
    y = 20  # 距离页面底部 20 points
    c.drawString(x, y, footer_text)
    c.save()
    packet.seek(0)
    watermark_pdf = PdfReader(packet)
    watermark_page = watermark_pdf.pages[0]
    return watermark_page

# 使用 PdfReader 读取两个 PDF 文件
reader_template = PdfReader(template_pdf_path)
reader_summary = PdfReader(summary_pdf_path)
writer = PdfWriter()

# 以模板 PDF 第一页的尺寸作为目标页面尺寸
first_template_page = reader_template.pages[0]
target_width = float(first_template_page.mediabox.width)
target_height = float(first_template_page.mediabox.height)

# 处理模板 PDF 的每一页
for page in reader_template.pages:
    adjusted_page = adjust_page_size(page, target_width, target_height)
    writer.add_page(adjusted_page)

# 处理 summary_seal PDF 的每一页
for page in reader_summary.pages:
    adjusted_page = adjust_page_size(page, target_width, target_height)
    writer.add_page(adjusted_page)

# ----------------------------
# 添加页脚：本次报告仅供科研使用    页码 x/n
# ----------------------------
total_pages = len(writer.pages)
for i, page in enumerate(writer.pages):
    watermark_page = create_footer_overlay(target_width, target_height, i + 1, total_pages)
    page.merge_page(watermark_page)

# 将合并后的 PDF 写入 final_pdf_path
with open(final_pdf_path, "wb") as out_file:
    writer.write(out_file)

print(f"合并后的PDF已保存为: {final_pdf_path}")
