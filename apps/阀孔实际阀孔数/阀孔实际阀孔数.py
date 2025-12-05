import tkinter as tk
from tkinter import ttk, filedialog, Menu
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Circle
import numpy as np
import json
import os
import sys

# --- 全局常量和配置 ---
CONFIG_FILE = 'tray_design_config.json'
EXAMPLE_CONFIG_FILE = 'example.json'

DEFAULT_PARAMS = {
    "diameter": "1600",
    "wd": "199",       
    "lw": "1056",         
    "pitch_base": "75",     
    "pitch_prime": "65",    
    "wc": "60",          
    "hole_dia": "39",
    "ws": "100"
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
    def __init__(self, root):
        self.root = root
        self.root.title("阀孔实际阀孔数")
        
        # 设置窗口全屏启动
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-fullscreen', True)
        
        self.load_config()

        # Increase menu font size globally for this app
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
        # 布局模式变量 (isosceles 或 equilateral)
        self.layout_mode = tk.StringVar(value="isosceles") 
        
        self.create_inputs()

        # === 绘图区域初始化 ===
        self.fig, self.ax = plt.subplots(figsize=(6, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.result_label = ttk.Label(self.left_frame, text="阀孔总数: 0", font=(CHINESE_FONT, 24, "bold"), foreground="blue")
        self.result_label.pack(pady=30)

        # === 右键菜单功能 ===
        self.popup_menu = Menu(self.root, tearoff=0)
        self.popup_menu.add_command(label="另存为图片...", command=self.save_plot_as_image)
        self.canvas_widget.bind("<Button-3>", self.show_popup_menu)

        self.plot_tray()
        
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        self.config = DEFAULT_PARAMS.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved_config = json.load(f)
                    for key in self.config:
                        if key in saved_config:
                            self.config[key] = saved_config[key]
            except Exception as e:
                print(f"加载配置失败: {e}. 使用默认值。")
        
    def save_config(self):
        current_values = {}
        for key, entry in self.inputs.items():
            if key == "pitch_prime" and self.layout_mode.get() == "equilateral":
                current_values[key] = entry.get() 
            else:
                current_values[key] = entry.get()
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(current_values, f, indent=4)
        except Exception as e:
            pass

    def on_closing(self):
        self.save_config()
        self.root.destroy()
    
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
            initialfile="阀孔实际阀孔数.png"
        )
        if file_path:
            try:
                self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("保存成功", f"图片已保存到：{file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"保存图片时发生错误：{e}")

    def reset_params(self):
        if messagebox.askyesno("重置", "确定要重置为示例参数吗？"):
            try:
                with open(EXAMPLE_CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    self.config = DEFAULT_PARAMS.copy()
                    self.config.update(loaded_config)
            except Exception as e:
                messagebox.showerror("错误", f"无法加载示例参数: {e}")
                self.config = DEFAULT_PARAMS.copy()

            # 刷新输入框
            for key in self.inputs:
                if key in self.config:
                    if isinstance(self.inputs[key], ttk.Entry):
                         self.inputs[key].delete(0, tk.END)
                         self.inputs[key].insert(0, self.config[key])
            self.layout_mode.set("isosceles")
            self.toggle_mode()
            self.plot_tray()
            self.save_config()

    def toggle_mode(self):
        mode = self.layout_mode.get()
        if mode == "equilateral":
            self.inputs["pitch_prime"].config(state='disabled')
        else:
            self.inputs["pitch_prime"].config(state='normal')

    def create_inputs(self):
        title_label = ttk.Label(self.left_frame, text="参数设置 (mm)", font=(CHINESE_FONT, 32, "bold"))
        title_label.pack(pady=(0, 20))

        # === 样式设置 ===
        style = ttk.Style()
        # 1. 设置 LabelFrame 标题的字体样式 (大字体)
        style.configure("Big.TLabelframe.Label", font=(CHINESE_FONT, 28, "bold"), foreground="black")
        style.configure("Big.TLabelframe", padding=10) # 增加内部边距

        # 2. 设置按钮样式
        style.configure("Big.TButton", font=(CHINESE_FONT, 28, "bold"))

        # === 排布模式选择单选框 ===
        # 使用自定义的 Big.TLabelframe 样式
        rb_frame = ttk.LabelFrame(self.left_frame, text="排布模式", style="Big.TLabelframe")
        rb_frame.pack(fill=tk.X, pady=20) # 增加外部间距
        
        # 将单选按钮的字体大小调整为 28
        rb1 = tk.Radiobutton(rb_frame, text="等腰三角形 (自定义t')", variable=self.layout_mode, 
                             value="isosceles", command=self.toggle_mode, font=(CHINESE_FONT, 28))
        rb1.pack(anchor=tk.W, pady=10, padx=10) # 增加内部间距
        
        rb2 = tk.Radiobutton(rb_frame, text="正三角形 (自动t')", variable=self.layout_mode, 
                             value="equilateral", command=self.toggle_mode, font=(CHINESE_FONT, 28))
        rb2.pack(anchor=tk.W, pady=10, padx=10) # 增加内部间距

        # 参数列表
        params_order = [
            ("塔直径 (Φ)", "diameter"),  
            ("弓形降液管宽度 (Wd)", "wd"),
            ("堰长 (Lw)", "lw"),         
            ("孔中心距 (t)", "pitch_base"),     
            ("排间距 (t')", "pitch_prime"),    
            ("边缘区宽度 (Wc)", "wc"),          
            ("阀孔直径", "hole_dia"),        
            ("破沫区宽度 (Ws)", "ws") 
        ]
        
        self.inputs["clearance"] = tk.StringVar(value="")

        for label_text, var_name in params_order:
            frame = ttk.Frame(self.left_frame)
            frame.pack(fill=tk.X, pady=12) 
            
            lbl = ttk.Label(frame, text=label_text, width=22, anchor="w", font=(CHINESE_FONT, 28))
            lbl.pack(side=tk.LEFT)
            
            entry = ttk.Entry(frame, width=10, font=(CHINESE_FONT, 28))
            entry.insert(0, self.config.get(var_name, DEFAULT_PARAMS.get(var_name, "0")))
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            
            self.inputs[var_name] = entry

        # 初始化输入框状态
        self.toggle_mode()

        self.btn_draw = tk.Button(self.left_frame, text="生成排布 / 保存参数", command=self.plot_tray,
                                  bg="#4CAF50", fg="white", font=(CHINESE_FONT, 28, "bold"), relief="raised")
        self.btn_draw.pack(pady=40, fill=tk.X, ipady=15)
        
        self.btn_reset = tk.Button(self.left_frame, text="重置为示例参数", command=self.reset_params,
                                   font=(CHINESE_FONT, 28, "bold"), relief="raised", fg="red")
        self.btn_reset.pack(pady=10, fill=tk.X, ipady=15)
        
        info_text = (
            f"说明：\n"
            f"1. **正三角形模式**下，t' 自动计算为 t × √2 / 2。\n"
            f"2. 阀孔排布区域严格限制在蓝色跑道边界内。\n"
            f"3. 右键图片可另存为。"
        )
        desc = ttk.Label(self.left_frame, text=info_text, foreground="gray", font=(CHINESE_FONT, 18), justify=tk.LEFT)
        desc.pack(side=tk.BOTTOM, pady=20, anchor="w")

    def get_float_input(self, name):
        try:
            if isinstance(self.inputs[name], ttk.Entry):
                val = float(self.inputs[name].get())
            elif isinstance(self.inputs[name], tk.StringVar):
                 val = float(self.inputs[name].get() or 0.0)
            else:
                val = 0.0
            return val
        except ValueError:
            return 0.0

    def plot_tray(self):
        # 1. 获取输入数据
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
                     return
                t_prime = t_base * (np.sqrt(2) / 2.0)
                
                self.inputs["pitch_prime"].config(state='normal')
                self.inputs["pitch_prime"].delete(0, tk.END)
                self.inputs["pitch_prime"].insert(0, f"{t_prime:.2f}")
                self.inputs["pitch_prime"].config(state='disabled')
            else:
                t_prime = self.get_float_input("pitch_prime")

        except Exception:
            messagebox.showerror("输入错误", "请输入有效的数字！")
            return

        if D <= 0 or t_base <= 0 or t_prime <= 0 or Wc <= 0 or Ws <= 0: 
            messagebox.showerror("输入错误", "主要尺寸参数必须大于0。")
            return

        R = D / 2.0
        hole_radius = d_hole / 2.0
        BEAM_HALF_THICKNESS = Wc / 8.0 
        clearance = Wc / 4.0 

        self.save_config()
        self.ax.clear()
        
        weir_y = R - Wd  
        beam_center_locations = [0, -D/4, D/4] 
        beam_locations_pairs = []
        for center in beam_center_locations:
            x1 = center - BEAM_HALF_THICKNESS
            x2 = center + BEAM_HALF_THICKNESS
            beam_locations_pairs.append((x1, x2))
            
        all_x_coords = set([-R, R])
        for x1, x2 in beam_locations_pairs:
            all_x_coords.add(x1)
            all_x_coords.add(x2)
        region_x_bounds = sorted(list(all_x_coords))

        # 绘制塔径大圆
        tower_circle = Circle((0, 0), R, fill=False, color=LINE_COLOR, linewidth=LINE_WIDTH)
        self.ax.add_patch(tower_circle)

        # 绘制堰线
        x_at_weir = np.sqrt(np.maximum(0, R**2 - weir_y**2)) 
        self.ax.plot([-x_at_weir, x_at_weir], [weir_y, weir_y], 
                     color=LINE_COLOR, linestyle='-', linewidth=LINE_WIDTH)
        self.ax.plot([-x_at_weir, x_at_weir], [-weir_y, -weir_y], 
                     color=LINE_COLOR, linestyle='-', linewidth=LINE_WIDTH)
        
        # 绘制布孔有效区外边界圆弧 (R - Wc/4) 和 辅助线
        NEW_ARC_INSET = Wc / 4.0 
        arc_R = R - NEW_ARC_INSET  
        active_y_limit_for_plot = weir_y - NEW_ARC_INSET 
        
        x_max_on_arc_R = np.sqrt(np.maximum(0, arc_R**2 - active_y_limit_for_plot**2))
        
        # 绘制横线 (被梁截断)
        x_plot_segments = []
        x_break_points = sorted(list(set([-x_max_on_arc_R, x_max_on_arc_R] + [x for pair in beam_locations_pairs for x in pair])))
        
        last_x = -x_max_on_arc_R
        for i in range(len(x_break_points)):
            current_x = x_break_points[i]
            if current_x <= last_x: continue
            is_in_beam_gap = False
            for x1, x2 in beam_locations_pairs:
                if x1 < (last_x + current_x)/2.0 < x2:
                    is_in_beam_gap = True
                    break
            segment_start = max(last_x, -x_max_on_arc_R)
            segment_end = min(current_x, x_max_on_arc_R)
            if segment_end > segment_start + 0.1 and not is_in_beam_gap: 
                x_plot_segments.append((segment_start, segment_end))
            last_x = current_x

        for x_start, x_end in x_plot_segments:
            self.ax.plot([x_start, x_end], [active_y_limit_for_plot, active_y_limit_for_plot], 
                         color=LINE_COLOR, linestyle='-', linewidth=LINE_WIDTH)
            self.ax.plot([x_start, x_end], [-active_y_limit_for_plot, -active_y_limit_for_plot], 
                         color=LINE_COLOR, linestyle='-', linewidth=LINE_WIDTH)

        # 绘制圆弧 (被梁截断)
        if arc_R > 0:
            for i in range(len(region_x_bounds) - 1):
                x_min_region = region_x_bounds[i]
                x_max_region = region_x_bounds[i+1]
                is_beam_gap = any(abs(x_min_region - x1) < 0.1 and abs(x_max_region - x2) < 0.1 for x1, x2 in beam_locations_pairs)
                if is_beam_gap: continue

                x_start_arc = max(x_min_region, -arc_R)
                x_end_arc = min(x_max_region, arc_R)
                if x_end_arc <= x_start_arc: continue 
                
                x_values = np.linspace(x_start_arc, x_end_arc, 100)
                y_upper_arc = np.sqrt(np.maximum(0, arc_R**2 - x_values**2))
                valid_indices_upper = y_upper_arc <= active_y_limit_for_plot
                
                if np.any(valid_indices_upper):
                     self.ax.plot(x_values[valid_indices_upper], y_upper_arc[valid_indices_upper], 
                                  color=LINE_COLOR, linestyle='-', linewidth=LINE_WIDTH)

                y_lower_arc = -np.sqrt(np.maximum(0, arc_R**2 - x_values**2))
                valid_indices_lower = y_lower_arc >= -active_y_limit_for_plot
                
                if np.any(valid_indices_lower):
                    self.ax.plot(x_values[valid_indices_lower], y_lower_arc[valid_indices_lower], 
                                 color=LINE_COLOR, linestyle='-', linewidth=LINE_WIDTH)

        # 绘制塔板分块线 (梁)
        effective_min_y_for_beams = max(-active_y_limit_for_plot, -arc_R)
        effective_max_y_for_beams = min(active_y_limit_for_plot, arc_R)
        beam_plot_locations = [x for pair in beam_locations_pairs for x in pair]
        
        for bx in beam_plot_locations:
            y_at_beam_on_arc_R = np.sqrt(np.maximum(0, arc_R**2 - bx**2))
            draw_y_min = max(effective_min_y_for_beams, -y_at_beam_on_arc_R)
            draw_y_max = min(effective_max_y_for_beams, y_at_beam_on_arc_R)
            if draw_y_max > draw_y_min:
                self.ax.plot([bx, bx], [draw_y_min, draw_y_max], 
                             color=LINE_COLOR, linestyle='-', linewidth=LINE_WIDTH) 

        # 绘制 Ws/Wc 跑道形状 (蓝色虚线)
        R_runway = R - Wc 
        Y_runway_line_abs = weir_y - Ws 
        active_y_limit_for_holes_new = Y_runway_line_abs - hole_radius
        active_safe_R_for_holes_new = R_runway - hole_radius
        
        if R_runway > 0 and Y_runway_line_abs > 0 and R_runway > Y_runway_line_abs:
            x_limit_for_runway_line = np.sqrt(np.maximum(0, R_runway**2 - Y_runway_line_abs**2))
            self.ax.plot([-x_limit_for_runway_line, x_limit_for_runway_line], [Y_runway_line_abs, Y_runway_line_abs], 
                         color='blue', linestyle='--', linewidth=1.5)
            self.ax.plot([-x_limit_for_runway_line, x_limit_for_runway_line], [-Y_runway_line_abs, -Y_runway_line_abs], 
                         color='blue', linestyle='--', linewidth=1.5)
            
            # 左侧弧线
            theta_start_left = np.arctan2(Y_runway_line_abs, -x_limit_for_runway_line)
            theta_end_left = np.arctan2(-Y_runway_line_abs, -x_limit_for_runway_line)
            theta_values_left = np.linspace(theta_start_left, theta_end_left + 2*np.pi if theta_end_left < theta_start_left else theta_end_left, 100)
            x_left_arc = R_runway * np.cos(theta_values_left)
            y_left_arc = R_runway * np.sin(theta_values_left)
            valid_indices_left = (x_left_arc <= 0.1) & (y_left_arc >= -Y_runway_line_abs - 0.1) & (y_left_arc <= Y_runway_line_abs + 0.1)
            if np.any(valid_indices_left):
                self.ax.plot(x_left_arc[valid_indices_left], y_left_arc[valid_indices_left], color='blue', linestyle='--', linewidth=1.5)

            # 右侧弧线
            theta_start_right = np.arctan2(Y_runway_line_abs, x_limit_for_runway_line)
            theta_end_right = np.arctan2(-Y_runway_line_abs, x_limit_for_runway_line)
            theta_values_right = np.linspace(theta_end_right, theta_start_right, 100) if theta_end_right < theta_start_right else np.linspace(theta_start_right, theta_end_right, 100)
            x_right_arc = R_runway * np.cos(theta_values_right)
            y_right_arc = R_runway * np.sin(theta_values_right)
            valid_indices_right = (x_right_arc >= -0.1) & (y_right_arc >= -Y_runway_line_abs - 0.1) & (y_right_arc <= Y_runway_line_abs + 0.1)
            if np.any(valid_indices_right):
                self.ax.plot(x_right_arc[valid_indices_right], y_right_arc[valid_indices_right], color='blue', linestyle='--', linewidth=1.5)

        # 阀孔排布
        valves_list = []
        beam_exclusion_distance = clearance + hole_radius 
        
        rows_y = []
        j = 0
        while j * t_prime <= active_y_limit_for_holes_new:
            current_y = j * t_prime
            if current_y >= -active_y_limit_for_holes_new: rows_y.append(current_y)
            j += 1
        j = 1
        while -j * t_prime >= -active_y_limit_for_holes_new:
            current_y = -j * t_prime
            if current_y <= active_y_limit_for_holes_new: rows_y.append(current_y)
            j += 1
        rows_y.sort()

        row_index = 0
        for y in rows_y:
            x_offset = 0.0
            if row_index % 2 != 0: x_offset = t_base / 2.0
            
            max_x_abs_for_hole = np.sqrt(np.maximum(0, active_safe_R_for_holes_new**2 - y**2))
            if max_x_abs_for_hole <= 0: 
                row_index += 1
                continue

            current_row_x_centers = []
            k = 0
            while True:
                x_candidate = k * t_base + x_offset
                if x_candidate <= max_x_abs_for_hole: current_row_x_centers.append(x_candidate)
                else: break
                k += 1
            k = 1
            while True:
                x_candidate = -k * t_base + x_offset
                if x_candidate >= -max_x_abs_for_hole: current_row_x_centers.append(x_candidate)
                else: break
                k += 1
            
            x_coords_for_this_row = sorted(list(set(current_row_x_centers)))

            for x in x_coords_for_this_row:
                on_beam = False
                for bx_center in beam_center_locations: 
                    if abs(x - bx_center) < beam_exclusion_distance:
                        on_beam = True
                        break
                if on_beam: continue

                valves_list.append((x, y))
                v_circle = Circle((x, y), hole_radius, color='black', alpha=1.0, linewidth=0.5) 
                self.ax.add_patch(v_circle)
            
            row_index += 1 

        # 绘制交叉斜线
        for i, (x1, y1) in enumerate(valves_list):
            for j in range(i + 1, len(valves_list)):
                (x2, y2) = valves_list[j]
                if abs(abs(y1 - y2) - t_prime) < 1.0 and abs(abs(x1 - x2) - t_base / 2.0) < 1.0:
                    self.ax.plot([x1, x2], [y1, y2], color='black', linestyle='-', linewidth=1.5, alpha=0.6)

        # 视图设置
        count = len(valves_list)
        self.ax.set_aspect('equal', adjustable='box')
        limit = R * 1.05
        self.ax.set_xlim(-limit, limit)
        self.ax.set_ylim(-limit, limit)
        
        # 动态标题
        layout_name = "正三角形" if self.layout_mode.get() == "equilateral" else "等腰三角形"
        title_str = (f"{layout_name}叉排\n"
                     f"D={int(D)} t={int(t_base)} t'={t_prime:.1f} Ws={int(Ws)} Wc={int(Wc)} | 孔数: {count}")
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