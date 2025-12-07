import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, Menu, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle
import numpy as np
import json
import os
import sys
import math

# --- 全局配置 ---
# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 配置文件路径
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
DEFAULT_CONFIG_FILE = os.path.join(BASE_DIR, 'default_config.json')

# 生成图片的像素配置
IMG_WIDTH = 1920
IMG_HEIGHT = 1920
IMG_DPI = 300

# 代码中的硬编码默认值 (防止文件丢失)
HARDCODED_DEFAULTS = {
    "current_mode": "valve",
    "valve": {
        "diameter": "1600",
        "wd": "199",       
        "lw": "1056",         
        "pitch_base": "75",     
        "pitch_prime": "65",    
        "wc": "60",          
        "hole_dia": "39",
        "ws": "100",
        "num_sections": "4",
        "layout_mode": "isosceles"
    },
    "sieve": {
        "diameter": "1600",
        "wd": "199",       
        "lw": "1056",         
        "pitch_base": "20",     
        "pitch_prime": "17.32",    
        "wc": "60",          
        "hole_dia": "10",
        "ws": "100",
        "num_sections": "4",
        "magnification": "5",
        "layout_mode": "equilateral"
    }
}

# --- 字体设置 ---
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Heiti TC']
    plt.rcParams['axes.unicode_minus'] = False
    CHINESE_FONT = 'SimHei'
except:
    CHINESE_FONT = 'Arial'

# 统一的线条样式
LINE_COLOR = 'black'
LINE_WIDTH = 2

