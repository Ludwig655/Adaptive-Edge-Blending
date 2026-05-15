import numpy as np
import cv2
from scipy.ndimage import sobel


def compute_gradient_consistency(original: np.ndarray, blended: np.ndarray, mask: np.ndarray) -> float:
    mask = (mask > 0).astype(np.float32)
    
    if len(original.shape) == 3:
        original_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        blended_gray = cv2.cvtColor(blended, cv2.COLOR_BGR2GRAY)
    else:
        original_gray = original
        blended_gray = blended
    
    grad_orig_x = sobel(original_gray, axis=1)
    grad_orig_y = sobel(original_gray, axis=0)
    grad_blend_x = sobel(blended_gray, axis=1)
    grad_blend_y = sobel(blended_gray, axis=0)
    
    grad_mag_orig = np.sqrt(grad_orig_x ** 2 + grad_orig_y ** 2)
    grad_mag_blend = np.sqrt(grad_blend_x ** 2 + grad_blend_y ** 2)
    
    edge_mask = mask > 0
    if np.sum(edge_mask) == 0:
        return 1.0
    
    diff = np.abs(grad_mag_blend - grad_mag_orig)
    max_grad = np.max(grad_mag_orig[edge_mask]) if np.max(grad_mag_orig[edge_mask]) > 0 else 1.0
    normalized_diff = np.mean(diff[edge_mask]) / max_grad
    
    return 1.0 - normalized_diff


def compute_color_discrepancy(original: np.ndarray, blended: np.ndarray, mask: np.ndarray) -> float:
    mask = (mask > 0).astype(np.float32)
    
    if len(original.shape) == 3:
        diff = np.abs(blended.astype(np.float32) - original.astype(np.float32))
        avg_diff = np.mean(diff, axis=2)
    else:
        avg_diff = np.abs(blended.astype(np.float32) - original.astype(np.float32))
    
    edge_mask = mask > 0
    if np.sum(edge_mask) == 0:
        return 1.0
    
    max_possible = 255.0
    normalized_diff = np.mean(avg_diff[edge_mask]) / max_possible
    
    return 1.0 - normalized_diff


def compute_texture_similarity(original: np.ndarray, blended: np.ndarray, mask: np.ndarray) -> float:
    mask = (mask > 0).astype(np.float32)
    
    if len(original.shape) == 3:
        original_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        blended_gray = cv2.cvtColor(blended, cv2.COLOR_BGR2GRAY)
    else:
        original_gray = original
        blended_gray = blended
    
    kernel = np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]])
    sobel_x_orig = cv2.filter2D(original_gray, cv2.CV_64F, kernel)
    sobel_x_blend = cv2.filter2D(blended_gray, cv2.CV_64F, kernel)
    
    kernel = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]])
    sobel_y_orig = cv2.filter2D(original_gray, cv2.CV_64F, kernel)
    sobel_y_blend = cv2.filter2D(blended_gray, cv2.CV_64F, kernel)
    
    g_orig = np.sqrt(sobel_x_orig ** 2 + sobel_y_orig ** 2)
    g_blend = np.sqrt(sobel_x_blend ** 2 + sobel_y_blend ** 2)
    
    edge_mask = mask > 0
    if np.sum(edge_mask) == 0:
        return 1.0
    
    g_orig_norm = g_orig[edge_mask]
    g_blend_norm = g_blend[edge_mask]
    
    if np.std(g_orig_norm) < 1e-6 or np.std(g_blend_norm) < 1e-6:
        return 0.0
    
    corr = np.corrcoef(g_orig_norm, g_blend_norm)[0, 1]
    
    return max(0.0, corr)


def evaluate_blending_quality(original: np.ndarray, blended: np.ndarray, mask: np.ndarray) -> dict:
    metrics = {
        'edge_smoothness': compute_gradient_consistency(original, blended, mask),
        'color_consistency': compute_color_discrepancy(original, blended, mask),
        'texture_coherence': compute_texture_similarity(original, blended, mask)
    }
    return metrics