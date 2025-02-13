#!/usr/bin/env python3
import os
import glob
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
from reportlab.lib import colors

# ---------------------
# 参数设置
BASE_SAMPLE_DIR = "/home/huben/hlahd.1.7.0/sample"
SAMPLE_INFO_FILE = "/home/huben/hlahd.1.7.0/sample_info/sample_info.xlsx"
WORD_TEMPLATE = "/home/huben/hlahd.1.7.0/sample_info/HLA-typing.docx"  # 当前未使用
# 后期可以调整修改
GENES = ["A", "B", "C", "DQB1", "DRB1", "DPB1"]


def find_download_folder(base_dir):
    """
    在 base_dir 下寻找下载文件夹（排除特定名称的目录），返回找到的第一个目录
    """
    for item in os.listdir(base_dir):
        full_path = os.path.join(base_dir, item)
        if os.path.isdir(full_path) and item not in ["result"] and not item.endswith(".pdf") and not item.endswith(
                ".xlsx"):
            return full_path
    return None


def extract_hla_from_file(result_file_path):
    """
    解析最终结果文本文件，返回一个字典，键为基因（例如 "A"），值为等位基因串。
    若第二列为 "-"，则复制第一列。去除 "HLA-<gene>*" 前缀，仅保留等位基因号（如 "02:01:01"）。
    """
    hla_data = {}
    with open(result_file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            gene = parts[0].strip()
            if gene not in GENES:
                continue
            allele1 = parts[1].strip()
            allele2 = parts[2].strip()
            if "*" in allele1:
                allele1 = allele1.split("*")[1]
            if "*" in allele2:
                allele2 = allele2.split("*")[1]
            if allele2 == "-":
                allele2 = allele1
            hla_data[gene] = f"{allele1},{allele2}"
    return hla_data


def generate_pdf(pdf_data_rows, pdf_path):
    """
    生成 PDF 报告，每页最多显示5个样本的信息。
    每个样本包含3个表格展示信息，页末添加页脚信息（Author、Reviewer、日期），然后换页（PageBreak）。
    """
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []
    max_per_page = 5  # 每页最多显示5个样本
    current_date = datetime.now().strftime("%Y-%m-%d")

    for i, pdf_row in enumerate(pdf_data_rows):
        # 每页的第一个样本不加 Spacer，其余样本之间加间隔
        if i % max_per_page != 0:
            elements.append(Spacer(1, 12))

        # 表格1：显示 Sample_ID（Donor_ID）
        data1 = [
            ["Sample_ID"],
            [pdf_row.get("Donor_ID", "")]
        ]
        table1 = Table(data1, colWidths=[450])
        style1 = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table1.setStyle(style1)
        elements.append(table1)

        # 表格2：显示 HLA-A, HLA-B, HLA-C
        data2 = [
            ["HLA-A", "HLA-B", "HLA-C"],
            [pdf_row.get("A", ""), pdf_row.get("B", ""), pdf_row.get("C", "")]
        ]
        table2 = Table(data2, colWidths=[150, 150, 150])
        style2 = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table2.setStyle(style2)
        elements.append(table2)

        # 表格3：显示 HLA-DQB1, HLA-DRB1, HLA-DPB1
        data3 = [
            ["HLA-DQB1", "HLA-DRB1", "HLA-DPB1"],
            [pdf_row.get("DQB1", ""), pdf_row.get("DRB1", ""), pdf_row.get("DPB1", "")]
        ]
        table3 = Table(data3, colWidths=[150, 150, 150])
        style3 = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table3.setStyle(style3)
        elements.append(table3)

        # 判断是否为本页最后一个样本或者最后一个样本总体，
        # 如果是，则在该页末尾添加页脚信息，再插入 PageBreak（如果后面还有内容）
        if (i + 1) % max_per_page == 0 or (i + 1) == len(pdf_data_rows):
            elements.append(Spacer(1, 20))
            footer_data = [
                ["Author: BoyuZhao", "Reviewer: LangCao", f"Date:{current_date}"]
            ]
            footer_table = Table(footer_data, colWidths=[180, 180, 180])
            style_footer = TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0, colors.white)
            ])
            footer_table.setStyle(style_footer)
            elements.append(footer_table)

            # 如果不是最后一页，则添加分页符
            if (i + 1) < len(pdf_data_rows):
                elements.append(PageBreak())

    doc.build(elements)


