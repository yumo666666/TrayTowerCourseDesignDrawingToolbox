import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, Menu, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches
import matplotlib.path as mpath
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

# 生成图片的像素配置 (19.2 * 100 = 1920, 32.0 * 100 = 3200)
IMG_WIDTH = 1920
IMG_HEIGHT = 3200
IMG_DPI = 100

# 代码中的硬编码默认值 (防止文件丢失)
HARDCODED_DEFAULTS = {
    "current_mode": "standard",
    "standard": {
        "D": "1.6",
        "Z": "13.95",
        "N_rect": "22",
        "N_strip": "10",
        "W_d": "0.192",
        "H_weir": "0.049",
        "H_liq_weir": "0.021",
        "H_d": "0.13763",
        "h_b": "0.0485"
    }
}

# --- 字体设置 ---
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Heiti TC']
    plt.rcParams['axes.unicode_minus'] = False
    CHINESE_FONT = 'SimHei'
except:
    CHINESE_FONT = 'Arial'

# ==========================================
# 绘图函数 (保持原有逻辑)
# ==========================================

def create_tower_plot(D, Z, N_rect, N_strip, W_d, H_weir, H_liq_weir, H_d, h_b, figsize=(19.2, 32.0), dpi=100):
    """
    根据给定的参数生成精馏塔绘图，并在右侧标注参数。
    新增参数 Hd (降液管液高) 和 h_b (降液管底隙 h0)。
    """
    
    # 派生参数
    R = D / 2
    N_total = N_rect + N_strip
    Head_H = D * 0.25 
    
    # --- 液位和间距计算 ---
    Liquid_Slope = 0.07
    H_liq_inlet = H_liq_weir + Liquid_Slope 
    Plate_Spacing = Z / (N_total + 2) 
    FEED_PLATE_IDX = N_rect + 1 
    target_fall_height = Plate_Spacing - Liquid_Slope
    
    # --- 绘图初始化 ---
    fig = Figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    
    # --- 绘图辅助函数 (内部定义以简化传入) ---

    def draw_waterfall(ax, x_weir, y_weir_top, direction, fall_height, color, h_b):
        """绘制抛物线跌落液流，修正水平终点，使其落到下一层板的 y + h_b 处"""
        start_x = x_weir
        start_y = y_weir_top
        
        # 修正: 液流的终点 y 坐标应为 (下一层板的 y) + h_b
        # 下一层板的 y 坐标为 (y_current_plate - Plate_Spacing)，所以终点为 (y_current_plate - Plate_Spacing) + h_b
        end_y = start_y - Plate_Spacing + h_b 
        
        max_horizontal_dist = W_d * 0.8 
        dist = 0.2 * direction 
        end_x = start_x + max_horizontal_dist * direction
        control_x2 = start_x + dist * 0.8

        verts = [
            (start_x, start_y), (start_x + dist, start_y), 
            (end_x, end_y), (end_x - 0.05 * direction, end_y), 
            (control_x2, start_y - 0.1), (start_x, start_y - 0.1), 
            (start_x, start_y),
        ]
        
        codes = [
            mpath.Path.MOVETO, mpath.Path.CURVE3, mpath.Path.CURVE3,
            mpath.Path.LINETO, mpath.Path.CURVE3, mpath.Path.CURVE3,
            mpath.Path.CLOSEPOLY,
        ]
        
        path = mpath.Path(verts, codes)
        patch = patches.PathPatch(path, facecolor=color, edgecolor='none', alpha=0.6, zorder=2)
        ax.add_patch(patch)

    def draw_gradient_liquid(ax, x_start, x_end, y_base, h_start, h_end, color):
        """绘制有坡度的板上液层 (梯形)"""
        verts = [
            (x_start, y_base), (x_end, y_base), (x_end, y_base + h_end),       
            (x_start, y_base + h_start), (x_start, y_base)              
        ]
        poly = patches.Polygon(verts, facecolor=color, edgecolor='none', alpha=0.7, zorder=2)
        ax.add_patch(poly)

    def draw_gas_arrows(ax, x_start, x_end, y_base, color='red'):
        """在液层下方绘制红色细箭头表示气相流动"""
        num_arrows = 3
        x_positions = np.linspace(x_start, x_end, num_arrows + 2)[1:-1]
        
        # 气相箭头的起点 Y 坐标 (板上四分之一板间距处)
        y_start_arrow = y_base + Plate_Spacing * 0.33 
        
        # 气相箭头的长度 (二分之一板间距)
        arrow_length = Plate_Spacing * 0.33
        
        # 箭头宽度/长度与塔板间距成比例
        head_width = Plate_Spacing * 0.08
        head_length = Plate_Spacing * 0.1
        arrow_linewidth = 2

        for x in x_positions:
            ax.arrow(x, y_start_arrow, 0, arrow_length, 
                     head_width=head_width, head_length=head_length, 
                     fc=color, ec=color, alpha=0.8, lw=arrow_linewidth, zorder=3)

    # --- A. 塔体外壳 ---
    rect_tower = patches.Rectangle((-R, 0), D, Z, lw=2, ec='black', fc='none', zorder=5)
    ax.add_patch(rect_tower)
    top_head = patches.Arc((0, Z), D, Head_H*2, theta1=0, theta2=180, lw=2, ec='black', zorder=5)
    ax.add_patch(top_head)
    bottom_head = patches.Arc((0, 0), D, Head_H*2, theta1=180, theta2=360, lw=2, ec='black', zorder=5)
    ax.add_patch(bottom_head)
    
    clip_rect = patches.Rectangle((-R, 0), D, Z, transform=ax.transData)
    ax.set_clip_path(clip_rect)

    # --- B. 塔板循环 (修正降液管侧壁和液位绘制) ---
    for i in range(N_total):
        plate_idx = i + 1
        y = Z - 1.5 * Plate_Spacing - i * Plate_Spacing
        is_odd = (plate_idx % 2 != 0)
        
        if plate_idx < FEED_PLATE_IDX:
            liq_color = '#a6cee3'
        else:
            liq_color = '#fdbf6f'

        x_left_wall = -R
        x_right_wall = R
        
        # 降液管底部 Y 坐标 (即与下一层板的距离为 h_b)
        y_droptube_bottom = y - Plate_Spacing + h_b
        # 降液管内液面 Y 坐标
        y_droptube_level = y + H_weir + H_liq_weir - H_d

        if is_odd:
            # 奇数板：降液管在右侧
            x_weir = R - W_d
            
            # 1. 堰板 (垂直)
            ax.plot([x_weir, x_weir], [y, y + H_weir], 'k-', lw=2, zorder=3) 
            # 2. 塔板 (水平)
            ax.plot([-R, x_weir], [y, y], 'k-', lw=1.5, zorder=3)            
            
            # 3. 降液管侧壁 (竖直板向下延伸到 h_b)
            ax.plot([R, R], [y, y_droptube_bottom], 'k-', lw=1, zorder=3)
            ax.plot([x_weir, x_weir], [y + H_weir, y_droptube_bottom], 'k-', lw=1, zorder=3)

            # 5. 绘制降液管液柱 (底部边界即为 h_b)
            ax.add_patch(patches.Rectangle((x_weir, y_droptube_bottom), W_d, y_droptube_level - y_droptube_bottom, facecolor=liq_color, alpha=0.9, zorder=3, edgecolor='none'))

            # 6. 液层和液流
            draw_gradient_liquid(ax, -R, x_weir + 0.0, y, H_weir + H_liq_inlet, H_weir + H_liq_weir, liq_color)
            draw_waterfall(ax, x_weir, y + H_weir + H_liq_weir, direction=1, fall_height=target_fall_height, color=liq_color, h_b=h_b)
            draw_gas_arrows(ax, x_left_wall + 0.2, x_weir - 0.2, y)

        else:
            # 偶数板：降液管在左侧
            x_weir = -R + W_d
            
            # 1. 堰板 (垂直)
            ax.plot([x_weir, x_weir], [y, y + H_weir], 'k-', lw=2, zorder=3) 
            # 2. 塔板 (水平)
            ax.plot([x_weir, R], [y, y], 'k-', lw=1.5, zorder=3)             
            
            # 3. 降液管侧壁 (竖直板向下延伸到 h_b)
            ax.plot([-R, -R], [y, y_droptube_bottom], 'k-', lw=1, zorder=3)
            ax.plot([x_weir, x_weir], [y + H_weir, y_droptube_bottom], 'k-', lw=1, zorder=3)

            # 5. 绘制降液管液柱 (底部边界即为 h_b)
            ax.add_patch(patches.Rectangle((-R, y_droptube_bottom), W_d, y_droptube_level - y_droptube_bottom, facecolor=liq_color, alpha=0.9, zorder=3, edgecolor='none'))

            # 6. 液层和液流
            draw_gradient_liquid(ax, x_weir - 0.0, R, y, H_weir + H_liq_weir, H_weir + H_liq_inlet, liq_color)
            draw_waterfall(ax, x_weir, y + H_weir + H_liq_weir, direction=-1, fall_height=target_fall_height, color=liq_color, h_b=h_b)
            draw_gas_arrows(ax, x_weir + 0.2, x_right_wall - 0.2, y)


    # --- C & D. 塔底储液和进出口标注 ---
    x_bottom = np.linspace(-R, R, 200)
    y_bottom_arc = -Head_H * np.sqrt(1 - (x_bottom/R)**2)
    sump_level_y = 1.5 * Plate_Spacing * 0.4 
    y_liquid_top = np.full_like(x_bottom, sump_level_y)

    ax.fill_between(x_bottom, y_bottom_arc, y_liquid_top, color='#fdbf6f', alpha=0.6, zorder=2)
    ax.text(0, sump_level_y * 0.5, '塔底储液', ha='center', fontsize=30, color='brown', zorder=4)

    # 顶部向上箭头
    ax.arrow(0, Z + Head_H, 0, 1.0, head_width=0.25, head_length=0.4, fc='black', ec='black', lw=2, length_includes_head=True, zorder=6)
    ax.text(0.3, Z + Head_H + 0.5, '塔顶气相', ha='left', va='center', fontsize=36, color='black')

    # 回流 (L) (固定在左侧) 
    y_ref = Z - Plate_Spacing
    ax.annotate('回流 (L)', xy=(-R, y_ref), xytext=(-R - 1.5, y_ref),
                arrowprops=dict(facecolor='blue', width=3, headwidth=10), 
                va='center', ha='right', color='blue', zorder=5,
                fontsize=36) 

    # 原料 (F) - 动态修正水平位置 (根据 N_rect 奇偶性)
    y_feed = Z - Plate_Spacing * (1.5 + (N_rect - 1) + 0.5)
    
    if N_rect % 2 == 0: 
        F_x, F_text_x, F_ha = -R, -R - 1.5, 'right'
    else: 
        F_x, F_text_x, F_ha = R, R + 1.5, 'left'
        
    ax.annotate('原料 (F)', xy=(F_x, y_feed), xytext=(F_text_x, y_feed),
                arrowprops=dict(facecolor='green', width=3, headwidth=10), 
                va='center', ha=F_ha, color='green', zorder=5,
                fontsize=36) 

    # 气体 (V) - 动态修正水平位置 (根据 N_total 奇偶性)
    y_gas = Z - Plate_Spacing * (1.5 + N_total - 1) - Plate_Spacing * 0.5
    if y_gas < sump_level_y: 
        y_gas = sump_level_y + 0.5 * Plate_Spacing
        
    if N_total % 2 == 0: 
        V_x, V_text_x, V_ha = R, R + 1.5, 'left'
    else: 
        V_x, V_text_x, V_ha = -R, -R - 1.5, 'right'
        
    ax.annotate('气体 (V)', xy=(V_x, y_gas), xytext=(V_text_x, y_gas),
                arrowprops=dict(facecolor='red', width=3, headwidth=10), 
                va='center', ha=V_ha, color='red', zorder=5,
                fontsize=36) 

    # 底部向下箭头 (塔底液相)
    ax.arrow(0, -Head_H, 0, -1.0, head_width=0.25, head_length=0.4, fc='black', ec='black', lw=2, length_includes_head=True, zorder=6)
    ax.text(-0.3, -Head_H - 0.5, '塔底液相', ha='right', va='center', fontsize=36, color='black')

    # --- F. 参数标注 (新增 Hd 和 h_b) ---
    text_x_start = R + 0.8
    y_start = Z
    line_spacing = 0.35 
    
    param_display_data = [
        ("D", "塔内径 D", f"{D:.3f} m"),
        ("Z", "塔高 Z", f"{Z:.2f} m"),
        ("N_rect", "精馏段板数 NP精", f"{N_rect} 块"),
        ("N_strip", "提馏段板数 NP提", f"{N_strip} 块"),
        ("W_d", "降液管宽度 Wd", f"{W_d:.3f} m"),
        ("H_weir", "堰板高度 Hw堰高", f"{H_weir:.3f} m"),
        ("H_liq_weir", "堰上液层高度 How", f"{H_liq_weir:.3f} m"),
        ("H_d", "降液管液高 Hd", f"{H_d:.5f} m"),        
        ("h_b", "降液管底隙 h0", f"{h_b:.4f} m")         
    ]
    
    y_current = y_start
    for _, label, value in param_display_data:
        y_current -= line_spacing * 1.5 
        ax.text(text_x_start, y_current, f"{label}: {value}", 
                fontsize=30, ha='left', va='center', color='darkslategray')

    # --- G. 视图设置 ---
    ax.set_aspect('equal')
    ax.set_xlim(-R - 2.0 - 5.0, R + 6) 
    ax.set_ylim(-Head_H - 1.5, Z + Head_H + 2.0)
    ax.axis('off')
    
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    return fig

