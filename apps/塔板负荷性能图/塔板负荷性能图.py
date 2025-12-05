import tkinter as tk
from tkinter import ttk, filedialog, Menu, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import sys
import json
import os
from functools import partial
from scipy.optimize import fsolve 

# === 配置文件路径 ===
PARAMS_FILE = "params.json"
EXAMPLE_PARAMS_FILE = "example.json"

# === 字体和配置 ===
try:
    # 尝试设置中文字体，确保中文显示
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Heiti TC', 'KaiTi']
    plt.rcParams['axes.unicode_minus'] = False
    CHINESE_FONT = 'SimHei'
except:
    # 如果找不到中文字体，使用 Arial
    CHINESE_FONT = 'Arial'

# === 默认参数和键定义 (已修正：通用参数按塔型独立命名) ===

# 浮阀塔参数 (FL - 全部参数)
DEFAULT_PARAMS_FL = {
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
}
FL_KEYS = list(DEFAULT_PARAMS_FL.keys())

# 筛板塔参数 (SL - 全部参数)
DEFAULT_PARAMS_SL = {
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
SL_KEYS = list(DEFAULT_PARAMS_SL.keys())

# 组合所有默认参数 (用于程序内部初始化，扁平结构)
DEFAULT_PARAMS = {}
DEFAULT_PARAMS.update(DEFAULT_PARAMS_FL) 
DEFAULT_PARAMS.update(DEFAULT_PARAMS_SL)
DEFAULT_PARAMS["plate_type"] = "浮阀塔" 

# 定义所有输入框的键的集合
ALL_INPUT_KEYS = set(FL_KEYS) | set(SL_KEYS)

# 定义输入组和分隔符的**正确的视觉顺序**
VISUAL_ORDER_KEYS = [
    "type_selection_group", 
    "mist_sep_1", 
    "mist_FL_group",      
    "mist_SL_group",      
    "mist_sep_2",
    "flood_line_group_FL", 
    "flood_line_group_SL", 
    "flood_sep",
    "Ls_max_group_FL",     
    "Ls_max_group_SL",     
    "Ls_max_sep",
    "Vs_min_FL_group",     
    "weeping_SL_group",    
    "Vs_min_sep",
    "Ls_min_group_FL",     
    "Ls_min_group_SL",     
    "Ls_min_sep",
    "op_point_group_FL",   
    "op_point_group_SL",   
    "op_point_sep"
]

class TowerOperatingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("塔板负荷性能图")
        
        # 设置窗口全屏启动
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-fullscreen', True)
        
        # 1. 加载参数
        self.current_params = self.load_params()
        
        # Increase menu font size globally for this app
        self.root.option_add('*Menu.font', 'Arial 16')
        
        # 绑定窗口关闭事件
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.inputs = {}
        self.input_frames = {} 
        
        # === 布局结构 ===
        # 使用 Grid 布局以保持与图解法一致的比例 (1:3)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        self.left_frame = ttk.Frame(root, padding="20")
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        
        self.right_frame = ttk.Frame(root, padding="10")
        self.right_frame.grid(row=0, column=1, sticky="nsew")

        # 塔型选择变量
        self.plate_type_var = tk.StringVar(value=self.current_params.get("plate_type", "浮阀塔"))
        self.plate_type_var.trace_add("write", self.on_plate_type_change) 

        # **动态输入容器**
        self.input_container = ttk.Frame(self.left_frame)
        
        # 创建输入控件
        self.create_inputs()

        # 确保输入容器在标题和按钮之间
        self.button_frame = ttk.Frame(self.left_frame)
        self.button_frame.pack(fill=tk.X, pady=20)
        
        # 更新按钮样式，使用 tk.Button 以支持自定义背景色
        self.btn_update = tk.Button(self.button_frame, text="开始绘图", command=self.plot_and_save_diagram, 
                                    bg="#4CAF50", fg="white", font=("Arial", 18, "bold"), relief="raised", padx=20, pady=10)
        self.btn_update.pack(fill=tk.X, pady=5)
        
        self.btn_reset = tk.Button(self.button_frame, text="重置为示例参数", command=self.reset_params,
                                   font=("Arial", 18, "bold"), relief="raised", padx=20, pady=10, fg="red")
        self.btn_reset.pack(fill=tk.X, pady=5)

        self.input_container.pack(fill=tk.X, expand=True, before=self.button_frame)
        
        # === 绘图初始化 ===
        self.fig, self.ax = plt.subplots(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 左下角结果文本框
        self.result_label = ttk.Label(self.left_frame, text="详细计算数据:", font=(CHINESE_FONT, 18, "bold"))
        self.result_label.pack(pady=(20, 5), anchor=tk.W)
        self.coord_text = tk.Text(self.left_frame, height=8, width=45, font=(CHINESE_FONT, 14))
        self.coord_text.pack(pady=(0, 20), fill=tk.X)

        # 右键菜单
        self.popup_menu = Menu(self.root, tearoff=0)
        self.popup_menu.add_command(label="另存为图片...", command=self.save_plot_as_image)
        self.canvas_widget.bind("<Button-3>", self.show_popup_menu)

        # 初始刷新
        self.update_input_visibility()
        self.plot_diagram()

    def reset_params(self):
        if messagebox.askyesno("重置", "确定要重置为示例参数吗？"):
            # 1. 从 example.json 加载参数
            try:
                self.current_params = self.load_params_from_file(EXAMPLE_PARAMS_FILE)
            except Exception as e:
                 messagebox.showerror("错误", f"无法加载示例参数: {e}")
                 return

            # 2. 刷新界面
            self.plate_type_var.set(self.current_params.get("plate_type", "浮阀塔"))
            # 刷新输入框
            for key in ALL_INPUT_KEYS:
                if key in self.inputs:
                    self.inputs[key].delete(0, tk.END)
                    self.inputs[key].insert(0, self.current_params.get(key, ""))
            # 3. 保存并绘图
            self.save_current_input_params()
            self.plot_diagram()

    # --- JSON 文件处理 ---
    def load_params_from_file(self, filepath):
        """通用：从指定文件加载参数并展平"""
        flat_params = DEFAULT_PARAMS.copy()
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                    # 从结构化数据中加载
                    current_type = loaded_data.get("plate_type", "浮阀塔")
                    flat_params["plate_type"] = current_type

                    # 加载浮阀塔的全部参数
                    fl_data = loaded_data.get("浮阀塔", {})
                    for key in FL_KEYS:
                        flat_params[key] = fl_data.get(key, DEFAULT_PARAMS_FL.get(key, ""))
                        
                    # 加载筛板塔的全部参数
                    sl_data = loaded_data.get("筛板塔", {})
                    for key in SL_KEYS:
                        flat_params[key] = sl_data.get(key, DEFAULT_PARAMS_SL.get(key, ""))

                    return flat_params
            except Exception:
                pass
        return flat_params

    def load_params(self):
        return self.load_params_from_file(PARAMS_FILE)

    def save_params(self, params_to_save):
        save_data_flat = params_to_save.copy()
        current_type = self.plate_type_var.get()
        
        # 1. 尝试加载现有结构数据作为基础，防止覆盖未修改的塔型参数
        structured_data = {
            "plate_type": current_type,
            "浮阀塔": DEFAULT_PARAMS_FL.copy(), 
            "筛板塔": DEFAULT_PARAMS_SL.copy()
        }
        
        if os.path.exists(PARAMS_FILE):
             try:
                with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    # 载入现有的参数作为基础
                    structured_data["浮阀塔"].update(existing_data.get("浮阀塔", {}))
                    structured_data["筛板塔"].update(existing_data.get("筛板塔", {}))
             except Exception:
                 pass 

        # 2. 从当前扁平数据中分离出浮阀塔和筛板塔的参数
        fl_data_new = {k: save_data_flat[k] for k in FL_KEYS if k in save_data_flat}
        sl_data_new = {k: save_data_flat[k] for k in SL_KEYS if k in save_data_flat}

        # 3. 替换对应的参数集
        structured_data["浮阀塔"].update(fl_data_new)
        structured_data["筛板塔"].update(sl_data_new)

        # 4. 保存
        try:
            with open(PARAMS_FILE, 'w', encoding='utf-8') as f: 
                json.dump(structured_data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    # --- GUI 事件处理 ---
    def on_closing(self):
        if messagebox.askokcancel("退出程序", "确定要关闭并退出程序吗?"):
            self.save_current_input_params() 
            self.root.destroy()
            sys.exit(0)

    def show_popup_menu(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def save_plot_as_image(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")],
            title="保存图片",
            initialfile="塔板负荷性能图.png"
        )
        if file_path:
            try:
                self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("成功", f"图片已保存: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", str(e))

    def save_current_input_params(self):
        params_to_save = {}
        # 收集所有输入框的值，包括当前隐藏的
        for key in ALL_INPUT_KEYS:
            if key in self.inputs:
                params_to_save[key] = self.inputs[key].get()
        self.save_params(params_to_save)
        
    def on_plate_type_change(self, *args):
        # 1. 立即保存旧参数，并将新参数加载到输入框
        self.save_current_input_params()
        self.current_params = self.load_params()
        
        # 2. 用新加载的参数更新所有输入框的内容
        for key in ALL_INPUT_KEYS:
            if key in self.inputs:
                self.inputs[key].delete(0, tk.END)
                # 由于 load_params 已经将所有参数以扁平结构加载，这里可以直接使用
                self.inputs[key].insert(0, self.current_params.get(key, "")) 
        
        # 3. 更新可见性并绘图
        self.update_input_visibility()
        self.plot_diagram()

    def update_input_visibility(self):
        """根据塔型切换显示，使用 VISUAL_ORDER_KEYS 排序"""
        current_type = self.plate_type_var.get()
        
        # 1. 隐藏所有
        for frame in self.input_container.winfo_children():
            frame.pack_forget()

        # 2. 按顺序显示
        for key in VISUAL_ORDER_KEYS:
            frame = self.input_frames.get(key)
            if frame is None: continue

            should_pack = False
            
            # --- 归类 Key ---
            common_keys = [
                "type_selection_group", "mist_sep_1", "mist_sep_2", 
                "flood_sep", "Ls_max_sep", "Vs_min_sep", "Ls_min_sep", "op_point_sep"
            ]
            fl_only = [
                "mist_FL_group", "Vs_min_FL_group", 
                "flood_line_group_FL", "Ls_max_group_FL", "Ls_min_group_FL", "op_point_group_FL"
            ]
            sl_only = [
                "mist_SL_group", "weeping_SL_group",
                "flood_line_group_SL", "Ls_max_group_SL", "Ls_min_group_SL", "op_point_group_SL"
            ]

            if key in common_keys:
                should_pack = True
            elif key in fl_only and current_type == "浮阀塔":
                should_pack = True
            elif key in sl_only and current_type == "筛板塔":
                should_pack = True
            
            if should_pack:
                # 分隔符 padding 大一点，组 padding 小一点
                pad_y = 10 if key.endswith("_sep") else 5
                frame.pack(fill=tk.X, pady=pad_y)

    # --- 界面构建 ---
    def create_inputs(self):
        # 样式定义
        style = ttk.Style()
        FONT_ENTRY = (CHINESE_FONT, 18)        
        FONT_TITLE = (CHINESE_FONT, 20, "bold") 
        FONT_BUTTON = (CHINESE_FONT, 18, "bold")
        
        style.configure("Big.TButton", font=FONT_BUTTON)
        style.configure("Custom.TRadiobutton", font=FONT_ENTRY)

        # 顶部固定标题
        title = ttk.Label(self.left_frame, text="参数设置", font=FONT_TITLE)
        title.pack(pady=(0, 20))
        
        # === 辅助函数：创建垂直布局的输入组 ===
        def create_vertical_group(group_key, title_text, create_inputs_func):
            group_frame = ttk.Frame(self.input_container)
            self.input_frames[group_key] = group_frame
            
            # 第一行：标题
            ttk.Label(group_frame, text=title_text, font=FONT_TITLE, foreground="#333333").pack(anchor=tk.W, pady=(0, 5))
            
            # 第二行：输入控件容器
            input_row = ttk.Frame(group_frame)
            input_row.pack(anchor=tk.W, fill=tk.X)
            
            create_inputs_func(input_row)
            return group_frame

        # 辅助：简单的文本 Label
        def add_label(parent, text, font=FONT_ENTRY):
            ttk.Label(parent, text=text, font=font).pack(side=tk.LEFT, padx=2)

        # 辅助：创建 Entry 并存入 self.inputs
        def add_entry(parent, key, width):
            value = self.current_params.get(key, "")
            e = ttk.Entry(parent, width=width, font=FONT_ENTRY)
            e.insert(0, value)
            e.pack(side=tk.LEFT, padx=2)
            self.inputs[key] = e
            return e

        # 辅助：创建分隔符
        def create_separator(key):
            sep_frame = ttk.Frame(self.input_container)
            ttk.Separator(sep_frame, orient='horizontal').pack(fill='x')
            self.input_frames[key] = sep_frame

        # ==================== 1. 塔型选择 ====================
        def setup_type_selection(parent):
            ttk.Radiobutton(parent, text="浮阀塔", variable=self.plate_type_var, value="浮阀塔", 
                            command=self.on_plate_type_change, style="Custom.TRadiobutton").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Radiobutton(parent, text="筛板塔", variable=self.plate_type_var, value="筛板塔", 
                            command=self.on_plate_type_change, style="Custom.TRadiobutton").pack(side=tk.LEFT)

        create_vertical_group("type_selection_group", "1. 塔型选择:", setup_type_selection)
        create_separator("mist_sep_1")

        # ==================== 2. 雾沫线 ====================
        # 2a. 浮阀塔: Vs = A * Ls + B
        def setup_mist_fl(parent):
            add_label(parent, "Vs =") 
            add_entry(parent, "mist_carry_FL_A", 9)
            add_label(parent, "× Ls +")
            add_entry(parent, "mist_carry_FL_B", 9)
        create_vertical_group("mist_FL_group", "2a. 雾沫线:", setup_mist_fl)

        # 2b. 筛板塔: Vs = C * Ls^(2/3) + D
        def setup_mist_sl(parent):
            add_label(parent, "Vs =") 
            add_entry(parent, "mist_carry_SL_C", 9)
            add_label(parent, "× Ls⅔ +")
            add_entry(parent, "mist_carry_SL_D", 9)
        create_vertical_group("mist_SL_group", "2b. 雾沫线:", setup_mist_sl)
        create_separator("mist_sep_2")
        
        # ==================== 3. 液泛线 (独立分组) ====================
        # 浮阀塔: Vs² = C2*Ls² + C3*Ls^(2/3) + C1
        def setup_flood_fl(parent):
            add_label(parent, "Vs² =") 
            add_entry(parent, "flood_C2_FL", 8)
            add_label(parent, "× Ls² +")
            add_entry(parent, "flood_C3_FL", 8)
            add_label(parent, "× Ls⅔ +")
            add_entry(parent, "flood_C1_FL", 8)
        create_vertical_group("flood_line_group_FL", "3a. 液泛线:", setup_flood_fl)
        
        # 筛板塔: Vs² = C2*Ls² + C3*Ls^(2/3) + C1
        def setup_flood_sl(parent):
            add_label(parent, "Vs² =") 
            add_entry(parent, "flood_C2_SL", 8)
            add_label(parent, "× Ls² +")
            add_entry(parent, "flood_C3_SL", 8)
            add_label(parent, "× Ls⅔ +")
            add_entry(parent, "flood_C1_SL", 8)
        create_vertical_group("flood_line_group_SL", "3b. 液泛线:", setup_flood_sl)
        create_separator("flood_sep")

        # ==================== 4. 液相上限 (Ls_max) (独立分组) ====================
        def setup_ls_max_fl(parent):
            add_label(parent, "Ls,max (FL) =")
            add_entry(parent, "Ls_max_FL", 12)
        create_vertical_group("Ls_max_group_FL", "4a. 液相上限", setup_ls_max_fl)

        def setup_ls_max_sl(parent):
            add_label(parent, "Ls,max (SL) =")
            add_entry(parent, "Ls_max_SL", 12)
        create_vertical_group("Ls_max_group_SL", "4b. 液相上限:", setup_ls_max_sl)
        create_separator("Ls_max_sep")

        # ==================== 5. 气相下限 / 漏液线 (已修正：weeping_C* 键名) ====================
        # 5a. 浮阀塔 Vs,min = C
        def setup_vs_min_fl(parent):
            add_label(parent, "Vs,min =")
            add_entry(parent, "Vs_min_FL", 12)
        create_vertical_group("Vs_min_FL_group", "5a. 漏液线:", setup_vs_min_fl)

        # 5b. 筛板塔 (Vs,weep = C1 * sqrt(C2 + C3 * Ls^(2/3)))
        def setup_weeping_sl(parent):
            add_label(parent, "Vs,min =") 
            add_entry(parent, "weeping_C1_SL", 6)
            add_label(parent, "× √(")
            add_entry(parent, "weeping_C2_SL", 8)
            add_label(parent, "+")
            add_entry(parent, "weeping_C3_SL", 8)
            add_label(parent, "× Ls⅔ )")
        create_vertical_group("weeping_SL_group", "5b. 漏液线:", setup_weeping_sl)
        create_separator("Vs_min_sep")

        # ==================== 6. 液相下限 (Ls_min) (独立分组) ====================
        def setup_ls_min_fl(parent):
            add_label(parent, "Ls,min (FL) =")
            add_entry(parent, "Ls_min_FL", 12)
        create_vertical_group("Ls_min_group_FL", "6a. 液相下限:", setup_ls_min_fl)

        def setup_ls_min_sl(parent):
            add_label(parent, "Ls,min (SL) =")
            add_entry(parent, "Ls_min_SL", 12)
        create_vertical_group("Ls_min_group_SL", "6b. 液相下限:", setup_ls_min_sl)
        create_separator("Ls_min_sep")

        # ==================== 7. 操作点 (独立分组) ====================
        def setup_op_point_fl(parent):
            add_label(parent, "Vs=")
            add_entry(parent, "op_Vs_FL", 8)
            add_label(parent, "   Ls=")
            add_entry(parent, "op_Ls_FL", 8)
        create_vertical_group("op_point_group_FL", "7a. 操作点:", setup_op_point_fl)
        
        def setup_op_point_sl(parent):
            add_label(parent, "Vs=")
            add_entry(parent, "op_Vs_SL", 8)
            add_label(parent, "   Ls=")
            add_entry(parent, "op_Ls_SL", 8)
        create_vertical_group("op_point_group_SL", "7b. 操作点:", setup_op_point_sl)
        create_separator("op_point_sep")

    # --- 计算和绘图方法 (已修正：根据塔型获取正确的参数集，并严格限定曲线绘图范围) ---
    def get_val(self, name):
        try:
            return float(self.inputs[name].get())
        except ValueError:
            return 0.0

    def plot_and_save_diagram(self):
        self.plot_diagram()
        self.save_current_input_params()

    def plot_diagram(self):
        current_type = self.plate_type_var.get()
        suffix = "_FL" if current_type == "浮阀塔" else "_SL" # 动态后缀
        
        # --- 获取全部参数（使用动态后缀） ---
        C1 = self.get_val(f"flood_C1{suffix}")
        C2 = self.get_val(f"flood_C2{suffix}")
        C3 = self.get_val(f"flood_C3{suffix}")
        Ls_max = self.get_val(f"Ls_max{suffix}")
        Ls_min = self.get_val(f"Ls_min{suffix}")
        Op_Vs = self.get_val(f"op_Vs{suffix}")
        Op_Ls = self.get_val(f"op_Ls{suffix}")
        
        if Ls_max <= 0 or Op_Ls <= 0 or Ls_min >= Ls_max: 
             self.ax.clear()
             self.ax.text(0.5, 0.5, "参数无效，无法绘图", 
                          transform=self.ax.transAxes, ha='center', va='center', fontsize=24)
             self.canvas.draw()
             return

        # Ls 边界在图表中的显示值 (Ls * 1000)
        x_min_plot = Ls_min * 1000 
        x_max_plot = Ls_max * 1000
        # ============================================

        # --- 1. 定义边界函数 ---
        # 液泛线函数
        def flood_func(ls): 
            ls = np.maximum(1e-9, ls)
            val = C1 + C2*(ls**2) + C3*(ls**(2/3.0))
            return np.sqrt(np.maximum(0, val))

        # 雾沫线和漏液线/Vs,min 函数
        if current_type == "浮阀塔":
            A = self.get_val("mist_carry_FL_A")
            B = self.get_val("mist_carry_FL_B")
            Vs_min_const = self.get_val("Vs_min_FL")
            Vs_min_label = "漏液线"
            
            def mist_func(ls): return A * ls + B
            def weeping_func(ls): return np.full_like(ls, Vs_min_const) 
            
        elif current_type == "筛板塔":
            C_sl = self.get_val("mist_carry_SL_C")
            D_sl = self.get_val("mist_carry_SL_D")
            W_C1 = self.get_val("weeping_C1_SL")
            W_C2 = self.get_val("weeping_C2_SL")
            W_C3 = self.get_val("weeping_C3_SL")
            Vs_min_label = "漏液线"
            
            def mist_func(ls): 
                ls = np.maximum(1e-9, ls)
                return C_sl * (ls**(2/3.0)) + D_sl
                
            def weeping_func(ls): 
                ls = np.maximum(1e-9, ls)
                val = W_C2 + W_C3 * (ls**(2/3.0))
                return W_C1 * np.sqrt(np.maximum(0, val))
        else:
            return

        self.ax.clear()

        # k: 操作线的斜率 V_s = k * L_s
        k = Op_Vs / Op_Ls if Op_Ls > 1e-9 else 0.0
        
        # --- 2. 核心：计算所有有效交点 (操作弹性) ---
        all_intersections = [] 
        initial_guess = Op_Ls
        
        # 容差
        epsilon = 1e-6 

        # 辅助函数：解方程 f(Ls) = k * Ls => f(Ls) - k * Ls = 0，并严格验证结果
        def solve_and_collect(target_func, name):
            if name == "Weeping" and current_type == "浮阀塔":
                name_key = "$V_{s,min}$"
            elif name == "Weeping" and current_type == "筛板塔":
                 name_key = "Weeping"
            else:
                 name_key = name

            try:
                # 尝试求解
                L_i_list = fsolve(lambda ls: target_func(ls) - k * ls, initial_guess, full_output=True)
                
                L_i = L_i_list[0][0] 
                V_i = k * L_i
                
                # V_i > 0 约束是必须的
                if L_i > epsilon and V_i > epsilon:
                    
                    if not (Ls_min - epsilon <= L_i <= Ls_max + epsilon): 
                        return
                        
                    V_weep_at_L = weeping_func(L_i)
                    V_mist_at_L = mist_func(L_i)
                    V_flood_at_L = flood_func(L_i)
                    
                    is_valid = False
                    
                    if name in ["Flood", "Mist"]:
                        # 上限：该点必须高于 Weeping/Vs,min 线
                        if V_i >= V_weep_at_L - epsilon:
                             is_valid = True
                    elif name in ["Weeping", "$V_{s,min}$"]:
                        # 下限：该点必须低于 Mist 和 Flood 线
                        if V_i <= V_mist_at_L + epsilon and V_i <= V_flood_at_L + epsilon:
                            is_valid = True
                            
                    if is_valid:
                        all_intersections.append({'Ls': L_i, 'Vs': V_i, 'Source': name_key})

            except Exception:
                pass

        # 2a. 曲线交点 (包括 Weeping/Vs,min)
        solve_and_collect(mist_func, "Mist")
        solve_and_collect(flood_func, "Flood")
        solve_and_collect(weeping_func, "Weeping") 


        # 2b. Ls 限制线交点
        
        # Ls_max 交点 (垂直线交点)
        L_i_max = Ls_max
        V_i_max = k * L_i_max
        if V_i_max > epsilon and L_i_max > 0 and L_i_max >= Ls_min - epsilon:
             V_weep_at_Lmax = weeping_func(L_i_max)
             V_mist_at_Lmax = mist_func(L_i_max)
             V_flood_at_Lmax = flood_func(L_i_max)

             if V_weep_at_Lmax - epsilon <= V_i_max <= V_mist_at_Lmax + epsilon and V_i_max <= V_flood_at_Lmax + epsilon:
                all_intersections.append({'Ls': L_i_max, 'Vs': V_i_max, 'Source': "Ls_max"})

        # Ls_min 交点 (垂直线交点)
        L_i_min = Ls_min
        V_i_min = k * L_i_min
        if V_i_min > epsilon and L_i_min > 0 and L_i_min <= Ls_max + epsilon:
             V_weep_at_Lmin = weeping_func(L_i_min)
             V_mist_at_Lmin = mist_func(L_i_min)
             V_flood_at_Lmin = flood_func(L_i_min)

             if V_weep_at_Lmin - epsilon <= V_i_min <= V_mist_at_Lmin + epsilon and V_i_min <= V_flood_at_Lmin + epsilon:
                all_intersections.append({'Ls': L_i_min, 'Vs': V_i_min, 'Source': "Ls_min"})
        
        
        # --- 3. 筛选并确定 Vs_min / Vs_max (采用简化逻辑，假设有效操作区域连续且仅有两个极值点) ---
        
        all_intersections.sort(key=lambda x: x['Vs'])
        
        Vs_min_val = 0.0
        Ls_min_op_intersect = 0.0
        Vs_min_source = "N/A"
        
        Vs_max_val = 0.0
        Ls_max_op_intersect = 0.0
        Vs_max_source = "N/A"

        # 遍历交点，找到满足 V_weep < V_i < V_upper_bound 的最小和最大 V_i
        valid_points = []
        for pt in all_intersections:
            L = pt['Ls']
            V = pt['Vs']
            
            V_weep = weeping_func(L)
            V_upper = min(mist_func(L), flood_func(L))
            
            if V_weep - epsilon <= V <= V_upper + epsilon:
                # 检查 L 是否在 Ls_min 和 Ls_max 范围内
                if Ls_min - epsilon <= L <= Ls_max + epsilon:
                   valid_points.append(pt)

        # 确保至少有两个有效点才能计算弹性
        if len(valid_points) >= 2:
            valid_points.sort(key=lambda x: x['Vs'])
            
            min_pt = valid_points[0]
            max_pt = valid_points[-1]

            Vs_min_val = min_pt['Vs']
            Ls_min_op_intersect = min_pt['Ls']
            Vs_min_source = min_pt['Source']

            Vs_max_val = max_pt['Vs']
            Ls_max_op_intersect = max_pt['Ls']
            Vs_max_source = max_pt['Source']
        
        E_op = Vs_max_val / Vs_min_val if Vs_min_val > 0 else 0.0

        Ls_max_intersect = Ls_max_op_intersect
        Vs_min_op_line = Vs_min_val 
        Ls_min_intersect = Ls_min_op_intersect
        
        # --- 4. 绘图 ---
        LINE_WIDTH_THICK = 3.0
        LINE_WIDTH_AUX = 2.0
        COLOR_RED = '#E60000'    
        COLOR_BLUE = '#0000FF'   
        COLOR_GREEN = '#008000'  
        COLOR_YELLOW = '#FFD700' 
        COLOR_PURPLE = '#800080' 
        COLOR_SHADE = '#D3D3D3' 

        # **严格限定曲线绘图范围**
        # ls_plot_range 用于绘制曲线和阴影，严格限定在 [Ls_min, Ls_max]
        ls_plot_range = np.linspace(Ls_min, Ls_max, 200)
        ls_plot_range_scaled = ls_plot_range * 1000
        
        # 重新计算曲线值 (Raw values)
        vs_mist_curve = mist_func(ls_plot_range)
        vs_weep_curve = weeping_func(ls_plot_range)
        vs_flood_curve = flood_func(ls_plot_range)
        
        self.ax.clear()

        # --- Vs 绘图数组的条件化 (满足最新要求) ---
        epsilon_plot = 1e-9 # 用于绘制时的严格 > 0 比较

        # 1. 漏液线/Vs,min 线 (Purple): 只需要 Vs > 0
        vs_weep_plot = np.where(vs_weep_curve > epsilon_plot, vs_weep_curve, np.nan)
        
        # 2. 雾沫线 (Red): 必须 Vs > Vs_weep 且 Vs > 0
        condition_mist = (vs_mist_curve > vs_weep_curve + epsilon) & (vs_mist_curve > epsilon_plot)
        vs_mist_plot = np.where(condition_mist, vs_mist_curve, np.nan)
        
        # 3. 液泛线 (Blue): 必须 Vs > Vs_weep 且 Vs > 0
        condition_flood = (vs_flood_curve > vs_weep_curve + epsilon) & (vs_flood_curve > epsilon_plot)
        vs_flood_plot = np.where(condition_flood, vs_flood_curve, np.nan) 
        
        # --- 5. 动态轴限调整 (提前计算，用于绘制 Ls 垂直线) ---
        Ls_plot_max = max(Ls_max, Ls_max_op_intersect) 
        
        # 计算显示区域的最大 Vs 值 (考虑曲线、操作点、交点)
        Vs_max_bounds = []
        Vs_max_bounds.append(np.nanmax(vs_mist_plot) if np.any(~np.isnan(vs_mist_plot)) else 0)
        Vs_max_bounds.append(np.nanmax(vs_flood_plot) if np.any(~np.isnan(vs_flood_plot)) else 0)
        Vs_max_bounds.append(np.nanmax(vs_weep_plot) if np.any(~np.isnan(vs_weep_plot)) else 0)
        Vs_max_bounds.append(Vs_max_val)
        Vs_max_bounds.append(Op_Vs)

        Vs_data_max = max(Vs_max_bounds) if Vs_max_bounds else 5.0
        Vs_limit_view = Vs_data_max * 1.15
        x_limit_view = (Ls_plot_max * 1000) * 1.15

        self.ax.set_xlim(0, x_limit_view)
        self.ax.set_ylim(0, Vs_limit_view)
        # -----------------------------------------------------------------

        # 绘制操作区域阴影 (使用修正后的数组)
        # 上限： Min(修正后的 Mist, 修正后的 Flood)
        vs_upper_bound = np.minimum(vs_mist_plot, vs_flood_plot)
        # 下限： 修正后的 Weep
        vs_lower_bound = vs_weep_plot 

        # 阴影填充: 从 Weeping line 到 Min(Mist, Flood)，且 Vs > 0
        self.ax.fill_between(ls_plot_range_scaled, vs_lower_bound, vs_upper_bound, 
                             where=(vs_lower_bound > epsilon_plot), 
                             color=COLOR_SHADE, alpha=0.5, label='操作区域')
        
        
        # **修正点 4: 绘制 Ls,min 和 Ls,max 边界线 (从 Vs=0 到 Vs_limit_view)**
        
        # Ls_min 垂直线 (Yellow)
        self.ax.plot([x_min_plot, x_min_plot], [0, Vs_limit_view], 
                     color=COLOR_YELLOW, linewidth=LINE_WIDTH_THICK, linestyle='-', label="$L_{s,min}$")

        # Ls_max 垂直线 (Green)
        self.ax.plot([x_max_plot, x_max_plot], [0, Vs_limit_view], 
                     color=COLOR_GREEN, linewidth=LINE_WIDTH_THICK, linestyle='-', label="$L_{s,max}$")
        
        # **绘制三条性能曲线 (使用修正后的 Vs_plot 数组)**
        self.ax.plot(ls_plot_range_scaled, vs_weep_plot, 
                     color=COLOR_PURPLE, linewidth=LINE_WIDTH_THICK, linestyle='-', label=Vs_min_label)

        self.ax.plot(ls_plot_range_scaled, vs_mist_plot, 
                     color=COLOR_RED, linewidth=LINE_WIDTH_THICK, linestyle='-', label="雾沫线")

        self.ax.plot(ls_plot_range_scaled, vs_flood_plot, 
                     color=COLOR_BLUE, linewidth=LINE_WIDTH_THICK, linestyle='-', label="液泛线")

        # 绘制操作点 P
        self.ax.plot(Op_Ls*1000, Op_Vs, 'ko', markersize=8, zorder=10)
        self.ax.text(Op_Ls*1000-0.05, Op_Vs + 0.1, "P", fontsize=22, fontweight='bold')

        # 绘制操作线和交点
        if Op_Ls > 0 and Vs_max_val > 0:
            # 操作线 (从原点到 Vs_max)
            self.ax.plot([0, Ls_max_intersect*1000], [0, Vs_max_val], 
                         color='black', linestyle='-', linewidth=2.5, zorder=6)
            
            # Vs_max 虚线 
            self.ax.plot([0, Ls_max_intersect*1000], [Vs_max_val, Vs_max_val], 
                         color='black', linestyle='--', linewidth=LINE_WIDTH_AUX, zorder=5)
            # Vs_max 交点 
            self.ax.plot(Ls_max_intersect*1000, Vs_max_val, 'ro', markersize=6, zorder=10, label="$V_{s,max}$ 极值点")
            
            if Ls_min_intersect > 0 and Vs_min_op_line > 0:
                # Vs_min 虚线 
                self.ax.plot([0, Ls_min_intersect*1000], [Vs_min_op_line, Vs_min_op_line], 
                             color='black', linestyle='--', linewidth=LINE_WIDTH_AUX, zorder=5)
                # Vs_min 交点 
                self.ax.plot(Ls_min_intersect*1000, Vs_min_op_line, 'mo', markersize=6, zorder=10, label="$V_{s,min}$ 极值点") 
                
        # --- 标题与坐标轴 ---
        title_main = f"塔板负荷性能图 ({current_type})"
        title_sub = (f"$V_{{s,max}} = {Vs_max_val:.4f} m^3/s$  \n"
                     f"$V_{{s,min}} = {Vs_min_val:.4f} m^3/s$ \n"
                     f"操作弹性 $E_{{op}} = V_{{s,max}} / V_{{s,min}} = {E_op:.2f}$")
        
        self.ax.set_title(f"{title_main}\n{title_sub}", fontproperties=CHINESE_FONT, fontsize=24, pad=20)
        
        self.ax.set_xlabel("$L_s \\times 10^3 \\, (m^3/s)$", fontsize=20, labelpad=10)
        self.ax.set_ylabel("$V_s \\, (m^3/s)$", fontsize=20, labelpad=10)
        self.ax.tick_params(axis='both', which='major', labelsize=16)
        
        self.ax.legend(prop={'size': 16}, loc='upper right', framealpha=0.9)
        self.ax.grid(True, linestyle=':', alpha=0.4)
        
        # --- 更新结果文本框 ---
        res_str = f"塔型: {current_type}\n"
        res_str += f"Vs_max = {Vs_max_val:.6f}\n"
        res_str += f"Vs_min = {Vs_min_val:.6f} \n"
        res_str += f"操作弹性 E_op = {E_op:.4f}\n"
        res_str += f"操作点 P: ({Op_Ls*1000:.4f}, {Op_Vs:.4f})\n"
        res_str += f"Vs_max交点: ({Ls_max_intersect*1000:.4f}, {Vs_max_val:.4f})\n"
        res_str += f"Vs_min交点: ({Ls_min_intersect*1000:.4f}, {Vs_min_op_line:.4f})\n"
        
        res_str += "\n所有有效交点 (按 Vs 升序):\n"
        for i, pt in enumerate(valid_points): # 仅显示有效点
            res_str += f"V({i+1}): Ls={pt['Ls']*1000:.4f}, Vs={pt['Vs']:.4f}, Source={pt['Source']}\n"
            
        self.coord_text.delete(1.0, tk.END)
        self.coord_text.insert(tk.END, res_str)
        
        self.canvas.draw()

if __name__ == "__main__":
    if not tk._default_root:
        root = tk.Tk()
        app = TowerOperatingApp(root)
        root.mainloop()
    else:
        root = tk.Toplevel()
        app = TowerOperatingApp(root)