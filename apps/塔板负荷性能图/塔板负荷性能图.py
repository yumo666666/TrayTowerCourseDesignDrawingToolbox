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
from scipy.optimize import fsolve

# --- 全局配置 ---
# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 配置文件路径
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
DEFAULT_CONFIG_FILE = os.path.join(BASE_DIR, 'default_config.json')

# 生成图片的像素配置
IMG_WIDTH = 5760
IMG_HEIGHT = 5760
IMG_DPI = 300 # 保持 100 方便计算

# 代码中的硬编码默认值
HARDCODED_DEFAULTS = {
    "current_mode": "浮阀塔",
    "浮阀塔": {
        "mist_carry_FL_A": "-51.820977",
        "mist_carry_FL_B": "4.484449735",
        "Vs_min_FL": "1.06300244",
        "flood_C1_FL": "31.9418866",
        "flood_C2_FL": "-11224.46846",
        "flood_C3_FL": "-109.2073926",
        "Ls_max_FL": "0.0099495",
        "Ls_min_FL": "0.00081888",
        "op_Vs_FL": "2.154",
        "op_Ls_FL": "0.00466"
    },
    "筛板塔": {
        "mist_carry_SL_C": "-10.07",
        "mist_carry_SL_D": "1.29",
        "weeping_C1_SL": "3.025",
        "weeping_C2_SL": "0.00961",
        "weeping_C3_SL": "0.114",
        "flood_C1_SL": "1.37",
        "flood_C2_SL": "-3176",
        "flood_C3_SL": "-13.16",
        "Ls_max_SL": "0.00567",
        "Ls_min_SL": "0.00056",
        "op_Vs_SL": "0.621",
        "op_Ls_SL": "0.0017"
    }
}

# --- 字体设置 ---
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Heiti TC', 'KaiTi']
    plt.rcParams['axes.unicode_minus'] = False
    CHINESE_FONT = 'SimHei'
except:
    CHINESE_FONT = 'Arial'

