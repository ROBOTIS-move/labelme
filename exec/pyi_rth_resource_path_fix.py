#!/usr/bin/env python3
"""
PyInstaller runtime hook for fixing resource path issues.
This hook provides a universal resource path resolution function.
"""

import os
import sys

def resource_path(relative_path):
    """
    PyInstaller 환경에서 리소스 파일의 절대 경로를 반환합니다.
    
    Args:
        relative_path (str): 리소스 파일의 상대 경로
        
    Returns:
        str: 리소스 파일의 절대 경로
    """
    try:
        # PyInstaller 환경인 경우
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # 임시 디렉토리의 리소스 경로
            return os.path.join(sys._MEIPASS, relative_path)
        else:
            # 개발 환경인 경우
            return os.path.join(os.path.abspath('.'), relative_path)
    except Exception:
        # 폴백: 현재 디렉토리 기준
        return relative_path

# 전역적으로 사용할 수 있도록 builtins에 추가
try:
    import builtins
    builtins.resource_path = resource_path
except ImportError:
    # Python 2 호환성
    import __builtin__
    __builtin__.resource_path = resource_path

# PyInstaller 환경 감지 및 경로 설정
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    temp_dir = sys._MEIPASS
    
    # 주요 리소스 디렉토리들의 환경 변수 설정
    resource_mappings = {
        'LABELME_BASE_DIR': temp_dir,
        'LABELME_DATA_DIR': os.path.join(temp_dir, 'labelme'),
        'LABELME_CONFIG_DIR': os.path.join(temp_dir, 'labelme', 'config'),
        'LABELME_ICONS_DIR': os.path.join(temp_dir, 'labelme', 'icons'),
        'LABELME_TRANSLATE_DIR': os.path.join(temp_dir, 'labelme', 'translate'),
    }
    
    for env_var, path in resource_mappings.items():
        if os.path.exists(path):
            os.environ[env_var] = path
    
    # Qt 리소스 경로 설정
    qt_conf_path = os.path.join(temp_dir, 'qt.conf')
    if not os.path.exists(qt_conf_path):
        try:
            with open(qt_conf_path, 'w') as f:
                f.write('[Paths]\n')
                f.write(f'Prefix = {temp_dir}\n')
                f.write('Binaries = .\n')
                f.write('Libraries = .\n')
                f.write('Plugins = qt5_plugins\n')
        except Exception:
            pass
    
    # 디버깅을 위한 경로 출력 (필요시 주석 해제)
    # print(f"[DEBUG] PyInstaller temp dir: {temp_dir}")
    # print(f"[DEBUG] Available files: {os.listdir(temp_dir)[:10]}")  # 처음 10개만