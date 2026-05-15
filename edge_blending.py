import numpy as np
import cv2
from scipy.ndimage import distance_transform_edt, convolve
from scipy.stats import norm


class BlendingConfig:
    sigma: float = 5.0
    convergence_rate: float = 0.8
    texture_weight: float = 0.3
    color_weight: float = 0.7
    
    @staticmethod
    def adaptive_sigma(defect_size):
        return max(2.0, defect_size * 0.1)


class DefectMaskProcessor:
    @staticmethod
    def extract_defect_contour(mask: np.ndarray) -> tuple:
        mask = (mask > 0).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            contour_points = np.array([])
        else:
            contour_points = contours[0].squeeze()
        
        moments = cv2.moments(mask)
        if moments["m00"] != 0:
            geometric_center = (
                int(moments["m10"] / moments["m00"]),
                int(moments["m01"] / moments["m00"])
            )
        else:
            geometric_center = (mask.shape[1] // 2, mask.shape[0] // 2)
        
        return mask, contour_points, geometric_center
    
    @staticmethod
    def compute_signed_distance_field(mask: np.ndarray) -> np.ndarray:
        mask_binary = (mask > 0).astype(np.float32)
        dist_in = distance_transform_edt(mask_binary)
        dist_out = distance_transform_edt(1 - mask_binary)
        sdf = dist_in - dist_out
        return sdf
    
    @staticmethod
    def compute_weight_map(sdf: np.ndarray, sigma: float) -> np.ndarray:
        abs_dist = np.abs(sdf)
        weight_map = np.zeros_like(sdf)
        
        mask_inside = abs_dist <= sigma
        mask_transition = (abs_dist > sigma) & (abs_dist <= 2 * sigma)
        
        weight_map[mask_inside] = 1.0
        weight_map[mask_transition] = 1.0 - (abs_dist[mask_transition] - sigma) / sigma
        
        return weight_map


class EdgeBlending:
    def __init__(self, config: BlendingConfig = None):
        self.config = config if config is not None else BlendingConfig()
    
    def compute_local_statistics(self, image: np.ndarray, mask: np.ndarray, kernel_size: int = 5) -> tuple:
        if len(image.shape) == 3:
            channels = image.shape[2]
            mean = np.zeros((image.shape[0], image.shape[1], channels))
            std = np.zeros((image.shape[0], image.shape[1], channels))
            
            for c in range(channels):
                mean[..., c] = cv2.GaussianBlur(image[..., c], (kernel_size, kernel_size), 0)
                std[..., c] = cv2.GaussianBlur(image[..., c] ** 2, (kernel_size, kernel_size), 0)
                std[..., c] = np.sqrt(np.maximum(std[..., c] - mean[..., c] ** 2, 0))
        else:
            mean = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
            var = cv2.GaussianBlur(image ** 2, (kernel_size, kernel_size), 0)
            std = np.sqrt(np.maximum(var - mean ** 2, 0))
        
        return mean, std
    
    def weight_function(self, distance_ratio: np.ndarray, local_std_ratio: np.ndarray) -> np.ndarray:
        w_dist = 0.5 * (1 + np.tanh(3 * (1 - 2 * distance_ratio)))
        w_texture = np.exp(-local_std_ratio ** 2)
        
        if len(w_texture.shape) == 3 and len(w_dist.shape) == 2:
            w_dist = np.expand_dims(w_dist, axis=-1)
        
        return w_dist * w_texture
    
    def adaptive_blending(self, background: np.ndarray, defect: np.ndarray, 
                         mask: np.ndarray, sigma_scale: float = 0.1) -> np.ndarray:
        mask = (mask > 0).astype(np.float32)
        result = background.copy().astype(np.float32)
        
        _, _, center = DefectMaskProcessor.extract_defect_contour(mask)
        
        y_coords, x_coords = np.ogrid[:background.shape[0], :background.shape[1]]
        dist_to_center = np.sqrt((x_coords - center[0]) ** 2 + (y_coords - center[1]) ** 2)
        max_dist = np.max(dist_to_center[mask > 0])
        distance_ratio = dist_to_center / max_dist
        
        sdf = DefectMaskProcessor.compute_signed_distance_field(mask)
        sigma = self.config.adaptive_sigma(max_dist) * sigma_scale
        base_weight = DefectMaskProcessor.compute_weight_map(sdf, sigma)
        
        bg_mean, bg_std = self.compute_local_statistics(background, mask)
        df_mean, df_std = self.compute_local_statistics(defect, mask)
        
        local_std_ratio = np.where(bg_std > 0, df_std / (bg_std + 1e-6), 0)
        local_std_ratio = np.clip(local_std_ratio, 0, 2)
        
        if len(local_std_ratio.shape) == 3:
            local_std_ratio = np.mean(local_std_ratio, axis=-1)
        
        texture_weight = self.weight_function(distance_ratio, local_std_ratio)
        
        final_weight = self.config.texture_weight * texture_weight + \
                      self.config.color_weight * base_weight
        final_weight = np.clip(final_weight, 0, 1)
        
        if len(background.shape) == 3:
            for c in range(background.shape[2]):
                result[..., c] = (1 - final_weight) * background[..., c] + \
                                final_weight * defect[..., c]
        else:
            result = (1 - final_weight) * background + final_weight * defect
        
        return result.astype(np.uint8), final_weight
    
    def multi_scale_blending(self, background: np.ndarray, defect: np.ndarray, 
                           mask: np.ndarray, sigma_levels=[2, 4, 8]) -> np.ndarray:
        result = background.copy()
        weight_sum = np.zeros(background.shape[:2], dtype=np.float32)
        
        for sigma in sigma_levels:
            sdf = DefectMaskProcessor.compute_signed_distance_field(mask)
            weight_map = DefectMaskProcessor.compute_weight_map(sdf, sigma)
            
            blurred_bg = cv2.GaussianBlur(background, (sigma * 2 + 1, sigma * 2 + 1), sigma)
            blurred_df = cv2.GaussianBlur(defect, (sigma * 2 + 1, sigma * 2 + 1), sigma)
            
            if len(result.shape) == 3:
                for c in range(result.shape[2]):
                    result[..., c] = (1 - weight_map) * result[..., c] + weight_map * blurred_df[..., c]
            else:
                result = (1 - weight_map) * result + weight_map * blurred_df
            
            weight_sum += weight_map
        
        return result.astype(np.uint8), weight_sum


def place_defect(background_img: np.ndarray, defect_img: np.ndarray, 
                defect_mask: np.ndarray, position: tuple) -> tuple:
    mask_processor = DefectMaskProcessor()
    processed_mask, contour_points, center = mask_processor.extract_defect_contour(defect_mask)
    
    offset_x = position[0] - center[0]
    offset_y = position[1] - center[1]
    
    bg_h, bg_w = background_img.shape[:2]
    df_h, df_w = defect_img.shape[:2]
    
    x_start = max(0, -offset_x)
    x_end = min(df_w, bg_w - offset_x)
    y_start = max(0, -offset_y)
    y_end = min(df_h, bg_h - offset_y)
    
    bg_x_start = max(0, offset_x)
    bg_x_end = bg_x_start + (x_end - x_start)
    bg_y_start = max(0, offset_y)
    bg_y_end = bg_y_start + (y_end - y_start)
    
    placed_defect = np.zeros_like(background_img)
    placed_mask = np.zeros((bg_h, bg_w), dtype=np.float32)
    
    placed_defect[bg_y_start:bg_y_end, bg_x_start:bg_x_end] = defect_img[y_start:y_end, x_start:x_end]
    placed_mask[bg_y_start:bg_y_end, bg_x_start:bg_x_end] = processed_mask[y_start:y_end, x_start:x_end]
    
    new_center = (position[0], position[1])
    
    return placed_defect, placed_mask, new_center


def compute_distance_weights(defect_mask: np.ndarray, sigma: float = 5.0) -> np.ndarray:
    sdf = DefectMaskProcessor.compute_signed_distance_field(defect_mask)
    weight_map = DefectMaskProcessor.compute_weight_map(sdf, sigma)
    return weight_map


def adaptive_pixel_fusion(background_patch: np.ndarray, defect_patch: np.ndarray, 
                          weight_map: np.ndarray) -> np.ndarray:
    if len(background_patch.shape) == 3:
        result = np.zeros_like(background_patch, dtype=np.float32)
        for c in range(background_patch.shape[2]):
            result[..., c] = (1 - weight_map) * background_patch[..., c] + \
                            weight_map * defect_patch[..., c]
    else:
        result = (1 - weight_map) * background_patch + weight_map * defect_patch
    
    return result.astype(np.uint8)