class ValveTrayApp:
    """
    阀孔/筛板 塔盘排布程序
    标准应用程序模板类
    """
    def __init__(self, root):
        self.root = root
        self.root.title("阀孔/筛板实际孔数计算")
        
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
        self.current_mode_str = self.config.get("current_mode", "valve")
        self.mode_var = tk.StringVar(value=self.current_mode_str)
        self.layout_mode_var = tk.StringVar(value="isosceles") # 临时存储布局模式

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
        
        # 绘图缩放因子
        self.current_scale = 1.0

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
        self.main_paned.add(self.left_frame, minsize=350, width=int(screen_width * 0.35))
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
        """创建具体的输入控件"""
        lbl_title = ttk.Label(parent, text="参数设置 (mm)", font=self.font_title, anchor="center")
        lbl_title.pack(fill=tk.X, pady=(0, 20))
        
        # === 模式切换 ===
        mode_frame = ttk.LabelFrame(parent, text="塔盘类型", padding=10)
        mode_frame.pack(fill=tk.X, pady=5)
        
        rb_valve = tk.Radiobutton(mode_frame, text="浮阀塔盘", variable=self.mode_var, 
                              value="valve", command=self.on_mode_change, font=self.font_bold)
        rb_valve.pack(side=tk.LEFT, padx=10, expand=True)
        
        rb_sieve = tk.Radiobutton(mode_frame, text="筛板塔盘", variable=self.mode_var, 
                              value="sieve", command=self.on_mode_change, font=self.font_bold)
        rb_sieve.pack(side=tk.LEFT, padx=10, expand=True)

        # === 动态参数区域 ===
        self.dynamic_input_frame = ttk.Frame(parent)
        self.dynamic_input_frame.pack(fill=tk.X)
        
        # 初始化显示当前模式的控件
        self.refresh_dynamic_inputs()

        # 按钮区
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=20)

        btn_draw = tk.Button(btn_frame, text="生成排布 / 计算", command=self.plot_graph,
                           bg="#4CAF50", fg="white", font=self.font_bold, relief="raised", height=2)
        btn_draw.pack(fill=tk.X, pady=5)

        btn_reset = tk.Button(btn_frame, text="重置参数", command=self.reset_params,
                            font=self.font_base, relief="raised", fg="red")
        btn_reset.pack(fill=tk.X, pady=5)
        
        lbl_info = ttk.Label(parent, text="说明：\n1. 切换模式会自动保存当前参数。\n2.筛板模式下使用公式计算孔数，仅绘制示意图\n3. 筛板示意图右上角展示局部排布。\n4. 中间黑色分割线可以左右拖动调整宽度。", 
                           foreground="gray", justify=tk.LEFT, wraplength=250)
        lbl_info.pack(fill=tk.X, pady=20)

        # 结果标签
        self.result_label = ttk.Label(parent, text="孔总数: -", font=self.font_title, foreground="blue", anchor="center")
        self.result_label.pack(fill=tk.X, pady=10)

    def refresh_dynamic_inputs(self):
        """刷新动态输入区域 (重建控件)"""
        # 清空旧控件
        for widget in self.dynamic_input_frame.winfo_children():
            widget.destroy()
        
        self.inputs = {}
        
        current_mode = self.mode_var.get()
        params = self.config.get(current_mode, {})

        # === 排布模式 ===
        layout_group = ttk.LabelFrame(self.dynamic_input_frame, text="排布模式", padding=10)
        layout_group.pack(fill=tk.X, pady=5)

        # 获取当前 layout_mode
        self.layout_mode_var.set(params.get("layout_mode", "isosceles"))
        # 存入 inputs 以便 save_current_params_to_memory 读取
        # Radiobutton 不直接存入 self.inputs，而是通过 layout_mode_var 关联，
        # 我们需要在 save 时手动处理，或者将其包装进 inputs。
        # 为了统一处理，我们在 save_current_params_to_memory 中特殊处理 layout_mode_var
        
        rb1 = tk.Radiobutton(layout_group, text="等腰三角形 (自定义t')", variable=self.layout_mode_var, 
                             value="isosceles", command=self.on_layout_mode_change)
        rb1.pack(anchor=tk.W)
        
        rb2 = tk.Radiobutton(layout_group, text="正三角形 (自动t')", variable=self.layout_mode_var, 
                             value="equilateral", command=self.on_layout_mode_change)
        rb2.pack(anchor=tk.W)

        # === 参数列表 ===
        param_group = ttk.LabelFrame(self.dynamic_input_frame, text="尺寸参数 (mm)", padding=10)
        param_group.pack(fill=tk.X, pady=5)

        self.add_input_row(param_group, "塔直径 (Φ):", "diameter", params)
        self.add_input_row(param_group, "弓形降液管宽(Wd):", "wd", params)
        self.add_input_row(param_group, "堰长 (Lw):", "lw", params)
        self.add_input_row(param_group, "孔中心距 (t):", "pitch_base", params)
        self.add_input_row(param_group, "排间距 (t'):", "pitch_prime", params)
        self.add_input_row(param_group, "边缘区宽度 (Wc):", "wc", params)
        self.add_input_row(param_group, "孔/阀直径:", "hole_dia", params)
        self.add_input_row(param_group, "破沫区宽度 (Ws):", "ws", params)
        self.add_input_row(param_group, "分块数:", "num_sections", params)
        
        # 触发一次布局变更处理以设置 t' 状态
        self.on_layout_mode_change()

    def add_input_row(self, parent, label_text, key, params_dict):
        """辅助函数：添加一行输入框"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        lbl = ttk.Label(frame, text=label_text, width=18, anchor="w", font=self.font_base)
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
        
        # 3. 刷新 UI
        self.refresh_dynamic_inputs()

    def on_layout_mode_change(self):
        """排布模式改变时的回调"""
        mode = self.layout_mode_var.get()
        if "pitch_prime" in self.inputs:
            entry = self.inputs["pitch_prime"]
            if mode == "equilateral":
                # 自动计算 t'
                try:
                    t_base = float(self.inputs["pitch_base"].get())
                    t_prime = t_base * (np.sqrt(3) / 2.0)
                    entry.delete(0, tk.END)
                    entry.insert(0, f"{t_prime:.2f}")
                    entry.config(state='disabled')
                except:
                    pass
            else:
                entry.config(state='normal')

    def save_current_params_to_memory(self):
        """将当前 UI 的值保存到 self.config"""
        mode = self.current_mode_str
        if mode not in self.config:
            self.config[mode] = {}
            
        target_dict = self.config[mode]
        for key, widget in self.inputs.items():
            if isinstance(widget, ttk.Entry):
                target_dict[key] = widget.get()
        
        target_dict["layout_mode"] = self.layout_mode_var.get()

    def create_plot_area(self):
        """创建右侧绘图区"""
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.axis('off')
        
        self.ax.text(0.5, 0.5, "请点击左侧“生成排布”按钮", 
                    ha='center', va='center', fontsize=16, fontproperties=CHINESE_FONT)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.popup_menu = Menu(self.root, tearoff=0)
        self.popup_menu.add_command(label="另存为图片...", command=self.save_plot_as_image)
        self.canvas_widget.bind("<Button-3>", self.show_popup_menu)

    def render_and_show(self, temp_fig):
        """将高清图渲染并显示在屏幕上"""
        canvas = FigureCanvasAgg(temp_fig)
        canvas.draw()
        renderer = canvas.get_renderer()
        raw_data = renderer.buffer_rgba()
        buf = np.asarray(raw_data)
        
        self.ax.clear()
        self.ax.imshow(buf)
        self.ax.axis('off')
        self.canvas.draw()
        
        self.generated_fig = temp_fig

    def plot_graph(self):
        """核心绘图/计算逻辑"""
        self.save_current_params_to_memory()
        self.save_config()
        
        mode = self.mode_var.get()
        params = self.config.get(mode, {})
        
        # 准备数据
        try:
            D = float(params.get("diameter", 0))
            Wd = float(params.get("wd", 0))
            t_base = float(params.get("pitch_base", 0))
            t_prime = float(params.get("pitch_prime", 0))
            Wc = float(params.get("wc", 0))
            Ws = float(params.get("ws", 0))
            d_hole = float(params.get("hole_dia", 0))
            num_sections = int(float(params.get("num_sections", 1)))
            layout_mode = params.get("layout_mode", "isosceles")
            
            # 正三角形模式下重新计算 t_prime 以确保精确
            if layout_mode == "equilateral":
                 t_prime = t_base * (np.sqrt(3) / 2.0)
                 
            if D <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值！")
            return

        data = (D, Wd, t_base, t_prime, Wc, Ws, d_hole, num_sections)

        # 创建高清绘图对象
        w_inch = IMG_WIDTH / IMG_DPI
        h_inch = IMG_HEIGHT / IMG_DPI
        temp_fig = Figure(figsize=(w_inch, h_inch), dpi=IMG_DPI)
        # 留出边距给标题和坐标轴，避免 [0,0,1,1] 铺满导致文字被切
        ax_temp = temp_fig.add_axes([0.1, 0.05, 0.8, 0.8])

        count = 0
        if mode == "valve":
            count = self.plot_valve_tray(ax_temp, data)
        else:
            count = self.plot_sieve_tray(ax_temp, data)
            
        self.render_and_show(temp_fig)
        self.result_label.config(text=f"孔总数: {count}")

    # --- 绘图逻辑迁移 ---
    
    def plot_valve_tray(self, ax, data):
        D, Wd, t_base, t_prime, Wc, Ws, d_hole, num_sections = data
        R = D / 2.0
        hole_radius = d_hole / 2.0
        BEAM_HALF_THICKNESS = Wc / 8.0 
        clearance = Wc / 4.0 

        # 样式
        lw_base = LINE_WIDTH * self.current_scale
        hole_lw = 0.5 * self.current_scale
        cross_lw = 1.5 * self.current_scale
        
        # 梁
        beam_centers = []
        if num_sections > 1:
            step = D / num_sections
            start = -R
            for i in range(1, num_sections):
                beam_centers.append(start + i * step)

        self._draw_base_structure(ax, R, Wd, Wc, BEAM_HALF_THICKNESS, D, beam_centers, lw_base)
        weir_y = R - Wd
        self._draw_runway_lines(ax, R, Wc, Ws, weir_y, lw_base)

        # 阀孔
        Y_runway_line_abs = weir_y - Ws 
        active_y_limit = Y_runway_line_abs - hole_radius
        R_runway = R - Wc
        active_safe_R = R_runway - hole_radius
        beam_exclusion = clearance + hole_radius
        
        valves_list = []
        rows_y = []
        j = 0
        while j * t_prime <= active_y_limit:
            current_y = j * t_prime
            if current_y >= -active_y_limit: rows_y.append(current_y)
            j += 1
        j = 1
        while -j * t_prime >= -active_y_limit:
            current_y = -j * t_prime
            if current_y <= active_y_limit: rows_y.append(current_y)
            j += 1
        rows_y.sort()

        row_index = 0
        for y in rows_y:
            x_offset = 0.0
            if row_index % 2 != 0: x_offset = t_base / 2.0
            
            max_x = np.sqrt(np.maximum(0, active_safe_R**2 - y**2))
            if max_x <= 0: 
                row_index += 1
                continue

            row_x = []
            k = 0
            while True:
                x = k * t_base + x_offset
                if x <= max_x: row_x.append(x)
                else: break
                k += 1
            k = 1
            while True:
                x = -k * t_base + x_offset
                if x >= -max_x: row_x.append(x)
                else: break
                k += 1
            
            row_x = sorted(list(set(row_x)))

            for x in row_x:
                on_beam = False
                for bx in beam_centers:
                    if abs(x - bx) < beam_exclusion:
                        on_beam = True
                        break
                if on_beam: continue

                valves_list.append((x, y))
                v_circle = Circle((x, y), hole_radius, color='black', alpha=1.0, linewidth=hole_lw, fill=False) 
                ax.add_patch(v_circle)
            
            row_index += 1

        for i, (x1, y1) in enumerate(valves_list):
            for j in range(i + 1, min(i + 50, len(valves_list))): 
                (x2, y2) = valves_list[j]
                if abs(abs(y1 - y2) - t_prime) < 0.1 and abs(abs(x1 - x2) - t_base / 2.0) < 0.1:
                    ax.plot([x1, x2], [y1, y2], color='black', linestyle='-', linewidth=cross_lw, alpha=0.6)

        self._finalize_plot(ax, len(valves_list), D, t_base, t_prime, Ws, Wc, "浮阀", is_sieve=False, num_sections=num_sections)
        return len(valves_list)

    def plot_sieve_tray(self, ax, data):
        D, Wd, t_base, t_prime, Wc, Ws, d_hole, num_sections = data
        R = D / 2.0
        hole_radius = d_hole / 2.0
        BEAM_HALF_THICKNESS = Wc / 8.0 
        clearance = Wc / 4.0 

        lw_base = LINE_WIDTH * self.current_scale
        hole_lw = 1.0 * self.current_scale
        
        beam_centers = []
        if num_sections > 1:
            step = D / num_sections
            start = -R
            for i in range(1, num_sections):
                beam_centers.append(start + i * step)
        
        self._draw_base_structure(ax, R, Wd, Wc, BEAM_HALF_THICKNESS, D, beam_centers, lw_base)
        weir_y = R - Wd
        self._draw_runway_lines(ax, R, Wc, Ws, weir_y, lw_base)

        # 十字虚线
        Y_runway = weir_y - Ws
        R_runway = R - Wc
        if Y_runway > 0 and R_runway > 0:
            x_limit = R_runway
            ax.plot([-x_limit, x_limit], [0, 0], color='black', linestyle='--', linewidth=hole_lw)
            ax.plot([0, 0], [-Y_runway, Y_runway], color='black', linestyle='--', linewidth=hole_lw)

        # 放大镜逻辑
        self._draw_magnifier(ax, R_runway, Y_runway, t_base, t_prime, hole_radius, hole_lw)

        count = self._calculate_sieve_count(D, Wd, Wc, Ws, t_base, t_prime, hole_radius, clearance, beam_centers)
        self._finalize_plot(ax, count, D, t_base, t_prime, Ws, Wc, "筛板", is_sieve=True, num_sections=num_sections)
        return count

    def _draw_magnifier(self, ax, R_runway, Y_runway, t_base, t_prime, hole_radius, hole_lw):
        mag_radius = min(R_runway, Y_runway) * 0.55 
        mag_center_y = Y_runway - mag_radius
        dist_sq = (R_runway - mag_radius)**2
        mag_center_x = np.sqrt(dist_sq - mag_center_y**2) if dist_sq >= mag_center_y**2 else 0
        
        mag_lw = 2.0 * self.current_scale
        mag_circle = Circle((mag_center_x, mag_center_y), mag_radius, facecolor='white', edgecolor='black', linewidth=mag_lw, zorder=10)
        ax.add_patch(mag_circle)

        target_holes = 50
        area_mag = np.pi * mag_radius**2
        unit_area = t_base * t_prime
        magnification = np.sqrt(area_mag / (target_holes * 1.5 * unit_area)) if unit_area > 0 else 1.0
        if magnification < 0.5: magnification = 0.5

        scaled_t_base = t_base * magnification
        scaled_t_prime = t_prime * magnification
        scaled_hole_r = hole_radius * magnification
        
        rows_needed = int(mag_radius / scaled_t_prime) + 2
        cols_needed = int(mag_radius / scaled_t_base) + 2

        candidate_holes = []
        for r in range(-rows_needed, rows_needed + 1):
            y_local = r * scaled_t_prime
            x_offset = 0 if r % 2 == 0 else scaled_t_base / 2.0
            for c in range(-cols_needed, cols_needed + 1):
                x_local = c * scaled_t_base + x_offset
                dist = np.sqrt(x_local**2 + y_local**2)
                if dist + scaled_hole_r <= mag_radius * 1.1:
                     candidate_holes.append((dist, x_local, y_local))
        
        candidate_holes.sort(key=lambda x: x[0])
        holes_to_draw = candidate_holes[:target_holes]

        for _, x_local, y_local in holes_to_draw:
            h_c = Circle((mag_center_x + x_local, mag_center_y + y_local), 
                         scaled_hole_r, color='black', fill=False, linewidth=hole_lw, zorder=11)
            ax.add_patch(h_c)

        for i in range(len(holes_to_draw)):
            _, x1_local, y1_local = holes_to_draw[i]
            x1_abs = mag_center_x + x1_local
            y1_abs = mag_center_y + y1_local
            
            for j in range(i + 1, len(holes_to_draw)):
                _, x2_local, y2_local = holes_to_draw[j]
                x2_abs = mag_center_x + x2_local
                y2_abs = mag_center_y + y2_local
                
                dx = abs(x1_local - x2_local)
                dy = abs(y1_local - y2_local)
                tol = scaled_t_base * 0.1 
                
                if abs(dy - scaled_t_prime) < tol and abs(dx - scaled_t_base/2.0) < tol:
                    ax.plot([x1_abs, x2_abs], [y1_abs, y2_abs], color='black', linestyle='-', linewidth=hole_lw, alpha=0.6, zorder=11)

    def _calculate_sieve_count(self, D, Wd, Wc, Ws, t_base, t_prime, hole_radius, clearance, beam_centers):
        R = D / 2.0
        R_runway = R - Wc
        Y_limit = (R - Wd) - Ws
        if R_runway <= 0 or Y_limit <= 0: return 0

        if Y_limit >= R_runway:
            area_runway = np.pi * R_runway**2
        else:
            d = Y_limit
            sector_area = R_runway**2 * np.arccos(d/R_runway)
            triangle_area = d * np.sqrt(R_runway**2 - d**2)
            segment_area = sector_area - triangle_area
            area_runway = np.pi * R_runway**2 - 2 * segment_area

        exclusion_width = 2 * (clearance + hole_radius)
        area_beams = 0
        for bx in beam_centers:
            if abs(bx) >= R_runway: continue
            max_y_at_beam = np.sqrt(R_runway**2 - bx**2)
            actual_h = min(max_y_at_beam, Y_limit)
            area_beams += 2 * actual_h * exclusion_width

        net_area = max(0, area_runway - area_beams)
        area_per_hole = t_base * t_prime
        return int(net_area / area_per_hole) if area_per_hole > 0 else 0

    def _draw_base_structure(self, ax, R, Wd, Wc, BEAM_HALF_THICKNESS, D, beam_centers, lw_base):
        weir_y = R - Wd
        tower_circle = Circle((0, 0), R, fill=False, color=LINE_COLOR, linewidth=lw_base)
        ax.add_patch(tower_circle)

        x_at_weir = np.sqrt(np.maximum(0, R**2 - weir_y**2))
        ax.plot([-x_at_weir, x_at_weir], [weir_y, weir_y], color=LINE_COLOR, linewidth=lw_base)
        ax.plot([-x_at_weir, x_at_weir], [-weir_y, -weir_y], color=LINE_COLOR, linewidth=lw_base)

        arc_inset = Wc / 4.0
        arc_R = R - arc_inset
        active_y = weir_y - arc_inset
        
        beam_intervals = [(c - BEAM_HALF_THICKNESS, c + BEAM_HALF_THICKNESS) for c in beam_centers]
        def in_beam(x):
            for b_start, b_end in beam_intervals:
                if b_start < x < b_end: return True
            return False

        x_max_line = np.sqrt(np.maximum(0, arc_R**2 - active_y**2))
        xs = np.linspace(-x_max_line, x_max_line, 200)
        curr_seg = []
        for x in xs:
            if not in_beam(x): curr_seg.append(x)
            else:
                if curr_seg:
                    ax.plot([curr_seg[0], curr_seg[-1]], [active_y, active_y], color=LINE_COLOR, linewidth=lw_base)
                    ax.plot([curr_seg[0], curr_seg[-1]], [-active_y, -active_y], color=LINE_COLOR, linewidth=lw_base)
                    curr_seg = []
        if curr_seg:
            ax.plot([curr_seg[0], curr_seg[-1]], [active_y, active_y], color=LINE_COLOR, linewidth=lw_base)
            ax.plot([curr_seg[0], curr_seg[-1]], [-active_y, -active_y], color=LINE_COLOR, linewidth=lw_base)

        theta = np.linspace(0, 2*np.pi, 360)
        x_arc = arc_R * np.cos(theta)
        y_arc = arc_R * np.sin(theta)
        mask = (np.abs(y_arc) < active_y)
        curr_arc_x, curr_arc_y = [], []
        for i in range(len(mask)):
            if mask[i] and not in_beam(x_arc[i]):
                curr_arc_x.append(x_arc[i])
                curr_arc_y.append(y_arc[i])
            else:
                if curr_arc_x:
                    ax.plot(curr_arc_x, curr_arc_y, color=LINE_COLOR, linewidth=lw_base)
                    curr_arc_x, curr_arc_y = [], []
        if curr_arc_x: ax.plot(curr_arc_x, curr_arc_y, color=LINE_COLOR, linewidth=lw_base)

        for b_start, b_end in beam_intervals:
            for bx in [b_start, b_end]:
                y_lim_at_beam = np.sqrt(np.maximum(0, arc_R**2 - bx**2))
                draw_h = min(y_lim_at_beam, active_y)
                ax.plot([bx, bx], [-draw_h, draw_h], color=LINE_COLOR, linewidth=lw_base)

    def _draw_runway_lines(self, ax, R, Wc, Ws, weir_y, lw_base):
        R_runway = R - Wc
        Y_runway = weir_y - Ws
        if R_runway <= 0 or Y_runway <= 0: return
        dash_lw = lw_base * 0.75
        x_limit = np.sqrt(np.maximum(0, R_runway**2 - Y_runway**2))
        
        ax.plot([-x_limit, x_limit], [Y_runway, Y_runway], color='blue', linestyle='--', linewidth=dash_lw)
        ax.plot([-x_limit, x_limit], [-Y_runway, -Y_runway], color='blue', linestyle='--', linewidth=dash_lw)
        
        theta_start = np.arcsin(Y_runway / R_runway)
        t_right = np.linspace(-theta_start, theta_start, 50)
        ax.plot(R_runway * np.cos(t_right), R_runway * np.sin(t_right), color='blue', linestyle='--', linewidth=dash_lw)
        t_left = np.linspace(np.pi - theta_start, np.pi + theta_start, 50)
        ax.plot(R_runway * np.cos(t_left), R_runway * np.sin(t_left), color='blue', linestyle='--', linewidth=dash_lw)

    def _finalize_plot(self, ax, count, D, t, t_prime, Ws, Wc, type_name, is_sieve=False, num_sections=1):
        ax.set_aspect('equal', adjustable='box')
        limit = D/2.0 * 1.05
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        
        layout_name = "正三角形" if self.config[self.mode_var.get()].get("layout_mode") == "equilateral" else "等腰三角形"
        title_str = (f"{type_name} - {layout_name}排布\n"
                     f"D={int(D)} t={int(t)} t'={t_prime:.1f} Ws={int(Ws)} Wc={int(Wc)}\n"
                     f"分块数: {num_sections} | 总孔数: {count}")
        if is_sieve: title_str += " (估算)"
            
        title_fs = 32 * self.current_scale
        tick_fs = 24 * self.current_scale
        
        ax.set_title(title_str, fontproperties=CHINESE_FONT, fontsize=title_fs, pad=20 * self.current_scale)
        ax.tick_params(axis='both', which='major', labelsize=tick_fs)

    def load_config(self):
        """加载配置"""
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

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    for k, v in saved.items():
                        if isinstance(v, dict) and k in self.config:
                            self.config[k].update(v)
                        else:
                            self.config[k] = v
            except Exception as e:
                print(f"读取用户配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def reset_params(self):
        """重置参数"""
        if messagebox.askyesno("确认", "确定要重置为默认参数吗？"):
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
                except:
                    pass
            
            # 恢复当前模式
            current_mode = self.config.get("current_mode", "valve")
            self.mode_var.set(current_mode)
            self.current_mode_str = current_mode
            
            self.refresh_dynamic_inputs()
            self.plot_graph()

    def save_plot_as_image(self):
        """保存图片"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("JPG图片", "*.jpg"), ("PDF文档", "*.pdf")],
            title="保存图表",
            initialfile=f"{self.mode_var.get()}_layout.png"
        )
        if file_path:
            try:
                if self.generated_fig:
                    self.generated_fig.savefig(file_path, dpi=IMG_DPI, bbox_inches='tight')
                else:
                    self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("成功", f"已保存至：{file_path}")
            except Exception as e:
                messagebox.showerror("失败", f"保存失败：{e}")

    def show_popup_menu(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()

    def on_window_resize(self, event):
        self.current_scale = max(0.5, event.height / 1000.0)

    def on_closing(self):
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.save_current_params_to_memory()
            self.save_config()
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = ValveTrayApp(root)
    root.mainloop()
