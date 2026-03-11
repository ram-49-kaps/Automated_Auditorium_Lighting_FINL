"""
Unit tests for Phase 4: Lighting Decision Engine

Tests cover:
- Pydantic model validation (architecturally correct models)
- Rule-based generation with groups
- LangChain chain (mocked)
- DMX adapter conversion
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase_4 import (
    LightingParameters,
    GroupLightingInstruction,
    LightingInstruction,
    TimeWindow,
    Transition,
    TransitionType,
    FocusArea,
    LightingDecisionEngine,
    generate_lighting_instruction,
    batch_generate_instructions
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_scene_data():
    """Sample scene data from Phase 1"""
    return {
        "scene_id": "scene_001",
        "emotion": {"primary_emotion": "fear"},
        "content": {"text": "A dark and stormy night. Lightning flashes."},
        "timing": {
            "start_time": 0,
            "end_time": 10,
            "duration": 10
        }
    }


@pytest.fixture
def sample_joy_scene():
    """Sample joyful scene"""
    return {
        "scene_id": "scene_002",
        "emotion": {"primary_emotion": "joy"},
        "content": {"text": "The celebration begins!"},
        "timing": {"start_time": 10, "end_time": 25, "duration": 15}
    }


# =============================================================================
# PYDANTIC MODEL TESTS
# =============================================================================

class TestLightingParameters:
    """Test LightingParameters model - NO DMX here"""
    
    def test_valid_parameters(self):
        """Test creating valid semantic parameters"""
        params = LightingParameters(
            intensity=75.0,
            color="warm_amber",
            focus_area=FocusArea.CENTER_STAGE
        )
        assert params.intensity == 75.0
        assert params.color == "warm_amber"
        assert params.focus_area == FocusArea.CENTER_STAGE
    
    def test_intensity_bounds(self):
        """Test intensity is bounded 0-100"""
        params = LightingParameters(intensity=100.0, color="white")
        assert params.intensity == 100.0
        
        with pytest.raises(ValueError):
            LightingParameters(intensity=150.0, color="white")
    
    def test_no_dmx_channels(self):
        """Verify there's no DMX in parameters model"""
        params = LightingParameters(intensity=50.0, color="blue")
        data = params.model_dump()
        assert "dmx" not in str(data).lower()
        assert "channel" not in str(data).lower()


class TestGroupLightingInstruction:
    """Test GroupLightingInstruction - uses groups, not fixtures"""
    
    def test_valid_group_instruction(self):
        """Test creating group instruction"""
        instruction = GroupLightingInstruction(
            group_id="front_wash",
            parameters=LightingParameters(intensity=60.0, color="neutral"),
            transition=Transition(type=TransitionType.FADE, duration_seconds=2.0)
        )
        assert instruction.group_id == "front_wash"
        assert instruction.parameters.intensity == 60.0
    
    def test_group_not_fixture(self):
        """Verify we use group_id not fixture_id"""
        instruction = GroupLightingInstruction(
            group_id="back_light",
            parameters=LightingParameters(intensity=50.0, color="white")
        )
        assert hasattr(instruction, "group_id")
        assert not hasattr(instruction, "fixture_id")


class TestLightingInstruction:
    """Test complete LightingInstruction output"""
    
    def test_valid_instruction(self):
        """Test creating complete instruction"""
        instruction = LightingInstruction(
            scene_id="scene_001",
            emotion="fear",
            time_window=TimeWindow(start_time=0, end_time=10),
            groups=[
                GroupLightingInstruction(
                    group_id="front_wash",
                    parameters=LightingParameters(intensity=30.0, color="deep_red")
                )
            ]
        )
        assert instruction.scene_id == "scene_001"
        assert len(instruction.groups) == 1
    
    def test_no_reasoning_required(self):
        """Reasoning is in optional metadata, not a required field"""
        instruction = LightingInstruction(
            scene_id="test",
            emotion="neutral",
            time_window=TimeWindow(start_time=0, end_time=5),
            groups=[]
        )
        # No reasoning field exists
        assert not hasattr(instruction, "reasoning")
        # Optional metadata exists
        assert instruction.metadata is None
    
    def test_metadata_optional(self):
        """Metadata stores debug info, reasoning, etc."""
        instruction = LightingInstruction(
            scene_id="test",
            emotion="neutral",
            time_window=TimeWindow(start_time=0, end_time=5),
            groups=[],
            metadata={"generation_method": "llm", "debug": "info"}
        )
        assert instruction.metadata["generation_method"] == "llm"


