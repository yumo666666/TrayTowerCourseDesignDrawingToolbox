import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.path as mpath
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys 
import json 
import os 

# ==========================================
# 全局常量
# ==========================================
# 定义用于保存参数的 JSON 文件名
PARAM_FILE = 'distillation_tower_params.json'
EXAMPLE_PARAM_FILE = 'example.json'

# ==========================================
# 绘图函数 (已添加 Hd 和 h_b 的支持，并修正了降液管侧壁的绘制)
# ==========================================

def create_tower_plot(D, Z, N_rect, N_strip, W_d, H_weir, H_liq_weir, H_d, h_b):
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
    fig, ax = plt.subplots(figsize=(7, 12)) 
    
    # 基础设置
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS'] 
    plt.rcParams['axes.unicode_minus'] = False 

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
            # 注意：此处使用 R 作为降液管右侧的 x 坐标
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
    ax.text(0, sump_level_y * 0.5, '塔底储液', ha='center', fontsize=20, color='brown', zorder=4)

    # 顶部向上箭头
    ax.arrow(0, Z + Head_H, 0, 1.0, head_width=0.25, head_length=0.4, fc='black', ec='black', lw=2, length_includes_head=True, zorder=6)
    ax.text(0.3, Z + Head_H + 0.5, '塔顶气相', ha='left', va='center', fontsize=24, color='black')

    # 回流 (L) (固定在左侧) 
    y_ref = Z - Plate_Spacing
    ax.annotate('回流 (L)', xy=(-R, y_ref), xytext=(-R - 1.5, y_ref),
                arrowprops=dict(facecolor='blue', width=3, headwidth=10), 
                va='center', ha='right', color='blue', zorder=5,
                fontsize=24) 

    # 原料 (F) - 动态修正水平位置 (根据 N_rect 奇偶性)
    y_feed = Z - Plate_Spacing * (1.5 + (N_rect - 1) + 0.5)
    
    if N_rect % 2 == 0: 
        F_x, F_text_x, F_ha = -R, -R - 1.5, 'right'
    else: 
        F_x, F_text_x, F_ha = R, R + 1.5, 'left'
        
    ax.annotate('原料 (F)', xy=(F_x, y_feed), xytext=(F_text_x, y_feed),
                arrowprops=dict(facecolor='green', width=3, headwidth=10), 
                va='center', ha=F_ha, color='green', zorder=5,
                fontsize=24) 


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
                fontsize=24) 

    # 底部向下箭头 (塔底液相)
    ax.arrow(0, -Head_H, 0, -1.0, head_width=0.25, head_length=0.4, fc='black', ec='black', lw=2, length_includes_head=True, zorder=6)
    ax.text(-0.3, -Head_H - 0.5, '塔底液相', ha='right', va='center', fontsize=24, color='black')


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
                fontsize=20, ha='left', va='center', color='darkslategray')


    # --- G. 视图设置 ---
    ax.set_aspect('equal')
    ax.set_xlim(-R - 2.0 - 5.0, R + 6) 
    ax.set_ylim(-Head_H - 1.5, Z + Head_H + 2.0)
    ax.axis('off')
    
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    return fig


# ==========================================
# GUI 界面类 (新增参数和 h_b > H_weir 校验)
# ==========================================

