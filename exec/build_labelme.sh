#!/bin/bash
set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting labelme executable build process (Fixed Version)...${NC}"

# 0) 경로 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${ROOT}/labelme"
VENV_PATH="${HOME}/.venvs/labelme-build"

echo -e "${BLUE}📁 Project paths:${NC}"
echo "  - Script dir: ${SCRIPT_DIR}"
echo "  - Root dir: ${ROOT}"
echo "  - App dir: ${APP_DIR}"
echo "  - Venv path: ${VENV_PATH}"

# 1) 가상환경 활성화
if [ ! -d "${VENV_PATH}" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv "${VENV_PATH}"
fi

echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source "${VENV_PATH}/bin/activate"

# 환경 변수 설정
export QT_API=pyqt5
unset PYTHONPATH || true
export PYTHONNOUSERSITE=1

# 2) 패키지 설치
echo -e "${YELLOW}📦 Installing required packages...${NC}"
pip install --upgrade pip setuptools wheel pyinstaller

# labelme 의존성 설치
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
    "opencv-python>=4.6.0" \
    "PyQt5!=5.15.3,!=5.15.4" \
    "colorama"

# labelme 개발 모드로 설치
echo -e "${YELLOW}📦 Installing labelme...${NC}"
cd "${ROOT}"
pip install -e .

# 3) 필수 파일 복사
echo -e "${YELLOW}📋 Preparing build files...${NC}"
cd "${APP_DIR}"
cp -f "${ROOT}/version.xml" . 2>/dev/null || echo "version.xml not found, skipping..."
cp -f "${ROOT}/package.xml" . 2>/dev/null || echo "package.xml not found, skipping..."

# 4) 빌드 디렉토리 정리
echo -e "${YELLOW}🧹 Cleaning build directories...${NC}"
rm -rf build dist *.spec

# 5) 시스템 Qt 플러그인 경로 확인
QT_PLUGINS_PATH="/usr/lib/x86_64-linux-gnu/qt5/plugins"
if [ ! -d "$QT_PLUGINS_PATH" ]; then
    QT_PLUGINS_PATH=$(python -c "
import os
try:
    import PyQt5.QtCore
    qt_path = os.path.dirname(PyQt5.QtCore.__file__)
    plugins_path = os.path.join(qt_path, 'Qt5', 'plugins')
    if os.path.exists(plugins_path):
        print(plugins_path)
    else:
        plugins_path = os.path.join(qt_path, 'Qt', 'plugins')
        if os.path.exists(plugins_path):
            print(plugins_path)
        else:
            print('/usr/lib/x86_64-linux-gnu/qt5/plugins')
except:
    print('/usr/lib/x86_64-linux-gnu/qt5/plugins')
" 2>/dev/null || echo "/usr/lib/x86_64-linux-gnu/qt5/plugins")
fi

echo -e "${BLUE}🔧 Using Qt plugins path: ${QT_PLUGINS_PATH}${NC}"

# 6) PyInstaller 빌드 (개선된 옵션)
echo -e "${GREEN}🔨 Starting PyInstaller build with Qt fixes...${NC}"
echo -e "${YELLOW}⏱️  This may take several minutes...${NC}"

pyinstaller \
  --onefile \
  --windowed \
  --name labelme \
  --hidden-import=yaml \
  --hidden-import=_yaml \
  --hidden-import=qtpy \
  --hidden-import=qtpy.QtCore \
  --hidden-import=qtpy.QtWidgets \
  --hidden-import=qtpy.QtGui \
  --hidden-import=termcolor \
  --hidden-import=colorama \
  --hidden-import=cv2 \
  --hidden-import=imgviz \
  --hidden-import=matplotlib \
  --hidden-import=natsort \
  --hidden-import=numpy \
  --hidden-import=PIL \
  --hidden-import=lxml \
  --hidden-import=requests \
  --collect-submodules=PyQt5 \
  --collect-data=matplotlib \
  --exclude-module=PySide6 \
  --exclude-module=PySide2 \
  --exclude-module=PyQt6 \
  --exclude-module=tkinter \
  --add-data="config:labelme/config" \
  --add-data="icons:labelme/icons" \
  --add-data="translate:labelme/translate" \
  --add-binary="${QT_PLUGINS_PATH}/platforms:qt5_plugins/platforms" \
  --add-binary="${QT_PLUGINS_PATH}/imageformats:qt5_plugins/imageformats" \
  --add-binary="${QT_PLUGINS_PATH}/iconengines:qt5_plugins/iconengines" \
  --strip \
  __main__.py

# 7) 빌드 결과 확인
if [ -f "${APP_DIR}/dist/labelme" ]; then
    echo -e "${GREEN}✅ Build completed successfully!${NC}"
    
    # 실행 권한 부여
    chmod +x "${APP_DIR}/dist/labelme"
    
    # 파일 크기 표시
    FILE_SIZE=$(du -sh "${APP_DIR}/dist/labelme" | cut -f1)
    echo -e "${YELLOW}📊 File size: ${FILE_SIZE}${NC}"
    
    # 실행 가능한 래퍼 스크립트 생성
    cat > "${APP_DIR}/dist/run_labelme.sh" << 'EOF'
#!/bin/bash
# Labelme 실행 래퍼 스크립트
export QT_QPA_PLATFORM_PLUGIN_PATH="$(dirname "$0")/qt5_plugins/platforms"
export QT_PLUGIN_PATH="$(dirname "$0")/qt5_plugins"
export QT_QPA_PLATFORM=xcb

# 현재 디렉토리를 실행 파일이 있는 위치로 변경
cd "$(dirname "$0")"

# labelme 실행
exec ./labelme "$@"
EOF
    
    chmod +x "${APP_DIR}/dist/run_labelme.sh"
    
    echo -e "${GREEN}📍 Files created:${NC}"
    echo -e "  - Executable: ${APP_DIR}/dist/labelme"
    echo -e "  - Wrapper script: ${APP_DIR}/dist/run_labelme.sh"
    
else
    echo -e "${RED}❌ Build failed! Executable not found.${NC}"
    exit 1
fi

# 8) 정리
echo -e "${YELLOW}🧹 Cleaning up...${NC}"
rm -f "${APP_DIR}/version.xml" "${APP_DIR}/package.xml"

echo -e "${GREEN}🎉 Build process completed!${NC}"
echo -e "${GREEN}💡 To run labelme, use: ${APP_DIR}/dist/run_labelme.sh${NC}"
echo -e "${YELLOW}   (The wrapper script sets proper Qt environment variables)${NC}"
