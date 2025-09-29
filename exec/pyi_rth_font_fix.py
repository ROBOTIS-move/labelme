#!/usr/bin/env python3
"""
PyInstaller runtime hook to fix Qt font issues.
"""

import os
import sys

try:
    # Qt 폰트 경고 억제
    os.environ['QT_LOGGING_RULES'] = 'qt5ct.debug=false;*.debug=false'
    
    # Windows 시스템 폰트 사용 강제
    os.environ['QT_QPA_FONTDIR'] = ''  # 빈 값으로 설정하여 시스템 기본 폰트 사용
    
    # Qt 플랫폼 설정
    if sys.platform.startswith('win'):
        os.environ['QT_QPA_PLATFORM'] = 'windows:fontengine=directwrite'
        
    # Qt 디버그 출력 최소화
    os.environ['QT_QUIET_WARNINGS'] = '1'
    
except Exception as e:
    # 오류가 발생해도 계속 진행
    pass