"""
modified_entry.py - 支持 <<Modified>> 事件的增强型输入框控件

使用方法：
1. 导入控件：
   from modified_entry import ModifiedAwareEntry

2. 基本使用示例：
   entry = ModifiedAwareEntry(parent_frame)
   entry.pack()
   entry.bind("<<Modified>>", callback_function)

3. 可用方法和属性：
   - replace_text(new_text): 安全修改文本并触发事件
   - modification_count: 获取修改次数统计
   - freeze_tracking()/resume_tracking(): 批量操作保护

4. 事件说明：
   <<Modified>> 事件在以下情况触发：
   - 用户键盘输入（内容实际变化）
   - 剪贴板操作（粘贴/剪切）
   - 程序调用 insert/delete 方法
   - 通过 textvariable 修改值

版本要求：Python 3.7+，Tkinter 8.6+

示例代码：
import tkinter as tk
from tkinter import ttk
from modified_entry import ModifiedAwareEntry

def on_modified(event):
    print(f"内容修改为：{event.widget.get()}")

root = tk.Tk()
entry = ModifiedAwareEntry(root)
entry.pack(padx=20, pady=20)
entry.bind("<<Modified>>", on_modified)

# 安全修改文本
entry.replace_text("初始值")
root.mainloop()
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Any


class ModifiedAwareEntry(ttk.Entry):
    """
    增强型输入框控件，支持精确的修改事件检测

    参数：
    master - 父容器
    **kwargs - 标准ttk.Entry参数
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._prev_text = self.get()
        self.modification_count = 0
        self._tracking = True

        # 绑定原生事件
        self._bind_events()

        # 处理变量追踪
        self._var_trace_id = None
        self._setup_var_tracing()

    def _bind_events(self):
        """绑定所有相关输入事件"""
        events = [
            ("<KeyRelease>", self._check_modification),
            ("<<Paste>>", self._delayed_check),
            ("<<Cut>>", self._delayed_check),
            ("<<Undo>>", self._delayed_check),
            ("<<Redo>>", self._delayed_check),
        ]
        for sequence, handler in events:
            self.bind(sequence, handler)

    def _setup_var_tracing(self):
        """配置变量追踪"""
        if var := self["textvariable"]:
            var = var if isinstance(var, tk.Variable) else self.tk.globalgetvar(var)
            self._var_trace_id = var.trace_add("write", self._var_modified)

    def _var_modified(self, *args):
        """处理变量修改"""
        if self._tracking:
            self.after_idle(self._check_modification)

    def _delayed_check(self, event=None):
        """延迟检测剪贴板操作"""
        self.after(10, self._check_modification)

    def _check_modification(self, event=None):
        """执行实际修改检测"""
        if not self._tracking:
            return

        current = self.get()
        if current != self._prev_text:
            self._prev_text = current
            self.modification_count += 1
            self.event_generate("<<Modified>>")

    def custom_insert(self, index: str, text: str) -> None:
        """重写插入方法"""
        if self._tracking:
            original = self.get()
            super().insert(index, text)
            if self.get() != original:
                self._trigger_modified()
        else:
            super().insert(index, text)

    def custom_delete(self, first: str, last: Optional[str] = None) -> None:
        """重写删除方法"""
        if self._tracking:
            original = self.get()
            super().delete(first, last)
            if self.get() != original:
                self._trigger_modified()
        else:
            super().delete(first, last)

    def _trigger_modified(self):
        """内部触发修改事件"""
        self.modification_count += 1
        self.event_generate("<<Modified>>")

    def replace_text(self, new_text: str) -> None:
        """安全替换文本内容
        参数：
            new_text - 要设置的新文本
        """
        current = self.get()
        if current != new_text:
            self.freeze_tracking()
            self.delete(0, tk.END)
            self.insert(0, new_text)
            self.resume_tracking()
            self._trigger_modified()

    def freeze_tracking(self):
        """暂停修改检测"""
        self._tracking = False

    def resume_tracking(self):
        """恢复修改检测"""
        self._tracking = True
        self._check_modification()


    def set_background_color(self, color: str) -> None:
        """设置Entry控件的背景颜色
        参数：
            color - 要设置的颜色值（例如 'red', '#FF0000'）
        """
        print(f"尝试设置背景颜色为: {color}")  # 添加调试信息
        try:
            # 创建一个唯一的样式名称，避免重复创建相同样式的性能问题
            style_name = f"Custom.ModifiedEntry.TEntry.{hash(color) % 10000}"
            style = ttk.Style()
            # 使用fieldbackground而不是background来正确设置ttk.Entry的背景色
            style.configure(style_name, fieldbackground=color)
            self.configure(style=style_name)
            print(f"成功设置背景颜色为: {color}")  # 添加调试信息
        except tk.TclError as e:
            print(f"错误: 无效的颜色值: {color}\n{e}")  # 添加调试信息

    # 重写标准方法
    insert = custom_insert
    delete = custom_delete

    def destroy(self):
        """清理资源"""
        if self._var_trace_id and (var := self["textvariable"]):
            # 确保变量存在后再移除追踪
            if isinstance(var, tk.Variable):
                try:
                    var.trace_remove("write", self._var_trace_id)
                except tk.TclError:
                    # 变量可能已经被销毁
                    pass
        super().destroy()


if __name__ == "__main__":
    # 演示程序
    root = tk.Tk()
    root.title("ModifiedAwareEntry 演示")

    def show_changes(event):
        entry = event.widget
        status.config(text=f"修改次数：{entry.modification_count}")

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)

    entry = ModifiedAwareEntry(frame)
    entry.pack(fill="x", pady=10)
    entry.bind("<<Modified>>", show_changes)

    ttk.Button(frame, text="安全设置", command=lambda: entry.replace_text("新值")).pack(
        side=tk.LEFT
    )
    ttk.Button(frame, text="原生设置", command=lambda: entry.insert(0, "测试")).pack(
        side=tk.LEFT
    )

    status = ttk.Label(frame)
    status.pack(pady=10)

    root.mainloop()