def main():
    # 1. 找到下载文件夹（例如 HBBIO-20250125-L-01-2025-01-281900）
    download_folder = find_download_folder(BASE_SAMPLE_DIR)
    if not download_folder:
        print("未在 {} 下找到下载文件夹！".format(BASE_SAMPLE_DIR))
        return
    print("下载文件夹：", download_folder)

    # 提取 Excel/Word 的基础名称：取下载文件夹名称中第二部分（例如 "20250125"）
    folder_parts = os.path.basename(download_folder).split("-")
    if len(folder_parts) < 2:
        print("下载文件夹名称格式异常！")
        return
    excel_base = folder_parts[1]
    excel_save_path = os.path.join(BASE_SAMPLE_DIR, excel_base + ".xlsx")

    result_dir = os.path.join(download_folder, "result")
    if not os.path.isdir(result_dir):
        print("结果目录 {} 不存在！".format(result_dir))
        return

    pdf_data_rows = []  # 用于汇总 Excel 与 PDF 的数据，每项为 dict
    sample_folders = [d for d in os.listdir(result_dir)
                      if os.path.isdir(os.path.join(result_dir, d)) and d.startswith("JZ")]

    # 逐个样本处理
    for sample_folder in sample_folders:
        sample_folder_full = os.path.join(result_dir, sample_folder)
        # 每个样本文件夹内部有一个 result 子目录，其中包含最终结果文件 *_final.result.txt
        inner_result_dir = os.path.join(sample_folder_full, "result")
        if not os.path.isdir(inner_result_dir):
            print("样本文件夹 {} 中未找到 result 子目录，跳过".format(sample_folder))
            continue
        txt_files = glob.glob(os.path.join(inner_result_dir, "*_final.result.txt"))
        if not txt_files:
            print("样本文件夹 {} 中未找到最终结果文件，跳过".format(sample_folder))
            continue
        final_result_file = txt_files[0]
        hla_dict = extract_hla_from_file(final_result_file)

        # 解析文件名以获取 Company 和样本标识
        base_txt_name = os.path.basename(final_result_file)
        parts = base_txt_name.split("-")
        if len(parts) < 3:
            print("文件名格式异常：", base_txt_name)
            continue
        company = parts[1]  # 例如 "009C250124"
        third_part = parts[2]
        sample_id_full = third_part.split("_")[0]  # 例如 "009C25012401"
        huben_str = sample_id_full[-2:]
        try:
            huben_val = int(huben_str)
        except Exception as e:
            print("无法转换 Huben 数值：", huben_str)
            continue

        # 读取 sample_info.xlsx
        try:
            sample_info_df = pd.read_excel(SAMPLE_INFO_FILE, engine='openpyxl')
        except Exception as e:
            print("读取 sample_info.xlsx 失败：", e)
            return

        # 在 sample_info.xlsx 中查找匹配记录：匹配 Company 和 Huben
        df_match = sample_info_df[(sample_info_df["Company"] == company) & (sample_info_df["Huben"] == huben_val)]
        if df_match.empty:
            print("未在 sample_info.xlsx 中找到 Company={} Huben={} 的记录，跳过".format(company, huben_val))
            continue
        record = df_match.iloc[0]
        donor_id = str(record["sample"]).strip()  # Donor_ID
        lot_number = str(record["lot"]).strip()  # LotNumber

        # 将 Huben 值也保存，便于后续排序（Excel 中不输出该字段）
        pdf_row = {
            "LotNumber": lot_number,
            "Donor_ID": donor_id,
            "A": hla_dict.get("A", ""),
            "B": hla_dict.get("B", ""),
            "C": hla_dict.get("C", ""),
            "DQB1": hla_dict.get("DQB1", ""),
            "DRB1": hla_dict.get("DRB1", ""),
            "DPB1": hla_dict.get("DPB1", ""),
            "Huben": huben_val
        }
        pdf_data_rows.append(pdf_row)

    if pdf_data_rows:
        # 按 Huben 排序，保证输出顺序与 sample_info.xlsx 中的顺序一致
        pdf_data_rows.sort(key=lambda x: x["Huben"])

        # 生成 Excel 汇总文件（不输出 Huben 字段）
        df_summary = pd.DataFrame(pdf_data_rows,
                                  columns=["LotNumber", "Donor_ID", "A", "B", "C", "DQB1", "DRB1", "DPB1"])
        df_summary.rename(columns={"A": "HLA-A", "B": "HLA-B", "C": "HLA-C",
                                   "DQB1": "HLA-DQB1", "DRB1": "HLA-DRB1", "DPB1": "HLA-DPB1"},
                          inplace=True)
        try:
            df_summary.to_excel(excel_save_path, index=False, engine='openpyxl')
            print("生成 Excel 汇总文件：", excel_save_path)
        except Exception as e:
            print("生成 Excel 文件失败：", e)

        # 生成汇总 PDF 文件（保存至 BASE_SAMPLE_DIR）
        pdf_file_path = os.path.join(BASE_SAMPLE_DIR, excel_base + "_summary.pdf")
        try:
            generate_pdf(pdf_data_rows, pdf_file_path)
            print("生成汇总 PDF 文件：", pdf_file_path)
        except Exception as e:
            print("生成 PDF 文件失败：", e)


if __name__ == "__main__":
    main()
