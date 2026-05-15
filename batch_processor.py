import os
import cv2
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path
from edge_blending import EdgeBlending, BlendingConfig, place_defect
from evaluation import evaluate_blending_quality


class DatasetConfig:
    """数据集配置"""
    
    def __init__(self, name: str, background_dir: str, defect_dir: str, 
                 mask_dir: str, output_dir: str):
        self.name = name
        self.background_dir = background_dir
        self.defect_dir = defect_dir
        self.mask_dir = mask_dir
        self.output_dir = output_dir
    
    def create_dirs(self):
        """创建必要的目录"""
        for d in [self.output_dir]:
            os.makedirs(d, exist_ok=True)


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, config: BlendingConfig = None):
        self.blender = EdgeBlending(config=config)
    
    def load_image(self, path: str) -> np.ndarray:
        """加载图像"""
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(f"无法加载图像: {path}")
        return img
    
    def load_mask(self, path: str) -> np.ndarray:
        """加载掩码"""
        mask = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise FileNotFoundError(f"无法加载掩码: {path}")
        return mask
    
    def get_image_pairs(self, background_dir: str, defect_dir: str, 
                       mask_dir: str) -> List[Dict]:
        """获取图像配对"""
        pairs = []
        
        bg_files = sorted([f for f in os.listdir(background_dir) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))])
        
        df_files = sorted([f for f in os.listdir(defect_dir) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))])
        
        mask_files = sorted([f for f in os.listdir(mask_dir) 
                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))])
        
        n_pairs = min(len(bg_files), len(df_files), len(mask_files))
        
        for i in range(n_pairs):
            pairs.append({
                'background': os.path.join(background_dir, bg_files[i]),
                'defect': os.path.join(defect_dir, df_files[i]),
                'mask': os.path.join(mask_dir, mask_files[i]),
                'bg_name': os.path.splitext(bg_files[i])[0],
                'df_name': os.path.splitext(df_files[i])[0]
            })
        
        return pairs
    
    def process_single(self, background: np.ndarray, defect: np.ndarray, 
                      mask: np.ndarray, position: Tuple[int, int] = None) -> Dict:
        """处理单对图像"""
        if position is None:
            h, w = background.shape[:2]
            position = (w // 2, h // 2)
        
        placed_defect, placed_mask, center = place_defect(background, defect, mask, position)
        
        result, final_weight = self.blender.adaptive_blending(
            background=background,
            defect=placed_defect,
            mask=placed_mask,
            sigma_scale=0.15
        )
        
        metrics = evaluate_blending_quality(background, result, placed_mask)
        
        return {
            'background': background,
            'placed_defect': placed_defect,
            'result': result,
            'weight_map': final_weight,
            'metrics': metrics
        }
    
    def save_batch_results(self, batch_id: int, data: Dict, output_dir: str):
        """保存一批结果"""
        batch_dir = os.path.join(output_dir, f"batch_{batch_id:04d}")
        os.makedirs(batch_dir, exist_ok=True)
        
        bg_name = data['bg_name']
        df_name = data['df_name']
        
        cv2.imwrite(os.path.join(batch_dir, f"01_original_{bg_name}.png"), data['background'])
        cv2.imwrite(os.path.join(batch_dir, f"02_defect_{df_name}.png"), data['placed_defect'])
        cv2.imwrite(os.path.join(batch_dir, f"03_result_{bg_name}_blended.png"), data['result'])
        cv2.imwrite(os.path.join(batch_dir, f"04_weight_map_{bg_name}.png"), 
                   (data['weight_map'] * 255).astype(np.uint8))
        
        metrics_file = os.path.join(batch_dir, f"metrics_{bg_name}_{df_name}.txt")
        with open(metrics_file, 'w', encoding='utf-8') as f:
            f.write(f"批次ID: {batch_id}\n")
            f.write(f"背景图像: {bg_name}\n")
            f.write(f"缺陷图像: {df_name}\n")
            f.write("=" * 40 + "\n")
            f.write(f"边缘平滑度: {data['metrics']['edge_smoothness']:.4f}\n")
            f.write(f"颜色一致性: {data['metrics']['color_consistency']:.4f}\n")
            f.write(f"纹理连贯性: {data['metrics']['texture_coherence']:.4f}\n")
    
    def process_directory(self, dataset_config: DatasetConfig, 
                         positions: List[Tuple[int, int]] = None):
        """批量处理整个目录"""
        dataset_config.create_dirs()
        
        pairs = self.get_image_pairs(
            dataset_config.background_dir,
            dataset_config.defect_dir,
            dataset_config.mask_dir
        )
        
        if not pairs:
            print("未找到图像对！请检查目录结构。")
            return []
        
        print(f"找到 {len(pairs)} 对图像")
        print("-" * 50)
        
        results = []
        for idx, pair in enumerate(pairs):
            try:
                print(f"处理第 {idx + 1}/{len(pairs)} 对...")
                print(f"  背景: {pair['bg_name']}")
                print(f"  缺陷: {pair['df_name']}")
                
                bg = self.load_image(pair['background'])
                df = self.load_image(pair['defect'])
                mask = self.load_mask(pair['mask'])
                
                position = positions[idx] if positions else None
                
                result_data = self.process_single(bg, df, mask, position)
                result_data.update({
                    'bg_name': pair['bg_name'],
                    'df_name': pair['df_name']
                })
                
                self.save_batch_results(idx + 1, result_data, dataset_config.output_dir)
                
                results.append(result_data)
                
                print(f"  [OK] 完成")
                print(f"    边缘平滑度: {result_data['metrics']['edge_smoothness']:.4f}")
                print(f"    颜色一致性: {result_data['metrics']['color_consistency']:.4f}")
                print(f"    纹理连贯性: {result_data['metrics']['texture_coherence']:.4f}")
                
            except Exception as e:
                print(f"  [FAIL] 失败: {e}")
        
        print("-" * 50)
        print(f"处理完成！成功: {len(results)}/{len(pairs)}")
        print(f"输出目录: {dataset_config.output_dir}")
        
        return results


def create_default_dataset_structure(base_dir: str = "datasets"):
    """创建默认的数据集目录结构"""
    dirs = {
        'background': os.path.join(base_dir, "backgrounds"),
        'defect': os.path.join(base_dir, "defects"),
        'mask': os.path.join(base_dir, "masks"),
        'output': os.path.join(base_dir, "output")
    }
    
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    
    print(f"[OK] 数据集目录结构已创建:")
    for name, path in dirs.items():
        print(f"  {name:12s} -> {path}")
    
    return dirs
