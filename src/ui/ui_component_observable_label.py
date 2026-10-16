"""
observable_label.py - 增强型可观察标签控件

功能特性：
1. 支持禁用状态管理
2. 禁用时可设置替代文本
3. 自动恢复原始文本内容
4. 状态变更回调支持
5. 自定义颜色和字体管理
6. 文本修改事件通知

注意：
- 请使用 `configure()` 方法而不是 `config()` 方法来修改控件属性，以确保所有增强功能正常工作。
"""

import tkinter as tk
from typing import Optional, Callable, Any

class ObservableLabel(tk.Label):
    """
    可观察状态标签控件

    参数：
    master          - 父容器
    text            - 初始显示文本（默认：空字符串）
    enabled_fg      - 启用状态前景色（默认："blue"）
    disabled_fg     - 禁用状态前景色（默认："gray"）
    disabled_text   - 禁用时显示的替代文本（默认：None，使用原始文本）
    state_change_cb - 状态变更回调函数（参数：bool）
    **kwargs        - 标准Label控件参数

    方法：
    disable()       - 设置禁用状态
    set_colors()    - 配置双态颜色
    set_font()      - 配置双态字体
    """

    # 字体配置常量
    DEFAULT_FONT_FAMILY = "Helvetica"
    ENABLED_FONT_SIZE = 12
    DISABLED_FONT_SIZE = 12
    FONT_WEIGHT = "bold"

    def __init__(
        self,
        master: tk.Misc,
        text: str = "",
        enabled_fg: str = "blue",
        disabled_fg: str = "gray",
        disabled_text: Optional[str] = None,
        state_change_cb: Optional[Callable[[bool], Any]] = None,
        **kwargs
    ):
        # 初始化字体配置
        base_font = kwargs.pop("font", None)

        # 解析基础字体信息
        if base_font is None:
            family = self.DEFAULT_FONT_FAMILY
        elif isinstance(base_font, str):
            family = base_font
        elif isinstance(base_font, (tuple, list)):
            family = base_font[0] if len(base_font) > 0 else self.DEFAULT_FONT_FAMILY
        else:
            family = self.DEFAULT_FONT_FAMILY

        # 使用解析出的family和常量创建双态字体
        self._enabled_font = (family, self.ENABLED_FONT_SIZE, self.FONT_WEIGHT)
        self._disabled_font = (family, self.DISABLED_FONT_SIZE, self.FONT_WEIGHT)

        # 初始化父类
        super().__init__(master, text=text, font=self._enabled_font, **kwargs)

        # 状态管理系统
        self._is_disabled = False
        self._original_text = text
        self._disabled_text = disabled_text or text  # 禁用显示文本
        self._current_text = text                    # 当前实际显示文本
        self._state_change_cb = state_change_cb

        # 颜色管理系统
        self._enabled_fg = enabled_fg
        self._disabled_fg = disabled_fg
        self.configure(fg=enabled_fg)

        # 文本变更追踪
        self._prev_text = text

    def disable(
        self,
        state: bool,
        disabled_text: Optional[str] = None,
        persist: bool = False
    ) -> 'ObservableLabel':
        """
        设置控件禁用状态

        参数：
        state        - 是否禁用（True/False）
        disabled_text- 自定义禁用文本（可选）
        persist      - 是否保留禁用期间的文本修改（默认False）

        返回：
        self（支持链式调用）
        """
        if state == self._is_disabled:
            return self

        # 修改部分：在状态转换前获取实际显示的文本
        current_display_text = self.cget("text")  # 关键修改点

        # 状态转换处理
        if state:
            # 进入禁用状态时保存原始文本
            if not persist:
                self._original_text = current_display_text  # 使用实际显示的文本
            self._current_text = disabled_text or self._disabled_text
        else:
            # 退出禁用状态时处理持久化
            if persist:
                self._original_text = current_display_text
            self._current_text = self._original_text

        self._is_disabled = state
        self._update_visual_state()

        # 触发回调
        if self._state_change_cb:
            self._state_change_cb(state)

        return self

    def _update_visual_state(self) -> None:
        """更新控件视觉状态"""
        # 获取目标状态下的显示属性
        if self._is_disabled:
            fg_color = self._disabled_fg
            font = self._disabled_font
            display_text = self._current_text
        else:
            fg_color = self._enabled_fg
            font = self._enabled_font
            display_text = self._current_text

        # 直接操作底层配置，避免触发configure方法中的事件逻辑
        super().configure(text=display_text, fg=fg_color, font=font)

    def configure(self, **kwargs) -> None:
        """
        增强版配置方法

        特殊处理：
        - 禁用状态下自动拦截颜色/字体修改
        - 智能处理文本更新
        """
        # 处理文本更新
        if "text" in kwargs:
            new_text = kwargs["text"]
            if self._is_disabled:
                self._current_text = new_text
            else:
                self._original_text = new_text
                self._current_text = new_text

        # # 过滤无效修改
        if self._is_disabled:
            kwargs.pop("fg", None)
            kwargs.pop("font", None)

        # 执行父类配置
        super().configure(**kwargs)

        # 触发文本变更事件
        if "text" in kwargs:
            new_text = kwargs["text"]
            # 只有当新文本与记录的上一个文本不同时才触发事件
            if new_text != self._prev_text:
                self._prev_text = new_text
                self.event_generate("<<LabelModified>>", when="tail")

    @property
    def is_disabled(self) -> bool:
        """获取当前禁用状态（只读）"""
        return self._is_disabled

    @property
    def original_text(self) -> str:
        """获取原始文本内容（只读）"""
        return self._original_text

    def set_colors(
        self,
        enabled: Optional[str] = None,
        disabled: Optional[str] = None
    ) -> 'ObservableLabel':
        """
        配置状态颜色

        参数：
        enabled  - 启用状态颜色（可选）
        disabled - 禁用状态颜色（可选）
        """
        if enabled:
            self._enabled_fg = enabled
        if disabled:
            self._disabled_fg = disabled
        self._update_visual_state()
        return self

    def set_font(
        self,
        family: Optional[str] = None,
        enabled_size: Optional[int] = None,
        disabled_size: Optional[int] = None
    ) -> 'ObservableLabel':
        """
        配置双态字体

        参数：
        family       - 字体名称（可选）
        enabled_size - 启用状态字号（可选）
        disabled_size- 禁用状态字号（可选）
        """
        if family:
            self._enabled_font = (family, self._enabled_font[1], self.FONT_WEIGHT)
            self._disabled_font = (family, self._disabled_font[1], self.FONT_WEIGHT)
        if enabled_size:
            self._enabled_font = (self._enabled_font[0], enabled_size, self.FONT_WEIGHT)
        if disabled_size:
            self._disabled_font = (self._disabled_font[0], disabled_size, self.FONT_WEIGHT)
        self._update_visual_state()
        return self


if __name__ == "__main__":
    # ======================
    # 使用示例
    # ======================
    root = tk.Tk()
    root.title("ObservableLabel 演示")
    root.geometry("600x200")

    def on_state_change(state: bool):
        status.config(text=f"当前状态：{'禁用' if state else '启用'}")

    def on_text_change(event):
        print(f"文本变更通知：{event.widget['text']}")

    # 创建演示控件
    label = ObservableLabel(
        root,
        text="初始文本",
        disabled_text="[禁用状态]",
        state_change_cb=on_state_change,
        font=("微软雅黑", 12, "bold")
    )
    label.pack(pady=15)
    label.bind("<<LabelModified>>", on_text_change)

    # 状态显示
    status = tk.Label(root, text="当前状态：启用")
    status.pack()

    # 控制按钮
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="启用", command=lambda: label.disable(False)).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="禁用", command=lambda: label.disable(True)).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="随机文本",
            command=lambda: label.config(text=f"测试{tk.getrandbits(8)}")).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="改颜色",
            command=lambda: label.set_colors(
                enabled=f"#{tk.getrandbits(24):06x}",
                disabled=f"#{tk.getrandbits(24):06x}"
            )).pack(side=tk.LEFT, padx=5)

    root.mainloop()
