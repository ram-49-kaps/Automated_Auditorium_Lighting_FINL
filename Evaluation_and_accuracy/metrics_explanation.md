# Scene Evaluation Metrics Explanation

This document defines the metrics used to evaluate the scene segmentation and boundary detection accuracy of our automated lighting pipeline.

## Metric 1 — Scene Count Accuracy
**Purpose:** Measures the correctness of the raw number of scenes predicted by the model compared to the actual ground truth.
**Formula:** `Scene_Count_Accuracy = max(0, 1 - |PredictedScenes - TrueScenes| / TrueScenes)`
**Range:** 0.0 to 1.0 (Higher is better)
**Interpretation:** This metric penalizes the model proportionally to how far off the scene count is from reality. If the model severely over-segments or under-segments the script, the score approaches 0.

### Example:
- **TrueScenes** = 10
- **PredictedScenes** = 9
- **Accuracy** = `1 - |9 - 10| / 10 = 1 - 1/10 = 0.9`

---

## Metric 2 — Boundary Detection Accuracy
**Purpose:** Measures how accurately the model identified the start and end boundaries of scenes. A boundary is considered "correct" if it lands reasonably close (as defined by matching heuristic) to the true scene boundary.
**Formula:** `BoundaryAccuracy = CorrectBoundaries / TotalBoundaries`
**Range:** 0.0 to 1.0 (Higher is better)
**Interpretation:** This metric evaluates precision on transitions. If the script has 10 scene changes, how many did the model catch accurately?

### Example:
- **True boundaries (TotalBoundaries)** = 10
- **Correct predicted** = 8
- **Accuracy** = `8 / 10 = 0.8`

---

## Metric 3 — Scene Matching Accuracy
**Purpose:** Measures how well the predicted scenes structurally match the true scenes in content. A scene is considered "matched" if the predicted segment correctly encapsulates the core text of the true scene.
**Formula:** `SceneMatchingAccuracy = MatchedScenes / TrueScenes`
**Range:** 0.0 to 1.0 (Higher is better)
**Interpretation:** While Scene Count tells you if you have the *right number* of scenes, Scene Matching tells you if you got the *right scenes*.

### Example:
- **MatchedScenes** = 7
- **TrueScenes** = 10
- **Accuracy** = `7 / 10 = 0.7`

---

## Metric 4 — Weighted Accuracy (FINAL SCORE)
**Purpose:** Combines the three structural metrics into a single, comprehensive final score representing the overall quality of scene detection.
**Formula:** `FinalAccuracy = (0.4 × SceneCountAccuracy) + (0.3 × BoundaryAccuracy) + (0.3 × SceneMatchingAccuracy)`
**Range:** 0.0 to 1.0 (Higher is better)
**Interpretation:** Scene count is weighted slightly higher (40%) to emphasize the importance of structural pacing, while boundary precision (30%) and content matching (30%) make up the remainder of the score to ensure quality.
