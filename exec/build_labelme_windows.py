import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
import venv

class LabelmeWindowsBuilder:
    def __init__(self):
        self.script_dir = Path(__file__).parent.resolve()
        self.root_dir = self.script_dir.parent
        self.app_dir = self.root_dir / "labelme"
        self.venv_path = Path.home() / ".venvs" / "labelme-build-windows"

        # ANSI codes for color output (supported in Windows Terminal)
        self.colors = {
            'RED': '\033[0;31m',
            'GREEN': '\033[0;32m',
            'YELLOW': '\033[1;33m',
            'BLUE': '\033[0;34m',
            'NC': '\033[0m'  # No Color
        }

        # Use colorama for color support on Windows
        try:
            import colorama
            colorama.init(autoreset=True)
        except ImportError:
            # If colorama is not available, disable colors
            self.colors = {k: '' for k in self.colors.keys()}

    def print_colored(self, message, color='NC'):
        """Print a colored message"""
        print(f"{self.colors[color]}{message}{self.colors['NC']}")

    def check_requirements(self):
        """Check system requirements"""
        self.print_colored("🔍 Checking system requirements...", 'YELLOW')

        # Check for Windows
        if platform.system() != 'Windows':
            self.print_colored("❌ This script only runs on Windows.", 'RED')
            sys.exit(1)

        # Check Python version
        if sys.version_info < (3, 6):
            self.print_colored("❌ Python 3.6 or higher is required.", 'RED')
            sys.exit(1)

        self.print_colored(f"✅ Python {sys.version.split()[0]} confirmed", 'GREEN')
        self.print_colored(f"✅ Windows {platform.release()} confirmed", 'GREEN')

    def setup_virtual_environment(self):
        """Set up virtual environment"""
        self.print_colored("📦 Setting up virtual environment...", 'YELLOW')

        if self.venv_path.exists():
            self.print_colored(f"🔄 Removing existing virtual environment: {self.venv_path}", 'YELLOW')
            shutil.rmtree(self.venv_path)

        # Create virtual environment
        self.print_colored(f"📦 Creating virtual environment: {self.venv_path}", 'YELLOW')
        venv.create(self.venv_path, with_pip=True, clear=True)

        # Set paths for virtual environment activation
        if platform.system() == 'Windows':
            self.python_exe = self.venv_path / "Scripts" / "python.exe"
            self.pip_exe = self.venv_path / "Scripts" / "pip.exe"
        else:
            self.python_exe = self.venv_path / "bin" / "python"
            self.pip_exe = self.venv_path / "bin" / "pip"

        if not self.python_exe.exists():
            self.print_colored("❌ Failed to create virtual environment", 'RED')
            sys.exit(1)

        self.print_colored("✅ Virtual environment created successfully", 'GREEN')

    def run_pip_command(self, args):
        """Run pip command"""
        cmd = [str(self.python_exe), "-m", "pip"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            self.print_colored(f"❌ Failed to run pip command: {' '.join(args)}", 'RED')
            self.print_colored(f"Error: {result.stderr}", 'RED')
            sys.exit(1)
        return result

    def install_packages(self):
        """Install required packages"""
        self.print_colored("📦 Installing required packages...", 'YELLOW')

        # Upgrade pip
        self.print_colored("⬆️ Upgrading pip...", 'YELLOW')
        self.run_pip_command(["install", "--upgrade", "pip", "setuptools", "wheel"])

        # Install PyInstaller
        self.print_colored("🔨 Installing PyInstaller...", 'YELLOW')
        self.run_pip_command(["install", "pyinstaller"])

        # Install labelme dependencies
        self.print_colored("📚 Installing labelme dependencies...", 'YELLOW')
        dependencies = [
            "imgviz>=0.11",
            "matplotlib>=3.3",
            "natsort>=7.1.0",
            "numpy",
            "Pillow>=6.2",
            "PyYAML",
            "qtpy!=1.11.2",
            "termcolor",
            "cryptography",
            "lxml",
            "requests",
            "opencv-python-headless>=4.6.0",  # headless version to prevent Qt conflicts
            "PyQt5!=5.15.3,!=5.15.4",
            "colorama"
        ]

        self.print_colored(f"  📦 Installing {len(dependencies)}...", 'BLUE')
        self.run_pip_command(["install"] + dependencies)

        # Install labelme in development mode
        self.print_colored("🏷️ Installing labelme package...", 'YELLOW')
        os.chdir(str(self.root_dir))
        self.run_pip_command(["install", "-e", "."])

        self.print_colored("✅ All packages installed successfully", 'GREEN')

    def prepare_build_files(self):
        """Prepare files required for build"""
        self.print_colored("📋 Preparing build files...", 'YELLOW')

        # Check for existence of required files
        version_xml = self.root_dir / "version.xml"
        package_xml = self.root_dir / "package.xml"

        if version_xml.exists():
            shutil.copy2(version_xml, self.app_dir / "version.xml")
            self.print_colored("✅ version.xml copied successfully", 'GREEN')
        else:
            self.print_colored("⚠️ version.xml not found", 'YELLOW')

        if package_xml.exists():
            shutil.copy2(package_xml, self.app_dir / "package.xml")  
            self.print_colored("✅ package.xml copied successfully", 'GREEN')
        else:
            self.print_colored("⚠️ package.xml not found", 'YELLOW')

    def clean_build_directories(self):
        """Clean build directories"""
        self.print_colored("🧹 Cleaning up previous build files...", 'YELLOW')

        os.chdir(str(self.app_dir))

        dirs_to_clean = ["build", "dist"]
        files_to_clean = ["*.spec"]

        for dir_name in dirs_to_clean:
            dir_path = Path(dir_name)
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    self.print_colored(f"  🗑️ Removed directory {dir_name}", 'BLUE')
                except PermissionError as e:
                    self.print_colored(f"  ⚠️ Failed to remove directory {dir_name} (Permission issue): {e}", 'YELLOW')
                    # Attempt to delete individual files
                    try:
                        import time
                        time.sleep(1)  # Wait a moment
                        for root, dirs, files in os.walk(dir_path, topdown=False):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    os.chmod(file_path, 0o777)  # Change permissions
                                    os.remove(file_path)
                                except:
                                    pass
                            for dir in dirs:
                                try:
                                    os.rmdir(os.path.join(root, dir))
                                except:
                                    pass
                        try:
                            os.rmdir(dir_path)
                            self.print_colored(f"  🗑️ Force removed directory {dir_name} successfully", 'BLUE')
                        except:
                            self.print_colored(f"  ⚠️ Some files in {dir_name} could not be removed (continuing)", 'YELLOW')
                    except Exception as cleanup_error:
                        self.print_colored(f"  ⚠️ Error during cleanup of {dir_name}: {cleanup_error} (ignoring and continuing)", 'YELLOW')
                except Exception as e:
                    self.print_colored(f"  ⚠️ Error while removing directory {dir_name}: {e} (ignoring and continuing)", 'YELLOW')

        import glob
        for pattern in files_to_clean:
            try:
                for file_path in glob.glob(pattern):
                    os.remove(file_path)
                    self.print_colored(f"  🗑️ Removed file {file_path}", 'BLUE')
            except Exception as e:
                self.print_colored(f"  ⚠️ Error while removing files with pattern {pattern}: {e} (ignoring and continuing)", 'YELLOW')

    def get_qt_plugins_path(self):
        """Find Windows PyQt5 plugin path"""
        try:
            # Find PyQt5 path in virtual environment
            result = subprocess.run([
                str(self.python_exe), "-c",
                "import PyQt5; import os; print(os.path.dirname(PyQt5.__file__))"
            ], capture_output=True, text=True, encoding='utf-8')

            if result.returncode == 0:
                pyqt5_path = Path(result.stdout.strip())
                plugins_path = pyqt5_path / "Qt5" / "plugins"
                if plugins_path.exists():
                    return str(plugins_path)

                # Try other possible paths
                alt_paths = [
                    pyqt5_path / "Qt" / "plugins",
                    pyqt5_path.parent / "PyQt5" / "Qt5" / "plugins"
                ]

                for path in alt_paths:
                    if path.exists():
                        return str(path)

        except Exception as e:
            self.print_colored(f"⚠️ Failed to auto-detect Qt plugin path: {e}", 'YELLOW')

        return None

    def build_executable(self):
        """Build executable with PyInstaller"""
        self.print_colored("🔨 Building executable with PyInstaller...", 'GREEN')
        self.print_colored("⏱️ This process may take a few minutes...", 'YELLOW')

        # Find Qt plugin path
        qt_plugins_path = self.get_qt_plugins_path()
        if qt_plugins_path:
            self.print_colored(f"🔧 Qt plugin path: {qt_plugins_path}", 'BLUE')
        else:
            self.print_colored("⚠️ Qt plugin path not found. Using default settings.", 'YELLOW')

        # Configure PyInstaller command
        pyinstaller_cmd = [
            str(self.python_exe), "-m", "PyInstaller",
            "--onefile",
            "--console",  # Change to support both GUI and Console
            "--name", "labelme",
            "--icon", str(self.app_dir / "icons" / "icon.ico"),
            "--distpath", str(self.app_dir / "dist"),
            "--workpath", str(self.app_dir / "build"),
            "--specpath", str(self.app_dir),

            # Hidden imports
            "--hidden-import", "yaml",
            "--hidden-import", "_yaml",
            "--hidden-import", "qtpy",
            "--hidden-import", "qtpy.QtCore",
            "--hidden-import", "qtpy.QtWidgets",
            "--hidden-import", "qtpy.QtGui",
            "--hidden-import", "qtpy.QtOpenGL",
            "--hidden-import", "qtpy.QtPrintSupport",
            "--hidden-import", "termcolor",
            "--hidden-import", "colorama",
            "--hidden-import", "imgviz",
            "--hidden-import", "matplotlib",
            "--hidden-import", "matplotlib.backends.backend_qt5agg",
            "--hidden-import", "natsort",
            "--hidden-import", "numpy",
            "--hidden-import", "PIL",
            "--hidden-import", "PIL.Image",
            "--hidden-import", "PIL.ImageDraw",
            "--hidden-import", "PIL.ImageFilter",
            "--hidden-import", "lxml",
            "--hidden-import", "requests",
            "--hidden-import", "cv2",

            # Exclude modules
            "--exclude-module", "PySide6",
            "--exclude-module", "PySide2",
            "--exclude-module", "PyQt6",
            "--exclude-module", "tkinter",
            "--exclude-module", "tornado",
            "--exclude-module", "sphinx",
            "--exclude-module", "IPython",
            "--exclude-module", "jupyter",

            # Add data files
            "--add-data", f"{self.root_dir}/version.xml;.",
            "--add-data", f"{self.root_dir}/package.xml;.",
            "--add-data", f"{self.app_dir}/config;labelme/config",
            "--add-data", f"{self.app_dir}/icons;labelme/icons",
            "--add-data", f"{self.app_dir}/translate;labelme/translate",
            "--add-data", f"{self.app_dir}/cli;labelme/cli",

            # Include all labelme package data
            "--add-data", f"{self.app_dir}/__init__.py;labelme",

            # Additional resource files
            "--add-data", f"{self.root_dir}/README.md;.",
            "--add-data", f"{self.root_dir}/LICENSE;.",

            # Collect all of PyQt5
            "--collect-all", "PyQt5",
            "--collect-all", "qtpy",

            # Runtime hooks
            "--runtime-hook", str(self.script_dir / "pyi_rth_console_fix.py"),
            "--runtime-hook", str(self.script_dir / "pyi_rth_qt_plugins.py"),
            "--runtime-hook", str(self.script_dir / "pyi_rth_labelme_resources.py"),
            "--runtime-hook", str(self.script_dir / "pyi_rth_resource_path_fix.py"),
            "--runtime-hook", str(self.script_dir / "pyi_rth_user_data_fix.py"),

            # Optimization options
            "--strip",
            "--noupx",

            str(self.app_dir / "__main__.py")
        ]

        # Add Qt plugins if they exist
        if qt_plugins_path:
            qt_path = Path(qt_plugins_path)
            plugin_dirs = ["platforms", "imageformats", "iconengines", "styles"]

            for plugin_dir in plugin_dirs:
                src_path = qt_path / plugin_dir
                if src_path.exists():
                    pyinstaller_cmd.extend([
                        "--add-binary", f"{src_path};qt5_plugins/{plugin_dir}"
                    ])

            # Add Qt5 lib folder (including fonts)
            qt5_lib_path = qt_path.parent / "Qt5" / "lib"
            if qt5_lib_path.exists():
                pyinstaller_cmd.extend([
                    "--add-binary", f"{qt5_lib_path};PyQt5/Qt5/lib"
                ])

            # Add environment variable setting to use Windows system fonts
            pyinstaller_cmd.extend([
                "--runtime-hook", str(self.script_dir / "pyi_rth_font_fix.py")
            ])

        # Run PyInstaller
        self.print_colored("🚀 Running PyInstaller...", 'GREEN')

        # Add SSL libraries
        ssl_dlls = self.find_openssl_dlls()
        for dll_path in ssl_dlls:
            pyinstaller_cmd.extend(["--add-binary", f"{dll_path};."])

        result = subprocess.run(pyinstaller_cmd, cwd=str(self.app_dir))

        if result.returncode != 0:
            self.print_colored("❌ PyInstaller build failed", 'RED')
            sys.exit(1)

        return result.returncode == 0

    def find_openssl_dlls(self):
        """Find OpenSSL DLLs in the Python environment"""
        python_dir = Path(self.python_exe).parent.parent
        dll_dir = python_dir / "DLLs"

        if not dll_dir.exists():
            self.print_colored(f"⚠️ DLLs directory not found at {dll_dir}", 'YELLOW')
            return []

        dll_files = []
        for dll in dll_dir.glob("libcrypto-*.dll"):
            dll_files.append(dll)
        for dll in dll_dir.glob("libssl-*.dll"):
            dll_files.append(dll)

        if dll_files:
            self.print_colored(f"✅ Found OpenSSL DLLs: {[f.name for f in dll_files]}", 'GREEN')
        else:
            self.print_colored("⚠️ Could not find OpenSSL DLLs (libcrypto-*.dll, libssl-*.dll)", 'YELLOW')

        return dll_files

    def verify_build_result(self):
        """Verify build result"""
        executable_path = self.app_dir / "dist" / "labelme.exe"

        if executable_path.exists():
            file_size = executable_path.stat().st_size / (1024 * 1024)  # MB
            self.print_colored("✅ Build successful!", 'GREEN')
            self.print_colored(f"📍 Executable location: {executable_path}", 'GREEN')
            self.print_colored(f"📊 File size: {file_size:.1f} MB", 'YELLOW')

            # Display file information
            self.print_colored("📋 File information:", 'YELLOW')
            self.print_colored(f"  - Path: {executable_path}", 'BLUE')
            self.print_colored(f"  - Size: {file_size:.1f} MB", 'BLUE')

            return True
        else:
            self.print_colored("❌ Build failed! Executable not found.", 'RED')

            # Check build log
            warn_file = self.app_dir / "build" / "labelme" / "warn-labelme.txt"
            if warn_file.exists():
                self.print_colored("📋 Build warnings:", 'YELLOW')
                with open(warn_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    for line in lines[-20:]:  # Display only the last 20 lines
                        print(f"  {line.rstrip()}")

            return False

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        self.print_colored("🧹 Cleaning up temporary files...", 'YELLOW')

        temp_files = [
            self.app_dir / "version.xml",
            self.app_dir / "package.xml"
        ]

        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()
                self.print_colored(f"  🗑️ Removed {temp_file.name}", 'BLUE')

    def print_final_instructions(self):
        """Final instructions"""
        executable_path = self.app_dir / "dist" / "labelme.exe"

        self.print_colored("=" * 50, 'GREEN')
        self.print_colored("✅ Build complete!", 'GREEN')
        self.print_colored("=" * 50, 'GREEN')

        self.print_colored("📋 Usage:", 'YELLOW')
        self.print_colored(f"  1. Executable file: {executable_path}", 'BLUE')
        self.print_colored("  2. Double-click to run", 'BLUE')
        self.print_colored("  3. Or from the command prompt: labelme.exe", 'BLUE')

        self.print_colored("\n⚠️ Notes:", 'YELLOW')
        self.print_colored("  - May be blocked by Windows Defender (set to 'Allow')", 'BLUE')
        self.print_colored("  - The first run may take some time", 'BLUE')
        self.print_colored("  - The executable can be copied to another PC for use", 'BLUE')

    def run_build(self):
        """Run the entire build process"""
        try:
            self.print_colored("🚀 Starting labelme Windows build...", 'GREEN')
            self.print_colored("🪟 Target: Windows (.exe file)", 'YELLOW')

            # Build steps
            self.check_requirements()
            self.setup_virtual_environment()
            self.install_packages()
            self.prepare_build_files()
            self.clean_build_directories()

            if self.build_executable():
                if self.verify_build_result():
                    self.cleanup_temp_files()
                    self.print_final_instructions()
                    self.print_colored("🎉 Build process completed successfully!", 'GREEN')
                    return True

            return False

        except KeyboardInterrupt:
            self.print_colored("\n⏹️ Build interrupted by user.", 'YELLOW')
            return False
        except Exception as e:
            self.print_colored(f"❌ An unexpected error occurred: {e}", 'RED')
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main execution function"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("labelme Windows Build Script")
        print("Usage: python build_labelme_windows.py")
        print("\nThis script generates the labelme.exe file in a Windows environment.")
        print("The build takes a few minutes and requires an internet connection.")
        return

    builder = LabelmeWindowsBuilder()
    success = builder.run_build()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()