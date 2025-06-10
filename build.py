import os
import subprocess
import sys

def activate_virtualenv():
    # Path to activate virtual environment
    activate_script = "myenv\\Scripts\\activate.bat"
    if not os.path.exists(activate_script):
        print("Virtual environment not found!")
        sys.exit(1)

    # Activate virtual environment
    subprocess.call(activate_script, shell=True)

def install_dependencies():
    # Install dependencies from requirements.txt
    subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def create_executable():
    # Use PyInstaller to create the executable
    subprocess.call([sys.executable, "-m", "PyInstaller", "--onefile", "--clean", "--distpath", "run", "--name", "my_program.exe", "main.py"])

if __name__ == "__main__":
    #activate_virtualenv()
    #install_dependencies()  # Uncomment if you need to install dependencies each time
    create_executable()
    print("Build complete. Executable is located in the 'dist' folder.")