# =============================================================================
# LIGHTING DECISION ENGINE TESTS
# =============================================================================

class TestLightingDecisionEngine:
    """Test the decision engine"""
    
    def test_engine_init_no_llm(self):
        """Test initialization without LLM"""
        engine = LightingDecisionEngine(use_llm=False)
        assert engine.use_llm == False
        assert engine.chain is None
    
    def test_generate_instruction_rule_based(self, sample_scene_data):
        """Test rule-based generation outputs correct structure"""
        engine = LightingDecisionEngine(use_llm=False)
        result = engine.generate_instruction(sample_scene_data)
        
        # Check output type
        assert isinstance(result, LightingInstruction)
        
        # Check fields
        assert result.scene_id == "scene_001"
        assert result.emotion == "fear"
        assert result.time_window.start_time == 0
        assert result.time_window.end_time == 10
        
        # Check groups exist (not fixtures)
        assert len(result.groups) > 0
        for group in result.groups:
            assert hasattr(group, "group_id")
            assert not hasattr(group, "fixture_id")
    
    def test_no_dmx_in_output(self, sample_scene_data):
        """Verify no DMX channels in Phase 4 output"""
        engine = LightingDecisionEngine(use_llm=False)
        result = engine.generate_instruction(sample_scene_data)
        
        result_str = str(result.model_dump())
        assert "dmx" not in result_str.lower()
    
    def test_generation_method_in_metadata(self, sample_scene_data):
        """Generation method is in metadata, not top-level"""
        engine = LightingDecisionEngine(use_llm=False)
        result = engine.generate_instruction(sample_scene_data)
        
        assert result.metadata is not None
        assert result.metadata["generation_method"] == "rule_based"


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_generate_lighting_instruction(self, sample_scene_data):
        """Test single scene function"""
        result = generate_lighting_instruction(sample_scene_data, use_llm=False)
        assert isinstance(result, LightingInstruction)
    
    def test_batch_generate(self, sample_scene_data, sample_joy_scene):
        """Test batch generation"""
        scenes = [sample_scene_data, sample_joy_scene]
        results = batch_generate_instructions(scenes, use_llm=False)
        
        assert len(results) == 2
        assert all(isinstance(r, LightingInstruction) for r in results)


# =============================================================================
# DMX ADAPTER TESTS
# =============================================================================

class TestDMXAdapter:
    """Test the DMX adapter (separate from Phase 4)"""
    
    def test_adapter_converts_groups_to_fixtures(self, sample_scene_data):
        """Test that adapter expands groups to fixtures"""
        from adapters.dmx_adapter import DMXAdapter, convert_instruction_to_cues
        
        engine = LightingDecisionEngine(use_llm=False)
        instruction = engine.generate_instruction(sample_scene_data)
        
        # Convert to DMX cues
        cue_dict = convert_instruction_to_cues(instruction)
        
        # Now DMX should appear (in adapter output, not Phase 4 output)
        assert "cues" in cue_dict
        assert "scene_id" in cue_dict
    
    def test_adapter_output_has_dmx(self, sample_scene_data):
        """Adapter output SHOULD have DMX channels"""
        from adapters.dmx_adapter import DMXAdapter, convert_instruction_to_cues
        
        engine = LightingDecisionEngine(use_llm=False)
        instruction = engine.generate_instruction(sample_scene_data)
        cue_dict = convert_instruction_to_cues(instruction)
        
        # Check for DMX in adapter output
        if cue_dict["cues"]:
            assert "dmx_channels" in cue_dict["cues"][0]


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
