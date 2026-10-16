"""主程序入口，包含多标签页界面"""

import logging
import os
import sys
import traceback
import tkinter as tk
from tkinter import ttk

# 添加项目根目录到Python路径（避免重复添加）
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# 统一使用日志配置模块
try:
    from utils.logger_config import setup_module_logger
    logger = setup_module_logger("main", logging.INFO)
except ImportError as e:
    # 降级处理：使用标准日志配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

# 导入模块化组件
try:
    from ip_allocator import IPAllocator
    from ip_anonymizer import IPAnonymizer
    from ip_calculator import IPSubnetCalculator
    from ip_converter import IPConverter
    from ip_work_stats import WorkStats
    from ui.gui_styles import configure_styles
except ImportError as e:
    logger.error(f"无法加载必要的功能模块: {e}")
    logger.error(
        "请确保 ip_allocator.py, ip_anonymizer.py, ip_calculator.py, ip_converter.py 存在于当前目录")
    sys.exit(1)


class NetworkTools:
    """主应用程序类，负责管理多标签页界面"""

    # 定义窗口尺寸常量
    DEFAULT_WIDTH = 1100
    DEFAULT_HEIGHT = 600
    MIN_WIDTH = 800
    MIN_HEIGHT = 500

    def __init__(self, root: tk.Tk) -> None:
        """初始化应用程序

        Args:
            root: Tkinter根窗口对象
        """
        self.root = root
        self.root.title("IP网络工具套件 v4.0")

        # 设置现代化样式
        self._setup_styles()

        # 使用Notebook创建多标签页界面
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 初始化标签页和对应的工具实例
        # 使用字典存储标签页索引与组件的映射，便于扩展
        self._tab_components: dict = {}

        # 创建各个标签页
        self._create_tabs()

        # 添加标签页切换事件监听器
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        logger.info("应用程序初始化完成")

    def _setup_styles(self) -> None:
        """设置现代化UI样式"""
        self.style = ttk.Style()

        # 尝试使用现代化主题，如果失败则忽略（使用系统默认）
        # clam, alt, default, classic 是常见的跨平台主题
        available_themes = self.style.theme_names()
        if 'clam' in available_themes:
            self.style.theme_use('clam')
            logger.debug("使用 'clam' 主题")
        else:
            logger.debug(f"使用系统默认主题，可用主题: {available_themes}")

        configure_styles(self.style)

    def _create_tabs(self) -> None:
        """创建所有标签页"""
        # 1. IP转换器
        converter_frame = ttk.Frame(self.notebook)
        self.notebook.add(converter_frame, text="IP转换器")
        self.converter = IPConverter(converter_frame)
        self._tab_components[0] = self.converter

        # 2. IP地址空间计算器
        calculator_frame = ttk.Frame(self.notebook)
        self.notebook.add(calculator_frame, text="IP地址空间计算器")
        self.calculator = IPSubnetCalculator(calculator_frame)
        self._tab_components[1] = self.calculator

        # 3. IP脱敏器
        document_frame = ttk.Frame(self.notebook)
        self.notebook.add(document_frame, text="IP脱敏器")
        self.document_tool = IPAnonymizer(document_frame)
        self._tab_components[2] = self.document_tool

        # 4. 工作统计
        work_stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(work_stats_frame, text="工作统计")
        self.work_stats = WorkStats(work_stats_frame)
        self._tab_components[3] = self.work_stats

        self.document_tool.set_work_stats_launcher(self._open_work_stats_from_anonymizer)

        # 5. IP地址分配
        allocator_frame = ttk.Frame(self.notebook)
        self.notebook.add(allocator_frame, text="IP地址分配")
        self.allocator = IPAllocator(allocator_frame)
        self._tab_components[4] = self.allocator

        logger.debug(f"已创建 {len(self._tab_components)} 个标签页")

    def _on_tab_changed(self, event: tk.Event) -> None:
        """处理标签页切换事件，确保焦点正确设置

        Args:
            event: 标签页切换事件对象
        """
        try:
            current_tab_index = self.notebook.index(self.notebook.select())
            # 直接从字典中获取对应的组件实例
            component = self._tab_components.get(current_tab_index)

            if component and hasattr(component, 'set_initial_focus'):
                component.set_initial_focus()
                logger.debug(f"标签页 {current_tab_index} 获得焦点")
        except tk.TclError as e:
            # 处理极少数情况下获取索引失败的情况
            logger.warning(f"获取标签页索引失败: {e}")

    def _open_work_stats_from_anonymizer(self, file_paths: list[str]) -> None:
        """从IP脱敏器跳转到工作统计页并载入最终脱敏文件列表"""
        self.work_stats.load_files(file_paths)
        self.notebook.select(3)
        self.work_stats.set_initial_focus()

    def center_window(self) -> None:
        """窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()

        # 如果窗口尚未渲染出正确尺寸（通常为1），则使用默认尺寸
        if width <= 1:
            width = self.DEFAULT_WIDTH
        if height <= 1:
            height = self.DEFAULT_HEIGHT

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        logger.debug(f"窗口位置: {width}x{height}+{x}+{y}")


def main() -> None:
    """程序主入口函数"""
    logger.info("启动 IP网络工具套件 v4.0")

    try:
        root = tk.Tk()

        # 设置窗口最小尺寸，防止布局错乱
        root.minsize(NetworkTools.MIN_WIDTH, NetworkTools.MIN_HEIGHT)

        app = NetworkTools(root)

        # 居中窗口
        app.center_window()

        # 启动主循环
        logger.info("进入主事件循环")
        root.mainloop()

    except KeyboardInterrupt:
        # 允许用户通过 Ctrl+C 优雅退出
        logger.info("程序已被用户中断")
        print("\n程序已被用户中断。")
        sys.exit(0)
    except Exception as e:
        # 捕获其他未预期的异常，打印错误信息并退出
        logger.critical(f"发生严重错误: {e}", exc_info=True)
        print(f"发生严重错误: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("程序退出")


if __name__ == "__main__":
    main()
