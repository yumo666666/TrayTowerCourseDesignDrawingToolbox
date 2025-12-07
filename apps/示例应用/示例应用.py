import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, Menu, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
import json
import os
import sys

# --- 全局配置 ---
# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 配置文件路径
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
DEFAULT_CONFIG_FILE = os.path.join(BASE_DIR, 'default_config.json')

# 生成图片的像素配置
IMG_WIDTH = 1920
IMG_HEIGHT = 1920
IMG_DPI = 300  # DPI 保持 100 方便计算，实际尺寸由 WIDTH/HEIGHT 决定

# 代码中的硬编码默认值 (防止文件丢失)
HARDCODED_DEFAULTS = {
    "current_mode": "mode_a",
    "mode_a": {
        "title": "模式A - 椭圆",
        "param_a": "100",
        "param_b": "50",
        "show_grid": "1"
    },
    "mode_b": {
        "title": "模式B - 螺旋线",
        "param_a": "10",
        "param_b": "2",
        "show_grid": "1"
    }
}

# --- 字体设置 ---
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Heiti TC']
    plt.rcParams['axes.unicode_minus'] = False
    CHINESE_FONT = 'SimHei'
except:
    CHINESE_FONT = 'Arial'

class StandardApp:
    """
    标准应用程序模板类
    用于规范化所有子程序的结构
    """
    def __init__(self, root):
        self.root = root
        self.root.title("标准示例程序") # TODO: 修改标题
        
        # === 窗口设置 ===
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-fullscreen', True)
            
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # === 数据初始化 ===
        self.inputs = {}  # 存储输入框控件引用
        self.config = {}  # 存储配置数据
        self.load_config()
        
        # 记录当前模式，用于切换时保存旧数据
        self.current_mode_str = self.config.get("current_mode", "mode_a")
        self.mode_var = tk.StringVar(value=self.current_mode_str)

        # === 字体初始化 (自适应) ===
        self.base_font_size = 12
        self.font_base = tkfont.Font(family=CHINESE_FONT, size=self.base_font_size)
        self.font_bold = tkfont.Font(family=CHINESE_FONT, size=self.base_font_size, weight="bold")
        self.font_title = tkfont.Font(family=CHINESE_FONT, size=int(self.base_font_size*1.5), weight="bold")
        
        # 全局菜单字体
        self.root.option_add('*Menu.font', f'{CHINESE_FONT} 12')

        # === UI 布局 ===
        self.setup_ui()
        
        # === 绑定事件 ===
        self.root.bind("<Configure>", self.on_window_resize)
        
        # === 初始化状态 ===
        self.generated_fig = None # 存储生成的高清图引用

    def setup_ui(self):
        """初始化界面布局"""
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.FLAT, sashwidth=8, bg="black", opaqueresize=False)
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # 1. 左侧控制区
        self.left_frame = ttk.Frame(self.main_paned, padding="10")
        
        # 2. 右侧绘图区
        self.right_frame = ttk.Frame(self.main_paned, padding="0")

        # 添加到分割窗口
        screen_width = self.root.winfo_screenwidth()
        self.main_paned.add(self.left_frame, minsize=300, width=int(screen_width * 0.4))
        self.main_paned.add(self.right_frame, minsize=400, stretch="always")

        self.create_scrollable_input_area()
        self.create_plot_area()

    def create_scrollable_input_area(self):
        """创建带滚动条的左侧输入区"""
        canvas_container = tk.Canvas(self.left_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical", command=canvas_container.yview)
        self.scrollable_frame = ttk.Frame(canvas_container)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_container.configure(scrollregion=canvas_container.bbox("all"))
        )
        canvas_window = canvas_container.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas_container.itemconfig(canvas_window, width=event.width)
        canvas_container.bind("<Configure>", on_canvas_configure)

        canvas_container.configure(yscrollcommand=scrollbar.set)

        canvas_container.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.left_frame.rowconfigure(0, weight=1)
        self.left_frame.columnconfigure(0, weight=1)
        
        def _on_mousewheel(event):
            canvas_container.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_container.bind_all("<MouseWheel>", _on_mousewheel)

        self.create_inputs(self.scrollable_frame)

    def create_inputs(self, parent):
        """[子类需修改] 创建具体的输入控件"""
        lbl_title = ttk.Label(parent, text="参数设置", font=self.font_title, anchor="center")
        lbl_title.pack(fill=tk.X, pady=(0, 20))
        
        # === 模式切换 ===
        mode_frame = ttk.LabelFrame(parent, text="图表模式", padding=10)
        mode_frame.pack(fill=tk.X, pady=5)
        
        rb_a = tk.Radiobutton(mode_frame, text="模式A (椭圆)", variable=self.mode_var, 
                              value="mode_a", command=self.on_mode_change, font=self.font_bold)
        rb_a.pack(side=tk.LEFT, padx=10, expand=True)
        
        rb_b = tk.Radiobutton(mode_frame, text="模式B (螺旋)", variable=self.mode_var, 
                              value="mode_b", command=self.on_mode_change, font=self.font_bold)
        rb_b.pack(side=tk.LEFT, padx=10, expand=True)

        # === 动态参数区域 ===
        # 我们使用一个 Frame 包裹所有会随模式变化的控件
        self.dynamic_input_frame = ttk.Frame(parent)
        self.dynamic_input_frame.pack(fill=tk.X)
        
        # 初始化显示当前模式的控件
        self.refresh_dynamic_inputs()

        # 按钮区
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=20)

        btn_draw = tk.Button(btn_frame, text="生成图表", command=self.plot_graph,
                           bg="#4CAF50", fg="white", font=self.font_bold, relief="raised", height=2)
        btn_draw.pack(fill=tk.X, pady=5)

        btn_reset = tk.Button(btn_frame, text="重置参数", command=self.reset_params,
                            font=self.font_base, relief="raised", fg="red")
        btn_reset.pack(fill=tk.X, pady=5)
        
        lbl_info = ttk.Label(parent, text="说明：\n1. 切换模式会自动保存当前参数。\n2. 模式A绘制椭圆，模式B绘制螺旋线。\n3. 中间黑色分割线可以左右拖动调整宽度。", 
                           foreground="gray", justify=tk.LEFT, wraplength=250)
        # 必须写这一个说明: 说明黑色分割线可以调
        lbl_info.pack(fill=tk.X, pady=20)

    def refresh_dynamic_inputs(self):
        """刷新动态输入区域 (重建控件)"""
        # 清空旧控件
        for widget in self.dynamic_input_frame.winfo_children():
            widget.destroy()
        
        # 清空 inputs 字典中与动态参数相关的引用，防止内存泄漏或逻辑错误
        # 注意：这里简单起见，我们重新构建 inputs
        # 但为了不丢失 Checkbox 等状态，我们需要小心
        # 在这个示例中，所有输入框都是动态重建的
        self.inputs = {}
        
        current_mode = self.mode_var.get()
        params = self.config.get(current_mode, {})

        # 参数组 1
        group1 = ttk.LabelFrame(self.dynamic_input_frame, text="基础参数", padding=10)
        group1.pack(fill=tk.X, pady=5)
        
        self.add_input_row(group1, "图表标题:", "title", params)
        self.add_input_row(group1, "参数 A:", "param_a", params)
        self.add_input_row(group1, "参数 B:", "param_b", params)

        # 参数组 2
        group2 = ttk.LabelFrame(self.dynamic_input_frame, text="显示选项", padding=10)
        group2.pack(fill=tk.X, pady=5)
        
        # 处理 int/str 类型转换
        grid_val = params.get("show_grid", 1)
        try:
            grid_val = int(grid_val)
        except:
            grid_val = 1
            
        self.inputs["show_grid"] = tk.IntVar(value=grid_val)
        cb = ttk.Checkbutton(group2, text="显示网格", variable=self.inputs["show_grid"])
        cb.pack(anchor="w")

    def add_input_row(self, parent, label_text, key, params_dict):
        """辅助函数：添加一行输入框"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        lbl = ttk.Label(frame, text=label_text, width=15, anchor="w", font=self.font_base)
        lbl.pack(side=tk.LEFT)
        
        entry = ttk.Entry(frame, font=self.font_base)
        entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        
        val = params_dict.get(key, "")
        entry.insert(0, str(val))
        
        self.inputs[key] = entry

    def on_mode_change(self):
        """切换模式时的回调"""
        new_mode = self.mode_var.get()
        if new_mode == self.current_mode_str:
            return

        # 1. 保存旧模式的参数
        self.save_current_params_to_memory()
        
        # 2. 更新当前模式记录
        self.current_mode_str = new_mode
        self.config["current_mode"] = new_mode
        
        # 3. 刷新 UI (加载新模式参数)
        self.refresh_dynamic_inputs()
        
        # 4. 自动重绘
        # self.plot_graph() # 可选，或者等待用户点击生成

    def save_current_params_to_memory(self):
        """将当前 UI 的值保存到 self.config 对应的模式中"""
        mode = self.current_mode_str
        if mode not in self.config:
            self.config[mode] = {}
            
        target_dict = self.config[mode]
        for key, widget in self.inputs.items():
            if isinstance(widget, ttk.Entry):
                target_dict[key] = widget.get()
            elif isinstance(widget, tk.IntVar):
                target_dict[key] = widget.get()

    def create_plot_area(self):
        """创建右侧绘图区"""
        # 屏幕预览用的低分辨率画布
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.axis('off') # 初始关闭坐标轴
        
        # 显示提示文字
        self.ax.text(0.5, 0.5, "请点击左侧“生成图表”按钮", 
                    ha='center', va='center', fontsize=16, fontproperties=CHINESE_FONT)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.popup_menu = Menu(self.root, tearoff=0)
        self.popup_menu.add_command(label="另存为图片...", command=self.save_plot_as_image)
        self.canvas_widget.bind("<Button-3>", self.show_popup_menu)

    def render_and_show(self, temp_fig):
        """将高清图渲染并显示在屏幕上"""
        # 1. 渲染到缓冲区 (Backend Agg)
        canvas = FigureCanvasAgg(temp_fig)
        canvas.draw()
        renderer = canvas.get_renderer()
        raw_data = renderer.buffer_rgba()
        
        # 2. 转换为 numpy 数组
        buf = np.asarray(raw_data)
        
        # 3. 在屏幕上显示 (显示为图像)
        self.ax.clear()
        self.ax.imshow(buf)
        self.ax.axis('off') # 关闭坐标轴，因为图像里已经有了
        self.canvas.draw()
        
        # 4. 保存引用以便另存为
        self.generated_fig = temp_fig

    def plot_graph(self):
        """[子类需修改] 核心绘图/计算逻辑"""
        # 绘图前先保存当前参数到 config 对象
        self.save_current_params_to_memory()
        # 然后保存到文件
        self.save_config()
        
        # 获取当前模式的参数
        mode = self.mode_var.get()
        params = self.config.get(mode, {})
        
        try:
            title = params.get("title", "未命名")
            val_a = float(params.get("param_a", 0))
            val_b = float(params.get("param_b", 0))
            show_grid = int(params.get("show_grid", 0))
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值！")
            return

        # 创建高清绘图对象 (离屏)
        w_inch = IMG_WIDTH / IMG_DPI
        h_inch = IMG_HEIGHT / IMG_DPI
        temp_fig = Figure(figsize=(w_inch, h_inch), dpi=IMG_DPI)
        # 注意：使用 add_subplot(111) 会有默认边距，如果想要精确控制像素，可以使用 add_axes
        # 这里为了简单展示图表，使用 subplot 即可，但如果要做精确工程图，建议用 add_axes([0.1, 0.1, 0.8, 0.8])
        ax_temp = temp_fig.add_subplot(111)

        if mode == "mode_a":
            # 模式 A: 椭圆
            t = np.linspace(0, 2*np.pi, 100)
            x = val_a * np.cos(t)
            y = val_b * np.sin(t)
            ax_temp.plot(x, y, label=f'椭圆 (A={val_a}, B={val_b})', color='blue')
            
        elif mode == "mode_b":
            # 模式 B: 螺旋线
            # param_a 控制圈数，param_b 控制间距
            t = np.linspace(0, val_a * 2 * np.pi, 500)
            r = val_b * t
            x = r * np.cos(t)
            y = r * np.sin(t)
            ax_temp.plot(x, y, label=f'螺旋 (圈数={val_a}, 间距={val_b})', color='red')

        ax_temp.set_title(title, fontproperties=CHINESE_FONT, fontsize=24) # 高清图字体要大一些
        
        if show_grid:
            ax_temp.grid(True, linestyle='--', alpha=0.6)
            
        ax_temp.legend(prop={'family': CHINESE_FONT, 'size': 8}, loc='upper right')
        ax_temp.axis('equal')

        # 渲染并显示
        self.render_and_show(temp_fig)

    def load_config(self):
        """加载配置：优先读取 config.json，其次 default_config.json，最后硬编码"""
        self.config = HARDCODED_DEFAULTS.copy()
        
        if os.path.exists(DEFAULT_CONFIG_FILE):
            try:
                with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    defaults = json.load(f)
                    # 深度合并 (简单版)
                    for k, v in defaults.items():
                        if isinstance(v, dict) and k in self.config:
                            self.config[k].update(v)
                        else:
                            self.config[k] = v
            except Exception as e:
                print(f"读取默认配置失败: {e}")

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    # 深度合并
                    for k, v in saved.items():
                        if isinstance(v, dict) and k in self.config:
                            self.config[k].update(v)
                        else:
                            self.config[k] = v
            except Exception as e:
                print(f"读取用户配置失败: {e}")

    def save_config(self):
        """保存配置到 config.json"""
        # 注意：self.config 应该在 save_current_params_to_memory 中已经更新了
        # 这里只需写入文件
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def reset_params(self):
        """重置参数：重新加载默认配置"""
        if messagebox.askyesno("确认", "确定要重置为默认参数吗？"):
            # 重新从 default_config.json 加载
            self.config = HARDCODED_DEFAULTS.copy()
            if os.path.exists(DEFAULT_CONFIG_FILE):
                try:
                    with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                        defaults = json.load(f)
                        for k, v in defaults.items():
                            if isinstance(v, dict) and k in self.config:
                                self.config[k].update(v)
                            else:
                                self.config[k] = v
                except Exception as e:
                    print(f"读取默认配置失败: {e}")
            
            # 恢复当前模式
            current_mode = self.config.get("current_mode", "mode_a")
            self.mode_var.set(current_mode)
            self.current_mode_str = current_mode
            
            # 刷新界面
            self.refresh_dynamic_inputs()
            self.plot_graph()

    def save_plot_as_image(self):
        """保存图片"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("JPG图片", "*.jpg"), ("PDF文档", "*.pdf")],
            title="保存图表",
            initialfile="示例图表.png"
        )
        if file_path:
            try:
                if self.generated_fig:
                    # 使用已生成的高清图保存
                    self.generated_fig.savefig(file_path, dpi=IMG_DPI, bbox_inches='tight')
                else:
                    # 如果还没生成，就保存当前的预览图 (fallback)
                    self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                    
                messagebox.showinfo("成功", f"已保存至：{file_path}")
            except Exception as e:
                messagebox.showerror("失败", f"保存失败：{e}")

    def show_popup_menu(self, event):
        """显示右键菜单"""
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()

    def on_window_resize(self, event):
        pass

    def on_closing(self):
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.save_current_params_to_memory()
            self.save_config()
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = StandardApp(root)
    root.mainloop()
