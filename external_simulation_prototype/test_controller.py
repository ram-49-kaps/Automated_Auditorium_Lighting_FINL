
import asyncio
import websockets
import json
import os

# CONFIGURATION
PORT = 8765
HOST = "localhost"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTRUCTIONS_PATH = os.path.join(SCRIPT_DIR, "current_show.json")

if not os.path.exists(INSTRUCTIONS_PATH):
    print(f"⚠️ Warning: {INSTRUCTIONS_PATH} not found. Waiting for backend to launch...")

# --- COLOR NAME → HEX MAPPING ---
# Must cover all colors from Phase 3 RAG knowledge base (baseline_semantics.json)
COLOR_MAP = {
    # Whites
    "white":        "#FFFFFF",
    "bright_white": "#FFFFFF",
    "warm_white":   "#FFF5E1",
    "cold_white":   "#E0E8FF",
    
    # Ambers / Yellows / Oranges
    "amber":        "#FFB347",
    "warm_amber":   "#FFB347",
    "yellow":       "#FFD700",
    "gold":         "#FFD700",
    "orange":       "#FF8C00",
    "sepia":        "#C19A6B",
    "peach":        "#FFCBA4",
    
    # Reds / Magentas / Pinks
    "red":          "#FF0000",
    "deep_red":     "#CC0033",
    "dark_red":     "#8B0000",
    "magenta":      "#FF00FF",
    "pink":         "#FF69B4",
    "rose":         "#FF007F",
    
    # Blues
    "blue":         "#3366FF",
    "dark_blue":    "#001166",
    "cool_blue":    "#4488FF",
    "steel_blue":   "#4682B4",
    "lavender":     "#9370DB",
    
    # Greens
    "green":        "#00CC44",
    "sickly_green": "#ADFF2F",
    "yellow_green": "#9ACD32",
    
    # Cyans / UV
    "cyan":         "#00FFFF",
    "uv":           "#7B00FF",
    
    # Greys / Darks
    "grey":         "#808080",
    "blackout":     "#000000",
}

# --- INSTRUCTION GROUP → FIXTURE TYPE MAPPING ---
# Maps the abstract group_ids from the JSON instructions
# to the actual fixture ID prefixes in our 3D simulation.
GROUP_TO_FIXTURES = {
    "FRONT_WASH": ["FOH_FRESNEL", "FOH_PROFILE"],       # Front-of-house wash & spot
    "BACK_LIGHT": ["STAGE_BLINDER"],                     # Back light / blinders
    "SIDE_FILL":  ["STAGE_RGB_PAR"],                     # Side fill: color PARs
    "SPECIALS":   ["FOH_MOVING"],                        # Specials: moving heads for focus
    "AMBIENT":    ["STAGE_RGB_PAR"],                      # Ambient: RGB wash layer
}

# --- EMOTION → SMOKE MAPPING ---
SMOKE_EMOTIONS = {"fear", "anger", "surprise", "tension", "anxiety", "dread", "mystery"}


