import os
import numpy as np
import cv2

def create_realistic_background(size=(400, 400), seed=0):
    """创建真实感的背景图（类似墙壁/纸张纹理）"""
    np.random.seed(seed)
    
    # 创建基础底色
    bg = np.ones((size[1], size[0], 3), dtype=np.uint8)
    
    # 主色调 - 米黄色/浅灰色
    base_color = [220 + np.random.randint(-20, 20), 
                  215 + np.random.randint(-20, 20), 
                  205 + np.random.randint(-20, 20)]
    
    bg[:, :] = base_color
    
    # 添加渐变效果
    y, x = np.ogrid[:size[1], :size[0]]
    center_x, center_y = size[0]//2, size[1]//2
    dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    max_dist = np.sqrt(center_x**2 + center_y**2)
    
    # 中心稍微亮一点，边缘稍暗
    gradient = 1 - 0.1 * (dist_from_center / max_dist)
    for c in range(3):
        bg[:, :, c] = (bg[:, :, c] * gradient).astype(np.uint8)
    
    # 添加细微噪声纹理
    noise = np.random.normal(0, 8, bg.shape).astype(np.int16)
    bg = np.clip(bg + noise, 0, 255).astype(np.uint8)
    
    # 添加一些细微的斑点/纹理变化
    for _ in range(200):
        px = np.random.randint(0, size[0])
        py = np.random.randint(0, size[1])
        radius = np.random.randint(1, 4)
        color_change = np.random.randint(-15, 15)
        
        cv2.circle(bg, (px, py), radius, 
                  (int(base_color[0]+color_change), 
                   int(base_color[1]+color_change), 
                   int(base_color[2]+color_change)), -1)
    
    return bg

def create_dark_defect(size=(80, 80), intensity=0.95):
    """创建深色黑色污点缺陷"""
    defect = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    
    # 创建不规则形状的污点
    center_x, center_y = size[0]//2, size[1]//2
    
    # 主污点区域
    for y in range(size[1]):
        for x in range(size[0]):
            dx = x - center_x
            dy = y - center_y
            
            # 不规则的距离函数，产生自然的污点形状
            r1 = np.sqrt(dx*dx + dy*dy)
            r2 = np.sqrt((dx*0.7)*(dx*0.7) + (dy*1.3)*(dy*1.3))
            r3 = np.sqrt((dx*1.2)*(dx*1.2) + (dy*0.8)*(dy*0.8))
            r = min(r1, r2, r3)
            
            max_r = min(size[0], size[1]) * 0.4
            
            if r < max_r:
                # 高斯衰减，中心更暗
                alpha = np.exp(-(r*r) / (2 * (max_r*0.5)**2))
                darkness = int(255 * alpha * intensity)
                
                # 深灰色到黑色
                defect[y, x] = [255 - darkness, 255 - darkness, 255 - darkness]
            else:
                defect[y, x] = [255, 255, 255]  # 白色背景
    
    # 添加一些更暗的斑点，增加真实感
    for _ in range(30):
        px = center_x + np.random.randint(-int(max_r*0.8), int(max_r*0.8))
        py = center_y + np.random.randint(-int(max_r*0.8), int(max_r*0.8))
        radius = np.random.randint(2, 6)
        
        dx = px - center_x
        dy = py - center_y
        r = np.sqrt(dx*dx + dy*dy)
        
        if r < max_r:
            cv2.circle(defect, (px, py), radius, (5, 5, 5), -1)
    
    return defect

