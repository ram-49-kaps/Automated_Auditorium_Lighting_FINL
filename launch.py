#!/usr/bin/env python3
import subprocess
import sys
import os
import time

def print_header(msg):
    print(f"\n{'='*50}\n{msg}\n{'='*50}\n")

def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(project_root, "frontend")

    print_header("Launching Automated Auditorium Lighting")

    # Start Backend
    print("Starting Backend API (FastAPI) on port 8000...")
    print("Using conda environment: venv_ALG_311")
    backend_cmd = ["conda", "run", "-n", "venv_ALG_311", "python", "-m", "backend.app"]
    
    try:
        backend_process = subprocess.Popen(
            backend_cmd, 
            cwd=project_root,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
    except FileNotFoundError:
        print("Error: 'conda' command not found. Please ensure Conda is installed and in your PATH.")
        sys.exit(1)

    time.sleep(2) # Give backend a moment to start

    # Start Frontend
    print("\nStarting Frontend (Vite/React) on port 5173...")
    frontend_cmd = ["npm", "run", "dev"]
    
    try:
        frontend_process = subprocess.Popen(
            frontend_cmd,
            cwd=frontend_dir,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
    except FileNotFoundError:
        print("Error: 'npm' command not found. Please ensure Node.js is installed and in your PATH.")
        backend_process.terminate()
        sys.exit(1)

    print_header("System is running! Press Ctrl+C to stop all services.")
    print("Frontend URL: http://localhost:5173")
    print("Backend URL: http://localhost:8000")

    try:
        # Keep the script running to hold the child processes
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n\nShutting down services...")
        backend_process.terminate()
        frontend_process.terminate()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
