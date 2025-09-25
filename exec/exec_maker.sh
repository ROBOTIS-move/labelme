#!/bin/bash
set -euo pipefail

# 빌드 타겟 설정
# BUILD_FOR_WINDOWS=1 : Windows용 .exe 파일 생성 (기본값)
# BUILD_FOR_WINDOWS=0 : Linux용 실행 파일 생성
BUILD_FOR_WINDOWS=${BUILD_FOR_WINDOWS:-1}

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ $BUILD_FOR_WINDOWS -eq 1 ]; then
    echo -e "${GREEN}🚀 Starting labelme Windows executable build process...${NC}"
    echo -e "${YELLOW}🪟 Target: Windows (.exe file)${NC}"
else
    echo -e "${GREEN}🚀 Starting labelme Linux executable build process...${NC}"
    echo -e "${YELLOW}🐧 Target: Linux (native executable)${NC}"
fi

# 0) 경로 고정: 이 스크립트가 exec/ 아래 있을 때 기준
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"          # ~/gaemi_ws/src/labelme
APP_DIR="${ROOT}/labelme"                       # ~/gaemi_ws/src/labelme/labelme
VENV_PATH="${HOME}/.venvs/labelme-build"

echo -e "${YELLOW}📁 Project paths:${NC}"
echo "  - Script dir: ${SCRIPT_DIR}"
echo "  - Root dir: ${ROOT}"
echo "  - App dir: ${APP_DIR}"
echo "  - Venv path: ${VENV_PATH}"

