# includes/movement_utils.py - 基於搜索結果[18][19]的移動工具類

"""
基於搜索結果[18]的MovementUtils設計理念：
"a collection of stateless static BP-accessible functions for a variety of movement-related operations"
"""

import numpy as np
from typing import Tuple, Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MovementUtils:
    """✅ 基於搜索結果[18]的統一移動工具類"""
    
    @staticmethod
    def compute_direction_to_target(current_pos: Tuple[float, float], 
                                  target_pos: Tuple[float, float]) -> Tuple[float, float]:
        """✅ 基於搜索結果[18]的ComputeDirectionIntent"""
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        dist = (dx**2 + dy**2)**0.5
        
        if dist == 0:
            return (0, 0)
        return (dx / dist, dy / dist)
    
    @staticmethod
    def calculate_distance(pos1: Tuple[float, float], 
                          pos2: Tuple[float, float]) -> float:
        """計算兩點距離"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return (dx**2 + dy**2)**0.5
    
    @staticmethod
    def find_safe_target_in_walkable_area(current_pos: Tuple[float, float],
                                        area_grid: Dict,
                                        max_distance: float = 0.03) -> Optional[Tuple[float, float]]:
        """✅ 修正版：確保永不超出可行走範圍"""
        try:
            current_y = current_pos[1]
            walkable_positions = []
            
            # 收集同一水平線上的可行走位置
            for pos_key, area_type in area_grid.items():
                if area_type == "walkable":
                    try:
                        if isinstance(pos_key, tuple):
                            target_x, target_y = pos_key
                        elif isinstance(pos_key, str) and ',' in pos_key:
                            x_str, y_str = pos_key.split(',')
                            target_x, target_y = float(x_str), float(y_str)
                        else:
                            continue
                        
                        # 同一水平線上的可行走點
                        if abs(target_y - current_y) < 0.02:
                            walkable_positions.append(target_x)
                    except Exception:
                        continue
            
            if not walkable_positions:
                logger.warning("沒有找到可行走位置")
                return None
            
            min_safe_x = min(walkable_positions)
            max_safe_x = max(walkable_positions)
            current_x = current_pos[0]
            
            logger.debug(f"可行走範圍: [{min_safe_x:.3f}, {max_safe_x:.3f}]")
            logger.debug(f"當前位置X: {current_x:.3f}")
            
            # ✅ 強制邊界修正：如果角色在範圍外，直接拉回
            if current_x < min_safe_x:
                emergency_target_x = min_safe_x + 0.01
                logger.warning(f"角色在左邊界外，強制拉回: ({emergency_target_x:.3f}, {current_pos[1]})")
                return (emergency_target_x, current_pos[1])
            
            elif current_x > max_safe_x:
                emergency_target_x = max_safe_x - 0.01
                logger.warning(f"角色在右邊界外，強制拉回: ({emergency_target_x:.3f}, {current_pos[1]})")
                return (emergency_target_x, current_pos[1])
            
            else:
                # ✅ 角色在範圍內，計算安全移動目標
                # 限制移動距離，確保不超出邊界
                safe_distance = min(max_distance, 
                                min(current_x - min_safe_x - 0.01, max_safe_x - current_x - 0.01))
                
                if safe_distance <= 0:
                    logger.debug("已在邊界，無法移動")
                    return None
                
                # 選擇移動方向（朝向中心）
                center_x = (min_safe_x + max_safe_x) / 2
                if current_x < center_x:
                    safe_target_x = min(current_x + safe_distance, max_safe_x - 0.01)
                else:
                    safe_target_x = max(current_x - safe_distance, min_safe_x + 0.01)
                
                # ✅ 最終安全檢查
                final_x = max(min_safe_x + 0.01, min(safe_target_x, max_safe_x - 0.01))
                
                logger.debug(f"安全移動目標: {current_pos} -> ({final_x}, {current_pos[1]}) 距離:{abs(final_x-current_x):.3f}")
                return (final_x, current_pos[1])
        
        except Exception as e:
            logger.error(f"安全目標計算失敗: {e}")
            return None
    
    @staticmethod
    def compute_area_aware_movement(current_pos: Tuple[float, float],
                                  target_pos: Tuple[float, float],
                                  area_grid: Dict,
                                  check_distance: float = 0.05) -> Optional[Tuple[float, float]]:
        """✅ 基於搜索結果[19]的AI obstacle avoidance"""
        # 生成多個方向候選
        directions = []
        for i in range(20):
            angle = (i * 18) * np.pi / 180
            directions.append((np.cos(angle), np.sin(angle)))
        
        direction_scores = []
        
        for direction in directions:
            score = 0
            
            # 1. 朝目標方向的偏好
            target_dir = MovementUtils.compute_direction_to_target(current_pos, target_pos)
            dot_product = direction[0] * target_dir[0] + direction[1] * target_dir[1]
            score += dot_product * 100
            
            # 2. 區域類型檢查
            test_pos = (
                current_pos[0] + direction[0] * check_distance,
                current_pos[1] + direction[1] * check_distance
            )
            
            area_type = MovementUtils.get_area_type_at_position(test_pos, area_grid)
            
            if area_type == "forbidden":
                score -= 200
            elif area_type == "walkable":
                score += 50
            elif area_type == "rope":
                score += 30
            elif area_type is None:
                score -= 10
            
            # 3. 水平線保持獎勵
            if abs(direction[1]) < 0.1:
                score += 50
            
            direction_scores.append((direction, score))
        
        # 選擇最佳方向
        best_direction = max(direction_scores, key=lambda x: x[1])
        
        if best_direction[1] < 0:
            return None
        
        return best_direction[0]
    
    @staticmethod
    def get_area_type_at_position(position: Tuple[float, float], 
                                area_grid: Dict) -> Optional[str]:
        """獲取位置的區域類型"""
        if not area_grid:
            return None
        
        # 多精度檢測
        test_positions = [
            (round(position[0], 2), round(position[1], 2)),
            (round(position[0], 1), round(position[1], 1)),
            (round(position[0], 3), round(position[1], 3)),
        ]
        
        for grid_pos in test_positions:
            # 嘗試tuple鍵值
            if grid_pos in area_grid:
                return area_grid[grid_pos]
            
            # 嘗試字串鍵值
            string_key = f"{grid_pos[0]},{grid_pos[1]}"
            if string_key in area_grid:
                return area_grid[string_key]
        
        # 範圍檢測
        x, y = position
        for grid_key, area_type in area_grid.items():
            try:
                if isinstance(grid_key, tuple):
                    gx, gy = grid_key
                elif isinstance(grid_key, str) and ',' in grid_key:
                    gx_str, gy_str = grid_key.split(',')
                    gx, gy = float(gx_str), float(gy_str)
                else:
                    continue
                
                if abs(gx - x) <= 0.02 and abs(gy - y) <= 0.02:
                    return area_type
            except Exception:
                continue
        
        return None
    
    @staticmethod
    def is_within_walkable_bounds(position: Tuple[float, float],
                                area_grid: Dict) -> bool:
        """檢查位置是否在可行走範圍內"""
        if not area_grid:
            return False
        
        current_y = position[1]
        walkable_x_positions = []
        
        for pos_key, area_type in area_grid.items():
            if area_type == "walkable":
                try:
                    if isinstance(pos_key, tuple):
                        target_x, target_y = pos_key
                    elif isinstance(pos_key, str) and ',' in pos_key:
                        x_str, y_str = pos_key.split(',')
                        target_x, target_y = float(x_str), float(y_str)
                    else:
                        continue
                    
                    if abs(target_y - current_y) < 0.05:
                        walkable_x_positions.append(target_x)
                except Exception:
                    continue
        
        if walkable_x_positions:
            min_safe_x = min(walkable_x_positions)
            max_safe_x = max(walkable_x_positions)
            pos_x = position[0]
            return min_safe_x <= pos_x <= max_safe_x
        
        return False
    
    @staticmethod
    def convert_direction_to_movement_command(direction: Tuple[float, float]) -> str:
        """修正版：8方向轉換"""
        if not direction or (direction[0] == 0 and direction[1] == 0):
            return "none"
        
        dx, dy = direction
        
        # 優先水平移動（符合2D橫向遊戲）
        if abs(dx) > abs(dy) * 1.5:  # 水平優先
            return 'right' if dx > 0 else 'left'
        elif abs(dy) > abs(dx) * 1.5:  # 垂直移動
            return 'down' if dy > 0 else 'up'
        else:  # 對角線移動，選擇水平
            return 'right' if dx > 0 else 'left'
    
    @staticmethod
    def validate_movement_safety(current_pos: Tuple[float, float],
                                target_pos: Tuple[float, float],
                                area_grid: Dict) -> bool:
        """驗證移動路徑安全性"""
        # 檢查目標位置
        target_area = MovementUtils.get_area_type_at_position(target_pos, area_grid)
        if target_area == "forbidden":
            return False
        
        # 檢查是否在可行走範圍內
        return MovementUtils.is_within_walkable_bounds(target_pos, area_grid)

    @staticmethod
    def is_within_walkable_bounds_enhanced(position: Tuple[float, float],
                                       area_grid: Dict, 
                                       tolerance_x: float = 0.01,
                                       tolerance_y: float = 0.02) -> bool:
        """✅ 高精度可行走範圍檢查"""
        if not area_grid:
            return False

        current_x, current_y = position
        walkable_positions = []
        
        logger.debug(f"檢查位置: ({current_x:.5f}, {current_y:.5f})")
        
        # 收集所有可行走位置
        for pos_key, area_type in area_grid.items():
            if area_type == "walkable":
                try:
                    if isinstance(pos_key, tuple):
                        target_x, target_y = pos_key
                    elif isinstance(pos_key, str) and ',' in pos_key:
                        x_str, y_str = pos_key.split(',')
                        target_x, target_y = float(x_str), float(y_str)
                    else:
                        continue
                    
                    walkable_positions.append((target_x, target_y))
                except Exception:
                    continue
        
        if not walkable_positions:
            logger.warning("沒有可行走位置")
            return False
        
        # ✅ 精確的範圍計算
        for wx, wy in walkable_positions:
            x_diff = abs(current_x - wx)
            y_diff = abs(current_y - wy)
            
            logger.debug(f"與 ({wx:.3f}, {wy:.3f}) 的距離: X差={x_diff:.5f}, Y差={y_diff:.5f}")
            
            # ✅ 使用不同的X和Y容忍度
            if x_diff <= tolerance_x and y_diff <= tolerance_y:
                logger.debug("位置匹配: 在可行走區域內")
                return True
        
        logger.warning("位置不匹配: 不在任何可行走區域內")
        return False

def find_safe_movement_target(current_pos, walkable_areas, target_pos=None):
    """找到安全的移動目標"""
    try:
        if not walkable_areas:
            logger.warning("沒有找到可行走位置")
            return None
        
        # 獲取可行走區域的邊界
        walkable_x = [float(pos.split(',')[0]) for pos in walkable_areas.keys() if ',' in pos]
        if not walkable_x:
            return None
        
        min_safe_x = min(walkable_x)
        max_safe_x = max(walkable_x)
        current_x = current_pos[0]
        
        logger.debug(f"可行走範圍: [{min_safe_x:.3f}, {max_safe_x:.3f}]")
        logger.debug(f"當前位置X: {current_x:.3f}")
        
        # 檢查是否在邊界外
        if current_x < min_safe_x:
            emergency_target_x = min_safe_x + 0.02
            logger.warning(f"角色在左邊界外，強制拉回: ({emergency_target_x:.3f}, {current_pos[1]})")
            return (emergency_target_x, current_pos[1])
        elif current_x > max_safe_x:
            emergency_target_x = max_safe_x - 0.02
            logger.warning(f"角色在右邊界外，強制拉回: ({emergency_target_x:.3f}, {current_pos[1]})")
            return (emergency_target_x, current_pos[1])
        
        # 如果指定了目標位置，檢查是否安全
        if target_pos:
            target_x = target_pos[0]
            if min_safe_x <= target_x <= max_safe_x:
                return target_pos
            else:
                # 將目標限制在安全範圍內
                final_x = max(min_safe_x, min(max_safe_x, target_x))
                logger.debug(f"安全移動目標: {current_pos} -> ({final_x}, {current_pos[1]}) 距離:{abs(final_x-current_x):.3f}")
                return (final_x, current_pos[1])
        
        # 沒有指定目標，檢查是否已在邊界
        if abs(current_x - min_safe_x) < 0.01 or abs(current_x - max_safe_x) < 0.01:
            logger.debug("已在邊界，無法移動")
            return None
        
        return current_pos
        
    except Exception as e:
        logger.error(f"安全目標計算失敗: {e}")
        return None