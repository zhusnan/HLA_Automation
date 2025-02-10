#!/usr/bin/env python3
import os
import gzip
import random
from collections import defaultdict

def determine_quality_scheme(quality_lines, num_reads=1000):
    """
    判断所采用的测序质量评分方案  
    Scheme 1: 包含 I, 9, -, #  
    Scheme 2: 包含 F, :, ;, ',', #
    """
    scheme1_chars = set('I9-#')
    scheme2_chars = set('F:;,#')

    unique_chars = set()
    for i, qual in enumerate(quality_lines):
        if i >= num_reads:
            break
        unique_chars.update(set(qual))

    print(f"发现的质量字符: {sorted(list(unique_chars))}")

    scheme1_match = len(unique_chars & scheme1_chars)
    scheme2_match = len(unique_chars & scheme2_chars)

    if scheme2_match > scheme1_match:
        print("检测到方案 2 (F,:,;,' ,#)")
        return 2
    else:
        print("检测到方案 1 (I,9,-,#)")
        return 1

def count_bad_qualities(quality_str, scheme):
    """根据不同方案统计低质量字符的数量"""
    if scheme == 1:
        return quality_str.count('-')
    else:
        return quality_str.count(',')

def has_unacceptable_quality(quality_str, scheme):
    """检查是否存在不可接受的质量字符（#）"""
    return '#' in quality_str

def get_uncompressed_size(read_lines):
    """计算 FASTQ 记录解压后的字节数"""
    return sum(len(line.encode('utf-8')) + 1 for line in read_lines)

def find_fastq_pairs(files):
    """
    在文件列表中寻找匹配的 R1 和 R2 文件  
    匹配规则：文件名包含 '_combined_R1.fastq.gz' 和 '_combined_R2.fastq.gz'  
    """
    r1_files = [f for f in files if '_combined_R1.fastq.gz' in f and not f.endswith('.md5')]
    r2_files = [f for f in files if '_combined_R2.fastq.gz' in f and not f.endswith('.md5')]

    pairs = []
    for r1 in r1_files:
        expected_r2 = r1.replace('_combined_R1.fastq.gz', '_combined_R2.fastq.gz')
        if expected_r2 in r2_files:
            pairs.append((r1, expected_r2))
    return pairs