# ==========================================
# 应用程序类 (重构为 StandardApp 结构)
# ==========================================

class StandardApp:
    """
    板式塔结构简图应用程序
    (基于 StandardApp 模板重构)
    """
    def __init__(self, root):
        self.root = root
        self.root.title("板式塔结构简图") 
        
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
        
        # 记录当前模式
        self.current_mode_str = self.config.get("current_mode", "standard")
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
        """创建具体的输入控件"""
        lbl_title = ttk.Label(parent, text="参数设置", font=self.font_title, anchor="center")
        lbl_title.pack(fill=tk.X, pady=(0, 20))
        
        # === 动态参数区域 ===
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

        btn_reset = tk.Button(btn_frame, text="重置为示例参数", command=self.reset_params,
                            font=self.font_base, relief="raised", fg="red")
        btn_reset.pack(fill=tk.X, pady=5)
        
        lbl_info = ttk.Label(parent, text="说明：\n1. 输入参数后点击生成图表。\n2. 中间黑色分割线可以左右拖动调整宽度。", 
                           foreground="gray", justify=tk.LEFT, wraplength=250)
        lbl_info.pack(fill=tk.X, pady=20)

    def refresh_dynamic_inputs(self):
        """刷新动态输入区域 (重建控件)"""
        # 清空旧控件
        for widget in self.dynamic_input_frame.winfo_children():
            widget.destroy()
        
        self.inputs = {}
        
        current_mode = self.mode_var.get()
        params = self.config.get(current_mode, {})

        # 参数组
        group1 = ttk.LabelFrame(self.dynamic_input_frame, text="塔体结构参数", padding=10)
        group1.pack(fill=tk.X, pady=5)
        
        self.add_input_row(group1, "塔内径 D (m):", "D", params)
        self.add_input_row(group1, "塔高 Z (m):", "Z", params)
        self.add_input_row(group1, "精馏段板数 NP精:", "N_rect", params)
        self.add_input_row(group1, "提馏段板数 NP提:", "N_strip", params)
        self.add_input_row(group1, "降液管宽度 Wd (m):", "W_d", params)
        self.add_input_row(group1, "堰板高度 Hw堰高 (m):", "H_weir", params)
        self.add_input_row(group1, "堰上液层高度 How (m):", "H_liq_weir", params)
        self.add_input_row(group1, "降液管清液液高 Hd (m):", "H_d", params)
        self.add_input_row(group1, "降液管底隙 h0 (m):", "h_b", params)

    def add_input_row(self, parent, label_text, key, params_dict):
        """辅助函数：添加一行输入框"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        lbl = ttk.Label(frame, text=label_text, width=20, anchor="w", font=self.font_base)
        lbl.pack(side=tk.LEFT)
        
        entry = ttk.Entry(frame, font=self.font_base)
        entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        
        val = params_dict.get(key, "")
        entry.insert(0, str(val))
        
        self.inputs[key] = entry

    def on_mode_change(self):
        """切换模式时的回调 (当前仅一种模式，预留接口)"""
        new_mode = self.mode_var.get()
        if new_mode == self.current_mode_str:
            return

        self.save_current_params_to_memory()
        self.current_mode_str = new_mode
        self.config["current_mode"] = new_mode
        self.refresh_dynamic_inputs()

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
        self.ax.axis('off') 
        
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
        """核心绘图/计算逻辑"""
        # 绘图前先保存当前参数到 config 对象
        self.save_current_params_to_memory()
        # 然后保存到文件
        self.save_config()
        
        # 获取当前模式的参数
        mode = self.mode_var.get()
        params = self.config.get(mode, {})
        
        try:
            # 读取并转换参数
            plot_params = {
                "D": float(params.get("D", 0)),
                "Z": float(params.get("Z", 0)),
                "N_rect": int(params.get("N_rect", 0)),
                "N_strip": int(params.get("N_strip", 0)),
                "W_d": float(params.get("W_d", 0)),
                "H_weir": float(params.get("H_weir", 0)),
                "H_liq_weir": float(params.get("H_liq_weir", 0)),
                "H_d": float(params.get("H_d", 0)),
                "h_b": float(params.get("h_b", 0))
            }

            if plot_params["N_rect"] < 1 or plot_params["N_strip"] < 1:
                 raise ValueError("板数 NP精/NP提 必须大于等于 1。")
            if plot_params["W_d"] >= plot_params["D"] / 2:
                raise ValueError("降液管宽度 Wd 不能大于或等于塔半径 D/2。")

        except ValueError as e:
            messagebox.showerror("参数错误", f"请检查输入的参数值是否正确。\n错误信息: {e}")
            return

        # 创建新图 (使用 create_tower_plot 返回的 Figure)
        temp_fig = create_tower_plot(**plot_params, figsize=(IMG_WIDTH/IMG_DPI, IMG_HEIGHT/IMG_DPI), dpi=IMG_DPI)
        
        # 渲染并显示
        self.render_and_show(temp_fig)
        
        # --- 校验 h_b > H_weir，并弹窗提示 ---
        if plot_params["h_b"] > plot_params["H_weir"]:
            messagebox.showwarning("参数建议", f"注意：降液管底隙 h_b/h0 ({plot_params['h_b']:.4f} m) 通常应小于堰板高度 Hw堰高 ({plot_params['H_weir']:.4f} m)，请检查参数是否符合设计要求。")

    def load_config(self):
        """加载配置：优先读取 config.json，其次 default_config.json，最后硬编码"""
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
        """保存配置到 config.json"""
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
            current_mode = self.config.get("current_mode", "standard")
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
            initialfile="板式塔结构简图.png"
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