class TowerApp:
    def __init__(self, master):
        self.master = master
        self.root = master  # Add this line for compatibility
        master.title("板式塔结构简图")

        # 设置窗口全屏启动
        try:
            master.state('zoomed')
        except:
            master.attributes('-fullscreen', True)
        
        # def on_closing():
        #     if messagebox.askokcancel("退出", "确定要关闭程序吗？"):
        #         self.save_params()
        #         master.destroy()
        #         sys.exit() 
                
        # master.protocol("WM_DELETE_WINDOW", on_closing)

        self.entry_font_spec = ('SimHei', 24) 
        self.style = ttk.Style()
        self.style.configure('TLabel', font=self.entry_font_spec) 
        self.style.configure('TButton', font=self.entry_font_spec) 

        # 默认参数 (已添加 Hd 和 h_b)
        self.default_params = {
            "D": 1.6,
            "Z": 13.95,
            "N_rect": 22,
            "N_strip": 10,
            "W_d": 0.192,
            "H_weir": 0.049,
            "H_liq_weir": 0.021,
            "H_d": 0.13763,        # 新增
            "h_b": 0.0485          # 新增
        }
        
        # 尝试加载上次保存的参数
        self.params = self.load_params()
        
        # Increase menu font size globally for this app
        self.root.option_add('*Menu.font', 'Arial 16')
        
        self.current_figure = None

        master.grid_columnconfigure(0, weight=1) 
        master.grid_columnconfigure(1, weight=3) 
        master.grid_rowconfigure(0, weight=1)

        # --- 左侧参数区域 (Frame 0) ---
        self.param_frame = ttk.Frame(master, padding="20", relief=tk.RIDGE) 
        self.param_frame.grid(row=0, column=0, sticky="nsew")
        self.param_frame.grid_columnconfigure(0, weight=1)
        self.param_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(self.param_frame, text="参数配置", font=("SimHei", 26, "bold")).grid(row=0, column=0, columnspan=2, pady=20)
        
        self.entries = {}
        row_num = 1
        
        # 参数标签 (已添加 Hd 和 h_b/h0)
        param_labels = {
            "D": "塔内径 D (m):",
            "Z": "塔高 Z (m):",
            "N_rect": "精馏段板数 NP精:",
            "N_strip": "提馏段板数 NP提:",
            "W_d": "降液管宽度 Wd (m):",
            "H_weir": "堰板高度 Hw堰高 (m):",
            "H_liq_weir": "堰上液层高度 How (m):",
            "H_d": "降液管清液液高 Hd (m):",   # 新增
            "h_b": "降液管底隙 h0 (m):"    # 新增
        }

        for var_name, label_text in param_labels.items():
            ttk.Label(self.param_frame, text=label_text).grid(row=row_num, column=0, sticky="w", pady=15) 
            
            entry = tk.Entry(self.param_frame, width=15, font=self.entry_font_spec) 
            
            entry.insert(0, str(self.params.get(var_name, self.default_params[var_name])))
            
            entry.grid(row=row_num, column=1, sticky="ew", pady=15) 
            self.entries[var_name] = entry
            row_num += 1

        # 使用 tk.Button 替换 ttk.Button 以支持自定义背景色
        self.btn_draw = tk.Button(self.param_frame, text="生成绘图", command=self.update_plot,
                                  bg="#4CAF50", fg="white", font=("SimHei", 24, "bold"), relief="raised")
        self.btn_draw.grid(row=row_num, column=0, columnspan=2, pady=50, sticky="ew")
        
        self.btn_reset = tk.Button(self.param_frame, text="重置为示例参数", command=self.reset_params,
                                   font=("SimHei", 24, "bold"), relief="raised", fg="red")
        self.btn_reset.grid(row=row_num+1, column=0, columnspan=2, pady=10, sticky="ew")

        # --- 右侧绘图区域 (Frame 1) ---
        self.plot_frame = ttk.Frame(master, relief=tk.SUNKEN)
        self.plot_frame.grid(row=0, column=1, sticky="nsew")
        self.plot_frame.grid_rowconfigure(0, weight=1)
        self.plot_frame.grid_columnconfigure(0, weight=1)

        # 初始化 Matplotlib 画布 (使用加载或默认参数)
        self.fig = create_tower_plot(**self.params)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")
        self.current_figure = self.fig

        # 绑定右键菜单事件
        self.canvas_widget.bind("<Button-3>", self.show_context_menu)
        self.create_context_menu()
        
        # 第一次调用 update_plot 确保参数正确传递并绘制
        self.update_plot()
        
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="另存为 (Save Plot)", command=self.save_plot)

    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def reset_params(self):
        if messagebox.askyesno("重置", "确定要重置为示例参数吗？"):
            # Load from example.json
            self.params = self.load_params_from_file(EXAMPLE_PARAM_FILE)
            
            # 更新输入框
            for var_name, entry in self.entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(self.params.get(var_name, "")))
            self.update_plot()

    def load_params_from_file(self, filepath):
        """通用：从指定 JSON 文件加载参数"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    loaded_params = json.load(f)
                    
                    # 尝试将加载的参数转换为正确的类型
                    loaded_params["D"] = float(loaded_params["D"])
                    loaded_params["Z"] = float(loaded_params["Z"])
                    loaded_params["N_rect"] = int(loaded_params["N_rect"])
                    loaded_params["N_strip"] = int(loaded_params["N_strip"])
                    loaded_params["W_d"] = float(loaded_params["W_d"])
                    loaded_params["H_weir"] = float(loaded_params["H_weir"])
                    loaded_params["H_liq_weir"] = float(loaded_params["H_liq_weir"])
                    
                    loaded_params["H_d"] = float(loaded_params.get("H_d", self.default_params["H_d"])) 
                    loaded_params["h_b"] = float(loaded_params.get("h_b", self.default_params["h_b"])) 
                    
                    return loaded_params
            except Exception as e:
                print(f"加载参数失败 {filepath}: {e}")
                return self.default_params.copy()
        else:
            return self.default_params.copy()

    def load_params(self):
        """从 JSON 文件加载参数，包含 Hd 和 h_b。"""
        return self.load_params_from_file(PARAM_FILE)

    def save_params(self):
        """将当前绘图参数保存到 JSON 文件，包含 Hd 和 h_b。"""
        try:
            params_to_save = {}
            for key in self.default_params.keys():
                try:
                    params_to_save[key] = self.entries[key].get()
                except:
                    params_to_save[key] = str(self.params.get(key, self.default_params[key]))


            with open(PARAM_FILE, 'w', encoding='utf-8') as f:
                json.dump(params_to_save, f, ensure_ascii=False, indent=4)
            print(f"参数已成功保存到: {PARAM_FILE}")
            
        except Exception as e:
            print(f"错误: 保存参数文件失败。错误信息: {e}")


    def update_plot(self):
        new_params = {}
        try:
            # 读取并验证参数
            new_params["D"] = float(self.entries["D"].get())
            new_params["Z"] = float(self.entries["Z"].get())
            new_params["N_rect"] = int(self.entries["N_rect"].get())
            new_params["N_strip"] = int(self.entries["N_strip"].get())
            new_params["W_d"] = float(self.entries["W_d"].get())
            new_params["H_weir"] = float(self.entries["H_weir"].get())
            new_params["H_liq_weir"] = float(self.entries["H_liq_weir"].get())
            new_params["H_d"] = float(self.entries["H_d"].get())        # 新增
            new_params["h_b"] = float(self.entries["h_b"].get())        # 新增
            
            if new_params["N_rect"] < 1 or new_params["N_strip"] < 1:
                 raise ValueError("板数 NP精/NP提 必须大于等于 1。")
            if new_params["W_d"] >= new_params["D"] / 2:
                raise ValueError("降液管宽度 Wd 不能大于或等于塔半径 D/2。")

        except ValueError as e:
            messagebox.showerror("参数错误", f"请检查输入的参数值是否正确。\n错误信息: {e}")
            return

        # 参数验证成功，更新 self.params
        self.params = new_params
        
        # 自动保存参数
        self.save_params() 

        # 销毁旧图
        plt.close(self.fig)
        
        # 创建新图
        self.fig = create_tower_plot(**new_params)
        self.current_figure = self.fig
        
        # --- 校验 h_b > H_weir，并弹窗提示 (在画完图后执行) ---
        if new_params["h_b"] > new_params["H_weir"]:
            messagebox.showwarning("参数建议", f"注意：降液管底隙 h_b/h0 ({new_params['h_b']:.4f} m) 通常应小于堰板高度 Hw堰高 ({new_params['H_weir']:.4f} m)，请检查参数是否符合设计要求。")
        
        # 销毁旧画布并创建新画布以正确更新绘图
        self.canvas_widget.destroy()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")
        
        # 重新绑定右键菜单事件
        self.canvas_widget.bind("<Button-3>", self.show_context_menu)


    def save_plot(self):
        if self.current_figure:
            f = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG file", "*.png"), ("JPEG file", "*.jpg"), ("All files", "*.*")],
                title="保存绘图文件",
                initialfile="板式塔结构简图.png"
            )
            if f:
                try:
                    self.current_figure.savefig(f, dpi=300, bbox_inches='tight')
                    messagebox.showinfo("保存成功", f"绘图已保存到: {f}")
                except Exception as e:
                    messagebox.showerror("保存失败", f"保存文件时发生错误: {e}")
        else:
            messagebox.showwarning("无图可存", "请先生成绘图。")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = TowerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"运行错误: {e}")
        print("请确认已安装所有依赖: pip install tkinter matplotlib numpy")