class CueEngine:
    def __init__(self):
        self.cues = []
        self.current_index = 0
        self.is_holding = True  # Start paused for the new "START" UI
        self.clients = set()
        self._start_end_inserted = False
        self.load_instructions()

    def load_instructions(self):
        """Load the JSON lighting instructions and extract script text."""
        try:
            if not os.path.exists(INSTRUCTIONS_PATH):
                return

            with open(INSTRUCTIONS_PATH, 'r') as f:
                data = json.load(f)

            instructions = []
            script_data = []

            # Handle both formats: Direct List (Legacy) or Dict with 'lighting_instructions' (Pipeline)
            if isinstance(data, list):
                instructions = data
            elif isinstance(data, dict):
                instructions = data.get("lighting_instructions", [])
                script_data = data.get("script_data", [])

            self.cues = []
            self._start_end_inserted = False
            
            for i, scene in enumerate(instructions):
                # 1. Convert lighting data
                scene_data = self._convert_groups(scene)

                # 2. Get Metadata
                meta = scene.get("metadata", {})
                raw_emotion = scene.get("emotion", "—")
                # emotion can be a dict {primary_emotion: "anxiety", ...} or a plain string
                if isinstance(raw_emotion, dict):
                    emotion = raw_emotion.get("primary_emotion", raw_emotion.get("primary", "neutral"))
                else:
                    emotion = str(raw_emotion) if raw_emotion else "neutral"
                     # 3. Get Timing — keys are 'start_time' and 'end_time' (not 'start'/'end')
                tw = scene.get("time_window", {})
                start_time = tw.get('start_time', tw.get('start', 0))
                end_time = tw.get('end_time', tw.get('end', 0))
                scene_duration_secs = end_time - start_time
                # Clamp: minimum 5s per scene, maximum 120s (2 min) so the show doesn't stall
                duration = max(5.0, min(120.0, scene_duration_secs))
                
                time_str = f"{start_time:.0f}s – {end_time:.0f}s"

                # 4. Get Script Text (The Fix!)
                # Try to find matching script scene by ID or Index. If not, look in 'scene' directly.
                script_text = ""
                script_full = ""
                scene_id = scene.get("scene_id")
                
                # Step 4a: Look in the lighting scene object itself first (sometimes it's bundled in by pipeline_runner)
                direct_content = scene.get("content", {})
                if isinstance(direct_content, str):
                    script_text = direct_content.strip()
                    script_full = script_text
                elif isinstance(direct_content, dict):
                    script_text = direct_content.get("text", "").strip()
                    script_full = script_text

                if not script_text:
                    script_text = scene.get("text", "").strip()
                    script_full = script_text
                
                # Step 4b: Find matching scene in script_data if still empty
                if not script_text:
                    matching_script_scene = next((s for s in script_data if s.get("scene_id") == scene_id), None)
                    
                    if matching_script_scene:
                        content_obj = matching_script_scene.get("content")
                        if isinstance(content_obj, str):
                            header = ""
                            raw_text = content_obj.strip()
                        elif isinstance(content_obj, dict):
                            header = content_obj.get("header", "")
                            header = header.strip() if header else ""
                            raw_text = content_obj.get("text", "")
                            raw_text = raw_text.strip() if raw_text else ""
                        else:
                            # Fallback if content doesn't exist or is None - use text field
                            header = ""
                            raw_text = matching_script_scene.get("text", "")
                            raw_text = raw_text.strip() if raw_text else ""
                        
                        # Prepend header if it's significant (like FADE IN, INT., CUT TO)
                        full_text = f"[{header}] {raw_text}" if header else raw_text
                        
                        # Short preview for cue list, full text stored separately
                        script_text = (full_text[:55] + '...') if len(full_text) > 55 else full_text
                        script_full = full_textfull = full_text
                else:
                    # Fallback to index if no ID match (risky but better than nothing)
                    if i < len(script_data):
                        content_obj = script_data[i].get("content")
                        if isinstance(content_obj, str):
                            header = ""
                            raw_text = content_obj.strip()
                        elif isinstance(content_obj, dict):
                            header = content_obj.get("header", "")
                            header = header.strip() if header else ""
                            raw_text = content_obj.get("text", "")
                            raw_text = raw_text.strip() if raw_text else ""
                        else:
                            header = ""
                            raw_text = script_data[i].get("text", "")
                            raw_text = raw_text.strip() if raw_text else ""
                        
                        full_text = f"[{header}] {raw_text}" if header else raw_text
                        script_text = (full_text[:55] + '...') if len(full_text) > 55 else full_text
                        script_full = full_text
                    else:
                        script_full = script_text

                # 5. Build Display String for the UI
                # Format: "SCENE_ID | EMOTION | TEXT"
                display_text = (
                    f"{scene_id} │ {emotion.upper()} │ \"{script_text}\""
                )

                # 6. Get Transition
                first_group = scene.get("groups", [{}])[0]
                transition = first_group.get("transition", {})
                trans_type = transition.get("type", "fade").upper()
                trans_dur = transition.get("duration", 2.0)

                self.cues.append({
                    "id": i,
                    "text": display_text,
                    "script_line": script_text,   # Short preview for list
                    "script_full": script_full,   # Full scene text
                    "scene": emotion.upper(),
                    "data": scene_data,
                    "duration": duration, 
                    "transition_type": trans_type.lower(),
                    "transition_duration": trans_dur,
                })

            print(f"✅ Loaded {len(self.cues)} lighting cues.")
            if len(self.cues) > 0:
                print(f"   Example Cue 1 Text: {self.cues[0]['text']}")

        except Exception as e:
            print(f"❌ Error loading instructions: {e}")
            import traceback
            traceback.print_exc()

    def _convert_groups(self, scene):
        """Convert JSON instruction groups to our simulation's fixture format."""
        result = {}
        has_smoke = False
        raw_em = scene.get("emotion", "neutral")
        if isinstance(raw_em, dict):
            emotion = raw_em.get("primary_emotion", raw_em.get("primary", "neutral"))
        else:
            emotion = str(raw_em) if raw_em else "neutral"

        for group in scene.get("groups", []):
            group_id = group.get("group_id", "")
            params = group.get("parameters", {})

            # Get intensity (0-100)
            intensity = params.get("intensity", 0)

            # Resolve color name to hex
            color_name = params.get("color", "white")
            color_hex = COLOR_MAP.get(color_name, "#FFFFFF")
            # If color is hex code
            if color_name.startswith("#"):
                color_hex = color_name

            # Map to simulation fixture keys
            fixture_prefixes = GROUP_TO_FIXTURES.get(group_id.upper(), []) # Handle case sensitivity
            
            # Map "specials" if not found
            if not fixture_prefixes and group_id == "specials":
                fixture_prefixes = ["FOH_PROFILE_01"] 
                
            for prefix in fixture_prefixes:
                result[prefix] = {
                    "intensity": int(intensity),
                    "color": color_hex,
                }

        # Determine smoke based on emotion
        if emotion in SMOKE_EMOTIONS:
            has_smoke = True

        result["SMOKE"] = has_smoke
        return result

    def override_cue_lighting(self, idx, command_text):
        """Override lighting via NLP command for a specific cue."""
        if 0 <= idx < len(self.cues):
            import sys, os
            PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            if PROJECT_ROOT not in sys.path:
                sys.path.append(PROJECT_ROOT)
            from backend.nlp_lighting_parser import parse_lighting_command
            
            parsed_params = parse_lighting_command(command_text)
            
            cue = self.cues[idx]
            original_data = cue.get("data", {})
            
            # Apply to target groups or all if not specified
            target_groups = parsed_params.get("groups", list(original_data.keys()))
            if not target_groups:
                target_groups = list(original_data.keys())
                
            for group_id in target_groups:
                # If group doesn't exist yet, initialize it
                if group_id not in original_data:
                    original_data[group_id] = {"intensity": 50, "color": "#FFFFFF"}
                    
                if "intensity" in parsed_params:
                    original_data[group_id]["intensity"] = parsed_params["intensity"]
                
                if "color" in parsed_params:
                    original_data[group_id]["color"] = parsed_params["color"]
            
            cue["data"] = original_data
            
            orig_text = cue["text"].split(" │ ")
            if len(orig_text) >= 3:
                cue["text"] = f"{orig_text[0]} │ NLP_OVERRIDE │ {orig_text[2]}"
            
            return True
        return False

    def override_theme(self, idx, new_theme):
        """Override the emotion of a specific cue and regenerate lighting."""
        if 0 <= idx < len(self.cues):
            cue = self.cues[idx]
            cue['scene'] = new_theme.upper()
            
            # Since we modify the theme on the fly, let's create a proxy 'scene' object 
            # and pass it to _convert_groups to fetch new lighting intent based on NEW emotion rule.
            # We don't have the LLM here, but we can do a quick rule-based mapping:
            # Simple fallback for live-editing
            theme_color_map = {
                "JOY": "warm_amber",
                "ANGER": "deep_red",
                "FEAR": "cool_blue",
                "SADNESS": "steel_blue",
                "SURPRISE": "cyan",
                "DISGUST": "sickly_green",
                "NEUTRAL": "white",
                "ANXIETY": "pale_violet",
                "BETRAYAL": "deep_red",
                "NOSTALGIA": "warm_amber",
                "MYSTERY": "deep_purple",
                "ROMANTIC": "soft_pink",
                "ANTICIPATION": "amber",
                "HOPE": "warm_white",
                "TRIUMPH": "gold",
                "TENSION": "cool_blue",
                "DESPAIR": "steel_blue",
                "SERENITY": "pale_blue",
                "CONFUSION": "pale_violet",
                "AWE": "deep_purple",
                "JEALOUSY": "sickly_green",
                "LOVE": "soft_pink",
                "GRIEF": "steel_blue",
                "EXCITEMENT": "amber",
                "CHAOTIC_ENERGY": "cyan",
                "COMEDIC_ENERGY": "warm_amber",
                "AMUSEMENT": "warm_amber",
                "MELANCHOLY": "steel_blue",
                "DREAD": "deep_red",
                "CONTENTMENT": "warm_white",
            }
            color_name = theme_color_map.get(new_theme.upper(), "white")
            
            # Build a mock scene to feed into _convert_groups
            mock_scene = {
                "emotion": new_theme.lower(),
                "groups": [
                    {"group_id": "FRONT_WASH", "parameters": {"intensity": 80, "color": color_name}},
                    {"group_id": "SIDE_FILL", "parameters": {"intensity": 60, "color": color_name}},
                    {"group_id": "BACK_LIGHT", "parameters": {"intensity": 40, "color": color_name}}
                ]
            }
            
            cue['data'] = self._convert_groups(mock_scene)
            
            # Update display text
            parts = cue['text'].split('│')
            if len(parts) >= 3:
                cue['text'] = f"{parts[0].strip()} │ {new_theme.upper()} │ {parts[2].strip()}"
            
            return True
        return False
        
    def insert_start_and_end(self, end_mode):
        if getattr(self, "_start_end_inserted", False):
            return
            
        blackout_data = {
            "FRONT_WASH": {"intensity": 0, "color": "#000000"},
            "BACK_LIGHT": {"intensity": 0, "color": "#000000"},
            "SIDE_FILL": {"intensity": 0, "color": "#000000"},
            "SPECIALS": {"intensity": 0, "color": "#000000"},
            "AMBIENT": {"intensity": 0, "color": "#000000"},
            "SMOKE": False
        }
        
        neutral_data = {
            "FRONT_WASH": {"intensity": 100, "color": "#FFFFFF"},
            "BACK_LIGHT": {"intensity": 100, "color": "#FFFFFF"},
            "SIDE_FILL": {"intensity": 80, "color": "#FFFFFF"},
            "SPECIALS": {"intensity": 100, "color": "#FFFFFF"},
            "AMBIENT": {"intensity": 100, "color": "#FFFFFF"},
            "SMOKE": False
        }

        # Cue 0: Immediate Blackout
        start_cue = {
            "id": -1,
            "text": "START │ BLACKOUT │ \"Preparing Simulation...\"",
            "script_line": "[System] Preparing Simulation...",
            "script_full": "[System] Preparing Simulation...",
            "scene": "BLACKOUT",
            "data": blackout_data,
            "duration": 1.5, 
            "transition_type": "cut", 
            "transition_duration": 0.0,
        }
        
        # End Cue:
        if end_mode == "neutral":
            end_cue = {
                "id": -1,
                "text": "END │ NEUTRAL │ \"Simulation Complete.\"",
                "script_line": "[System] Simulation Complete (Neutral)",
                "script_full": "[System] Simulation Complete (Neutral)",
                "scene": "NEUTRAL",
                "data": neutral_data,
                "duration": 10.0,
                "transition_type": "fade",
                "transition_duration": 4.0,
            }
        else:
            end_cue = {
                "id": -1,
                "text": "END │ BLACKOUT │ \"Simulation Complete.\"",
                "script_line": "[System] Simulation Complete (Fade Out)",
                "script_full": "[System] Simulation Complete (Fade Out)",
                "scene": "BLACKOUT",
                "data": blackout_data,
                "duration": 10.0,
                "transition_type": "fade",
                "transition_duration": 4.0,
            }
            
        # Ensure first real cue fades in
        if len(self.cues) > 0:
            self.cues[0]["transition_type"] = "fade"
            self.cues[0]["transition_duration"] = 3.0

        # Insert: START → [real cues] → FADE_TO_BLACK → END
        fade_to_black_cue = {
            "id": -1,
            "text": "FADE OUT │ BLACKOUT │ \"Fading to black...\"",
            "script_line": "[System] Fading to black...",
            "script_full": "[System] The show has ended. Fading all lights to black...",
            "scene": "FADE_OUT",
            "data": blackout_data,
            "duration": 5.0,
            "transition_type": "fade",
            "transition_duration": 5.0,
        }

        self.cues.insert(0, start_cue)
        self.cues.append(fade_to_black_cue)
        self.cues.append(end_cue)
        
        # Re-index
        for i, c in enumerate(self.cues):
            c["id"] = i
            
        self._start_end_inserted = True

    def get_state(self):
        """Build state payload for the frontend."""
        idx = self.current_index
        total = len(self.cues)

        # Context window: prev 3, current, next 4
        context = []
        for i in range(max(0, idx - 3), min(total, idx + 5)):
            cue = self.cues[i].copy()
            cue['active'] = (i == idx)
            # Remove heavy data from context (frontend doesn't need it for list display)
            cue.pop('data', None)
            context.append(cue)

        curr_cue = self.cues[idx] if 0 <= idx < total else None

        return {
            "type": "state_update",
            "is_holding": self.is_holding,
            "current_index": idx,
            "total_cues": total,
            "context_window": context,
            "scene_data": curr_cue["data"] if curr_cue else None,
            "transition_type": curr_cue.get("transition_type", "fade") if curr_cue else "fade",
            "transition_duration": curr_cue.get("transition_duration", 2.0) if curr_cue else 2.0,
        }

    def next_cue(self):
        if self.current_index < len(self.cues) - 1:
            self.current_index += 1
            cue = self.cues[self.current_index]
            print(f"  ▶ Cue {self.current_index}: {cue['scene']} ({cue['transition_type']})")
            return True
        return False

    def prev_cue(self):
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False


