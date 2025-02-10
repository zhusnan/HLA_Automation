import os
from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
from datetime import datetime

# 设置路径
SEAL_IMAGE_PATH = "/home/huben/hlahd.1.7.0/sample_info/seal_red.png"
BASE_SAMPLE_DIR = "/home/huben/hlahd.1.7.0/sample"
download_folders = [d for d in os.listdir(BASE_SAMPLE_DIR) 
                    if os.path.isdir(os.path.join(BASE_SAMPLE_DIR, d))]
                    
# 如果需要进一步确保目录名称中包含 '-'，可以再过滤：
download_folders = [d for d in download_folders if "-" in d]

if not download_folders:
    print("未找到符合格式的下载文件夹！")
    exit(1)

# 选择第一个符合条件的目录
download_folder = os.path.join(BASE_SAMPLE_DIR, download_folders[0])
folder_parts = os.path.basename(download_folder).split("-")
if len(folder_parts) < 2:
    print("下载文件夹名称格式异常！")
    exit(1)
excel_base = folder_parts[1]
PDF_FILE_PATH = os.path.join(BASE_SAMPLE_DIR, excel_base + "_summary.pdf")
OUTPUT_PDF_PATH = os.path.join(BASE_SAMPLE_DIR, excel_base + "_summary_seal.pdf")


# 1. 将 PDF 转换为图像，明确指定 DPI（例如200）
def pdf_to_image(pdf_path, dpi=200):
    images = convert_from_path(pdf_path, dpi=dpi)
    return images


# 2. 查找 PDF 中 "Date:{current_date}" 的位置
def find_date_position_in_pdf(pdf_path):
    current_date = datetime.now().strftime("%Y-%m-%d")
    search_text = f"Date:{current_date}"

    doc = fitz.open(pdf_path)
    positions = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text_instances = page.search_for(search_text)
        print(f"Found {len(text_instances)} instances of '{search_text}' on page {page_num + 1}")
        for inst in text_instances:
            positions.append(inst)
    return positions


# 3. 直接加载透明化的印章图像（不再透明化）
def load_stamp_image(stamp_path):
    # 直接加载透明背景的印章图像
    stamp_image = Image.open(stamp_path).convert("RGBA")  # 确保图像是RGBA格式
    return stamp_image


# 4. 将印章插入到图像中的指定位置
#    rect: 一个四元组 (x0, y0, x1, y1) 表示 PDF 中的文本区域（单位：点）
#    我们根据图像宽度与 A4 宽度(595pt)的比例计算缩放比例
def place_stamp_on_image(image, original_stamp_image, rect, stamp_width=150, stamp_height=150, offset_x=-30, offset_y=80):
    # 从原始印章图像创建一个副本，再调整大小
    stamp_image = original_stamp_image.copy().resize((stamp_width, stamp_height), Image.Resampling.LANCZOS)
    print("Resized stamp image size:", stamp_image.size)

    # rect 是一个四元组 (x0, y0, x1, y1)，我们使用右下角 (x1, y1) 来对齐印章的右下角
    x0, y0, x1, y1 = rect

    # 计算转换比例：PDF A4宽度约为595点，图像宽度以像素计
    scale = image.width / 595.0
    # 计算目标坐标：将右下角坐标转换为像素后减去印章尺寸
    x_target = int(x1 * scale) - stamp_width + offset_x
    y_target = int(y1 * scale) - stamp_height + offset_y

    print(f"Placing stamp at pixel position: ({x_target}, {y_target}), scale factor: {scale}")

    # 将印章粘贴到图像上，第三个参数 stamp_image 作为 mask 保持透明区域
    image.paste(stamp_image, (x_target, y_target), stamp_image)
    return image


# 5. 将所有图像保存为一个 PDF 文件
def save_images_to_pdf(images, output_pdf_path):
    if images:
        images[0].save(output_pdf_path, "PDF", resolution=100.0, save_all=True, append_images=images[1:])


def main():
    # 将 PDF 转换为图像，假设使用 dpi=200
    images = pdf_to_image(PDF_FILE_PATH, dpi=200)
    print(f"Converted {len(images)} pages at 200 DPI.")

    # 查找 PDF 中 "Date:{current_date}" 的位置
    date_positions = find_date_position_in_pdf(PDF_FILE_PATH)
    print(f"Found positions: {date_positions}")

    # 加载并处理印章图片（处理背景透明）
    original_stamp_image = load_stamp_image(SEAL_IMAGE_PATH)  # 这里调用的 prepare_stamp_image 会返回透明背景的印章图片

    stamped_images = []
    for i, img in enumerate(images):
        if i < len(date_positions):
            rect = date_positions[i]
            # 将 fitz.Rect 转换为四元组
            rect_tuple = (rect.x0, rect.y0, rect.x1, rect.y1)
            print(f"Page {i + 1}: stamping at rect {rect_tuple}")
            # 传入新的处理过的印章图片
            stamped_img = place_stamp_on_image(img, original_stamp_image, rect_tuple, stamp_width=150, stamp_height=150)
        else:
            stamped_img = img
        stamped_images.append(stamped_img)

    # 保存所有处理后的页面为最终 PDF
    if stamped_images:
        stamped_images[0].save(OUTPUT_PDF_PATH, "PDF", resolution=100.0, save_all=True,
                               append_images=stamped_images[1:])
    print(f"PDF with stamp saved as: {OUTPUT_PDF_PATH}")

if __name__ == "__main__":
    main()





