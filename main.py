import os
import sys
from batch_processor import (
    BatchProcessor, 
    DatasetConfig, 
    create_default_dataset_structure
)
from edge_blending import BlendingConfig


def main():
    print("=" * 60)
    print("边缘融合 - 批量处理系统")
    print("=" * 60)
    
    # 创建默认目录结构
    print("\n1. 初始化数据集目录...")
    dirs = create_default_dataset_structure()
    
    # 配置数据集
    dataset_config = DatasetConfig(
        name="default_dataset",
        background_dir=dirs['background'],
        defect_dir=dirs['defect'],
        mask_dir=dirs['mask'],
        output_dir=dirs['output']
    )
    
    # 配置融合参数
    config = BlendingConfig()
    config.sigma = 8.0
    config.texture_weight = 0.4
    config.color_weight = 0.6
    
    # 检查是否有数据
    has_data = (
        len(os.listdir(dirs['background'])) > 0 and
        len(os.listdir(dirs['defect'])) > 0 and
        len(os.listdir(dirs['mask'])) > 0
    )
    
    if not has_data:
        print("\n" + "=" * 60)
        print("数据集目录已创建！")
        print("=" * 60)
        print("\n请按以下步骤添加数据：")
        print(f"\n1. 背景图像 -> {dirs['background']}")
        print("   (放置你的原始背景图片)")
        print(f"\n2. 缺陷图像 -> {dirs['defect']}")
        print("   (放置缺陷/瑕疵图片)")
        print(f"\n3. 掩码图像 -> {dirs['mask']}")
        print("   (放置对应的掩码图片，白色区域表示缺陷位置)")
        print("\n注意：三个目录中的文件需要一一对应（按文件名排序）")
        print("\n添加数据后，再次运行此程序即可开始处理！")
        print("=" * 60)
        
        # 创建示例说明文件
        create_guide_files(dirs)
        return
    
    # 开始处理
    print("\n2. 开始批量处理...")
    processor = BatchProcessor(config=config)
    results = processor.process_directory(dataset_config)
    
    if results:
        print("\n" + "=" * 60)
        print("处理完成！")
        print("=" * 60)
        print(f"\n结果保存在: {dirs['output']}")
        print("\n每个批次包含:")
        print("  01_original_xxx.png   - 原始背景图")
        print("  02_defect_xxx.png     - 放置缺陷后的图")
        print("  03_result_xxx.png     - 融合结果")
        print("  04_weight_map_xxx.png - 权重分布")
        print("  metrics_xxx.txt       - 质量评估指标")
        print("=" * 60)


def create_guide_files(dirs):
    """创建示例说明文件"""
    # 在背景目录创建说明
    with open(os.path.join(dirs['background'], "README.txt"), 'w', encoding='utf-8') as f:
        f.write("背景图像目录\n")
        f.write("===========\n")
        f.write("请将原始背景图片放入此目录\n")
        f.write("\n支持格式: .png, .jpg, .jpeg, .bmp\n")
        f.write("\n示例：bg_001.png, bg_002.png, ...\n")
    
    # 在缺陷目录创建说明
    with open(os.path.join(dirs['defect'], "README.txt"), 'w', encoding='utf-8') as f:
        f.write("缺陷图像目录\n")
        f.write("===========\n")
        f.write("请将缺陷/瑕疵图片放入此目录\n")
        f.write("\n支持格式: .png, .jpg, .jpeg, .bmp\n")
        f.write("\n示例：defect_001.png, defect_002.png, ...\n")
    
    # 在掩码目录创建说明
    with open(os.path.join(dirs['mask'], "README.txt"), 'w', encoding='utf-8') as f:
        f.write("掩码图像目录\n")
        f.write("===========\n")
        f.write("请将缺陷对应的掩码图片放入此目录\n")
        f.write("\n说明：\n")
        f.write("- 白色区域 (255) 表示缺陷位置\n")
        f.write("- 黑色区域 (0) 表示正常区域\n")
        f.write("\n支持格式: .png, .jpg, .jpeg, .bmp\n")
        f.write("\n示例：mask_001.png, mask_002.png, ...\n")


def quick_start():
    """快速入门指南"""
    print("\n快速入门:")
    print("1. 运行 python main.py 初始化目录")
    print("2. 将图片放入对应目录")
    print("3. 再次运行 python main.py 开始处理")
    print("\n自定义配置:")
    print("修改 main.py 中的 BlendingConfig 参数")


if __name__ == "__main__":
    main()
