
# 此文件是加密逻辑的入口 wrapper
import sys
import os

# 确保当前目录在 sys.path 中，以便能找到 .so 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import core_brief_report_72bb0f15
from core_brief_report_72bb0f15 import *

if __name__ == "__main__":
    try:
        pass # 模块导入时已自动执行顶层代码
    except Exception as e:
        print(f"Skill Execution Error: {e}")
        sys.exit(1)