engine = CueEngine()


async def handler(websocket):
    engine.clients.add(websocket)
    try:
        # Send initial state immediately
        await websocket.send(json.dumps(engine.get_state()))

        async for message in websocket:
            msg = json.loads(message)
            cmd = msg.get("command")

            changed = False
            if cmd == "NEXT":
                changed = engine.next_cue()
            elif cmd == "PREV":
                changed = engine.prev_cue()
            elif cmd == "JUMP":
                idx = msg.get("index")
                if idx is not None and 0 <= idx < len(engine.cues):
                    engine.current_index = idx
                    changed = True
            elif cmd == "HOLD":
                engine.is_holding = not engine.is_holding
                status = "⏸ HOLDING" if engine.is_holding else "▶ RESUMED"
                print(f"  {status}")
                changed = True
            elif cmd == "RELOAD":
                engine.load_instructions()
                changed = True
            elif cmd == "THEME":
                idx = msg.get("index")
                new_theme = msg.get("theme")
                if idx is not None and new_theme:
                    changed = engine.override_theme(idx, new_theme)
            elif cmd == "OVERRIDE":
                idx = msg.get("index")
                text = msg.get("text")
                if idx is not None and text:
                    changed = engine.override_cue_lighting(idx, text)
            elif cmd == "START_SIM":
                end_mode = msg.get("endMode", "fade_out")
                engine.insert_start_and_end(end_mode)
                engine.current_index = 0
                engine.is_holding = False
                changed = True

            if changed:
                state = json.dumps(engine.get_state())
                for client in list(engine.clients):
                    try:
                        await client.send(state)
                    except:
                        engine.clients.discard(client)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        engine.clients.discard(websocket)


async def auto_runner():
    """Auto-advance cues based on their time_window durations."""
    while True:
        if not engine.is_holding and engine.current_index < len(engine.cues) - 1:
            curr = engine.cues[engine.current_index]
            duration = curr.get("duration", 3.0)

            await asyncio.sleep(duration)

            # Double-check hold state after sleep
            if not engine.is_holding:
                if engine.next_cue():
                    state = json.dumps(engine.get_state())
                    for client in list(engine.clients):
                        try:
                            await client.send(state)
                        except:
                            engine.clients.discard(client)
        else:
            await asyncio.sleep(0.5)


async def main():
    async with websockets.serve(handler, HOST, PORT):
        print(f"🎭 Lighting Console running on ws://{HOST}:{PORT}")
        print(f"   Waiting for 'current_show.json'...")
        await auto_runner()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopping Console...")
