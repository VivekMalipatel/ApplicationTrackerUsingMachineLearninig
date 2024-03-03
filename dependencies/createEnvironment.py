import subprocess
import platform

def create_conda_env():
    # Determine the OS
    os_type = platform.system()

    subprocess.run("conda update -n base -c defaults conda", shell=True)
    
    if os_type == "Darwin":  # macOS
        print("Detected macOS. Creating environment for osx-arm64.")
        # Create env for macOS ARM64
        subprocess.run("CONDA_SUBDIR=osx-arm64 conda create -n applicationTracker python=3.12 -c conda-forge --override-channels", shell=True)
        # Set CONDA_SUBDIR for the environment
        subprocess.run("conda env config vars set CONDA_SUBDIR=osx-arm64 -n applicationTracker", shell=True)
        
    elif os_type == "Windows":
        print("Detected Windows. Creating environment normally.")
        # Create env for Windows
        subprocess.run("conda create -n applicationTracker python=3.12 -c conda-forge --override-channels", shell=True)
        subprocess.run("conda activate applicationTracker", shell=True)
        
    else:
        print(f"Unsupported operating system: {os_type}")

if __name__ == "__main__":
    create_conda_env()
