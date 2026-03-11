import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles # Although we embed HTML for single-file simplicity here
import json
import dataclasses

# Import the World definition
from ..world.layout import INSTALLED_FIXTURES
from ..world.geometry import STAGE, TRUSSES

# Helper to serialize Dataclasses
class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

app = FastAPI()

@app.get("/")
async def get_sim():
    # 1. Serialize the detailed world state (Static Geometry)
    world_config = json.dumps({
        "stage": STAGE,
        "trusses": TRUSSES,
        "fixtures": INSTALLED_FIXTURES
    }, cls=EnhancedJSONEncoder)
    
    # 2. Embed into the HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Phase 9: Digital Twin Prototype</title>
        <style>body {{ margin: 0; overflow: hidden; background: #000; }}</style>
        <script async src="https://unpkg.com/es-module-shims@1.6.3/dist/es-module-shims.js"></script>
        <script type="importmap">
          {{
            "imports": {{
              "three": "https://unpkg.com/three@0.150.0/build/three.module.js",
              "three/addons/": "https://unpkg.com/three@0.150.0/examples/jsm/"
            }}
          }}
        </script>
    </head>
    <body>
        <script type="module">
            import * as THREE from 'three';
            import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
            import {{ RectAreaLightHelper }} from 'three/addons/helpers/RectAreaLightHelper.js';

            // --- 1. Load World Configuration ---
            const WORLD = {world_config};
            console.log("Loaded High-Fidelity World:", WORLD);

            // --- 2. Setup Scene (Physics Scale: 1 unit = 1 meter) ---
            const scene = new THREE.Scene();
            scene.fog = new THREE.FogExp2(0x050505, 0.05); // Atmospheric haze
            
            // Add Ambient Light so it's not pitch black
            const ambientLight = new THREE.AmbientLight(0x222222);
            scene.add(ambientLight);
            
            const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
            camera.position.set(0, 5, 15); // 5m up, 15m back (House Center)
            
            const renderer = new THREE.WebGLRenderer({{ antialias: true, logarithmicDepthBuffer: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.outputEncoding = THREE.sRGBEncoding;
            document.body.appendChild(renderer.domElement);

            const controls = new OrbitControls(camera, renderer.domElement);
            controls.target.set(0, 1, 0); // Look at stage center
            controls.update();

            // --- 3. Build Geometry ---
            
            // Stage Deck
            const deckGeo = new THREE.BoxGeometry(WORLD.stage.width, WORLD.stage.height, WORLD.stage.depth);
            const deckMat = new THREE.MeshStandardMaterial({{ color: 0x222222, roughness: 0.8 }});
            const deck = new THREE.Mesh(deckGeo, deckMat);
            deck.position.set(0, WORLD.stage.height / 2, -WORLD.stage.depth / 2 + WORLD.stage.apron_depth); 
            deck.receiveShadow = true;
            scene.add(deck);
            
            // Trusses (Visual Checks)
            const trussMat = new THREE.MeshBasicMaterial({{ color: 0x444444, wireframe: true }});
            WORLD.trusses.forEach(t => {{
                const geo = new THREE.CylinderGeometry(0.05, 0.05, t.width);
                const mesh = new THREE.Mesh(geo, trussMat);
                mesh.rotation.z = Math.PI / 2;
                mesh.position.set(t.x, t.y, t.z);
                scene.add(mesh);
            }});

            // --- 4. Spawn Fixtures (High Fidelity) ---
            const fixtures = {{}}; // Map UID -> Object
            
            WORLD.fixtures.forEach(f => {{
                const group = new THREE.Group();
                group.position.set(f.position.x, f.position.y, f.position.z);
                
                // Rotation (Look at stage center 0,1,0 for now)
                group.lookAt(0, 1, -5); 
                
                // Body
                const bodyGeo = new THREE.BoxGeometry(0.3, 0.3, 0.4);
                const bodyMat = new THREE.MeshStandardMaterial({{ color: 0x111111 }});
                const body = new THREE.Mesh(bodyGeo, bodyMat);
                group.add(body);
                
                // Actual Light Source
                // Using SpotLight for directionality
                const light = new THREE.SpotLight(0xffffff);
                
                // Physical Falloff logic (Approximation)
                light.intensity = 0; // Start off
                // CRITICAL FIX: Spec is Full Angle, Three.js wants Half Angle from center
                light.angle = (f.profile.beam_angle_range[1] / 2) * (Math.PI / 180); 
                light.penumbra = 0.5;
                light.decay = 2;
                light.distance = 20;
                light.castShadow = true;
                light.shadow.bias = -0.0001;
                
                group.add(light);
                group.add(light.target);
                light.target.position.set(0, 0, -1); // Local forward
                
                // Volumetric Cone (Visual only)
                const coneGeo = new THREE.ConeGeometry(Math.tan(light.angle)*10, 10, 32, 1, true);
                coneGeo.translate(0, -5, 0);
                const coneMat = new THREE.MeshBasicMaterial({{
                    color: 0xffffff,
                    transparent: true,
                    opacity: 0,
                    side: THREE.BackSide, // Inside of cone
                    blending: THREE.AdditiveBlending,
                    depthWrite: false
                }});
                const cone = new THREE.Mesh(coneGeo, coneMat);
                cone.rotation.x = -Math.PI / 2;
                group.add(cone);

                scene.add(group);
                
                // Store ref
                fixtures[f.uid] = {{ light, cone, mat: coneMat, profile: f.profile }};
            }});

            // --- 5. Expose Control API (For Adapter) ---
            window.updateFixture = (uid, intensity, colorHex) => {{
                const f = fixtures[uid];
                if (!f) return;
                
                const col = new THREE.Color(colorHex);
                
                // Update Light
                // Scale 0-1 intensity to physical-ish units
                if (f.profile.luminous_flux_approx > 0) {{
                    f.light.intensity = intensity * 50; 
                    f.light.color.copy(col);
                
                    // Update Cone
                    // Reduced opacity for cleaner look (0.1 -> 0.05)
                    f.mat.opacity = intensity * 0.05; 
                    f.mat.color.copy(col);
                }}
            }};

            // Animation Loop
            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();
            
            // Console check
            console.log("Renderer Ready. Call window.updateFixture(uid, 1, '#ff0000') to test.");

            // --- AUTO-TEST SEQUENCE (Fixed for New Layout) ---
            setTimeout(() => {{
                console.log("Autotest: Face Pipe Left ON (Warm)");
                // Turn on the 5 Left fixtures
                window.updateFixture("LX_Face_Pipe_Face_L1", 1.0, "#ffb347");
                window.updateFixture("LX_Face_Pipe_Face_L2", 1.0, "#ffb347");
                window.updateFixture("LX_Face_Pipe_Face_L3", 1.0, "#ffb347");
                window.updateFixture("LX_Face_Pipe_Face_L4", 1.0, "#ffb347");
                window.updateFixture("LX_Face_Pipe_Face_L5", 1.0, "#ffb347");
            }}, 2000);

            setTimeout(() => {{
                console.log("Autotest: Face Pipe Right ON (Cool)");
                // Turn on the 5 Right fixtures
                window.updateFixture("LX_Face_Pipe_Face_R1", 1.0, "#4A90E2");
                window.updateFixture("LX_Face_Pipe_Face_R2", 1.0, "#4A90E2");
                window.updateFixture("LX_Face_Pipe_Face_R3", 1.0, "#4A90E2");
                window.updateFixture("LX_Face_Pipe_Face_R4", 1.0, "#4A90E2");
                window.updateFixture("LX_Face_Pipe_Face_R5", 1.0, "#4A90E2");
            }}, 4000);
            
            setTimeout(() => {{
                console.log("Autotest: Upstage Movers ON (Magenta)");
                window.updateFixture("LX_Upstage_Mover_L1", 1.0, "#ff00ff");
                window.updateFixture("LX_Upstage_Mover_R1", 1.0, "#ff00ff");
            }}, 6000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    # Standalone run
    uvicorn.run(app, host="0.0.0.0", port=9000) 
