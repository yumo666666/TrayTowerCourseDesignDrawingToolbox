import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, filedialog
import os
import sys
import json
import subprocess
from PIL import Image, ImageTk
from datetime import datetime
import shutil

# --- 1. Dummy Imports for PyInstaller ---
try:
    import pandas
    import matplotlib
    import numpy
    import scipy
    import openpyxl
    import requests
    import pytz
except ImportError:
    pass
# ----------------------------------------

# Add features path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from features.date_range import is_within_date_range
except ImportError:
    def is_within_date_range(s, e): return True, "Module missing"

APPS_DIR = os.path.join(current_dir, 'apps')

# Magic Separator for Overlay
OVERLAY_SEPARATOR = b'<<<STUDENT_CONFIG_START>>>'

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("化工原理课设辅助工具")
        self.root.geometry("1100x800")
        
        # Determine Mode
        self.mode_data = self.load_mode_from_overlay()
        self.is_student = self.mode_data.get("mode") == "student"
        self.running_processes = []  # Track subprocesses
        
        self.setup_ui()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        # Terminate all tracked subprocesses
        for p in self.running_processes:
            if p.poll() is None:  # If still running
                try:
                    p.terminate()
                except:
                    pass
        self.root.destroy()
        sys.exit(0)

    def load_mode_from_overlay(self):
        """
        Attempt to read configuration appended to the end of the executable.
        If found, we are in STUDENT mode with limits.
        If not found, we are in TEACHER mode.
        """
        # Only check overlay if we are running as a frozen exe
        if getattr(sys, 'frozen', False):
            try:
                exe_path = sys.executable
                with open(exe_path, 'rb') as f:
                    content = f.read()
                    
                if OVERLAY_SEPARATOR in content:
                    # Find the last occurrence just in case
                    split_content = content.split(OVERLAY_SEPARATOR)
                    if len(split_content) > 1:
                        json_bytes = split_content[-1]
                        try:
                            config = json.loads(json_bytes.decode('utf-8'))
                            return config
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                print(f"Overlay read error: {e}")
                
        # Default Teacher Mode
        return {"mode": "teacher", "limits": {}}

    def setup_ui(self):
        # Fullscreen / Zoomed
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-fullscreen', True)

        # Header
        header = tk.Frame(self.root, bg="#333", height=80)
        header.pack(fill=tk.X)
        
        title_text = "板式塔课设工具箱 (学生版)" if self.is_student else "板式塔课设工具箱 (教师版)"
        title_lbl = tk.Label(header, text=title_text, font=("Microsoft YaHei", 20, "bold"), fg="white", bg="#333")
        title_lbl.pack(side=tk.LEFT, padx=30, pady=20)
        
        if not self.is_student:
            admin_btn = tk.Button(header, text="配置并生成学生版", command=self.open_admin_panel, 
                                  bg="#007ACC", fg="white", font=("Microsoft YaHei", 12), relief="flat", padx=15)
            admin_btn.pack(side=tk.RIGHT, padx=30, pady=20)
        
        # Content - Use a main frame instead of canvas for no scrollbar if preferred,
        # but to keep it robust we can just make the scrollable_frame expand.
        # User requested "no scrollbar", so we try to fit everything.
        self.main_frame = tk.Frame(self.root, bg="#f5f5f5")
        self.main_frame.pack(fill="both", expand=True)
        
        self.load_apps()

    def load_apps(self):
        if not os.path.exists(APPS_DIR):
            tk.Label(self.main_frame, text="未找到 apps 目录", bg="#f5f5f5").pack(pady=20)
            return

        # Filter valid apps
        apps = sorted(os.listdir(APPS_DIR))
        valid_apps = []
        for app_name in apps:
            app_path = os.path.join(APPS_DIR, app_name)
            script_path = os.path.join(app_path, f"{app_name}.py")
            if os.path.isdir(app_path) and os.path.exists(script_path):
                valid_apps.append(app_name)

        num_apps = len(valid_apps)
        if num_apps == 0:
            tk.Label(self.main_frame, text="没有可用的应用程序", bg="#f5f5f5").pack(pady=20)
            return

        # Layout Logic
        if num_apps == 1:
            row1_count = 1
            row2_count = 0
        else:
            row1_count = (num_apps + 1) // 2
            row2_count = num_apps - row1_count

        # Use grid for main frame to distribute height equally
        # We have 4 rows now: 
        # 0: Row 1 Info (Image+Title) - High Weight
        # 1: Row 1 Controls (Buttons) - Low Weight
        # 2: Row 2 Info - High Weight
        # 3: Row 2 Controls - Low Weight
        
        self.main_frame.rowconfigure(0, weight=10)
        self.main_frame.rowconfigure(1, weight=1)
        
        if row2_count > 0:
            self.main_frame.rowconfigure(2, weight=10)
            self.main_frame.rowconfigure(3, weight=1)
        
        # Create Frames for Rows (NOT USED - We use main_frame grid directly)
        # Populate Row 1
        for i in range(row1_count):
            app_name = valid_apps[i]
            self.main_frame.columnconfigure(i, weight=1)
            self.create_app_display(app_name, self.main_frame, 0, i)
            self.create_app_controls(app_name, self.main_frame, 1, i)

        # Populate Row 2
        if row2_count > 0:
            # Align columns logic
            # Row 2 reuses the same columns as Row 1
            for i in range(row2_count):
                app_idx = row1_count + i
                app_name = valid_apps[app_idx]
                self.create_app_display(app_name, self.main_frame, 2, i)
                self.create_app_controls(app_name, self.main_frame, 3, i)

    def create_app_display(self, app_name, parent, row, col):
        app_path = os.path.join(APPS_DIR, app_name)
        
        # Info Container
        container = tk.Frame(parent, bg="#f5f5f5")
        container.grid(row=row, column=col, sticky="nsew", padx=20, pady=(10, 0))
        
        # Actual Card
        card = tk.Frame(container, bg="white", relief="raised", bd=1)
        card.pack(fill="both", expand=True, ipadx=10, ipady=10)
        
        # Image
        img_path = os.path.join(app_path, "example.png")
        tk_img = None
        if os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                # Restore big image size
                pil_img.thumbnail((380, 240), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                pass
            
        lbl_img = tk.Label(card, bg="white")
        if tk_img:
            lbl_img.config(image=tk_img)
            lbl_img.image = tk_img 
        else:
            lbl_img.config(text="[无预览图]", width=20, height=10, bg="#eee")
        
        lbl_img.pack(pady=10, expand=True) # Expand image to take available space
            
        # Title
        lbl_title = tk.Label(card, text=app_name, font=("Microsoft YaHei", 16, "bold"), bg="white")
        lbl_title.pack(pady=5)
        
        # Status/Limit Info for Student
        # (Moved to controls area)

    def create_app_controls(self, app_name, parent, row, col):
        app_path = os.path.join(APPS_DIR, app_name)
        
        # Controls Container
        container = tk.Frame(parent, bg="#f5f5f5")
        container.grid(row=row, column=col, sticky="nsew", padx=20, pady=(0, 10))
        
        # Use a frame inside to match card width/style or just buttons
        # Let's make it look like an extension of the card
        btn_area = tk.Frame(container, bg="white", relief="raised", bd=1)
        btn_area.pack(fill="x", expand=True, ipadx=10, ipady=10) # fill x only

        # Inner centering frame
        center_frame = tk.Frame(btn_area, bg="white")
        center_frame.pack(anchor="center")

        # Status/Limit Info for Student (Moved to bottom of control area)
        if self.is_student:
             limits = self.mode_data.get("limits", {}).get(app_name)
             info_text = "无时间限制"
             fg_color = "green"
             
             if limits:
                 info_text = f"可用时间: {limits['start']} 至 {limits['end']}"
                 fg_color = "gray"
                 valid, status_code = is_within_date_range(limits['start'], limits['end'])
                 if not valid:
                     fg_color = "red"
                     if status_code == "NOT_STARTED":
                        info_text += " (未开始)"
                     elif status_code == "EXPIRED":
                        info_text += " (已过期)"
                     elif status_code == "NETWORK_ERROR":
                        info_text += " (需联网)"
                     else:
                        info_text += " (不可用)"
                 else:
                     fg_color = "green"
                     
             lbl_info = tk.Label(btn_area, text=info_text, fg=fg_color, bg="white", font=("Arial", 9))
             lbl_info.pack(side="bottom", pady=(5, 0))

        # Check for File Config
        file_config_path = os.path.join(app_path, "file_config.json")
        if os.path.exists(file_config_path):
            try:
                with open(file_config_path, 'r', encoding='utf-8') as f:
                    fconf = json.load(f)
                    if fconf.get("has_files"):
                         target_relative_path = fconf.get("path", ".")
                         full_target_path = os.path.abspath(os.path.join(app_path, target_relative_path))
                         
                         btn_edit = tk.Button(center_frame, text="编辑文件", 
                                              command=lambda p=full_target_path: self.open_file_manager(p),
                                              bg="#FF9800", fg="white", font=("Microsoft YaHei", 12, "bold"), relief="flat", padx=15, pady=5)
                         btn_edit.pack(side=tk.LEFT, padx=10)
            except Exception:
                pass

        # Launch Button
        btn = tk.Button(center_frame, text="启动程序", command=lambda n=app_name: self.launch_app(n),
                        bg="#4CAF50", fg="white", font=("Microsoft YaHei", 12, "bold"), relief="flat", padx=20, pady=5)
        btn.pack(side=tk.LEFT, padx=10)

    def open_file_manager(self, target_path):
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建目录: {target_path}\n{e}")
                return

        fm = Toplevel(self.root)
        fm.title("文件管理")
        fm.geometry("600x400")
        
        # Center window
        fm.update_idletasks()
        width = fm.winfo_width()
        height = fm.winfo_height()
        x = (fm.winfo_screenwidth() // 2) - (width // 2)
        y = (fm.winfo_screenheight() // 2) - (height // 2)
        fm.geometry(f'{width}x{height}+{x}+{y}')

        lbl_path = tk.Label(fm, text=f"当前目录: {target_path}", wraplength=580)
        lbl_path.pack(pady=5)

        listbox = tk.Listbox(fm, selectmode=tk.SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        def refresh_list():
            listbox.delete(0, tk.END)
            if os.path.exists(target_path):
                for f in os.listdir(target_path):
                    listbox.insert(tk.END, f)
        
        refresh_list()

        btn_frame = tk.Frame(fm)
        btn_frame.pack(fill=tk.X, pady=10)

        def upload_file():
            src = filedialog.askopenfilename(title="选择要上传的文件")
            if src:
                try:
                    fname = os.path.basename(src)
                    dst = os.path.join(target_path, fname)
                    shutil.copy2(src, dst)
                    refresh_list()
                    messagebox.showinfo("成功", "文件上传成功")
                except Exception as e:
                    messagebox.showerror("错误", f"上传失败: {e}")

        def delete_file():
            sel = listbox.curselection()
            if not sel:
                return
            fname = listbox.get(sel[0])
            try:
                fpath = os.path.join(target_path, fname)
                os.remove(fpath)
                refresh_list()
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {e}")

        tk.Button(btn_frame, text="上传文件", command=upload_file, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=20)
        tk.Button(btn_frame, text="删除选中", command=delete_file, bg="#F44336", fg="white").pack(side=tk.RIGHT, padx=20)

    def launch_app(self, app_name):
        # 1. Check limits if student
        if self.is_student:
            limits = self.mode_data.get("limits", {}).get(app_name)
            if limits:
                valid, status_code = is_within_date_range(limits['start'], limits['end'])
                if not valid:
                    if status_code == "NOT_STARTED":
                        messagebox.showwarning("访问受限", f"该应用当前不可用：\n未到开放时间 ({limits['start']})")
                    elif status_code == "EXPIRED":
                        messagebox.showwarning("访问受限", f"该应用当前不可用：\n已超过截止时间 ({limits['end']})")
                    elif status_code == "NETWORK_ERROR":
                        messagebox.showerror("网络错误", "无法获取网络时间，请检查您的网络连接。\n为了保证公平性，本程序必须在联网状态下运行。")
                    else:
                        messagebox.showwarning("访问受限", f"该应用当前不可用：\n{status_code}")
                    return

        # 2. Launch
        script_path = os.path.join(APPS_DIR, app_name, f"{app_name}.py")
        work_dir = os.path.join(APPS_DIR, app_name)
        
        try:
            # Determine python interpreter to use
            if getattr(sys, 'frozen', False):
                 # In frozen state (EXE), we use the EXE itself as the python interpreter
                 python_exe = sys.executable
            else:
                 python_exe = sys.executable
            
            # Use Popen to launch independent process
            p = subprocess.Popen([python_exe, script_path], cwd=work_dir)
            self.running_processes.append(p)
                 
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {e}\n\n如果您使用的是打包版，请确保已正确生成。")

    def open_admin_panel(self):
        win = Toplevel(self.root)
        win.title("管理员面板 - 生成学生版")
        win.geometry("700x600")
        
        # Center window
        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f'{width}x{height}+{x}+{y}')
        
        # Container
        canvas = tk.Canvas(win, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", tags="inner_frame_admin")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Canvas resize logic for admin panel
        def on_admin_canvas_resize(event):
            canvas.itemconfig("inner_frame_admin", width=event.width)
        canvas.bind("<Configure>", on_admin_canvas_resize)
        
        # Mousewheel for admin panel
        def on_admin_mousewheel(event):
            if scroll_frame.winfo_height() > canvas.winfo_height():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_admin_mousewheel)
        
        self.limit_entries = {}
        # Existing limits are likely empty if we are in clean Teacher mode
        existing_limits = {} 
        
        tk.Label(scroll_frame, text="请为每个应用设置开放时间范围 (格式: YYYY-MM-DD HH:MM)", font=("bold", 12)).pack(pady=10, padx=10)
        
        apps = sorted(os.listdir(APPS_DIR))
        valid_apps = []
        for app_name in apps:
            app_path = os.path.join(APPS_DIR, app_name)
            if os.path.isdir(app_path):
                valid_apps.append(app_name)

        num_apps = len(valid_apps)
        if num_apps == 1:
            row1_count = 1
            row2_count = 0
        else:
            row1_count = (num_apps + 1) // 2
            row2_count = num_apps - row1_count

        # Create Frames for Rows
        row1_frame = tk.Frame(scroll_frame)
        row1_frame.pack(fill="x", pady=20, expand=True)
        
        if row2_count > 0:
            row2_frame = tk.Frame(scroll_frame)
            row2_frame.pack(fill="x", pady=20, expand=True)
        else:
            row2_frame = None

        # Helper to create setting card
        def create_setting_card(app_name, parent, row, col):
            container = tk.Frame(parent)
            container.grid(row=row, column=col, sticky="nsew", padx=20, pady=10)
            
            frame = tk.LabelFrame(container, text=app_name, padx=10, pady=10, font=("bold", 11))
            frame.pack(fill="both", expand=True)
            
            # Start
            f_start = tk.Frame(frame)
            f_start.pack(fill="x", pady=2)
            tk.Label(f_start, text="开始:", width=5, anchor="w").pack(side="left")
            start_entry = tk.Entry(f_start, width=18)
            start_entry.insert(0, existing_limits.get(app_name, {}).get("start", datetime.now().strftime("%Y-%m-%d %H:%M")))
            start_entry.pack(side="left", padx=5)
            
            # End
            f_end = tk.Frame(frame)
            f_end.pack(fill="x", pady=2)
            tk.Label(f_end, text="结束:", width=5, anchor="w").pack(side="left")
            end_entry = tk.Entry(f_end, width=18)
            end_entry.insert(0, existing_limits.get(app_name, {}).get("end", "2025-12-31 23:59"))
            end_entry.pack(side="left", padx=5)
            
            self.limit_entries[app_name] = (start_entry, end_entry)

        # Populate Row 1
        for i in range(row1_count):
            app_name = valid_apps[i]
            row1_frame.grid_columnconfigure(i, weight=1)
            create_setting_card(app_name, row1_frame, 0, i)

        # Populate Row 2
        if row2_frame:
            for j in range(row1_count):
                row2_frame.grid_columnconfigure(j, weight=1)
            for i in range(row2_count):
                app_idx = row1_count + i
                app_name = valid_apps[app_idx]
                create_setting_card(app_name, row2_frame, 0, i)

        btn_frame = tk.Frame(win, pady=20)
        btn_frame.pack(side="bottom", fill="x")
        
        tk.Button(btn_frame, text="导出学生版 EXE", command=self.do_export_student_exe, 
                  bg="green", fg="white", font=("bold", 14), padx=20, pady=10).pack()

    def do_export_student_exe(self):
        """
        Generates a Student EXE by appending configuration to the current executable (Teacher EXE).
        This does NOT require PyInstaller or Python environment on the user's machine.
        """
        if not getattr(sys, 'frozen', False):
            messagebox.showerror("环境错误", "此功能仅在打包后的 EXE 中可用。\n请先使用 PyInstaller 打包此脚本为教师版 EXE。")
            return

        # 1. Gather limits
        limits = {}
        for app, (s_ent, e_ent) in self.limit_entries.items():
            start_str = s_ent.get().strip()
            end_str = e_ent.get().strip()
            # Simple validation
            try:
                # Try HH:MM first
                try:
                    datetime.strptime(start_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    datetime.strptime(start_str, "%Y-%m-%d")
                    
                try:
                    datetime.strptime(end_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    datetime.strptime(end_str, "%Y-%m-%d")
                    
            except ValueError:
                messagebox.showerror("格式错误", f"应用 {app} 的日期格式不正确 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM)")
                return
                
            limits[app] = {"start": start_str, "end": end_str}
            
        student_data = {"mode": "student", "limits": limits}
        json_bytes = json.dumps(student_data).encode('utf-8')
        
        # 2. Ask where to save
        save_path = filedialog.asksaveasfilename(
            defaultextension=".exe",
            filetypes=[("Executable", "*.exe")],
            initialfile="板式塔课设工具箱_学生版.exe",
            title="保存学生版 EXE"
        )
        
        if not save_path:
            return

        try:
            # 3. Read current EXE content
            current_exe_path = sys.executable
            with open(current_exe_path, 'rb') as f:
                exe_content = f.read()
                
            # Check if current EXE already has overlay
            if OVERLAY_SEPARATOR in exe_content:
                # Strip existing overlay to avoid stacking
                exe_content = exe_content.split(OVERLAY_SEPARATOR)[0]
            
            # 4. Append Config
            with open(save_path, 'wb') as f:
                f.write(exe_content)
                f.write(OVERLAY_SEPARATOR)
                f.write(json_bytes)
                
            messagebox.showinfo("成功", f"学生版 EXE 已成功导出至:\n{save_path}\n\n学生运行该文件时将自动应用时间限制。")
            
            # 5. Close Admin Panel (Wait for window to be destroyed safely)
            # Find the toplevel window that contains the button that called this
            # Since we are in the main app class, we might not have direct reference to 'win' variable here
            # But we can iterate through root's children or just keep track of it.
            # A simpler way: iterate Toplevels
            for widget in self.root.winfo_children():
                if isinstance(widget, Toplevel) and widget.title().startswith("管理员面板"):
                    widget.destroy()
                    break
            
        except Exception as e:
            messagebox.showerror("导出失败", f"无法生成文件:\n{e}")

if __name__ == "__main__":
    # Support for PyInstaller multiprocessing
    import multiprocessing
    multiprocessing.freeze_support()

    # Check if we are running a sub-script (via subprocess from the Launcher)
    if len(sys.argv) > 1 and sys.argv[1].endswith('.py'):
        script_path = sys.argv[1]
        if os.path.exists(script_path):
            # Setup environment
            script_dir = os.path.dirname(os.path.abspath(script_path))
            sys.path.insert(0, script_dir)
            os.chdir(script_dir)
            
            import runpy
            try:
                # Run the script as __main__
                runpy.run_path(script_path, run_name="__main__")
            except Exception as e:
                # Show error if script fails
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    r = tk.Tk()
                    r.withdraw()
                    messagebox.showerror("运行错误", f"无法启动应用:\n{script_path}\n\n{e}")
                    r.destroy()
                except:
                    print(f"Error running script: {e}")
            sys.exit(0)

    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()
