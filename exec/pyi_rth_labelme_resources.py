# Runtime hook for labelme resource files
import os
import sys

# PyInstaller 환경에서 실행 중인지 확인
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # 임시 디렉토리 경로 설정
    temp_dir = sys._MEIPASS
    
    # version.xml 파일 경로를 환경변수로 설정
    version_xml_path = os.path.join(temp_dir, 'version.xml')
    if os.path.exists(version_xml_path):
        os.environ['LABELME_VERSION_XML_PATH'] = version_xml_path
    
    package_xml_path = os.path.join(temp_dir, 'package.xml')  
    if os.path.exists(package_xml_path):
        os.environ['LABELME_PACKAGE_XML_PATH'] = package_xml_path
    
    # labelme 리소스 디렉토리들 환경변수 설정
    labelme_dir = os.path.join(temp_dir, 'labelme')
    if os.path.exists(labelme_dir):
        os.environ['LABELME_RESOURCE_DIR'] = labelme_dir
        
        # config 디렉토리
        config_dir = os.path.join(labelme_dir, 'config')
        if os.path.exists(config_dir):
            os.environ['LABELME_CONFIG_DIR'] = config_dir
        
        # icons 디렉토리
        icons_dir = os.path.join(labelme_dir, 'icons')
        if os.path.exists(icons_dir):
            os.environ['LABELME_ICONS_DIR'] = icons_dir
        
        # translate 디렉토리
        translate_dir = os.path.join(labelme_dir, 'translate')
        if os.path.exists(translate_dir):
            os.environ['LABELME_TRANSLATE_DIR'] = translate_dir
    
    # 현재 작업 디렉토리를 실행 파일 위치로 설정 (선택사항)
    # os.chdir(os.path.dirname(sys.executable))
    
    # Python 모듈 경로에 임시 디렉토리 추가
    if temp_dir not in sys.path:
        sys.path.insert(0, temp_dir)