class TowerOperatingApp:
    """
    塔板负荷性能图绘制应用
    结构参考 StandardApp
    """
    def __init__(self, root):
        self.root = root
        self.root.title("塔板负荷性能图")
        
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
        self.current_mode_str = self.config.get("current_mode", "浮阀塔")
        self.mode_var = tk.StringVar(value=self.current_mode_str)

        # === 字体初始化 ===
        self.base_font_size = 12
        self.font_base = tkfont.Font(family=CHINESE_FONT, size=self.base_font_size)
        self.font_bold = tkfont.Font(family=CHINESE_FONT, size=self.base_font_size, weight="bold")
        self.font_title = tkfont.Font(family=CHINESE_FONT, size=int(self.base_font_size*1.5), weight="bold")
        
        self.root.option_add('*Menu.font', f'{CHINESE_FONT} 12')

        # === UI 布局 ===
        self.setup_ui()
        
        # === 绑定事件 ===
        self.root.bind("<Configure>", self.on_window_resize)
        
        # === 初始化状态 ===
        self.generated_fig = None

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
        
        # === 模式切换 ===
        mode_frame = ttk.LabelFrame(parent, text="塔型选择", padding=10)
        mode_frame.pack(fill=tk.X, pady=5)
        
        rb_a = tk.Radiobutton(mode_frame, text="浮阀塔", variable=self.mode_var, 
                              value="浮阀塔", command=self.on_mode_change, font=self.font_bold)
        rb_a.pack(side=tk.LEFT, padx=10, expand=True)
        
        rb_b = tk.Radiobutton(mode_frame, text="筛板塔", variable=self.mode_var, 
                              value="筛板塔", command=self.on_mode_change, font=self.font_bold)
        rb_b.pack(side=tk.LEFT, padx=10, expand=True)

        # === 动态参数区域 ===
        self.dynamic_input_frame = ttk.Frame(parent)
        self.dynamic_input_frame.pack(fill=tk.X)
        
        self.refresh_dynamic_inputs()

        # === 按钮区 ===
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=20)

        btn_draw = tk.Button(btn_frame, text="生成图表", command=self.plot_graph,
                           bg="#4CAF50", fg="white", font=self.font_bold, relief="raised", height=2)
        btn_draw.pack(fill=tk.X, pady=5)

        btn_reset = tk.Button(btn_frame, text="重置参数", command=self.reset_params,
                            font=self.font_base, relief="raised", fg="red")
        btn_reset.pack(fill=tk.X, pady=5)
        
        # === 结果显示区 ===
        lbl_result = ttk.Label(parent, text="详细计算数据:", font=self.font_bold)
        lbl_result.pack(fill=tk.X, pady=(10, 5))
        
        self.coord_text = tk.Text(parent, height=10, font=self.font_base)
        self.coord_text.pack(fill=tk.X, pady=(0, 20))

    def add_input_row(self, parent, label_text, key, params_dict, entry_width=10):
        """辅助函数：添加一行输入框"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        lbl = ttk.Label(frame, text=label_text, width=15, anchor="w", font=self.font_base)
        lbl.pack(side=tk.LEFT)
        
        entry = ttk.Entry(frame, font=self.font_base, width=entry_width)
        entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        
        val = params_dict.get(key, "")
        entry.insert(0, str(val))
        
        self.inputs[key] = entry

    def refresh_dynamic_inputs(self):
        """刷新动态输入区域"""
        # 清空旧控件
        for widget in self.dynamic_input_frame.winfo_children():
            widget.destroy()
        
        self.inputs = {}
        
        current_mode = self.mode_var.get()
        params = self.config.get(current_mode, {})

        # 根据模式创建不同的输入组
        if current_mode == "浮阀塔":
            self.create_inputs_FL(self.dynamic_input_frame, params)
        else:
            self.create_inputs_SL(self.dynamic_input_frame, params)

    def create_inputs_FL(self, parent, params):
        # 2a. 雾沫线
        group = ttk.LabelFrame(parent, text="2. 雾沫线 (Vs = C1×Ls + C2)", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "C1:", "mist_carry_FL_A", params)
        self.add_input_row(group, "C2:", "mist_carry_FL_B", params)
        
        # 3a. 液泛线
        group = ttk.LabelFrame(parent, text="3. 液泛线 (Vs² = C1 + C2·Ls² + C3·Ls⅔)", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "C1:", "flood_C1_FL", params)
        self.add_input_row(group, "C2:", "flood_C2_FL", params)
        self.add_input_row(group, "C3:", "flood_C3_FL", params)

        # 4a. 液相上限
        group = ttk.LabelFrame(parent, text="4. 液相上限", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "Ls,max:", "Ls_max_FL", params)

        # 5a. 漏液线
        group = ttk.LabelFrame(parent, text="5. 漏液线 (Vs,min = C)", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "Vs,min:", "Vs_min_FL", params)

        # 6a. 液相下限
        group = ttk.LabelFrame(parent, text="6. 液相下限", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "Ls,min:", "Ls_min_FL", params)

        # 7a. 操作点
        group = ttk.LabelFrame(parent, text="7. 操作点", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "Vs:", "op_Vs_FL", params)
        self.add_input_row(group, "Ls:", "op_Ls_FL", params)

    def create_inputs_SL(self, parent, params):
        # 2b. 雾沫线
        group = ttk.LabelFrame(parent, text="2. 雾沫线 (Vs = C1·Ls⅔ + C2)", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "C1:", "mist_carry_SL_C", params)
        self.add_input_row(group, "C2:", "mist_carry_SL_D", params)

        # 3b. 液泛线
        group = ttk.LabelFrame(parent, text="3. 液泛线 (Vs² = C1 + C2·Ls² + C3·Ls⅔)", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "C1:", "flood_C1_SL", params)
        self.add_input_row(group, "C2:", "flood_C2_SL", params)
        self.add_input_row(group, "C3:", "flood_C3_SL", params)

        # 4b. 液相上限
        group = ttk.LabelFrame(parent, text="4. 液相上限", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "Ls,max:", "Ls_max_SL", params)

        # 5b. 漏液线
        group = ttk.LabelFrame(parent, text="5. 漏液线 (Vs = C1·√(C2 + C3·Ls⅔))", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "C1:", "weeping_C1_SL", params)
        self.add_input_row(group, "C2:", "weeping_C2_SL", params)
        self.add_input_row(group, "C3:", "weeping_C3_SL", params)

        # 6b. 液相下限
        group = ttk.LabelFrame(parent, text="6. 液相下限", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "Ls,min:", "Ls_min_SL", params)

        # 7b. 操作点
        group = ttk.LabelFrame(parent, text="7. 操作点", padding=10)
        group.pack(fill=tk.X, pady=5)
        self.add_input_row(group, "Vs:", "op_Vs_SL", params)
        self.add_input_row(group, "Ls:", "op_Ls_SL", params)

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

    def save_current_params_to_memory(self):
        """将当前 UI 的值保存到 self.config"""
        mode = self.current_mode_str
        if mode not in self.config:
            self.config[mode] = {}
            
        target_dict = self.config[mode]
        for key, widget in self.inputs.items():
            target_dict[key] = widget.get()

    def create_plot_area(self):
        """创建右侧绘图区"""
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.axis('off')
        
        self.ax.text(0.5, 0.5, "请点击左侧“生成图表”按钮", 
                    ha='center', va='center', fontsize=16, fontproperties=CHINESE_FONT)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.popup_menu = Menu(self.root, tearoff=0)
        self.popup_menu.add_command(label="另存为图片...", command=self.save_plot_as_image)
        self.canvas_widget.bind("<Button-3>", self.show_popup_menu)

    def render_and_show(self, temp_fig):
        """渲染并显示"""
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

    def get_val(self, params, key):
        try:
            return float(params.get(key, 0))
        except ValueError:
            return 0.0

    def plot_graph(self):
        """核心绘图逻辑"""
        self.save_current_params_to_memory()
        self.save_config()
        
        mode = self.mode_var.get()
        params = self.config.get(mode, {})
        
        suffix = "_FL" if mode == "浮阀塔" else "_SL"
        
        # 获取参数
        C1 = self.get_val(params, f"flood_C1{suffix}")
        C2 = self.get_val(params, f"flood_C2{suffix}")
        C3 = self.get_val(params, f"flood_C3{suffix}")
        Ls_max = self.get_val(params, f"Ls_max{suffix}")
        Ls_min = self.get_val(params, f"Ls_min{suffix}")
        Op_Vs = self.get_val(params, f"op_Vs{suffix}")
        Op_Ls = self.get_val(params, f"op_Ls{suffix}")

        # 创建高清绘图对象
        temp_fig = Figure(figsize=(IMG_WIDTH/IMG_DPI, IMG_HEIGHT/IMG_DPI), dpi=IMG_DPI)
        ax_temp = temp_fig.add_subplot(111)

        if Ls_max <= 0 or Op_Ls <= 0 or Ls_min >= Ls_max: 
             ax_temp.text(0.5, 0.5, "参数无效，无法绘图", 
                          transform=ax_temp.transAxes, ha='center', va='center', fontsize=36, fontproperties=CHINESE_FONT)
             self.render_and_show(temp_fig)
             return

        x_min_plot = Ls_min * 1000 
        x_max_plot = Ls_max * 1000

        # --- 定义函数 ---
        def flood_func(ls): 
            ls = np.maximum(1e-9, ls)
            val = C1 + C2*(ls**2) + C3*(ls**(2/3.0))
            return np.sqrt(np.maximum(0, val))

        if mode == "浮阀塔":
            A = self.get_val(params, "mist_carry_FL_A")
            B = self.get_val(params, "mist_carry_FL_B")
            Vs_min_const = self.get_val(params, "Vs_min_FL")
            Vs_min_label = "漏液线"
            
            def mist_func(ls): return A * ls + B
            def weeping_func(ls): return np.full_like(ls, Vs_min_const) 
            
        elif mode == "筛板塔":
            C_sl = self.get_val(params, "mist_carry_SL_C")
            D_sl = self.get_val(params, "mist_carry_SL_D")
            W_C1 = self.get_val(params, "weeping_C1_SL")
            W_C2 = self.get_val(params, "weeping_C2_SL")
            W_C3 = self.get_val(params, "weeping_C3_SL")
            Vs_min_label = "漏液线"
            
            def mist_func(ls): 
                ls = np.maximum(1e-9, ls)
                return C_sl * (ls**(2/3.0)) + D_sl
                
            def weeping_func(ls): 
                ls = np.maximum(1e-9, ls)
                val = W_C2 + W_C3 * (ls**(2/3.0))
                return W_C1 * np.sqrt(np.maximum(0, val))

        # --- 计算交点 ---
        k = Op_Vs / Op_Ls if Op_Ls > 1e-9 else 0.0
        all_intersections = [] 
        initial_guess = Op_Ls
        epsilon = 1e-6 

        def solve_and_collect(target_func, name):
            name_key = "$V_{s,min}$" if name == "Weeping" and mode == "浮阀塔" else name
            try:
                L_i_list = fsolve(lambda ls: target_func(ls) - k * ls, initial_guess, full_output=True)
                L_i = L_i_list[0][0] 
                V_i = k * L_i
                
                if L_i > epsilon and V_i > epsilon:
                    if not (Ls_min - epsilon <= L_i <= Ls_max + epsilon): return
                        
                    V_weep_at_L = weeping_func(L_i)
                    V_mist_at_L = mist_func(L_i)
                    V_flood_at_L = flood_func(L_i)
                    
                    is_valid = False
                    if name in ["Flood", "Mist"]:
                        if V_i >= V_weep_at_L - epsilon: is_valid = True
                    elif name in ["Weeping", "$V_{s,min}$"]:
                        if V_i <= V_mist_at_L + epsilon and V_i <= V_flood_at_L + epsilon: is_valid = True
                            
                    if is_valid:
                        all_intersections.append({'Ls': L_i, 'Vs': V_i, 'Source': name_key})
            except: pass

        solve_and_collect(mist_func, "Mist")
        solve_and_collect(flood_func, "Flood")
        solve_and_collect(weeping_func, "Weeping") 

        # Ls_max 交点
        L_i_max = Ls_max
        V_i_max = k * L_i_max
        if V_i_max > epsilon and L_i_max >= Ls_min - epsilon:
             V_weep_at_Lmax = weeping_func(L_i_max)
             V_mist_at_Lmax = mist_func(L_i_max)
             V_flood_at_Lmax = flood_func(L_i_max)
             if V_weep_at_Lmax - epsilon <= V_i_max <= V_mist_at_Lmax + epsilon and V_i_max <= V_flood_at_Lmax + epsilon:
                all_intersections.append({'Ls': L_i_max, 'Vs': V_i_max, 'Source': "Ls_max"})

        # Ls_min 交点
        L_i_min = Ls_min
        V_i_min = k * L_i_min
        if V_i_min > epsilon and L_i_min <= Ls_max + epsilon:
             V_weep_at_Lmin = weeping_func(L_i_min)
             V_mist_at_Lmin = mist_func(L_i_min)
             V_flood_at_Lmin = flood_func(L_i_min)
             if V_weep_at_Lmin - epsilon <= V_i_min <= V_mist_at_Lmin + epsilon and V_i_min <= V_flood_at_Lmin + epsilon:
                all_intersections.append({'Ls': L_i_min, 'Vs': V_i_min, 'Source': "Ls_min"})

        # --- 确定操作弹性 ---
        all_intersections.sort(key=lambda x: x['Vs'])
        valid_points = []
        for pt in all_intersections:
            L, V = pt['Ls'], pt['Vs']
            V_weep = weeping_func(L)
            V_upper = min(mist_func(L), flood_func(L))
            if V_weep - epsilon <= V <= V_upper + epsilon:
                if Ls_min - epsilon <= L <= Ls_max + epsilon:
                   valid_points.append(pt)

        Vs_min_val, Vs_max_val = 0.0, 0.0
        Ls_max_intersect, Ls_min_intersect = 0.0, 0.0
        
        if len(valid_points) >= 2:
            valid_points.sort(key=lambda x: x['Vs'])
            min_pt, max_pt = valid_points[0], valid_points[-1]
            Vs_min_val, Ls_min_intersect = min_pt['Vs'], min_pt['Ls']
            Vs_max_val, Ls_max_intersect = max_pt['Vs'], max_pt['Ls']
        
        E_op = Vs_max_val / Vs_min_val if Vs_min_val > 0 else 0.0

        # --- 绘图 ---
        LINE_WIDTH_THICK = 3.0
        ls_plot_range = np.linspace(Ls_min, Ls_max, 200)
        ls_plot_range_scaled = ls_plot_range * 1000
        
        vs_mist_curve = mist_func(ls_plot_range)
        vs_weep_curve = weeping_func(ls_plot_range)
        vs_flood_curve = flood_func(ls_plot_range)
        
        epsilon_plot = 1e-9
        vs_weep_plot = np.where(vs_weep_curve > epsilon_plot, vs_weep_curve, np.nan)
        condition_mist = (vs_mist_curve > vs_weep_curve + epsilon) & (vs_mist_curve > epsilon_plot)
        vs_mist_plot = np.where(condition_mist, vs_mist_curve, np.nan)
        condition_flood = (vs_flood_curve > vs_weep_curve + epsilon) & (vs_flood_curve > epsilon_plot)
        vs_flood_plot = np.where(condition_flood, vs_flood_curve, np.nan) 

        # 设置坐标轴
        Ls_plot_max = max(Ls_max, Ls_max_intersect) 
        Vs_max_bounds = [np.nanmax(vs_mist_plot), np.nanmax(vs_flood_plot), Vs_max_val, Op_Vs]
        Vs_data_max = max([v for v in Vs_max_bounds if not np.isnan(v)]) if Vs_max_bounds else 5.0
        
        ax_temp.set_xlim(0, (Ls_plot_max * 1000) * 1.15)
        ax_temp.set_ylim(0, Vs_data_max * 1.15)

        # 阴影
        vs_upper_bound = np.minimum(vs_mist_plot, vs_flood_plot)
        ax_temp.fill_between(ls_plot_range_scaled, vs_weep_plot, vs_upper_bound, 
                             where=(vs_weep_plot > epsilon_plot), color='#D3D3D3', alpha=0.5, label='操作区域')
        
        # 边界线
        ax_temp.plot([x_min_plot, x_min_plot], ax_temp.get_ylim(), color='#FFD700', lw=LINE_WIDTH_THICK, label="$L_{s,min}$")
        ax_temp.plot([x_max_plot, x_max_plot], ax_temp.get_ylim(), color='#008000', lw=LINE_WIDTH_THICK, label="$L_{s,max}$")
        
        # 曲线
        ax_temp.plot(ls_plot_range_scaled, vs_weep_plot, color='#800080', lw=LINE_WIDTH_THICK, label=Vs_min_label)
        ax_temp.plot(ls_plot_range_scaled, vs_mist_plot, color='#E60000', lw=LINE_WIDTH_THICK, label="雾沫线")
        ax_temp.plot(ls_plot_range_scaled, vs_flood_plot, color='#0000FF', lw=LINE_WIDTH_THICK, label="液泛线")

        # 操作点 P
        ax_temp.plot(Op_Ls*1000, Op_Vs, 'ko', markersize=8, zorder=10)
        ax_temp.text(Op_Ls*1000-0.05, Op_Vs + 0.1, "P", fontsize=35, fontweight='bold')

        # 操作线
        if Op_Ls > 0 and Vs_max_val > 0:
            ax_temp.plot([0, Ls_max_intersect*1000], [0, Vs_max_val], 'k-', lw=2.5, zorder=6)
            ax_temp.plot([0, Ls_max_intersect*1000], [Vs_max_val, Vs_max_val], 'k--', lw=2.0, zorder=5)
            ax_temp.plot(Ls_max_intersect*1000, Vs_max_val, 'ro', markersize=6, zorder=10)
            
            if Ls_min_intersect > 0 and Vs_min_val > 0:
                ax_temp.plot([0, Ls_min_intersect*1000], [Vs_min_val, Vs_min_val], 'k--', lw=2.0, zorder=5)
                ax_temp.plot(Ls_min_intersect*1000, Vs_min_val, 'mo', markersize=6, zorder=10)

        # 标题
        title_sub = (f"$V_{{s,max}} = {Vs_max_val:.4f} m^3/s$  \n"
                     f"$V_{{s,min}} = {Vs_min_val:.4f} m^3/s$ \n"
                     f"操作弹性 $E_{{op}} = {E_op:.2f}$")
        ax_temp.set_title(f" \n{title_sub}", fontproperties=CHINESE_FONT, fontsize=36, pad=20)
        ax_temp.set_xlabel("$L_s \\times 10^3 \\, (m^3/s)$", fontsize=32, labelpad=10)
        ax_temp.set_ylabel("$V_s \\, (m^3/s)$", fontsize=32, labelpad=10)
        ax_temp.tick_params(axis='both', which='major', labelsize=24)
        ax_temp.legend(prop={'size': 24}, loc='upper right', framealpha=0.9)
        ax_temp.grid(True, linestyle=':', alpha=0.4)

        self.render_and_show(temp_fig)

        # 更新结果文本
        res_str = f"塔型: {mode}\n"
        res_str += f"Vs_max = {Vs_max_val:.6f}\n"
        res_str += f"Vs_min = {Vs_min_val:.6f} \n"
        res_str += f"操作弹性 E_op = {E_op:.4f}\n"
        res_str += f"操作点 P: ({Op_Ls*1000:.4f}, {Op_Vs:.4f})\n"
        
        res_str += "\n所有有效交点:\n"
        for i, pt in enumerate(valid_points):
            res_str += f"V({i+1}): Ls={pt['Ls']*1000:.4f}, Vs={pt['Vs']:.4f}, Source={pt['Source']}\n"
            
        self.coord_text.delete(1.0, tk.END)
        self.coord_text.insert(tk.END, res_str)

    def load_config(self):
        """加载配置"""
        self.config = HARDCODED_DEFAULTS.copy()
        
        # 1. 尝试加载默认配置
        if os.path.exists(DEFAULT_CONFIG_FILE):
            try:
                with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    defaults = json.load(f)
                    self.merge_config(self.config, defaults)
            except Exception as e:
                print(f"读取默认配置失败: {e}")

        # 2. 尝试加载用户配置
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.merge_config(self.config, saved)
            except Exception as e:
                print(f"读取用户配置失败: {e}")

    def merge_config(self, base, new_data):
        """递归合并配置"""
        for k, v in new_data.items():
            if isinstance(v, dict) and k in base:
                self.merge_config(base[k], v)
            else:
                base[k] = v

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
                        self.merge_config(self.config, defaults)
                except: pass
            
            current_mode = self.config.get("current_mode", "浮阀塔")
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
            initialfile="塔板负荷性能图.png"
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
        pass

    def on_closing(self):
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.save_current_params_to_memory()
            self.save_config()
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = TowerOperatingApp(root)
    root.mainloop()
