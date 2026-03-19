import math

def compute_scene_count_accuracy(true_scenes: int, predicted_scenes: int) -> float:
    """
    Metric 1: Measures correctness of number of scenes.
    Formula: max(0, 1 - |PredictedScenes - TrueScenes| / TrueScenes)
    """
    if true_scenes == 0:
        return 0.0 if predicted_scenes > 0 else 1.0
    
    accuracy = 1.0 - (abs(predicted_scenes - true_scenes) / true_scenes)
    return max(0.0, float(accuracy))

def compute_boundary_accuracy(correct_boundaries: int, total_boundaries: int) -> float:
    """
    Metric 2: Measures correctness of scene boundaries.
    Formula: CorrectBoundaries / TotalBoundaries
    """
    if total_boundaries == 0:
        return 0.0 if correct_boundaries > 0 else 1.0
        
    return float(correct_boundaries / total_boundaries)

def compute_scene_matching_accuracy(matched_scenes: int, true_scenes: int) -> float:
    """
    Metric 3: Measures how well predicted scenes match true scenes.
    Formula: MatchedScenes / TrueScenes
    """
    if true_scenes == 0:
        return 0.0 if matched_scenes > 0 else 1.0
        
    return float(matched_scenes / true_scenes)

def compute_final_weighted_accuracy(scene_count_acc: float, boundary_acc: float, matching_acc: float) -> float:
    """
    Metric 4: Final accuracy must be weighted.
    Formula: 0.4 * SceneCountAccuracy + 0.3 * BoundaryAccuracy + 0.3 * SceneMatchingAccuracy
    """
    return (0.4 * scene_count_acc) + (0.3 * boundary_acc) + (0.3 * matching_acc)