# 1) 가상환경 생성 또는 활성화
if [ ! -d "${VENV_PATH}" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment at ${VENV_PATH}...${NC}"
    python3 -m venv "${VENV_PATH}"
fi

echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source "${VENV_PATH}/bin/activate"

# 환경 변수 설정
export QT_API=pyqt5
unset PYTHONPATH || true
export PYTHONNOUSERSITE=1

# 2) 필수 패키지 설치 확인 및 설치
echo -e "${YELLOW}📦 Installing/updating required packages...${NC}"

# 기본 패키지 업데이트
pip install --upgrade pip setuptools wheel

# PyInstaller 설치
pip install pyinstaller

# labelme 의존성 패키지들 설치 (OpenCV headless 버전 사용)
pip install \
    "imgviz>=0.11" \
    "matplotlib>=3.3" \
    "natsort>=7.1.0" \
    "numpy" \
    "Pillow>=6.2" \
    "PyYAML" \
    "qtpy!=1.11.2" \
    "termcolor" \
    "cryptography" \
    "lxml" \
    "requests" \
    "PyQt5!=5.15.3,!=5.15.4" \
    "colorama"

# labelme 개발 모드로 설치
echo -e "${YELLOW}📦 Installing labelme in development mode...${NC}"
cd "${ROOT}"
pip install -e .

# 3) 필요한 리소스 파일들 복사
echo -e "${YELLOW}📋 Preparing resource files...${NC}"
test -f "${ROOT}/version.xml"  || { echo -e "${RED}❌ version.xml not found at ${ROOT}/version.xml${NC}"; exit 1; }
test -f "${ROOT}/package.xml"  || { echo -e "${RED}❌ package.xml not found at ${ROOT}/package.xml${NC}"; exit 1; }

cp -f "${ROOT}/version.xml"  "${APP_DIR}/version.xml"
cp -f "${ROOT}/package.xml"  "${APP_DIR}/package.xml"

# 4) 빌드 디렉토리 정리
echo -e "${YELLOW}🧹 Cleaning build directories...${NC}"
cd "${APP_DIR}"
rm -rf build dist *.spec

# 5) 완전한 PyInstaller 빌드
echo -e "${GREEN}🔨 Starting complete PyInstaller build...${NC}"
echo -e "${YELLOW}⏱️  This may take several minutes...${NC}"

# 타겟 OS 설정 (Linux에서 Windows용 빌드)
BUILD_FOR_WINDOWS=${BUILD_FOR_WINDOWS:-1}  # 기본값을 Windows로 설정

if [ $BUILD_FOR_WINDOWS -eq 1 ]; then
    SEP=";"
    EXECUTABLE_NAME="labelme.exe"
    WINDOWED_OPT="--windowed"
    echo -e "${YELLOW}🪟 Building for Windows target${NC}"
else
    SEP=":"
    EXECUTABLE_NAME="labelme"
    WINDOWED_OPT="--console"
    echo -e "${YELLOW}🐧 Building for Unix-like target${NC}"
fi

# OpenCV without Qt 플러그인 설치 (Qt 충돌 방지)
pip uninstall -y opencv-python opencv-python-headless || true
pip install opencv-python-headless>=4.6.0

# Windows용 빌드 시 추가 설정
if [ $BUILD_FOR_WINDOWS -eq 1 ]; then
    echo -e "${YELLOW}⚙️ Applying Windows build settings...${NC}"
    # Wine이 설치되어 있으면 Windows DLL 경로 설정
    if command -v wine &> /dev/null; then
        echo -e "${YELLOW}🍷 Wine detected - setting up Windows environment${NC}"
        export WINEPREFIX="${HOME}/.wine"
    fi
    
    # pywin32는 Linux에서 설치 불가하므로 건너뛰기
    echo -e "${YELLOW}ℹ️  pywin32 is not available on Linux - will be handled by PyInstaller${NC}"
fi

# PyInstaller 명령어 준비
echo -e "${YELLOW}⚙️ Preparing PyInstaller command...${NC}"

# PyInstaller 실행
echo -e "${YELLOW}🔨 Running PyInstaller...${NC}"

# PyInstaller를 직접 명령어로 실행 (배열 대신)
pyinstaller \
  --onefile \
  $WINDOWED_OPT \
  --name="${EXECUTABLE_NAME%.*}" \
  --paths="${APP_DIR}" \
  --paths="${ROOT}" \
  --distpath="${APP_DIR}/dist" \
  --workpath="${APP_DIR}/build" \
  --specpath="${APP_DIR}" \
  --hidden-import=yaml \
  --hidden-import=_yaml \
  --hidden-import=qtpy \
  --hidden-import=qtpy.QtCore \
  --hidden-import=qtpy.QtWidgets \
  --hidden-import=qtpy.QtGui \
  --hidden-import=qtpy.QtOpenGL \
  --hidden-import=qtpy.QtPrintSupport \
  --hidden-import=qtpy.QtTest \
  --hidden-import=termcolor \
  --hidden-import=colorama \
  --hidden-import=imgviz \
  --hidden-import=matplotlib \
  --hidden-import=matplotlib.backends.backend_qt5agg \
  --hidden-import=matplotlib.backends.backend_qtagg \
  --hidden-import=natsort \
  --hidden-import=numpy \
  --hidden-import=PIL \
  --hidden-import=PIL.Image \
  --hidden-import=PIL.ImageDraw \
  --hidden-import=PIL.ImageFilter \
  --hidden-import=PIL.ImageTk \
  --hidden-import=lxml \
  --hidden-import=requests \
  --hidden-import=cv2 \
  --add-data="${ROOT}/version.xml:." \
  --add-data="${ROOT}/package.xml:." \
  --add-data="config:labelme/config" \
  --add-data="icons:labelme/icons" \
  --add-data="translate:labelme/translate" \
  --add-data="version.xml:labelme/version.xml" \
  --add-data="package.xml:labelme/package.xml" \
  --exclude-module=PySide6 \
  --exclude-module=PySide2 \
  --exclude-module=PyQt6 \
  --exclude-module=tkinter \
  --exclude-module=tornado \
  --exclude-module=sphinx \
  --exclude-module=IPython \
  --exclude-module=jupyter \
  --collect-all=PyQt5 \
  --collect-all=qtpy \
  --runtime-hook="${SCRIPT_DIR}/pyi_rth_qt_plugins.py" \
  --runtime-hook="${SCRIPT_DIR}/pyi_rth_labelme_resources.py" \
  --strip \
  --noupx \
  "__main__.py"

# 6) 빌드 결과 확인
EXPECTED_EXECUTABLE="${APP_DIR}/dist/${EXECUTABLE_NAME}"

if [ -f "${EXPECTED_EXECUTABLE}" ]; then
    echo -e "${GREEN}✅ Build completed successfully!${NC}"
    echo -e "${GREEN}📍 Executable location: ${EXPECTED_EXECUTABLE}${NC}"
    
    # 실행 파일 크기 표시
    FILE_SIZE=$(du -sh "${EXPECTED_EXECUTABLE}" | cut -f1)
    echo -e "${YELLOW}📊 File size: ${FILE_SIZE}${NC}"
    
    # 파일 정보 표시
    echo -e "${YELLOW}📋 File details:${NC}"
    file "${EXPECTED_EXECUTABLE}" 2>/dev/null || echo "File command not available"
    
    echo -e "${GREEN}🎉 Build process completed successfully!${NC}"
    echo -e "${GREEN}📂 Executable location: ${EXPECTED_EXECUTABLE}${NC}"
    
    if [ $BUILD_FOR_WINDOWS -eq 1 ]; then
        echo -e "${YELLOW}💡 Windows executable created: ${EXECUTABLE_NAME}${NC}"
        echo -e "${YELLOW}   Copy this file to Windows and double-click to run${NC}"
        echo -e "${YELLOW}   Or run from Windows command prompt: ${EXECUTABLE_NAME}${NC}"
    else
        echo -e "${YELLOW}💡 To test the executable, run: ${EXPECTED_EXECUTABLE}${NC}"
    fi
    
else
    echo -e "${RED}❌ Build failed! Executable not found at ${EXPECTED_EXECUTABLE}.${NC}"
    
    # 빌드 로그 확인
    if [ -f "${APP_DIR}/build/labelme/warn-labelme.txt" ]; then
        echo -e "${YELLOW}📋 Build warnings:${NC}"
        tail -20 "${APP_DIR}/build/labelme/warn-labelme.txt"
    fi
    
    # 생성된 파일들 확인
    echo -e "${YELLOW}📂 Files in dist directory:${NC}"
    ls -la "${APP_DIR}/dist/" 2>/dev/null || echo "No dist directory found"
    
    exit 1
fi

# 7) 임시 파일 정리
echo -e "${YELLOW}🧹 Cleaning up temporary files...${NC}"
rm -f "${APP_DIR}/version.xml"
rm -f "${APP_DIR}/package.xml"

# 최종 안내
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ BUILD COMPLETED SUCCESSFULLY${NC}"
echo -e "${GREEN}========================================${NC}"
if [ $BUILD_FOR_WINDOWS -eq 1 ]; then
    echo -e "${YELLOW}📋 Windows 사용 방법:${NC}"
    echo -e "   1. ${EXECUTABLE_NAME} 파일을 Windows PC로 복사"
    echo -e "   2. 더블클릭하여 실행"
    echo -e "   3. 또는 Windows 명령프롬프트에서: ${EXECUTABLE_NAME}"
    echo ""
    echo -e "${YELLOW}⚠️  주의사항:${NC}"
    echo -e "   - Windows Defender에서 차단될 수 있음 (허용으로 설정)"
    echo -e "   - 첫 실행 시 시간이 소요될 수 있음"
else
    echo -e "${YELLOW}📋 Linux 사용 방법:${NC}"
    echo -e "   터미널에서: ${EXPECTED_EXECUTABLE}"
fi
echo -e "${GREEN}========================================${NC}"