def create_crack_defect(size=(100, 100), num_branches=3, seed=0):
    """创建裂纹状缺陷"""
    np.random.seed(seed)
    
    defect = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
    mask = np.zeros((size[1], size[0]), dtype=np.uint8)
    
    center_x, center_y = size[0]//2, size[1]//2
    
    # 裂纹参数
    crack_thickness = 2  # 基础厚度
    crack_color = (15, 15, 15)  # 深色裂纹
    
    def draw_branch(start_x, start_y, angle, length, depth, max_depth):
        if depth > max_depth or length < 3:
            return
        
        end_x = int(start_x + length * np.cos(angle))
        end_y = int(start_y + length * np.sin(angle))
        
        # 确保在图像范围内
        end_x = np.clip(end_x, 5, size[0]-5)
        end_y = np.clip(end_y, 5, size[1]-5)
        
        # 绘制裂纹线条
        thickness = max(1, crack_thickness - depth)
        cv2.line(defect, (int(start_x), int(start_y)), (end_x, end_y), 
                crack_color, thickness=thickness)
        cv2.line(mask, (int(start_x), int(start_y)), (end_x, end_y), 255, thickness=thickness+1)
        
        # 添加一些小的分支点
        if np.random.random() < 0.7 and depth < max_depth:
            branch_angle1 = angle + np.random.uniform(-0.8, -0.3)
            branch_angle2 = angle + np.random.uniform(0.3, 0.8)
            branch_length = length * np.random.uniform(0.4, 0.7)
            
            draw_branch(end_x, end_y, branch_angle1, branch_length, depth+1, max_depth)
            draw_branch(end_x, end_y, branch_angle2, branch_length, depth+1, max_depth)
        
        # 继续延伸主裂纹
        if np.random.random() < 0.8:
            continue_angle = angle + np.random.uniform(-0.4, 0.4)
            continue_length = length * np.random.uniform(0.6, 0.9)
            draw_branch(end_x, end_y, continue_angle, continue_length, depth, max_depth)
    
    # 从中心向外生长裂纹
    for i in range(num_branches):
        start_angle = (i / num_branches) * 2 * np.pi + np.random.uniform(-0.3, 0.3)
        start_length = np.random.uniform(size[0]*0.25, size[0]*0.4)
        draw_branch(center_x, center_y, start_angle, start_length, 0, 3)
    
    # 添加一些额外的细节：小的横向裂纹
    for _ in range(10):
        x = np.random.randint(size[0]*0.2, size[0]*0.8)
        y = np.random.randint(size[1]*0.2, size[1]*0.8)
        
        # 检查附近是否有裂纹
        if np.any(mask[max(0,y-5):min(size[1],y+6), max(0,x-5):min(size[0],x+6)]):
            angle = np.random.uniform(0, 2*np.pi)
            length = np.random.randint(5, 15)
            cv2.line(defect, (x, y), 
                    (int(x + length*np.cos(angle)), int(y + length*np.sin(angle))),
                    crack_color, thickness=1)
            cv2.line(mask, (x, y), 
                    (int(x + length*np.cos(angle)), int(y + length*np.sin(angle))),
                    255, thickness=2)
    
    # 稍微模糊裂纹边缘，让它看起来更自然
    defect_blur = cv2.GaussianBlur(defect, (3, 3), 0.5)
    mask_blur = cv2.GaussianBlur(mask, (3, 3), 0.5)
    
    # 合并模糊和原图
    defect = cv2.addWeighted(defect, 0.7, defect_blur, 0.3, 0)
    mask = cv2.addWeighted(mask, 0.7, mask_blur, 0.3, 0)
    mask = (mask > 50).astype(np.uint8) * 255
    
    return defect, mask

def create_defect_mask(defect_img):
    """根据缺陷图创建掩码"""
    gray = cv2.cvtColor(defect_img, cv2.COLOR_BGR2GRAY)
    mask = np.zeros_like(gray)
    
    # 非白色区域（即污点区域）标记为255
    mask[gray < 240] = 255
    
    # 稍微膨胀一点，确保覆盖边缘
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.dilate(mask, kernel, iterations=1)
    
    return mask

def generate_sample_images(output_dir: str = "datasets", num_samples: int = 3):
    """生成示例数据集"""
    
    bg_dir = os.path.join(output_dir, "backgrounds")
    df_dir = os.path.join(output_dir, "defects")
    mask_dir = os.path.join(output_dir, "masks")
    
    for d in [bg_dir, df_dir, mask_dir]:
        os.makedirs(d, exist_ok=True)
    
    print(f"正在生成 {num_samples} 个示例数据...")
    
    for i in range(num_samples):
        # 生成真实背景
        bg = create_realistic_background(size=(400, 400), seed=i*100)
        
        # 交替生成污点和裂纹缺陷
        if i % 2 == 0:
            # 深色污点缺陷
            defect_size = (70 + i*15, 70 + i*15)
            defect = create_dark_defect(size=defect_size, intensity=0.95)
            mask = create_defect_mask(defect)
            defect_type = "dark"
        else:
            # 裂纹缺陷
            defect_size = (120 + i*20, 120 + i*20)
            defect, mask = create_crack_defect(size=defect_size, num_branches=4, seed=i*200)
            defect_type = "crack"
        
        # 统一编号，确保排序正确
        defect_name = f"defect_{i+1:02d}_{defect_type}"
        
        # 保存
        cv2.imwrite(os.path.join(bg_dir, f"bg_{i+1:02d}.png"), bg)
        cv2.imwrite(os.path.join(df_dir, f"{defect_name}.png"), defect)
        cv2.imwrite(os.path.join(mask_dir, f"mask_{i+1:02d}.png"), mask)
        
        print(f"  [OK] 生成样本 {i+1}/{num_samples} ({defect_type})")
    
    print(f"\n示例数据已保存到: {output_dir}")
    print(f"  - 真实背景图: {bg_dir}")
    print(f"  - 缺陷图（污点+裂纹）: {df_dir}")
    print(f"  - 掩码图: {mask_dir}")

if __name__ == "__main__":
    print("=" * 50)
    print("真实数据生成器")
    print("  - 真实感纹理背景")
    print("  - 深色黑色污点 + 裂纹缺陷")
    print("=" * 50)
    
    # 清理旧数据
    output_dir = "datasets"
    import shutil
    for folder in ["backgrounds", "defects", "masks", "output"]:
        folder_path = os.path.join(output_dir, folder)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
    
    generate_sample_images(output_dir, num_samples=4)
    
    print("\n现在运行: python main.py 开始处理！")
    print("=" * 50)
