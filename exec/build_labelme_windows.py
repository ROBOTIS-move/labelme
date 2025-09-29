#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows용 labelme 실행 파일 빌드 스크립트
Windows 환경에서 직접 실행하여 labelme.exe 파일을 생성합니다.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
import venv
import site

class LabelmeWindowsBuilder:
    def __init__(self):
        self.script_dir = Path(__file__).parent.resolve()
        self.root_dir = self.script_dir.parent
        self.app_dir = self.root_dir / "labelme"
        self.venv_path = Path.home() / ".venvs" / "labelme-build-windows"
        
        # 색상 출력을 위한 ANSI 코드 (Windows Terminal에서 지원)
        self.colors = {
            'RED': '\033[0;31m',
            'GREEN': '\033[0;32m',
            'YELLOW': '\033[1;33m',
            'BLUE': '\033[0;34m',
            'NC': '\033[0m'  # No Color
        }
        
        # Windows에서 colorama 사용하여 색상 지원
        try:
            import colorama
            colorama.init(autoreset=True)
        except ImportError:
            # colorama가 없으면 색상 비활성화
            self.colors = {k: '' for k in self.colors.keys()}

    def print_colored(self, message, color='NC'):
        """색상이 있는 메시지 출력"""
        print(f"{self.colors[color]}{message}{self.colors['NC']}")

    def check_requirements(self):
        """시스템 요구사항 확인"""
        self.print_colored("🔍 시스템 요구사항 확인 중...", 'YELLOW')
        
        # Windows 확인
        if platform.system() != 'Windows':
            self.print_colored("❌ 이 스크립트는 Windows 환경에서만 실행됩니다.", 'RED')
            sys.exit(1)
            
        # Python 버전 확인
        if sys.version_info < (3, 6):
            self.print_colored("❌ Python 3.6 이상이 필요합니다.", 'RED')
            sys.exit(1)
            
        self.print_colored(f"✅ Python {sys.version.split()[0]} 확인됨", 'GREEN')
        self.print_colored(f"✅ Windows {platform.release()} 확인됨", 'GREEN')

    def setup_virtual_environment(self):
        """가상환경 설정"""
        self.print_colored("📦 가상환경 설정 중...", 'YELLOW')
        
        if self.venv_path.exists():
            self.print_colored(f"🔄 기존 가상환경 제거: {self.venv_path}", 'YELLOW')
            shutil.rmtree(self.venv_path)
        
        # 가상환경 생성
        self.print_colored(f"📦 가상환경 생성: {self.venv_path}", 'YELLOW')
        venv.create(self.venv_path, with_pip=True, clear=True)
        
        # 가상환경 활성화를 위한 경로 설정
        if platform.system() == 'Windows':
            self.python_exe = self.venv_path / "Scripts" / "python.exe"
            self.pip_exe = self.venv_path / "Scripts" / "pip.exe"
        else:
            self.python_exe = self.venv_path / "bin" / "python"
            self.pip_exe = self.venv_path / "bin" / "pip"
            
        if not self.python_exe.exists():
            self.print_colored("❌ 가상환경 생성 실패", 'RED')
            sys.exit(1)
            
        self.print_colored("✅ 가상환경 생성 완료", 'GREEN')

    def run_pip_command(self, args):
        """pip 명령어 실행"""
        cmd = [str(self.python_exe), "-m", "pip"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            self.print_colored(f"❌ pip 명령어 실행 실패: {' '.join(args)}", 'RED')
            self.print_colored(f"오류: {result.stderr}", 'RED')
            sys.exit(1)
        return result

    def install_packages(self):
        """필요한 패키지 설치"""
        self.print_colored("📦 필수 패키지 설치 중...", 'YELLOW')
        
        # pip 업그레이드
        self.print_colored("⬆️ pip 업그레이드...", 'YELLOW')
        self.run_pip_command(["install", "--upgrade", "pip", "setuptools", "wheel"])
        
        # PyInstaller 설치
        self.print_colored("🔨 PyInstaller 설치...", 'YELLOW')
        self.run_pip_command(["install", "pyinstaller"])
        
        # labelme 의존성 패키지들 설치
        self.print_colored("📚 labelme 의존성 패키지 설치...", 'YELLOW')
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
            "opencv-python-headless>=4.6.0",  # headless 버전으로 Qt 충돌 방지
            "PyQt5!=5.15.3,!=5.15.4",
            "colorama"
        ]
        
        for dep in dependencies:
            self.print_colored(f"  📦 {dep} 설치 중...", 'BLUE')
            self.run_pip_command(["install", dep])
        
        # labelme 개발 모드로 설치
        self.print_colored("🏷️ labelme 패키지 설치...", 'YELLOW')
        os.chdir(str(self.root_dir))
        self.run_pip_command(["install", "-e", "."])
        
        self.print_colored("✅ 모든 패키지 설치 완료", 'GREEN')

    def prepare_build_files(self):
        """빌드에 필요한 파일들 준비"""
        self.print_colored("📋 빌드 파일 준비 중...", 'YELLOW')
        
        # 필수 파일들 존재 확인
        version_xml = self.root_dir / "version.xml"
        package_xml = self.root_dir / "package.xml"
        
        if version_xml.exists():
            shutil.copy2(version_xml, self.app_dir / "version.xml")
            self.print_colored("✅ version.xml 복사 완료", 'GREEN')
        else:
            self.print_colored("⚠️ version.xml을 찾을 수 없습니다", 'YELLOW')
            
        if package_xml.exists():
            shutil.copy2(package_xml, self.app_dir / "package.xml")  
            self.print_colored("✅ package.xml 복사 완료", 'GREEN')
        else:
            self.print_colored("⚠️ package.xml을 찾을 수 없습니다", 'YELLOW')

    def clean_build_directories(self):
        """빌드 디렉토리 정리"""
        self.print_colored("🧹 이전 빌드 파일 정리 중...", 'YELLOW')
        
        os.chdir(str(self.app_dir))
        
        dirs_to_clean = ["build", "dist"]
        files_to_clean = ["*.spec"]
        
        for dir_name in dirs_to_clean:
            dir_path = Path(dir_name)
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    self.print_colored(f"  🗑️ {dir_name} 디렉토리 제거", 'BLUE')
                except PermissionError as e:
                    self.print_colored(f"  ⚠️ {dir_name} 디렉토리 제거 실패 (권한 문제): {e}", 'YELLOW')
                    # 개별 파일 삭제 시도
                    try:
                        import time
                        time.sleep(1)  # 잠시 대기
                        for root, dirs, files in os.walk(dir_path, topdown=False):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    os.chmod(file_path, 0o777)  # 권한 변경
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
                            self.print_colored(f"  🗑️ {dir_name} 디렉토리 강제 제거 성공", 'BLUE')
                        except:
                            self.print_colored(f"  ⚠️ {dir_name} 디렉토리 일부 파일 제거 불가 (계속 진행)", 'YELLOW')
                    except Exception as cleanup_error:
                        self.print_colored(f"  ⚠️ {dir_name} 정리 중 오류: {cleanup_error} (무시하고 계속)", 'YELLOW')
                except Exception as e:
                    self.print_colored(f"  ⚠️ {dir_name} 디렉토리 제거 중 오류: {e} (무시하고 계속)", 'YELLOW')
                
        import glob
        for pattern in files_to_clean:
            try:
                for file_path in glob.glob(pattern):
                    os.remove(file_path)
                    self.print_colored(f"  🗑️ {file_path} 파일 제거", 'BLUE')
            except Exception as e:
                self.print_colored(f"  ⚠️ {pattern} 패턴 파일 제거 중 오류: {e} (무시하고 계속)", 'YELLOW')

    def get_qt_plugins_path(self):
        """Windows PyQt5 플러그인 경로 찾기"""
        try:
            # 가상환경에서 PyQt5 경로 찾기
            result = subprocess.run([
                str(self.python_exe), "-c",
                "import PyQt5; import os; print(os.path.dirname(PyQt5.__file__))"
            ], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                pyqt5_path = Path(result.stdout.strip())
                plugins_path = pyqt5_path / "Qt5" / "plugins"
                if plugins_path.exists():
                    return str(plugins_path)
                    
                # 다른 가능한 경로들 시도
                alt_paths = [
                    pyqt5_path / "Qt" / "plugins",
                    pyqt5_path.parent / "PyQt5" / "Qt5" / "plugins"
                ]
                
                for path in alt_paths:
                    if path.exists():
                        return str(path)
                        
        except Exception as e:
            self.print_colored(f"⚠️ Qt 플러그인 경로 자동 감지 실패: {e}", 'YELLOW')
            
        return None

    def build_executable(self):
        """PyInstaller로 실행 파일 빌드"""
        self.print_colored("🔨 PyInstaller로 실행 파일 빌드 중...", 'GREEN')
        self.print_colored("⏱️ 이 과정은 몇 분이 소요될 수 있습니다...", 'YELLOW')
        
        # Qt 플러그인 경로 찾기
        qt_plugins_path = self.get_qt_plugins_path()
        if qt_plugins_path:
            self.print_colored(f"🔧 Qt 플러그인 경로: {qt_plugins_path}", 'BLUE')
        else:
            self.print_colored("⚠️ Qt 플러그인 경로를 찾을 수 없습니다. 기본 설정을 사용합니다.", 'YELLOW')
        
        # PyInstaller 명령어 구성
        pyinstaller_cmd = [
            str(self.python_exe), "-m", "PyInstaller",
            "--onefile",
            "--console",  # GUI와 Console 모두 지원하도록 변경
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
            
            # 제외할 모듈들
            "--exclude-module", "PySide6",
            "--exclude-module", "PySide2", 
            "--exclude-module", "PyQt6",
            "--exclude-module", "tkinter",
            "--exclude-module", "tornado",
            "--exclude-module", "sphinx",
            "--exclude-module", "IPython",
            "--exclude-module", "jupyter",
            
            # 데이터 파일들 추가
            "--add-data", f"{self.root_dir}/version.xml;.",
            "--add-data", f"{self.root_dir}/package.xml;.",
            "--add-data", f"{self.app_dir}/config;labelme/config",
            "--add-data", f"{self.app_dir}/icons;labelme/icons", 
            "--add-data", f"{self.app_dir}/translate;labelme/translate",
            
            # labelme 전체 패키지 데이터 포함
            "--add-data", f"{self.app_dir}/__init__.py;labelme",
            
            # 추가 리소스 파일들
            "--add-data", f"{self.root_dir}/README.md;.",
            "--add-data", f"{self.root_dir}/LICENSE;.",
            
            # 전체 PyQt5 수집
            "--collect-all", "PyQt5",
            "--collect-all", "qtpy",
            
            # 런타임 훅
            "--runtime-hook", str(self.script_dir / "pyi_rth_console_fix.py"),
            "--runtime-hook", str(self.script_dir / "pyi_rth_qt_plugins.py"),
            "--runtime-hook", str(self.script_dir / "pyi_rth_labelme_resources.py"),
            "--runtime-hook", str(self.script_dir / "pyi_rth_resource_path_fix.py"),
            "--runtime-hook", str(self.script_dir / "pyi_rth_user_data_fix.py"),
            
            # 최적화 옵션
            "--strip",
            "--noupx",
            
            str(self.app_dir / "__main__.py")
        ]
        
        # Qt 플러그인이 있으면 추가
        if qt_plugins_path:
            qt_path = Path(qt_plugins_path)
            plugin_dirs = ["platforms", "imageformats", "iconengines", "styles"]
            
            for plugin_dir in plugin_dirs:
                src_path = qt_path / plugin_dir
                if src_path.exists():
                    pyinstaller_cmd.extend([
                        "--add-binary", f"{src_path};qt5_plugins/{plugin_dir}"
                    ])
            
            # Qt5 lib 폴더 추가 (폰트 포함)
            qt5_lib_path = qt_path.parent / "Qt5" / "lib"
            if qt5_lib_path.exists():
                pyinstaller_cmd.extend([
                    "--add-binary", f"{qt5_lib_path};PyQt5/Qt5/lib"
                ])
            
            # Windows 시스템 폰트를 사용하도록 환경 변수 설정 추가
            pyinstaller_cmd.extend([
                "--runtime-hook", str(self.script_dir / "pyi_rth_font_fix.py")
            ])
        
        # PyInstaller 실행
        self.print_colored("🚀 PyInstaller 실행...", 'GREEN')
        result = subprocess.run(pyinstaller_cmd, cwd=str(self.app_dir))
        
        if result.returncode != 0:
            self.print_colored("❌ PyInstaller 빌드 실패", 'RED')
            sys.exit(1)
            
        return result.returncode == 0

    def verify_build_result(self):
        """빌드 결과 확인"""
        executable_path = self.app_dir / "dist" / "labelme.exe"
        
        if executable_path.exists():
            file_size = executable_path.stat().st_size / (1024 * 1024)  # MB
            self.print_colored("✅ 빌드 성공!", 'GREEN')
            self.print_colored(f"📍 실행 파일 위치: {executable_path}", 'GREEN')
            self.print_colored(f"📊 파일 크기: {file_size:.1f} MB", 'YELLOW')
            
            # 파일 정보 표시
            self.print_colored("📋 파일 정보:", 'YELLOW')
            self.print_colored(f"  - 경로: {executable_path}", 'BLUE')
            self.print_colored(f"  - 크기: {file_size:.1f} MB", 'BLUE')
            
            return True
        else:
            self.print_colored("❌ 빌드 실패! 실행 파일을 찾을 수 없습니다.", 'RED')
            
            # 빌드 로그 확인
            warn_file = self.app_dir / "build" / "labelme" / "warn-labelme.txt"
            if warn_file.exists():
                self.print_colored("📋 빌드 경고사항:", 'YELLOW')
                with open(warn_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    for line in lines[-20:]:  # 마지막 20줄만 표시
                        print(f"  {line.rstrip()}")
            
            return False

    def cleanup_temp_files(self):
        """임시 파일들 정리"""
        self.print_colored("🧹 임시 파일 정리 중...", 'YELLOW')
        
        temp_files = [
            self.app_dir / "version.xml",
            self.app_dir / "package.xml"
        ]
        
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()
                self.print_colored(f"  🗑️ {temp_file.name} 제거", 'BLUE')

    def print_final_instructions(self):
        """최종 안내 메시지"""
        executable_path = self.app_dir / "dist" / "labelme.exe"
        
        self.print_colored("=" * 50, 'GREEN')
        self.print_colored("✅ 빌드 완료!", 'GREEN')
        self.print_colored("=" * 50, 'GREEN')
        
        self.print_colored("📋 사용 방법:", 'YELLOW')
        self.print_colored(f"  1. 실행 파일: {executable_path}", 'BLUE')
        self.print_colored("  2. 더블클릭하여 실행", 'BLUE')
        self.print_colored("  3. 또는 명령 프롬프트에서: labelme.exe", 'BLUE')
        
        self.print_colored("\n⚠️ 주의사항:", 'YELLOW')
        self.print_colored("  - Windows Defender에서 차단될 수 있습니다 (허용으로 설정)", 'BLUE')
        self.print_colored("  - 첫 실행 시 시간이 소요될 수 있습니다", 'BLUE')
        self.print_colored("  - 실행 파일을 다른 PC에 복사하여 사용할 수 있습니다", 'BLUE')

    def run_build(self):
        """전체 빌드 프로세스 실행"""
        try:
            self.print_colored("🚀 labelme Windows 빌드 시작...", 'GREEN')
            self.print_colored("🪟 대상: Windows (.exe 파일)", 'YELLOW')
            
            # 빌드 단계들
            self.check_requirements()
            self.setup_virtual_environment()
            self.install_packages()
            self.prepare_build_files()
            self.clean_build_directories()
            
            if self.build_executable():
                if self.verify_build_result():
                    self.cleanup_temp_files()
                    self.print_final_instructions()
                    self.print_colored("🎉 빌드 프로세스 성공적으로 완료!", 'GREEN')
                    return True
            
            return False
            
        except KeyboardInterrupt:
            self.print_colored("\n⏹️ 사용자에 의해 빌드가 중단되었습니다.", 'YELLOW')
            return False
        except Exception as e:
            self.print_colored(f"❌ 예상치 못한 오류 발생: {e}", 'RED')
            import traceback
            traceback.print_exc()
            return False


def main():
    """메인 실행 함수"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("labelme Windows 빌드 스크립트")
        print("사용법: python build_labelme_windows.py")
        print("\n이 스크립트는 Windows 환경에서 labelme.exe 파일을 생성합니다.")
        print("빌드에는 몇 분이 소요되며, 인터넷 연결이 필요합니다.")
        return
    
    builder = LabelmeWindowsBuilder()
    success = builder.run_build()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()