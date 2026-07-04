"""Plan 组装器（向后兼容层）

此文件仅重导出 plan_assembler 模块的所有公共符号。
所有逻辑已移至 plan_assembler.py。
新代码请直接 import plan_assembler。
"""

from .plan_assembler import *  # noqa: F401, F403
