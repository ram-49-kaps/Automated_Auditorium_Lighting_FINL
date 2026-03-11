<div align="center">
  <img src="frontend/public/lumina-logo.svg" alt="Lumina Logo" width="120" />
  <h1>Automated Auditorium Lighting System</h1>
  <p><em>An intelligent, AI-driven pipeline that transcribes scripts, analyzes emotional arcs, and automatically orchestrates dynamic stage lighting cues.</em></p>
  
  [![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)](#)
  [![Vite](https://img.shields.io/badge/vite-%23646CFF.svg?style=for-the-badge&logo=vite&logoColor=white)](#)
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](#)
  [![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white)](#)
  [![OpenAI](https://img.shields.io/badge/OpenAI-412991.svg?style=for-the-badge&logo=OpenAI&logoColor=white)](#)
</div>

<hr />

## 🌟 Overview

The **Automated Auditorium Lighting System** bridge the gap between human storytelling and technical stage production. By ingesting raw theatrical scripts or event schedules, the system leverages advanced Natural Language Processing (NLP) to segment scenes, analyze emotional sentiment, cross-reference professional stage lighting principles (via RAG), and dynamically generate highly accurate lighting cues (DMX values, fixtures, colors, and transitions) that perfectly match the mood of the performance.

## 🏗️ Architecture & Pipeline Phases

The project is structured into a rigorous multi-phase pipeline, orchestrated by a highly concurrent FastAPI backend and presented via a sleek React frontend.

| Phase | Component | Description | Technologies |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Ingestion & Segmentation** | Parses `.pdf`, `.docx`, and `.txt`. Uses LLMs to cleanly segment unstructured text into JSON scenes with timestamp estimations. | `PyPDF2`, `python-docx` |
| **Phase 2** | **Emotion Enrichment** | Analyzes dialogue and action lines to detect core emotions, valance, and arousal. Includes multi-lingual sentiment support. | `DistilRoBERTa`, `PyTorch` |
| **Phase 3** | **Dual RAG Knowledge** | Retrieves rules from standard stage lighting handbooks and maps semantic narrative states to valid lighting paradigms. | `FAISS`, `SentenceTransformers` |
| **Phase 4** | **Decision Engine** | Synthesizes emotional data and RAG rules into concrete lighting instructions (Color HEX, Intensity %, Transitions). | Custom Heuristics |
| **Phase 5** | **Simulation** | Real-time WebGL/Three.js 3D visualization mapping the generated cues to a virtual stage environments. | `Three.js`, `React Three Fiber` |
| **Phase 6** | **Orchestration** | Validates internal cue consistency, ensuring smooth DMX transitions and resolving conflicting fixture instructions. | `Pydantic` |
| **Phase 7** | **Evaluation & Metrics** | Benchmarks generated cues against industry standards, reporting on stability, coverage, and narrative congruence. | Custom Evaluation Suite |

## 🛠️ Technology Stack

### Frontend (Client)
- **Framework:** React 18, Vite
- **Styling:** TailwindCSS, Framer Motion (Micro-animations)
- **Data Visualization:** Recharts, WebGL (Phase 5)
- **Communication:** Axios, WebSockets (for real-time simulation)

### Backend (Server)
- **API Framework:** FastAPI (Python 3)
- **AI/ML:** PyTorch, HuggingFace Transformers (`DistilRoBERTa`), OpenAI API
- **Vector Database:** FAISS (Facebook AI Similarity Search)
- **Validation:** Pydantic

## 🚀 Getting Started

Ensure you have Python 3.10+ and Node.js 18+ installed on your machine.

### 1. Backend Setup

```bash
# Navigate to the project root
cd Automated_Auditorium_Lighting_Ram

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server (runs on port 8000)
uvicorn main:app --reload
```

### 2. Frontend Setup

```bash
# Open a new terminal and navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server (runs on port 5173)
npm run dev
```

### 3. Environment Variables
Create a `.env` file in the root directory and add any required API keys (e.g., `OPENAI_API_KEY` for advanced scene segmentation).

## 💡 Usage

1. Open your browser and navigate to `http://localhost:5173`.
2. Upload a script file (`.pdf`, `.txt`, `.docx`) via the modern drag-and-drop interface.
3. Watch the real-time processing pipeline extract scenes, analyze sentiment, and apply RAG models.
4. View the generated lighting cues in the Results Dashboard.
5. *(Optional)* Launch the Phase 5 visualization to see the lights simulated on a 3D stage.

## 🤝 Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a pull request. Ensure all new ML models or dependencies are properly documented in the `requirements.txt`.

## 📄 License

This project is licensed under the MIT License.