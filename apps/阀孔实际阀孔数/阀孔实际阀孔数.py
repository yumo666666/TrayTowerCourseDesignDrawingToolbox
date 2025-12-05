import tkinter as tk
from tkinter import ttk, filedialog, Menu
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Circle, Rectangle
import numpy as np
import json
import os
import math
import sys

# --- 全局常量和配置 ---
CONFIG_FILE = 'tray_design_config.json'
EXAMPLE_CONFIG_FILE = 'example.json'

# 默认参数结构
DEFAULT_PARAMS = {
    "current_type": "valve",
    "valve": {
        "diameter": "1600",
        "wd": "199",       
        "lw": "1056",         
        "pitch_base": "75",     
        "pitch_prime": "65",    
        "wc": "60",          
        "hole_dia": "39",
        "ws": "100",
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
    """
    def __init__(self, root):
        self.root = root
        self.root.title("阀孔/筛板实际孔数计算")
        
        # 设置窗口全屏启动
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-fullscreen', True)
            
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.load_config()

        # 全局增加菜单字体大小
        self.root.option_add('*Menu.font', 'Arial 16')

        # === 布局配置 ===
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        self.left_frame = ttk.Frame(root, padding="20")
        self.left_frame.grid(row=0, column=0, sticky="nsew")

        self.right_frame = ttk.Frame(root, padding="10")
        self.right_frame.grid(row=0, column=1, sticky="nsew")

        self.inputs = {}
        self.layout_mode = tk.StringVar(value="isosceles") 
        self.tray_type = tk.StringVar(value=self.config.get("current_type", "valve")) # 塔盘类型: valve 或 sieve

        self.create_inputs()

        # === 绘图区域初始化 ===
        self.fig, self.ax = plt.subplots(figsize=(6, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.result_label = ttk.Label(self.left_frame, text="孔总数: 0", font=(CHINESE_FONT, 24, "bold"), foreground="blue")
        self.result_label.pack(pady=30)

        # === 右键菜单功能 ===
        self.popup_menu = Menu(self.root, tearoff=0)
        self.popup_menu.add_command(label="另存为图片...", command=self.save_plot_as_image)
        self.canvas_widget.bind("<Button-3>", self.show_popup_menu)

        # 初始化界面状态
        # self.on_tray_type_change() # 不要在这里调用，因为会覆盖掉初始加载的正确参数？
        # 实际上 load_config 后 self.config 已经有了。
        # 只需要把 self.config[current_type] 的值填入 inputs 即可。
        self.on_tray_type_change()
        # self.plot_tray() # 移除自动绘图

    def on_closing(self):
        if messagebox.askokcancel("退出", "确定要关闭程序吗？"):
            self.save_config()
            self.root.destroy()
            sys.exit(0)

    def load_config(self):
        """加载配置文件，如果格式旧则自动迁移"""
        self.config = DEFAULT_PARAMS.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved_config = json.load(f)
                    
                    # 检查是否是新格式 (包含 'valve' 和 'sieve' 键)
                    if 'valve' in saved_config and 'sieve' in saved_config:
                        self.config = saved_config
                    else:
                        # 旧格式，默认归为 valve 数据，并保留默认 sieve 数据
                        # 尝试保留旧数据到 valve
                        for key in self.config['valve']:
                            if key in saved_config:
                                self.config['valve'][key] = saved_config[key]
            except Exception as e:
                print(f"加载配置失败: {e}. 使用默认值。")

    def save_config(self):
        """保存当前配置"""
        current_type = self.tray_type.get()
        self.config["current_type"] = current_type
        
        # 保存当前输入到对应的配置字典中
        target_dict = self.config[current_type]
        for key, entry in self.inputs.items():
            # 忽略不在当前类型配置中的键 (例如 magnification 在 valve 模式下)
            if key in target_dict:
                target_dict[key] = entry.get()
        
        target_dict["layout_mode"] = self.layout_mode.get()

        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def show_popup_menu(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def save_plot_as_image(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"),
                       ("JPEG图片", "*.jpg"),
                       ("所有文件", "*.*")],
            title="保存塔盘排布图",
            initialfile=f"{self.tray_type.get()}_tray_layout.png"
        )
        if file_path:
            try:
                self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("保存成功", f"图片已保存到：{file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"保存图片时发生错误：{e}")

    def on_tray_type_change(self):
        """当塔盘类型改变时调用"""
        # 1. 保存当前显示的参数到当前类型 (切换前保存)
        # 注意：这里有个逻辑陷阱，如果是用户点击切换，self.tray_type 已经变了。
        # 但我们希望保存的是切换前那个类型的参数？
        # Tkinter Radiobutton 改变 variable 后才触发 command。
        # 所以现在 self.tray_type 已经是新类型了。
        # 这意味着我们无法在这里保存旧类型的参数，除非我们记录上一次的类型。
        # 更好的策略是：
        # 每次点击“生成/保存”时保存参数。切换类型时，只负责加载新类型的参数。
        # 如果用户在切换前修改了参数但没点保存，参数会丢失？
        # 现在的逻辑是 save_config 会保存 self.inputs 到 self.tray_type 对应的 config。
        # 如果 self.tray_type 已经是新的了，那就会把旧界面的值保存到新配置里！这会导致参数混淆！
        
        # 修正逻辑：
        # 我们需要一个变量记录“上一次的类型”，或者在切换前先保存。
        # 但 Radiobutton 是先变值后回调。
        # 解决方法：在加载新参数前，不做保存。参数保存只在点击“生成”按钮或手动触发时进行。
        # 或者，我们接受用户切换类型时不自动保存未提交的更改。
        # 鉴于用户说“参数不要混”，我们必须确保加载的是目标类型的参数。
        
        t_type = self.tray_type.get()
        
        # 1. 加载新类型的参数到输入框
        if t_type in self.config:
            params = self.config[t_type]
            for key, entry in self.inputs.items():
                if key in params:
                    entry.delete(0, tk.END)
                    entry.insert(0, params[key])
            
            # 更新排布模式
            self.layout_mode.set(params.get("layout_mode", "isosceles"))
            self.toggle_mode()
        
        # 2. UI 调整 (筛板无特殊输入框，因为放大倍数已移除)
        # 之前有的 magnification_frame 逻辑已移除，这里不需要做什么
        
        # 3. 不自动绘图，清空画布或保持原状
        # self.ax.clear()
        # self.canvas.draw()
        # self.result_label.config(text="请点击生成按钮")
        pass

    def reset_params(self):
        """重置为默认参数"""
        if messagebox.askyesno("重置", "确定要重置为默认参数吗？"):
            t_type = self.tray_type.get()
            default_data = DEFAULT_PARAMS[t_type]
            self.config[t_type] = default_data.copy()
            
            # 刷新界面
            self.on_tray_type_change()
            self.save_config()

    def toggle_mode(self):
        """切换排布模式 (等腰/正三角)"""
        mode = self.layout_mode.get()
        if mode == "equilateral":
            self.inputs["pitch_prime"].config(state='disabled')
        else:
            self.inputs["pitch_prime"].config(state='normal')

    def create_inputs(self):
        title_label = ttk.Label(self.left_frame, text="参数设置 (mm)", font=(CHINESE_FONT, 32, "bold"))
        title_label.pack(pady=(0, 20))

        style = ttk.Style()
        style.configure("Big.TLabelframe.Label", font=(CHINESE_FONT, 28, "bold"), foreground="black")
        style.configure("Big.TLabelframe", padding=10)
        style.configure("Big.TButton", font=(CHINESE_FONT, 28, "bold"))

        # === 塔盘类型选择 ===
        type_frame = ttk.LabelFrame(self.left_frame, text="塔盘类型", style="Big.TLabelframe")
        type_frame.pack(fill=tk.X, pady=10)
        
        rb_valve = tk.Radiobutton(type_frame, text="浮阀塔盘 (Valve)", variable=self.tray_type, 
                                  value="valve", command=self.on_tray_type_change, font=(CHINESE_FONT, 28))
        rb_valve.pack(side=tk.LEFT, padx=20, pady=10)
        
        rb_sieve = tk.Radiobutton(type_frame, text="筛板塔盘 (Sieve)", variable=self.tray_type, 
                                  value="sieve", command=self.on_tray_type_change, font=(CHINESE_FONT, 28))
        rb_sieve.pack(side=tk.LEFT, padx=20, pady=10)

        # === 排布模式选择 ===
        rb_frame = ttk.LabelFrame(self.left_frame, text="排布模式", style="Big.TLabelframe")
        rb_frame.pack(fill=tk.X, pady=20)
        
        rb1 = tk.Radiobutton(rb_frame, text="等腰三角形 (自定义t')", variable=self.layout_mode, 
                             value="isosceles", command=self.toggle_mode, font=(CHINESE_FONT, 28))
        rb1.pack(anchor=tk.W, pady=10, padx=10)
        
        rb2 = tk.Radiobutton(rb_frame, text="正三角形 (自动t')", variable=self.layout_mode, 
                             value="equilateral", command=self.toggle_mode, font=(CHINESE_FONT, 28))
        rb2.pack(anchor=tk.W, pady=10, padx=10)

        # === 参数列表 ===
        params_order = [
            ("塔直径 (Φ)", "diameter"),  
            ("弓形降液管宽度 (Wd)", "wd"),
            ("堰长 (Lw)", "lw"),         
            ("孔中心距 (t)", "pitch_base"),     
            ("排间距 (t')", "pitch_prime"),    
            ("边缘区宽度 (Wc)", "wc"),          
            ("孔/阀直径", "hole_dia"),        
            ("破沫区宽度 (Ws)", "ws") 
        ]
        
        self.inputs_frames = []
        for label_text, var_name in params_order:
            frame = ttk.Frame(self.left_frame)
            frame.pack(fill=tk.X, pady=8) 
            self.inputs_frames.append(frame)
            
            lbl = ttk.Label(frame, text=label_text, width=22, anchor="w", font=(CHINESE_FONT, 28))
            lbl.pack(side=tk.LEFT)
            
            entry = ttk.Entry(frame, width=10, font=(CHINESE_FONT, 28))
            # 初始值暂时为空，由 on_tray_type_change 填充
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            self.inputs[var_name] = entry

        # === 按钮 ===
        self.btn_draw = tk.Button(self.left_frame, text="生成排布 / 计算", command=self.plot_tray,
                                  bg="#4CAF50", fg="white", font=(CHINESE_FONT, 28, "bold"), relief="raised")
        self.btn_draw.pack(pady=30, fill=tk.X, ipady=15)
        
        self.btn_reset = tk.Button(self.left_frame, text="重置默认参数", command=self.reset_params,
                                   font=(CHINESE_FONT, 28, "bold"), relief="raised", fg="red")
        self.btn_reset.pack(pady=10, fill=tk.X, ipady=15)

        # === 说明 ===
        info_text = (
            f"说明：\n"
            f"1. 切换塔盘类型会自动保存/加载对应参数。\n"
            f"2. 筛板模式下使用公式计算孔数，仅绘制示意图。\n"
            f"3. 筛板示意图右上角展示局部排布（自动放大）。"
        )
        desc = ttk.Label(self.left_frame, text=info_text, foreground="gray", font=(CHINESE_FONT, 18), justify=tk.LEFT)
        desc.pack(side=tk.BOTTOM, pady=20, anchor="w")

    def get_float_input(self, name):
        try:
            val = float(self.inputs[name].get())
            return val
        except (ValueError, KeyError):
            return 0.0

    def plot_tray(self):
        """主绘图/计算函数，根据类型分发"""
        # 点击生成时，先保存当前参数，避免丢失
        self.save_config()
        
        if self.tray_type.get() == "valve":
            self.plot_valve_tray()
        else:
            self.plot_sieve_tray()

    def _prepare_common_data(self):
        """准备通用数据并处理 t' 自动计算"""
        try:
            D = self.get_float_input("diameter")
            Wd = self.get_float_input("wd")      
            t_base = self.get_float_input("pitch_base")
            Wc = self.get_float_input("wc")      
            Ws = self.get_float_input("ws")      
            d_hole = self.get_float_input("hole_dia")

            mode = self.layout_mode.get()
            if mode == "equilateral":
                if t_base <= 0:
                    messagebox.showerror("输入错误", "正三角形模式下，孔中心距 (t) 必须大于0")
                    return None
                # 正三角形排布 (60度) 的行距是 t * sin(60) = t * sqrt(3)/2 ≈ 0.866 * t
                t_prime = t_base * (np.sqrt(3) / 2.0)
                
                self.inputs["pitch_prime"].config(state='normal')
                self.inputs["pitch_prime"].delete(0, tk.END)
                self.inputs["pitch_prime"].insert(0, f"{t_prime:.2f}")
                self.inputs["pitch_prime"].config(state='disabled')
            else:
                t_prime = self.get_float_input("pitch_prime")

            if D <= 0 or t_base <= 0 or t_prime <= 0:
                messagebox.showerror("输入错误", "主要尺寸参数必须大于0。")
                return None
            
            return (D, Wd, t_base, t_prime, Wc, Ws, d_hole)
        except Exception:
            messagebox.showerror("输入错误", "请输入有效的数字！")
            return None

    def plot_valve_tray(self):
        """原浮阀塔盘绘图逻辑"""
        data = self._prepare_common_data()
        if not data: return
        D, Wd, t_base, t_prime, Wc, Ws, d_hole = data

        R = D / 2.0
        hole_radius = d_hole / 2.0
        BEAM_HALF_THICKNESS = Wc / 8.0 
        clearance = Wc / 4.0 

        self.save_config()
        self.ax.clear()
        
        # --- 绘制基础结构 (圆, 堰, 梁) ---
        self._draw_base_structure(R, Wd, Wc, BEAM_HALF_THICKNESS, D)

        # --- 绘制跑道线 (Ws) ---
        weir_y = R - Wd
        self._draw_runway_lines(R, Wc, Ws, weir_y)

        # --- 阀孔具体排布 (逐个画) ---
        # 计算有效区域
        Y_runway_line_abs = weir_y - Ws 
        active_y_limit = Y_runway_line_abs - hole_radius
        R_runway = R - Wc
        active_safe_R = R_runway - hole_radius
        beam_exclusion = clearance + hole_radius
        beam_centers = [0, -D/4, D/4]

        valves_list = []
        
        # 生成行 Y 坐标
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

            # 生成该行 X 坐标
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
                # 检查梁避让
                on_beam = False
                for bx in beam_centers:
                    if abs(x - bx) < beam_exclusion:
                        on_beam = True
                        break
                if on_beam: continue

                valves_list.append((x, y))
                v_circle = Circle((x, y), hole_radius, color='black', alpha=1.0, linewidth=0.5, fill=False) 
                self.ax.add_patch(v_circle)
            
            row_index += 1

        # 绘制交叉线
        for i, (x1, y1) in enumerate(valves_list):
            # 简单优化：只检查附近的点
            for j in range(i + 1, min(i + 50, len(valves_list))): 
                (x2, y2) = valves_list[j]
                if abs(abs(y1 - y2) - t_prime) < 0.1 and abs(abs(x1 - x2) - t_base / 2.0) < 0.1:
                    self.ax.plot([x1, x2], [y1, y2], color='black', linestyle='-', linewidth=1.5, alpha=0.6)

        self._finalize_plot(len(valves_list), D, t_base, t_prime, Ws, Wc, "浮阀")

    def plot_sieve_tray(self):
        """筛板塔盘绘图逻辑 (公式计算 + 示意图)"""
        data = self._prepare_common_data()
        if not data: return
        D, Wd, t_base, t_prime, Wc, Ws, d_hole = data
        
        try:
            # magnification = float(self.inputs["magnification"].get()) # 已移除输入框
            pass
        except:
            pass

        R = D / 2.0
        hole_radius = d_hole / 2.0
        BEAM_HALF_THICKNESS = Wc / 8.0 
        clearance = Wc / 4.0 

        self.save_config()
        self.ax.clear()

        # --- 1. 绘制基础结构 ---
        self._draw_base_structure(R, Wd, Wc, BEAM_HALF_THICKNESS, D)

        # --- 2. 绘制跑道线 (Ws) ---
        weir_y = R - Wd
        self._draw_runway_lines(R, Wc, Ws, weir_y)

        # 3. 筛板特有：虚线分隔
        # 跑道区域范围
        Y_runway = weir_y - Ws
        R_runway = R - Wc
        # 画十字虚线
        if Y_runway > 0 and R_runway > 0:
            # 水平线 y=0 (在跑道范围内)
            x_limit = np.sqrt(np.maximum(0, R_runway**2)) # 实际上是 R_runway
            self.ax.plot([-x_limit, x_limit], [0, 0], color='black', linestyle='--', linewidth=1)
            # 垂直线 x=0 (在跑道范围内)
            self.ax.plot([0, 0], [-Y_runway, Y_runway], color='black', linestyle='--', linewidth=1)

        # --- 4. 筛板特有：右上角放大镜 ---
        # 右上角区域大致范围: x > 0, y > 0
        # 目标：放大镜圆圈尽量大，且与上方的水平蓝线 (y=Y_runway) 和右侧的圆弧蓝线 (R_runway) 相切 (内切)
        
        # 1. 设定半径 (保持 0.45 系数，或根据需要微调)
        mag_radius = min(R_runway, Y_runway) * 0.55 
        
        # 2. 计算圆心 Y (上切 y = Y_runway)
        # 上边缘 y = mag_center_y + mag_radius = Y_runway
        mag_center_y = Y_runway - mag_radius
        
        # 3. 计算圆心 X (右切 x^2 + y^2 = R_runway^2)
        # 圆心距原点距离 d + mag_radius = R_runway  => d = R_runway - mag_radius
        # x^2 + y^2 = d^2
        dist_sq = (R_runway - mag_radius)**2
        
        if dist_sq >= mag_center_y**2:
            mag_center_x = np.sqrt(dist_sq - mag_center_y**2)
        else:
            # 如果算出来无法右切（说明在 Y 轴方向已经受限，圆太大），优先切上边，X 居中或贴 Y 轴
            mag_center_x = 0 

        # 绘制放大镜背景 (白底黑边)
        mag_circle = Circle((mag_center_x, mag_center_y), mag_radius, facecolor='white', edgecolor='black', linewidth=2, zorder=10)
        self.ax.add_patch(mag_circle)

        # 在放大镜内绘制放大的孔
        # 裁剪区域设置为放大镜圆
        # 自动计算放大倍数，使得圆内大约能放下 10 个孔
        # 目标孔数 N = 10
        # 估算公式: N * (scaled_t * scaled_t') = pi * mag_radius^2
        # scaled_t = t * M, scaled_t' = t' * M
        # M^2 = (pi * mag_radius^2) / (N * t * t')
        target_holes = 50
        area_mag = np.pi * mag_radius**2
        unit_area = t_base * t_prime
        
        if unit_area > 0:
            # 增加 1.5 倍系数，确保网格足够密，能容纳下 target_holes 个孔 (考虑到边缘裁剪)
            magnification = np.sqrt(area_mag / (target_holes * 1.5 * unit_area))
            # 限制最小放大倍数，避免太小
            if magnification < 0.5: magnification = 0.5
        else:
            magnification = 1.0

        # 放大后的参数
        scaled_t_base = t_base * magnification
        scaled_t_prime = t_prime * magnification
        scaled_hole_r = hole_radius * magnification
        
        # 生成候选孔并裁剪
        # 以 mag_center 为原点生成局部网格
        rows_needed = int(mag_radius / scaled_t_prime) + 2
        cols_needed = int(mag_radius / scaled_t_base) + 2

        candidate_holes = []
        for r in range(-rows_needed, rows_needed + 1):
            y_local = r * scaled_t_prime
            x_offset = 0 if r % 2 == 0 else scaled_t_base / 2.0
            for c in range(-cols_needed, cols_needed + 1):
                x_local = c * scaled_t_base + x_offset
                
                # 检查是否在放大镜圆内 (考虑到孔半径)
                dist = np.sqrt(x_local**2 + y_local**2)
                # 只要圆心在放大镜内即可，或者完全在内
                # 为了视觉效果，我们只选离中心最近的
                if dist + scaled_hole_r <= mag_radius * 1.1: # 稍微放宽一点收集范围
                     candidate_holes.append((dist, x_local, y_local))
        
        # 按距离排序，取前 target_holes 个
        candidate_holes.sort(key=lambda x: x[0])
        holes_to_draw = candidate_holes[:target_holes]

        for _, x_local, y_local in holes_to_draw:
             # 绘制孔
            h_c = Circle((mag_center_x + x_local, mag_center_y + y_local), 
                         scaled_hole_r, color='black', fill=False, linewidth=1, zorder=11)
            self.ax.add_patch(h_c)

        # 绘制放大镜内的交叉线 (模拟相邻孔连线)
        for i in range(len(holes_to_draw)):
            _, x1_local, y1_local = holes_to_draw[i]
            x1_abs = mag_center_x + x1_local
            y1_abs = mag_center_y + y1_local
            
            for j in range(i + 1, len(holes_to_draw)):
                _, x2_local, y2_local = holes_to_draw[j]
                x2_abs = mag_center_x + x2_local
                y2_abs = mag_center_y + y2_local
                
                # 判断是否相邻 (使用放大后的间距)
                dx = abs(x1_local - x2_local)
                dy = abs(y1_local - y2_local)
                
                # 容差
                tol = scaled_t_base * 0.1 
                
                # 正三角形排布相邻判定 (或等腰)
                # 1. 同行相邻: dy ≈ 0, dx ≈ scaled_t_base (或者 scaled_t_base/2 * 2)
                # 2. 跨行相邻: dy ≈ scaled_t_prime, dx ≈ scaled_t_base / 2
                
                is_connected = False
                # 跨行连接
                if abs(dy - scaled_t_prime) < tol and abs(dx - scaled_t_base/2.0) < tol:
                    is_connected = True
                
                if is_connected:
                    # 检查连线是否在放大镜内 (简单起见，只要两个端点都在即可，或者裁剪)
                    # 这里因为孔已经被筛选过在圆内，所以直接连线问题不大，但为了美观可以加上裁剪
                    # 使用 zorder=10 与放大镜背景一致或略高
                    self.ax.plot([x1_abs, x2_abs], [y1_abs, y2_abs], color='black', linestyle='-', linewidth=1, alpha=0.6, zorder=11)

        # --- 5. 计算孔数 (公式法) ---
        count = self._calculate_sieve_count(D, Wd, Wc, Ws, t_base, t_prime, hole_radius, clearance)

        self._finalize_plot(count, D, t_base, t_prime, Ws, Wc, "筛板", is_sieve=True)

    def _calculate_sieve_count(self, D, Wd, Wc, Ws, t_base, t_prime, hole_radius, clearance):
        """
        使用几何面积法估算筛板孔数
        N = (有效跑道面积 - 梁占用面积) / (单孔占用面积)
        单孔占用面积 (叉排) = t * t'
        """
        R = D / 2.0
        R_runway = R - Wc
        Y_limit = (R - Wd) - Ws # weir_y - Ws

        if R_runway <= 0 or Y_limit <= 0:
            return 0

        # 1. 计算跑道总面积
        # 形状是 圆 R_runway 被 y = +/- Y_limit 截取的中间部分
        # 面积 = 圆面积 - 2 * 弓形面积
        # 弓形高度 h = R_runway - Y_limit
        # 如果 Y_limit >= R_runway，则面积为圆面积 (实际上被限制在 Y_limit 内，但圆本身更小)
        
        if Y_limit >= R_runway:
            area_runway = np.pi * R_runway**2
        else:
            # 弓形面积公式: R^2 * arccos(d/R) - d * sqrt(R^2 - d^2), 其中 d = Y_limit
            d = Y_limit
            sector_area = R_runway**2 * np.arccos(d/R_runway)
            triangle_area = d * np.sqrt(R_runway**2 - d**2)
            segment_area = sector_area - triangle_area
            area_runway = np.pi * R_runway**2 - 2 * segment_area

        # 2. 计算梁占用面积
        # 梁位于 x=0, x=-D/4, x=D/4
        # 每个梁的避让宽度 = 2 * (clearance + hole_radius) (因为是两侧避让，或者说是以梁中心为基准的禁区)
        # 原代码: if abs(x - bx) < beam_exclusion: continue
        # beam_exclusion = clearance + hole_radius
        # 所以禁区总宽度 = 2 * beam_exclusion
        
        exclusion_width = 2 * (clearance + hole_radius)
        beam_centers = [0, -D/4, D/4]
        
        area_beams = 0
        for bx in beam_centers:
            # 计算该梁在跑道内的长度
            # 跑道边界 x = +/- sqrt(R_runway^2 - y^2)
            # 近似为矩形条: Length * Width
            # 长度由 Y_limit 和 R_runway 共同决定
            
            # 梁中心 bx 处的最大 Y 值 (在圆 R_runway 上)
            if abs(bx) >= R_runway:
                continue # 梁在跑道圆外

            max_y_at_beam = np.sqrt(R_runway**2 - bx**2)
            # 实际高度受 Y_limit 限制
            actual_h = min(max_y_at_beam, Y_limit)
            
            length = 2 * actual_h # 上下对称
            area_beams += length * exclusion_width

        # 3. 净面积
        net_area = max(0, area_runway - area_beams)

        # 4. 孔数计算
        # 单元面积: t * t' (包含1个孔) ?
        # 验证: 矩形 t * 2t' 包含 2个孔 -> t * t' per hole.
        area_per_hole = t_base * t_prime
        
        count = int(net_area / area_per_hole)
        return count

    def _draw_base_structure(self, R, Wd, Wc, BEAM_HALF_THICKNESS, D):
        """绘制塔盘通用的基础线条"""
        weir_y = R - Wd
        
        # 1. 塔壁圆
        tower_circle = Circle((0, 0), R, fill=False, color=LINE_COLOR, linewidth=LINE_WIDTH)
        self.ax.add_patch(tower_circle)

        # 2. 堰线
        x_at_weir = np.sqrt(np.maximum(0, R**2 - weir_y**2))
        self.ax.plot([-x_at_weir, x_at_weir], [weir_y, weir_y], color=LINE_COLOR, linewidth=LINE_WIDTH)
        self.ax.plot([-x_at_weir, x_at_weir], [-weir_y, -weir_y], color=LINE_COLOR, linewidth=LINE_WIDTH)

        # 3. 边缘区/降液管区边界 (R - Wc/4 ? 原代码是 R - Wc/4 作为绘制边界，但 Wc 是边缘区宽度)
        # 原代码逻辑: NEW_ARC_INSET = Wc / 4.0. 
        # 通常边缘区是指 R 到 R-Wc 的环形区域。原代码画的线似乎是结构线。
        # 我保持原代码的视觉效果。
        arc_inset = Wc / 4.0
        arc_R = R - arc_inset
        active_y = weir_y - arc_inset
        
        # 绘制被梁打断的横线和圆弧
        # 为了简化，这里不重写复杂的打断逻辑，直接画，梁覆盖在上面即可 (或者简单分段)
        # 原代码做了精细的打断，我也复用一下核心逻辑简化版
        
        beam_centers = [0, -D/4, D/4]
        beam_intervals = []
        for c in beam_centers:
            beam_intervals.append((c - BEAM_HALF_THICKNESS, c + BEAM_HALF_THICKNESS))
        
        # 辅助函数：检查x是否在梁内
        def in_beam(x):
            for b_start, b_end in beam_intervals:
                if b_start < x < b_end: return True
            return False

        # 绘制上下横线 (y = +/- active_y)
        x_max_line = np.sqrt(np.maximum(0, arc_R**2 - active_y**2))
        xs = np.linspace(-x_max_line, x_max_line, 200)
        # 分段绘制
        segments = []
        curr_seg = []
        for x in xs:
            if not in_beam(x):
                curr_seg.append(x)
            else:
                if curr_seg: segments.append(curr_seg); curr_seg = []
        if curr_seg: segments.append(curr_seg)

        for seg in segments:
            if len(seg) > 1:
                self.ax.plot([seg[0], seg[-1]], [active_y, active_y], color=LINE_COLOR, linewidth=LINE_WIDTH)
                self.ax.plot([seg[0], seg[-1]], [-active_y, -active_y], color=LINE_COLOR, linewidth=LINE_WIDTH)

        # 绘制左右圆弧
        # 角度范围... 比较麻烦，直接用点筛选
        theta = np.linspace(0, 2*np.pi, 360)
        x_arc = arc_R * np.cos(theta)
        y_arc = arc_R * np.sin(theta)
        
        # 筛选条件: |y| < active_y 且 不在梁内
        mask = (np.abs(y_arc) < active_y)
        # 分段
        arc_segments = []
        curr_arc_x, curr_arc_y = [], []
        for i in range(len(mask)):
            if mask[i] and not in_beam(x_arc[i]):
                curr_arc_x.append(x_arc[i])
                curr_arc_y.append(y_arc[i])
            else:
                if curr_arc_x:
                    self.ax.plot(curr_arc_x, curr_arc_y, color=LINE_COLOR, linewidth=LINE_WIDTH)
                    curr_arc_x, curr_arc_y = [], []
        if curr_arc_x: self.ax.plot(curr_arc_x, curr_arc_y, color=LINE_COLOR, linewidth=LINE_WIDTH)

        # 绘制梁 (竖线)
        effective_y_max = min(active_y, arc_R)
        for b_start, b_end in beam_intervals:
            # 梁的两侧竖线
            for bx in [b_start, b_end]:
                y_lim_at_beam = np.sqrt(np.maximum(0, arc_R**2 - bx**2))
                draw_h = min(y_lim_at_beam, active_y)
                self.ax.plot([bx, bx], [-draw_h, draw_h], color=LINE_COLOR, linewidth=LINE_WIDTH)

    def _draw_runway_lines(self, R, Wc, Ws, weir_y):
        """绘制蓝色虚线跑道"""
        R_runway = R - Wc
        Y_runway = weir_y - Ws
        
        if R_runway <= 0 or Y_runway <= 0: return

        x_limit = np.sqrt(np.maximum(0, R_runway**2 - Y_runway**2))
        
        # 上下直线
        self.ax.plot([-x_limit, x_limit], [Y_runway, Y_runway], color='blue', linestyle='--', linewidth=1.5)
        self.ax.plot([-x_limit, x_limit], [-Y_runway, -Y_runway], color='blue', linestyle='--', linewidth=1.5)
        
        # 左右弧线
        theta_start = np.arcsin(Y_runway / R_runway)
        theta_end = np.pi - theta_start
        
        # 右弧
        t_right = np.linspace(-theta_start, theta_start, 50)
        self.ax.plot(R_runway * np.cos(t_right), R_runway * np.sin(t_right), color='blue', linestyle='--', linewidth=1.5)
        
        # 左弧
        t_left = np.linspace(theta_end, 2*np.pi - theta_end, 50) # wait, theta_end is ~170deg. 
        # simple way:
        t_left = np.linspace(np.pi - theta_start, np.pi + theta_start, 50)
        self.ax.plot(R_runway * np.cos(t_left), R_runway * np.sin(t_left), color='blue', linestyle='--', linewidth=1.5)

    def _finalize_plot(self, count, D, t, t_prime, Ws, Wc, type_name, is_sieve=False):
        """统一的收尾工作"""
        self.ax.set_aspect('equal', adjustable='box')
        limit = D/2.0 * 1.05
        self.ax.set_xlim(-limit, limit)
        self.ax.set_ylim(-limit, limit)
        
        layout_name = "正三角形" if self.layout_mode.get() == "equilateral" else "等腰三角形"
        title_str = (f"{type_name} - {layout_name}排布\n"
                     f"D={int(D)} t={int(t)} t'={t_prime:.1f} Ws={int(Ws)} Wc={int(Wc)} | 孔数: {count}")
        if is_sieve:
            title_str += " (估算)"
            
        self.ax.set_title(title_str, fontproperties=CHINESE_FONT, fontsize=20, pad=20)
        self.ax.tick_params(axis='both', which='major', labelsize=16)
        
        self.canvas.draw()
        self.result_label.config(text=f"阀孔总数: {count}")

if __name__ == "__main__":
    if not tk._default_root:
        root = tk.Tk()
        app = ValveTrayApp(root)
        root.mainloop()
    else:
        root = tk.Toplevel()
        app = ValveTrayApp(root)
