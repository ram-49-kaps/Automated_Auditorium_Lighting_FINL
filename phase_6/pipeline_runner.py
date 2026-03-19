"""
Phase 6: Pipeline Runner

The ORCHESTRATION SPINE.
Controls execution order, enables/disables phases, passes data between phases.

Phase 6:
- Treats every phase as a BLACK BOX
- ONLY calls published entry points
- NEVER modifies phase outputs
- NEVER retries silently
- NEVER swallows errors
"""

import time
import logging
from typing import Dict, List, Optional, Any

from .config_models import PipelineConfig, PhaseStatus, PhaseResult, PipelineResult
from .state_tracker import StateTracker
from .errors import (
    HardFailureError,
    NonFatalError,
    ContractViolationError,
    PhaseNotImplementedError
)

# Initialize logger for phase 6
logger = logging.getLogger("phase_6")


class PipelineRunner:
    """
    Phase 6 Pipeline Orchestrator
    
    Canonical execution order (LOCKED):
    1. Phase 1 — Script parsing & scene extraction
    2. Phase 2 — Emotion enrichment (optional, nullable)
    3. Phase 3 — RAG retrieval (REQUIRED)
    4. Phase 4 — LightingDecisionEngine (REQUIRED)
    5. Phase 5 — Simulation & visualization (OPTIONAL)
    6. Phase 7 — Logging & evaluation (OPTIONAL)
    7. Phase 8 — Hardware execution (FUTURE, OPTIONAL)
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize pipeline runner.
        
        Args:
            config: Pipeline configuration. Defaults to PipelineConfig().
        """
        self.config = config or PipelineConfig()
        self.state = StateTracker()
        self._simulation_launcher = None
    
    def run(self, script_path: str) -> PipelineResult:
        """
        Execute the full pipeline for a script.
        
        Args:
            script_path: Path to input script file
            
        Returns:
            PipelineResult with all phase results
        """
        result = PipelineResult(script_path=script_path)
        
        logger.info(f"Pipeline started: {script_path}")
        pipeline_start = time.time()
        
        try:
            # Phase 1: Parsing (REQUIRED - HARD FAIL)
            scenes = self._run_phase_1(script_path, result)
            
            self.state.start_pipeline(script_path, len(scenes))
            
            # Process each scene
            lighting_instructions = []
            processed_scenes = []
            for idx, scene in enumerate(scenes):
                scene_id = scene.get("scene_id", f"scene_{idx:03d}")
                self.state.set_current_scene(scene_id, idx)
                
                # Phase 2: Emotion (OPTIONAL - continue with null if fails)
                enriched_scene = self._run_phase_2(scene, result)
                
                # Phase 3: RAG retrieval (REQUIRED - HARD FAIL)
                rag_context = self._run_phase_3(enriched_scene, result)
                
                # Phase 4: Decision Engine (REQUIRED - HARD FAIL after fallback)
                instruction = self._run_phase_4(enriched_scene, rag_context, result)
                lighting_instructions.append(instruction)
                processed_scenes.append(enriched_scene)
            
            # Phase 5: Simulation (OPTIONAL - log & continue)
            if self.config.enable_phase_5:
                self._simulation_launcher = self._run_phase_5(lighting_instructions, result)
            else:
                result.add_phase_result(
                    self.state.skip_phase("phase_5", "Disabled by configuration")
                )
            
            # Phase 7: Evaluation (OPTIONAL - log & continue)
            if self.config.enable_phase_7:
                self._run_phase_7(lighting_instructions, processed_scenes, result)
            else:
                result.add_phase_result(
                    self.state.skip_phase("phase_7", "Disabled by configuration")
                )
            
            # Phase 8: Hardware (NOT IMPLEMENTED)
            if self.config.enable_phase_8:
                result.add_phase_result(
                    self.state.skip_phase("phase_8", "Not implemented")
                )
            
            result.mark_complete()
            self.state.complete_pipeline(PhaseStatus.SUCCESS)
            
        except HardFailureError as e:
            logger.error(f"Pipeline hard failure in {e.phase_name}: {e}")
            result.final_status = PhaseStatus.FAILED
            self.state.complete_pipeline(PhaseStatus.FAILED)
            
        except Exception as e:
            logger.exception(f"Unexpected pipeline error: {e}")
            result.final_status = PhaseStatus.FAILED
            self.state.complete_pipeline(PhaseStatus.FAILED)
        
        result.total_duration_seconds = time.time() - pipeline_start
        logger.info(f"Pipeline completed: {result.final_status.value} in {result.total_duration_seconds:.2f}s")
        
        return result
    
    def _run_phase_1(self, script_path: str, result: PipelineResult) -> List[Dict]:
        """
        Phase 1: Script parsing & scene extraction
        REQUIRED - HARD FAIL on error
        
        New architecture (v2): Calls run_phase_1() which handles
        1A (acquisition), 1B (structuring), 1C (LLM segmentation +
        timestamps), 1D (validation), 1E (JSON construction).
        """
        self.state.start_phase("phase_1")
        logger.info("Phase 1: Starting script parsing")
        
        try:
            from phase_1 import run_phase_1
            
            scenes, metadata = run_phase_1(script_path)
            
            # scenes is already a list of schema-valid dicts
            phase_result = self.state.complete_phase(
                "phase_1",
                PhaseStatus.SUCCESS,
                output={"scene_count": len(scenes), **metadata}
            )
            result.add_phase_result(phase_result)
            
            logger.info(f"Phase 1: Parsed {len(scenes)} scenes")
            return scenes
            
        except Exception as e:
            phase_result = self.state.complete_phase(
                "phase_1",
                PhaseStatus.FAILED,
                error_message=str(e)
            )
            result.add_phase_result(phase_result)
            raise HardFailureError(f"Phase 1 failed: {e}", phase_name="phase_1")
    
    def _run_phase_2(self, scene: Dict, result: PipelineResult) -> Dict:
        """
        Phase 2: Emotion enrichment
        OPTIONAL - continue with emotion=null if fails
        """
        self.state.start_phase("phase_2")
        
        try:
            from phase_2 import analyze_emotion
            
            # Phase 1 -> Phase 2 Strict Contract: Only pass scene_id and text
            scene_id = scene.get("scene_id")
            content = scene.get("text", "")
            
            # Architectural Rule: Minimum content threshold
            # Cinematic transitions (FADE IN, CUT TO) should not be analyzed for emotion
            word_count = len(content.split())
            if word_count < 4:
                logger.info(f"Phase 2 skipped for {scene_id} - text too short ({word_count} words)")
                scene["emotion"] = None
                
                phase_result = self.state.complete_phase(
                    "phase_2",
                    PhaseStatus.SUCCESS,
                    output={"emotion": None, "reason": "below_word_count_threshold"}
                )
                result.add_phase_result(phase_result)
                return scene
            
            # Conceptually Phase 2 only receives text (and scene_id)
            emotion_analysis_full = analyze_emotion(scene)
            
            # Extract the actual inner emotion dict from the Phase 2 contract
            emotion_dict = emotion_analysis_full.get("emotion")
            
            # Phase 2 Output Contract: Only inject the emotion dict
            scene["emotion"] = emotion_dict
            
            primary_val = emotion_dict.get("primary", "neutral") if emotion_dict else "neutral"
            
            phase_result = self.state.complete_phase(
                "phase_2",
                PhaseStatus.SUCCESS,
                output={"emotion": primary_val}
            )
            result.add_phase_result(phase_result)
            
            return scene
            
        except Exception as e:
            logger.warning(f"Phase 2 failed (non-fatal): {e}")
            scene["emotion"] = {"primary": "neutral", "confidence": 0.0}
            
            phase_result = self.state.complete_phase(
                "phase_2",
                PhaseStatus.FAILED,
                error_message=str(e)
            )
            result.add_phase_result(phase_result)
            
            # Non-fatal - continue with neutral emotion
            return scene
    
    def _run_phase_3(self, scene: Dict, result: PipelineResult) -> str:
        """
        Phase 3: RAG retrieval
        REQUIRED - HARD FAIL on error
        """
        self.state.start_phase("phase_3")
        
        try:
            from phase_3 import get_retriever
            
            retriever = get_retriever()
            emotion = scene.get("emotion", {}).get("primary_emotion", "neutral") if scene.get("emotion") else "neutral"
            scene_text = scene.get("text", "")
            
            context = retriever.build_context_for_llm(emotion, scene_text)
            
            phase_result = self.state.complete_phase(
                "phase_3",
                PhaseStatus.SUCCESS,
                output={"context_length": len(context)}
            )
            result.add_phase_result(phase_result)
            
            return context
            
        except Exception as e:
            phase_result = self.state.complete_phase(
                "phase_3",
                PhaseStatus.FAILED,
                error_message=str(e)
            )
            result.add_phase_result(phase_result)
            raise HardFailureError(f"Phase 3 failed: {e}", phase_name="phase_3")
    
    def _run_phase_4(
        self, 
        scene: Dict, 
        rag_context: str, 
        result: PipelineResult
    ) -> Dict:
        """
        Phase 4: Lighting Decision Engine
        REQUIRED - HARD FAIL after internal fallback exhausted
        """
        self.state.start_phase("phase_4")
        
        try:
            from phase_4 import LightingDecisionEngine
            
            engine = LightingDecisionEngine(use_llm=self.config.use_llm)
            instruction = engine.generate_instruction(scene)
            
            # Validate output against contract
            self._validate_lighting_instruction(instruction)
            
            phase_result = self.state.complete_phase(
                "phase_4",
                PhaseStatus.SUCCESS,
                output={"groups_count": len(instruction.groups)}
            )
            result.add_phase_result(phase_result)
            
            return instruction.model_dump()
            
        except ContractViolationError as e:
            phase_result = self.state.complete_phase(
                "phase_4",
                PhaseStatus.FAILED,
                error_message=str(e)
            )
            result.add_phase_result(phase_result)
            raise HardFailureError(f"Phase 4 contract violation: {e}", phase_name="phase_4")
            
        except Exception as e:
            phase_result = self.state.complete_phase(
                "phase_4",
                PhaseStatus.FAILED,
                error_message=str(e)
            )
            result.add_phase_result(phase_result)
            raise HardFailureError(f"Phase 4 failed: {e}", phase_name="phase_4")
    
    def _run_phase_5(
        self, 
        lighting_instructions: List[Dict], 
        result: PipelineResult
    ) -> Optional[Any]:
        """
        Phase 5: Simulation & visualization
        OPTIONAL - NON-FATAL, log & continue
        
        Returns:
            SimulationLauncher instance if successful, None otherwise.
        """
        self.state.start_phase("phase_5")
        
        try:
            from phase_5.server import launch_simulation
            
            # Launch the external simulation with real pipeline data
            launcher = launch_simulation(lighting_instructions)
            
            phase_result = self.state.complete_phase(
                "phase_5",
                PhaseStatus.SUCCESS
            )
            result.add_phase_result(phase_result)
            return launcher
            
        except ImportError:
            logger.warning("Phase 5 not available - skipping")
            phase_result = self.state.complete_phase(
                "phase_5",
                PhaseStatus.SKIPPED,
                error_message="Module not available"
            )
            result.add_phase_result(phase_result)
            
        except Exception as e:
            logger.warning(f"Phase 5 failed (non-fatal): {e}")
            phase_result = self.state.complete_phase(
                "phase_5",
                PhaseStatus.FAILED,
                error_message=str(e)
            )
            result.add_phase_result(phase_result)
            # Non-fatal - continue
        
        return None
    
    def _run_phase_7(
        self, 
        lighting_instructions: List[Dict],
        processed_scenes: List[Dict],
        result: PipelineResult
    ) -> None:
        """
        Phase 7: Logging, evaluation & v2 quality gate
        OPTIONAL - NON-FATAL, log & continue
        """
        self.state.start_phase("phase_7")
        
        try:
            from pathlib import Path
            from phase_7 import TraceLogger, MetricsEngine, EvaluationGate
            
            # --- Layer 1: Trace Logging ---
            trace_logger = TraceLogger(output_dir=Path("data/traces/"), seed=42)
            for scene, instruction in zip(processed_scenes, lighting_instructions):
                trace_logger.log_decision(scene, instruction)
            trace_file = trace_logger.save()
            logger.info(f"Phase 7: Trace saved to {trace_file}")
            print(f"📝 Trace saved: {trace_file} ({trace_logger.get_entry_count()} entries)")
            
            # --- Layer 2: Metrics Engine (v1) ---
            available_groups = {"front_wash", "back_light", "side_fill", "specials", "ambient"}
            metrics_engine = MetricsEngine(available_groups=available_groups)
            metrics_report = metrics_engine.generate_report(lighting_instructions)
            
            # Print v1 summary
            print(f"📊 Metrics Report:")
            print(f"   Scenes:    {metrics_report['summary']['num_instructions']}")
            seq = metrics_report.get('sequence_metrics', {})
            print(f"   Drift:     {seq.get('drift_score', 'N/A')}")
            for im in metrics_report.get('instruction_metrics', []):
                cov = im.get('coverage', {})
                div = im.get('diversity', {})
                print(f"   Scene {im.get('scene_id', '?')}: coverage={cov}, diversity={div}")
            
            # --- Layer 3: Evaluation Gate (v2) ---
            # Phase 2 natively outputs {"primary": x, "primary_confidence": y, ...}
            # which matches what EvaluationGate needs (as `emotion_dists` mapped below)
            emotion_dists = []
            for s in processed_scenes:
                e = s.get("emotion")
                if e:
                    # Map the strict Phase 2 JSON to EvaluationGate format
                    emotion_dists.append({
                        "primary_emotion": e.get("primary", "neutral"),
                        "primary_weight": e.get("primary_confidence", 1.0),
                        "primary_score": e.get("primary_confidence", 1.0),
                        "accent_emotions": [
                            {"emotion": e.get("secondary"), "weight": e.get("secondary_confidence", 0.0)},
                            {"emotion": e.get("accent"), "weight": e.get("accent_confidence", 0.0)}
                        ]
                    })
                else:
                    emotion_dists.append({
                        "primary_emotion": "neutral",
                        "primary_weight": 1.0,
                        "primary_score": 1.0,
                        "accent_emotions": []
                    })
            
            gate = EvaluationGate(output_dir="data/evaluations/")
            eval_report = gate.evaluate_pipeline(
                instructions=lighting_instructions,
                emotion_dists=emotion_dists,
            )
            
            # Print v2 verdict
            can_proceed = gate.should_proceed(eval_report)
            summary = gate.get_verdict_summary(eval_report)
            print(f"\n🔍 Evaluation Gate:")
            print(summary)
            
            if not can_proceed:
                logger.warning("Phase 7: Evaluation gate recommends review — pipeline continues (non-blocking)")
                print("   ⚠️  Gate: REVIEW RECOMMENDED (non-blocking)")
            else:
                print("   ✅ Gate: PASSED")
            
            phase_result = self.state.complete_phase(
                "phase_7",
                PhaseStatus.SUCCESS,
                output={
                    "trace_file": str(trace_file),
                    "entries": trace_logger.get_entry_count(),
                    "drift_score": seq.get('drift_score'),
                    "gate_passed": can_proceed,
                }
            )
            result.add_phase_result(phase_result)
            
        except ImportError:
            logger.warning("Phase 7 not available - skipping")
            phase_result = self.state.complete_phase(
                "phase_7",
                PhaseStatus.SKIPPED,
                error_message="Module not available"
            )
            result.add_phase_result(phase_result)
            
        except Exception as e:
            logger.warning(f"Phase 7 failed (non-fatal): {e}")
            phase_result = self.state.complete_phase(
                "phase_7",
                PhaseStatus.FAILED,
                error_message=str(e)
            )
            result.add_phase_result(phase_result)
            # Non-fatal - continue
    
    def _validate_lighting_instruction(self, instruction) -> None:
        """
        Validate LightingInstruction against contract.
        
        Phase 6 enforces ONLY:
        - group_id is present (not fixture_id)
        - intensity ∈ [0, 1]
        - Required fields exist
        """
        for group in instruction.groups:
            # Verify group_id exists
            if not group.group_id:
                raise ContractViolationError("Missing group_id in LightingInstruction")
            
            # Verify intensity in [0, 1]
            intensity = group.parameters.intensity
            if intensity < 0.0 or intensity > 1.0:
                raise ContractViolationError(
                    f"Intensity {intensity} out of range [0, 1]"
                )
    
    def get_state(self):
        """Get current pipeline state"""
        return self.state.get_state()
    
    def get_summary(self):
        """Get execution summary"""
        return self.state.get_summary()
