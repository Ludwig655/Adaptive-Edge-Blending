import subprocess
import sys
import os

def install_requirements():
    """安装项目所需依赖"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    
    print("正在安装项目依赖...")
    print(f"Python 解释器: {sys.executable}")
    print(f"依赖文件: {requirements_path}\n")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', requirements_path
        ])
        print("\n✓ 依赖安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 依赖安装失败: {e}")
        return False

def verify_dependencies():
    """验证依赖是否正确安装"""
    print("\n正在验证依赖...")
    
    dependencies = [
        ('numpy', 'numpy'),
        ('cv2', 'opencv-python'),
        ('scipy', 'scipy')
    ]
    
    all_ok = True
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            print(f"✓ {package_name}")
        except ImportError:
            print(f"✗ {package_name} (未安装)")
            all_ok = False
    
    return all_ok

if __name__ == "__main__":
    print("=" * 50)
    print("边缘融合项目 - 环境配置")
    print("=" * 50)
    
    if install_requirements():
        if verify_dependencies():
            print("\n" + "=" * 50)
            print("环境配置完成！现在可以运行: python example.py")
            print("=" * 50)
        else:
            print("\n部分依赖未正确安装，请检查")
    else:
        print("\n安装失败，请检查网络连接或权限")