def process_folder(input_folder, target_mb):
    """
    处理指定文件夹下的 FASTQ 文件  
    1. 遍历子目录，寻找匹配的 R1/R2 文件对；  
    2. 对每对文件采样判断质量评分方案，然后统计低质量字符，筛选后降采样输出子集文件；  
    3. 输出文件命名为 *_subset_R1.fastq 和 *_subset_R2.fastq  
    固定目标大小为传入的 target_mb（在本流程中 target_mb 固定为300）。
    """
    target_bytes = target_mb * 1024 * 1024  # MB 转换为字节
    total_bad_quals = 0
    folders_processed = 0

    print(f"正在搜索文件夹：{input_folder}")

    for root, dirs, files in os.walk(input_folder):
        print(f"\n检查目录：{root}")
        print(f"发现文件：{files}")

        fastq_pairs = find_fastq_pairs(files)
        if fastq_pairs:
            print(f"找到 {len(fastq_pairs)} 对 FASTQ 文件")
            for r1_name, r2_name in fastq_pairs:
                folders_processed += 1
                r1_file = os.path.join(root, r1_name)
                r2_file = os.path.join(root, r2_name)

                print(f"\n处理 FASTQ 文件：")
                print(f"R1: {r1_file}")
                print(f"R2: {r2_file}")

                quality_sample = []
                try:
                    with gzip.open(r1_file, 'rt') as f:
                        for i, line in enumerate(f):
                            if i % 4 == 3:
                                quality_sample.append(line.strip())
                            if len(quality_sample) >= 1000:
                                break
                except Exception as e:
                    print(f"采样质量时出错：{str(e)}")
                    continue

                quality_scheme = determine_quality_scheme(quality_sample)

                read_pairs = []
                quality_counts = defaultdict(int)
                try:
                    with gzip.open(r1_file, 'rt') as f1, gzip.open(r2_file, 'rt') as f2:
                        line_count = 0
                        while True:
                            r1_lines = [f1.readline().strip() for _ in range(4)]
                            r2_lines = [f2.readline().strip() for _ in range(4)]
                            if not r1_lines[0] or not r2_lines[0]:
                                break
                            line_count += 1
                            if line_count % 100000 == 0:
                                print(f"已处理 {line_count} 对读段...")
                            if line_count <= 3:
                                print(f"\n样本质量（前50字符）：")
                                print(f"R1: {r1_lines[3][:50]}")
                                print(f"R2: {r2_lines[3][:50]}")
                            if has_unacceptable_quality(r1_lines[3], quality_scheme) or \
                               has_unacceptable_quality(r2_lines[3], quality_scheme):
                                continue
                            pair_bad_quals = count_bad_qualities(r1_lines[3], quality_scheme) + \
                                             count_bad_qualities(r2_lines[3], quality_scheme)
                            total_bad_quals += pair_bad_quals
                            read_pairs.append((r1_lines, r2_lines))
                            quality_counts[len(read_pairs) - 1] = pair_bad_quals
                except Exception as e:
                    print(f"处理文件时出错：{str(e)}")
                    continue

                if not read_pairs:
                    print("未找到有效读段对")
                    continue

                r1_size = sum(get_uncompressed_size(pair[0]) for pair in read_pairs)
                r2_size = sum(get_uncompressed_size(pair[1]) for pair in read_pairs)
                print(f"当前解压大小 - R1: {r1_size/1024/1024:.2f}MB, R2: {r2_size/1024/1024:.2f}MB")
                if r1_size <= target_bytes and r2_size <= target_bytes:
                    print(f"目录 {root}：文件已满足目标大小，无需降采样")
                    continue

                sorted_pairs = sorted(quality_counts.items(), key=lambda x: (x[1], random.random()))
                pairs_to_keep = 0
                r1_running_size = 0
                r2_running_size = 0
                for idx, _ in sorted_pairs:
                    r1_size_contribution = get_uncompressed_size(read_pairs[idx][0])
                    r2_size_contribution = get_uncompressed_size(read_pairs[idx][1])
                    if r1_running_size + r1_size_contribution > target_bytes or \
                       r2_running_size + r2_size_contribution > target_bytes:
                        break
                    r1_running_size += r1_size_contribution
                    r2_running_size += r2_size_contribution
                    pairs_to_keep += 1

                base_name = r1_name.replace('_combined_R1.fastq.gz', '')
                out_r1 = os.path.join(root, f"{base_name}_subset_R1.fastq")
                out_r2 = os.path.join(root, f"{base_name}_subset_R2.fastq")
                kept_pairs = [read_pairs[idx] for idx, _ in sorted_pairs[:pairs_to_keep]]
                with open(out_r1, 'w') as f1, open(out_r2, 'w') as f2:
                    for r1_lines, r2_lines in kept_pairs:
                        f1.write('\n'.join(r1_lines) + '\n')
                        f2.write('\n'.join(r2_lines) + '\n')
                final_r1_size = os.path.getsize(out_r1) / (1024*1024)
                final_r2_size = os.path.getsize(out_r2) / (1024*1024)
                print(f"原始读段对数: {len(read_pairs)}")
                print(f"保留读段对数: {pairs_to_keep}")
                print(f"输出文件大小 - R1: {final_r1_size:.2f}MB, R2: {final_r2_size:.2f}MB")
                print(f"输出文件: {out_r1} 和 {out_r2}")
    if folders_processed == 0:
        print("\n未找到匹配的 FASTQ 文件对！")
    print(f"\n累计低质量字符总数: {total_bad_quals}")
    print("(方案 1 使用 '-' 统计, 方案 2 使用 ',' 统计)")

def process_fastq_files(target_mb):
    """
    固定使用下载后的文件夹 /home/huben/hlahd.1.7.0/sample 进行处理  
    固定目标文件大小为传入参数 target_mb（在本流程中 target_mb 固定为300）
    """
    input_folder = "/home/huben/hlahd.1.7.0/sample"
    process_folder(input_folder, target_mb)
