import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog, Toplevel
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.interpolate import interp1d
import os
import json
import sys

# =======================================================
# 定义脚本的绝对路径作为工作目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
# =======================================================

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
CONFIG_FILE = 'config.json'
EXAMPLE_CONFIG_FILE = 'example.json'

def get_available_excel_files():
    """扫描 DATA_DIR 获取所有 .xlsx 文件名，并返回列表。"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        return []
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx')]
    return files

class DistillationApp:
    def __init__(self, root):
        self.root = root
        self.excel_files = get_available_excel_files()
        
        self.root.title("图解法求理论板数") 
        
        # 设置窗口全屏启动
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-fullscreen', True)
        
        self.base_font_size = 10
        self.font_ui = tkfont.Font(family="Arial", size=self.base_font_size)
        self.font_bold = tkfont.Font(family="Arial", size=self.base_font_size, weight="bold")
        
        self.style = ttk.Style()
        self.style.configure("TCombobox", font=self.font_ui)
        self.root.option_add('*TCombobox*Listbox.font', self.font_ui)
        # Increase menu font size globally for this app
        self.root.option_add('*Menu.font', 'Arial 16')
        
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        self.frame_left = tk.Frame(root, bg="#f0f0f0", padx=10, pady=10)
        self.frame_left.grid(row=0, column=0, sticky="nsew")
        self.frame_left.bind("<Configure>", self.on_frame_resize) 
        
        self.frame_right = tk.Frame(root, bg='white')
        self.frame_right.grid(row=0, column=1, sticky="nsew")

        self.load_config() # Load config first
        self.create_inputs()

        self.figure, self.ax = plt.subplots(figsize=(5, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.frame_right)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.canvas.get_tk_widget().bind("<Button-3>", self.show_context_menu)
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="另存为图片 (Save As...)", command=self.save_plot)
        
        self.setup_axes()
        self.canvas.draw()
        
    def load_config(self):
        self.default_config = {
            'system_selection': self.excel_files[0] if self.excel_files else '', 
            'rect_slope': 0.53, 'rect_intercept': 0.44, 
            'strip_slope': 1.1, 'strip_intercept': -0.05, 
            'xD': 0.95, 'xF': 0.45, 'xW': 0.05,
            'plot_font_scale': 2.0, 'lw_steps': 0.8,
            'lw_main': 1.5, 'lw_vertical': 0.8
        }
        self.config = self.default_config.copy()
        config_path = os.path.join(BASE_DIR, CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
            except Exception:
                pass

    def reset_config(self):
        """重置为示例配置"""
        if messagebox.askyesno("重置", "确定要重置为示例参数吗？"):
            try:
                example_path = os.path.join(BASE_DIR, EXAMPLE_CONFIG_FILE)
                if os.path.exists(example_path):
                    with open(example_path, 'r') as f:
                        loaded_config = json.load(f)
                        self.config = self.default_config.copy()
                        self.config.update(loaded_config)
                else:
                    self.config = self.default_config.copy()
            except Exception as e:
                messagebox.showerror("错误", f"无法加载示例参数: {e}")
                return

            # 刷新界面显示
            self.refresh_inputs()
            self.save_config()
            self.plot_graph()

    def refresh_inputs(self):
        """刷新输入框的值"""
        # Update Combobox
        if self.config.get('system_selection') in self.excel_files:
             self.combo_file.set(self.config.get('system_selection'))
        elif self.excel_files:
             self.combo_file.set(self.excel_files[0])
        
        # Helper to update entry
        def update_entry(entry, val):
            entry.delete(0, tk.END)
            entry.insert(0, str(val))

        update_entry(self.entry_rect_slope, self.config.get('rect_slope'))
        update_entry(self.entry_rect_intercept, self.config.get('rect_intercept'))
        update_entry(self.entry_strip_slope, self.config.get('strip_slope'))
        update_entry(self.entry_strip_intercept, self.config.get('strip_intercept'))
        update_entry(self.entry_xD, self.config.get('xD'))
        update_entry(self.entry_xF, self.config.get('xF'))
        update_entry(self.entry_xW, self.config.get('xW'))

    def save_config(self):
        try:
            self.config['system_selection'] = self.combo_file.get()
            self.config['rect_slope'] = float(self.entry_rect_slope.get())
            self.config['rect_intercept'] = float(self.entry_rect_intercept.get())
            self.config['strip_slope'] = float(self.entry_strip_slope.get())
            self.config['strip_intercept'] = float(self.entry_strip_intercept.get())
            
            self.config['xD'] = float(self.entry_xD.get())
            self.config['xF'] = float(self.entry_xF.get())
            self.config['xW'] = float(self.entry_xW.get())

        except (AttributeError, ValueError):
            pass
            
        try:
            config_path = os.path.join(BASE_DIR, CONFIG_FILE)
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            pass

    def on_closing(self):
        try:
            self.save_config()
        except Exception:
            pass
        self.root.destroy()
        
    def on_frame_resize(self, event):
        new_size = max(9, int(event.height / 55))
        self.font_ui.configure(size=new_size)
        self.font_bold.configure(size=new_size)
        self.style.configure("TCombobox", font=self.font_ui)
        self.root.option_add('*TCombobox*Listbox.font', self.font_ui)
        if hasattr(self, 'combo_file'):
            self.combo_file.configure(font=self.font_ui)

    def open_settings_window(self):
        settings_window = Toplevel(self.root)
        settings_window.title("绘图设置 (Plot Settings)")
        settings_window.geometry("800x500") 
        settings_window.transient(self.root) 

        settings_font = self.font_ui 
        
        for i in range(5): settings_window.grid_rowconfigure(i, weight=1)
        for i in range(2): settings_window.grid_columnconfigure(i, weight=1)

        def add_setting_row(row, label_text, default_val):
            label = tk.Label(settings_window, text=label_text, font=settings_font)
            label.grid(row=row, column=0, sticky="nsew", padx=10, pady=5)
            entry = tk.Entry(settings_window, justify="center", font=settings_font)
            entry.insert(0, str(default_val))
            entry.grid(row=row, column=1, sticky="nsew", padx=10, pady=5)
            return entry

        self.setting_fs = add_setting_row(0, "图表字号比例 (Factor):", self.config.get('plot_font_scale', 2.0))
        self.setting_lw_main = add_setting_row(1, "主线宽 (曲线/操作线):", self.config.get('lw_main', 1.5))
        self.setting_lw_steps = add_setting_row(2, "阶梯线宽:", self.config.get('lw_steps', 0.8))
        self.setting_lw_vertical = add_setting_row(3, "垂直线宽:", self.config.get('lw_vertical', 0.8))

        btn_apply = tk.Button(settings_window, text="应用并关闭", font=settings_font, command=lambda: self.apply_settings(settings_window))
        btn_apply.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

    def apply_settings(self, window):
        try:
            self.config['plot_font_scale'] = float(self.setting_fs.get())
            self.config['lw_main'] = float(self.setting_lw_main.get())
            self.config['lw_steps'] = float(self.setting_lw_steps.get())
            self.config['lw_vertical'] = float(self.setting_lw_vertical.get())
            
            self.save_config()
            self.plot_graph()
            window.destroy()

        except ValueError:
            messagebox.showerror("输入错误", "请为所有设置输入有效的数字。")

    def create_inputs(self):
        rows = 14 # Increased for Reset button
        for i in range(rows): self.frame_left.rowconfigure(i, weight=1)
        self.frame_left.columnconfigure(0, weight=1)
        self.frame_left.columnconfigure(1, weight=1) 
        self.frame_left.columnconfigure(2, weight=2) 
        
        def add_simple_row(row_idx, label_text, default_key=None):
            tk.Label(self.frame_left, text=label_text, font=self.font_bold, bg="#f0f0f0", anchor="e").grid(row=row_idx, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
            entry = tk.Entry(self.frame_left, font=self.font_ui, justify="center")
            entry.insert(0, str(self.config.get(default_key, ''))) 
            entry.grid(row=row_idx, column=2, sticky="nsew", padx=5, pady=5)
            return entry

        tk.Label(self.frame_left, text="选择体系 (data目录 XLSX 文件):", font=self.font_bold, bg="#f0f0f0").grid(row=0, column=0, columnspan=3, sticky="sw")
        
        self.combo_file = ttk.Combobox(self.frame_left, values=self.excel_files, state="readonly", style="TCombobox", font=self.font_ui)
        
        if self.config.get('system_selection') in self.excel_files:
             self.combo_file.set(self.config.get('system_selection'))
        elif self.excel_files:
             self.combo_file.set(self.excel_files[0])
        else:
             self.combo_file.set("未找到文件")
             # self.combo_file.config(state="disabled") 
             
        self.combo_file.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=5)

        tk.Label(self.frame_left, text="--- 精馏段 (Rectifying) 操作线 y = kx + b ---", font=self.font_ui, bg="#f0f0f0").grid(row=2, column=0, columnspan=3, sticky="ew")
        
        tk.Label(self.frame_left, text="(斜率):", font=self.font_bold, bg="#f0f0f0", anchor="e").grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.entry_rect_slope = tk.Entry(self.frame_left, font=self.font_ui, justify="center")
        self.entry_rect_slope.insert(0, str(self.config.get('rect_slope', 0.53)))
        self.entry_rect_slope.grid(row=3, column=2, sticky="nsew", padx=5, pady=5)
        
        tk.Label(self.frame_left, text="(截距):", font=self.font_bold, bg="#f0f0f0", anchor="e").grid(row=4, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.entry_rect_intercept = tk.Entry(self.frame_left, font=self.font_ui, justify="center")
        self.entry_rect_intercept.insert(0, str(self.config.get('rect_intercept', 0.44)))
        self.entry_rect_intercept.grid(row=4, column=2, sticky="nsew", padx=5, pady=5)


        tk.Label(self.frame_left, text="--- 提馏段 (Stripping) 操作线 y = kx + b ---", font=self.font_ui, bg="#f0f0f0").grid(row=5, column=0, columnspan=3, sticky="ew")
        
        tk.Label(self.frame_left, text="(斜率):", font=self.font_bold, bg="#f0f0f0", anchor="e").grid(row=6, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.entry_strip_slope = tk.Entry(self.frame_left, font=self.font_ui, justify="center")
        self.entry_strip_slope.insert(0, str(self.config.get('strip_slope', 1.1)))
        self.entry_strip_slope.grid(row=6, column=2, sticky="nsew", padx=5, pady=5)
        
        tk.Label(self.frame_left, text="(截距):", font=self.font_bold, bg="#f0f0f0", anchor="e").grid(row=7, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.entry_strip_intercept = tk.Entry(self.frame_left, font=self.font_ui, justify="center")
        self.entry_strip_intercept.insert(0, str(self.config.get('strip_intercept', -0.05)))
        self.entry_strip_intercept.grid(row=7, column=2, sticky="nsew", padx=5, pady=5)
        
        
        tk.Label(self.frame_left, text="--- 垂直线设定 ---", font=self.font_ui, bg="#f0f0f0").grid(row=8, column=0, columnspan=3, sticky="ew")

        self.entry_xD = add_simple_row(9, "xD (塔顶):", default_key='xD')
        self.entry_xF = add_simple_row(10, "xF (进料):", default_key='xF')
        self.entry_xW = add_simple_row(11, "xW (塔底):", default_key='xW')

        btn_draw = tk.Button(self.frame_left, text="开始绘图", bg="#4CAF50", fg="white", font=self.font_bold, command=self.plot_graph)
        btn_draw.grid(row=12, column=0, columnspan=3, sticky="nsew", padx=5, pady=15)
        
        # Reset Button
        btn_reset = tk.Button(self.frame_left, text="重置为示例参数", font=self.font_bold, fg="red", command=self.reset_config)
        btn_reset.grid(row=13, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

    def setup_axes(self):
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.set_aspect('equal', adjustable='box') 
        lw_v = self.config.get('lw_vertical', 0.8)
        fs_scale = self.config.get('plot_font_scale', 2.0)
        self.ax.tick_params(direction='in', top=True, right=True, width=lw_v, labelsize=10 * fs_scale)
        for spine in self.ax.spines.values():
            spine.set_linewidth(self.config.get('lw_main', 1.5))
        self.ax.set_xlabel("x", fontsize=12 * fs_scale, labelpad=10 * fs_scale)
        self.ax.set_ylabel("y", fontsize=12 * fs_scale, rotation=0, labelpad=10 * fs_scale)

    def plot_graph(self):
        try:
            k_R = float(self.entry_rect_slope.get())
            b_R = float(self.entry_rect_intercept.get())
            k_S = float(self.entry_strip_slope.get())
            b_S = float(self.entry_strip_intercept.get())
            
            x_D = float(self.entry_xD.get())
            x_F = float(self.entry_xF.get())
            x_W = float(self.entry_xW.get())
        except ValueError:
            messagebox.showwarning("输入错误", "请检查所有输入是否为有效的单个数字。")
            return
            
        f_rect = np.poly1d([k_R, b_R]) 
        f_strip = np.poly1d([k_S, b_S]) 

        x_intersect = (b_S - b_R) / (k_R - k_S) if (k_R != k_S) else x_F 

        df = self.get_data_from_excel()
        if df is None: return
        
        curve_x_raw, curve_y_raw = df.iloc[:, 0].dropna().values, df.iloc[:, 1].dropna().values

        sort_idx = np.argsort(curve_x_raw)
        curve_x, curve_y = curve_x_raw[sort_idx], curve_y_raw[sort_idx]
        f_curve_y_to_x = interp1d(curve_y, curve_x, kind='cubic', fill_value="extrapolate")

        # 4. 阶梯计算
        steps_x, steps_y = [], []
        current_x, current_y = x_D, x_D
        steps_x.append(current_x); steps_y.append(current_y)
        count = 0
        max_steps = 100
        while count < max_steps:
            next_x = float(f_curve_y_to_x(current_y))
            steps_x.append(next_x); steps_y.append(current_y)
            if next_x < x_W:
                steps_x.append(next_x); steps_y.append(next_x); break
            
            current_x = next_x
            
            if current_x > x_intersect:
                next_y = f_rect(current_x) 
            else:
                next_y = f_strip(current_x) 
            
            steps_x.append(current_x); steps_y.append(next_y)
            current_y = next_y
            count += 1

        self.ax.clear()
        self.setup_axes()
        
        lw_m = self.config.get('lw_main', 1.5)
        lw_s = self.config.get('lw_steps', 0.8)
        lw_v = self.config.get('lw_vertical', 0.8)
        fs_scale = self.config.get('plot_font_scale', 2.0)
        
        # 绘制 45 度对角线
        self.ax.plot([0, 1], [0, 1], color='black', linewidth=lw_m)
        
        # 绘制平衡曲线 (黑色实线)
        x_range = np.linspace(0, 1, 200)
        self.ax.plot(x_range, interp1d(curve_x, curve_y, kind='cubic', fill_value="extrapolate")(x_range), color='black', linewidth=lw_m, label='平衡曲线')
        
        # === 绘制曲线的原始数据点 (红色圆点) ===
        self.ax.plot(curve_x_raw, curve_y_raw, 'ro', markersize=4 * fs_scale, label='原始数据点')
        
        # 绘制操作线
        self.ax.plot([x_intersect, x_D], f_rect([x_intersect, x_D]), color='blue', linewidth=lw_m, label='精馏操作线')
        self.ax.plot([x_W, x_intersect], f_strip([x_W, x_intersect]), color='#00FF00', linewidth=lw_m, label='提馏操作线')
        
        # 绘制 q 线
        y_intersect = f_rect(x_intersect)
        q_line_k = (y_intersect - x_F) / (x_intersect - x_F) if x_intersect != x_F else 1
        q_line_b = y_intersect - q_line_k * x_intersect
        f_q = np.poly1d([q_line_k, q_line_b])
        self.ax.plot([x_F, x_intersect], f_q([x_F, x_intersect]), color='green', linestyle='-', linewidth=lw_m)
        self.ax.text(x_F + 0.01, x_F + 0.01, 'q', fontsize=10 * fs_scale, color='green') 

        # 绘制垂直线
        for val, text in zip([x_D, x_F, x_W], [r'$x_D$', r'$x_F$', r'$x_W$']):
            self.ax.plot([val, val], [0, 1], color='black', linestyle=':', linewidth=lw_v)
            self.ax.text(val, -0.06, text, ha='center', fontsize=12 * fs_scale, color='black')

        # 绘制阶梯
        self.ax.plot(steps_x, steps_y, color='black', linewidth=lw_s)
        
        # === 绘制阶梯和线的交点 (黑色圆点) ===
        for i in range(len(steps_x)-1):
            self.ax.plot(steps_x[i], steps_y[i], 'k.', markersize=4 * fs_scale) 

        title_text = f"McCabe-Thiele Diagram\nTheoretical Plates (理论塔板数不包含再沸器): {count}"
        self.ax.set_title(title_text, fontsize=14 * fs_scale, fontweight='bold', pad=15 * fs_scale)
        self.ax.legend(loc='upper left', fontsize=8 * fs_scale)

        self.figure.tight_layout()
        self.canvas.draw()
        
    def get_data_from_excel(self):
        filename_selected = self.combo_file.get()
        if not filename_selected or filename_selected == "未找到文件":
             messagebox.showwarning("错误", "未选择或未找到任何 Excel 文件。")
             return None
             
        filename = os.path.join(DATA_DIR, filename_selected)
        
        if not os.path.exists(filename):
            messagebox.showerror("错误", f"未找到文件: {filename_selected}")
            return None
            
        try:
            return pd.read_excel(filename, header=None, usecols=[0, 1], engine='openpyxl')
        except Exception as e:
            messagebox.showerror("错误", f"读取Excel失败，请确认文件格式:\n{e}")
            return None

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def save_plot(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png", 
            filetypes=[("PNG files", "*.png")],
            initialfile="图解法求理论板数.png"
        )
        if file_path:
            self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            messagebox.showinfo("成功", f"图片已保存")

if __name__ == "__main__":
    root = tk.Tk()
    app = DistillationApp(root)
    root.mainloop()
