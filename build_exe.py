import os
import sys
import subprocess
import json

def build_exe():
    print("开始打包番茄计时器应用...")
    
    # 确保当前目录是项目目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # 检查数据文件是否存在，如果不存在则创建
    if not os.path.exists('pomodoro_history.json'):
        with open('pomodoro_history.json', 'w') as f:
            json.dump({}, f)
            print("创建了空的历史记录文件")
    
    if not os.path.exists('pomodoro_state.json'):
        with open('pomodoro_state.json', 'w') as f:
            json.dump({
                "is_working": True,
                "is_running": False,
                "is_idle_break": False,
                "time_left": 1500,
                "timestamp": None
            }, f)
            print("创建了默认状态文件")
    
    # 构建PyInstaller命令
    cmd = [
        'pyinstaller',
        '--name=番茄计时器',
        '--windowed',  # 不显示控制台窗口
        '--icon=NONE',  # 如果有图标文件，替换NONE为图标路径
        # 不再将数据文件添加到包中，因为现在使用可执行文件所在目录
        '--onefile',  # 生成单个exe文件
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        'pomodoro_timer.py'
    ]
    
    print("执行打包命令...")
    # 执行打包命令
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("打包成功!")
        print(f"可执行文件位于: {os.path.join(project_dir, 'dist', '番茄计时器.exe')}")
        
        # 复制初始数据文件到dist目录，作为初始数据
        dist_dir = os.path.join(project_dir, 'dist')
        try:
            # 复制历史文件
            if os.path.exists('pomodoro_history.json'):
                with open('pomodoro_history.json', 'r') as src_file:
                    history_data = json.load(src_file)
                
                with open(os.path.join(dist_dir, 'pomodoro_history.json'), 'w') as dest_file:
                    json.dump(history_data, dest_file)
                print("已复制历史数据文件到dist目录")
            
            # 复制状态文件
            if os.path.exists('pomodoro_state.json'):
                with open('pomodoro_state.json', 'r') as src_file:
                    state_data = json.load(src_file)
                
                with open(os.path.join(dist_dir, 'pomodoro_state.json'), 'w') as dest_file:
                    json.dump(state_data, dest_file)
                print("已复制状态文件到dist目录")
        except Exception as e:
            print(f"复制数据文件到dist目录失败: {e}")
    else:
        print("打包失败:")
        print(result.stderr)

if __name__ == "__main__":
    build_exe() 