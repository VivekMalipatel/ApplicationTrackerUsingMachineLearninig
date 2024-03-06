import subprocess
import sys
import platform

def run_command(command):
    try:
        subprocess.run(command, check=True, shell=True) 
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute command {' '.join(command)}: {e}")
        sys.exit(1)

def install_pytorch():
    os_type = platform.system()
    if os_type == "Darwin":  # macOS
        command = "conda install pytorch torchvision torchaudio -c pytorch"
    elif os_type == "Windows":
        cuda_version = get_cuda_version()
        if cuda_version:
            command = f"conda install --yes -c pytorch -c nvidia pytorch torchvision torchaudio cudatoolkit={cuda_version}"
        else:
            command = "conda install --yes -c pytorch torchvision torchaudio -c pytorch-nightly"
    else:
        print(f"Unsupported OS for PyTorch installation: {os_type}")
        sys.exit(1)
    run_command(command)

def get_cuda_version():
    try:
        result = subprocess.run(['nvcc', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if "release" in line:
                    return line.split(' ')[-2].replace(',', '') 
    except Exception as e:
        print(f"Error checking CUDA version: {e}")
    return None

def install_conda_dependencies():
    try:
        with open('dependencies/conda_dependencies.txt', 'r') as file:
            dependencies = file.read().splitlines()
        
        command1 = "conda update -n base -c defaults conda"
        command2 = "conda install -c conda-forge --yes " + " ".join(dependencies)
        
        run_command(command1)
        run_command(command2)
        install_pytorch()
        
    except FileNotFoundError as e:
        print(f"Failed to find the conda dependencies file: {e}")
        sys.exit(1)

def install_pip_dependencies():
    try:
        with open('dependencies/pip_dependencies.txt', 'r') as file:
            dependencies = file.read().splitlines()
        
        python_executable = sys.executable
        
        # Installing general pip dependencies
        command1 = [python_executable, '-m', 'pip', 'install', '--upgrade'] + dependencies
        subprocess.check_call(command1)
        
        # Downloading specific spacy model
        #command2 = [python_executable, '-m', 'spacy', 'download', 'en_core_web_trf']
        #subprocess.check_call(command2)

        if platform.system() == "Windows":
        
            python_command = 'python' if platform.system() == 'Windows' else 'python'
            command3 = [python_command, '-c', 'from', 'PIL', 'import', '_imaging']
            command4 = [python_command, '-c', 'from', 'PIL', 'import', 'Image, ImageOps, ImageFont, ImageDraw']
            run_command(command3)
            run_command(command4)
        
    except FileNotFoundError as e:
        print(f"Failed to find the pip dependencies file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_conda_dependencies()
    install_pip_dependencies()
    print("Dependencies Installed, Please restart the IDE")
