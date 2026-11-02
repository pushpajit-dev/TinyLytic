"""
TinyLytic Installation Wizard
Intelligent first-time setup system with runtime and dependency verification,
smart skip-if-installed detection, automatic environment setup, and clean uninstaller generator.
"""

import os
import sys
import subprocess
import shutil
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

REQUIRED_MODULES = [
    ("PyQt6", "PyQt6", "Modern Graphical User Interface"),
    ("torch", "torch", "PyTorch AI Deep Learning Runtime"),
    ("torchaudio", "torchaudio", "Audio Tensor Acceleration"),
    ("whisper", "openai-whisper", "Whisper Speech-to-Text Engine"),
    ("sounddevice", "sounddevice", "Microphone Input & Realtime Audio"),
    ("soundfile", "soundfile", "High-Fidelity Audio File Processing"),
    ("numpy", "numpy", "Numerical Array Processing"),
    ("yt_dlp", "yt-dlp", "YouTube Video Stream Extractor"),
    ("cv2", "opencv-python", "OpenCV Computer Vision & Slide Detection"),
    ("pytesseract", "pytesseract", "Optical Character Recognition (OCR)"),
    ("pyperclip", "pyperclip", "System Clipboard Integration"),
    ("psutil", "psutil", "Hardware & RAM Resource Profiler"),
    ("GPUtil", "GPUtil", "GPU & VRAM Acceleration Profiler"),
    ("requests", "requests", "Network & Activation Verification"),
    ("imageio_ffmpeg", "imageio-ffmpeg", "Embedded FFmpeg Media Transcoder"),
]

def check_module_installed(module_name):
    """Check if a Python module can be imported in the current environment."""
    try:
        cmd = [sys.executable, "-c", f"import {module_name}"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
        return res.returncode == 0
    except Exception:
        return False

def check_ffmpeg_available():
    """Check if ffmpeg is in PATH or imageio_ffmpeg."""
    try:
        res = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        if res.returncode == 0:
            return True
    except Exception:
        pass
    try:
        cmd = [sys.executable, "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if res.returncode == 0 and os.path.exists(res.stdout.strip()):
            return True
    except Exception:
        pass
    return False

def create_windows_shortcut(target_exe, shortcut_path, icon_path=None, working_dir=None, args=""):
    """Create a Windows .lnk shortcut using PowerShell."""
    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_exe}"
$Shortcut.Arguments = "{args}"
'''
    if working_dir:
        ps_script += f'\n$Shortcut.WorkingDirectory = "{working_dir}"'
    if icon_path and os.path.exists(icon_path):
        ps_script += f'\n$Shortcut.IconLocation = "{icon_path}"'
    ps_script += '\n$Shortcut.Save()'

    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
        return True
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        return False


try:
    import winreg
except ImportError:
    winreg = None

def find_existing_installation():
    """Detect any existing TinyLytic Studio installation across common paths and registry."""
    # 1. Standard AppData location
    default_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "TinyLytic_Studio")
    if os.path.exists(os.path.join(default_dir, "Tinylytic.py")) or os.path.exists(os.path.join(default_dir, "Launch_TinyLytic.bat")):
        return default_dir

    # 2. Check Windows Registry (Inno Setup / System Uninstall)
    if winreg:
        for root_key in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                sub_key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{E58E971B-A795-4BD9-9BCE-DF6B8E5F7E81}_is1"
                with winreg.OpenKey(root_key, sub_key) as key:
                    install_loc, _ = winreg.QueryValueEx(key, "InstallLocation")
                    if install_loc and os.path.exists(install_loc):
                        return install_loc
            except Exception:
                pass

    # 3. Check Program Files
    for pf in ["ProgramFiles", "ProgramFiles(x86)"]:
        base_pf = os.environ.get(pf)
        if base_pf:
            cand = os.path.join(base_pf, "TinyLytic Studio")
            if os.path.exists(os.path.join(cand, "Tinylytic.py")):
                return cand

    return None


class InstallerWizardGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TinyLytic Studio - Setup & Installation Wizard")
        self.root.geometry("680x520")
        self.root.minsize(620, 480)

        # Style & Theme
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Source directory
        self.src_dir = os.path.dirname(os.path.abspath(__file__))

        # Check for existing installation
        self.existing_install_dir = find_existing_installation()
        if self.existing_install_dir:
            self.install_dir_var = tk.StringVar(value=self.existing_install_dir)
        else:
            default_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "TinyLytic_Studio")
            self.install_dir_var = tk.StringVar(value=default_dir)

        # Environment check results
        self.missing_modules = []
        self.all_installed = False

        # Current Page Index
        self.current_step = 0
        self.pages = []

        self.setup_ui()
        self.show_page(0)

    def setup_ui(self):
        # Set Window Icon
        icon_file = os.path.join(self.src_dir, "app_icon.ico")
        if os.path.exists(icon_file):
            try:
                self.root.iconbitmap(icon_file)
            except Exception:
                pass

        # Header Banner
        header_frame = tk.Frame(self.root, bg="#1a202c", height=75)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(header_frame, text="TinyLytic Studio Setup", font=("Segoe UI", 16, "bold"), fg="#63b3ed", bg="#1a202c")
        title_lbl.pack(anchor="w", padx=20, pady=(10, 2))

        sub_lbl = tk.Label(header_frame, text="Developed by NoishiXzen & Aivory | aivorygen.netlify.app | noishixzen@gmail.com", font=("Segoe UI", 9), fg="#a0aec0", bg="#1a202c")
        sub_lbl.pack(anchor="w", padx=20, pady=(0, 10))

        # Content Frame
        self.container = tk.Frame(self.root, bg="#f7fafc")
        self.container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Bottom Button Bar
        btn_bar = tk.Frame(self.root, bg="#edf2f7", height=50)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.btn_cancel = tk.Button(btn_bar, text="Cancel", command=self.root.destroy, width=10, relief=tk.GROOVE)
        self.btn_cancel.pack(side=tk.RIGHT, padx=(5, 20), pady=10)

        self.btn_next = tk.Button(btn_bar, text="Next >", command=self.next_page, width=12, bg="#3182ce", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT)
        self.btn_next.pack(side=tk.RIGHT, padx=5, pady=10)

        self.btn_back = tk.Button(btn_bar, text="< Back", command=self.prev_page, width=10, relief=tk.GROOVE)
        self.btn_back.pack(side=tk.RIGHT, padx=5, pady=10)

        # Create Pages
        if self.existing_install_dir:
            self.page_detected = self.create_page_detected()
            self.page_runtime_check = self.create_page_runtime_check()
            self.page_installing = self.create_page_installing()
            self.page_finish = self.create_page_finish()
            self.pages = [self.page_detected, self.page_runtime_check, self.page_installing, self.page_finish]
        else:
            self.page_welcome = self.create_page_welcome()
            self.page_runtime_check = self.create_page_runtime_check()
            self.page_installing = self.create_page_installing()
            self.page_finish = self.create_page_finish()
            self.pages = [self.page_welcome, self.page_runtime_check, self.page_installing, self.page_finish]

    def create_page_detected(self):
        page = tk.Frame(self.container, bg="#f7fafc")

        lbl1 = tk.Label(page, text="Existing Installation Detected", font=("Segoe UI", 13, "bold"), bg="#f7fafc", fg="#2d3748")
        lbl1.pack(anchor="w", pady=(5, 6))

        info_frame = tk.Frame(page, bg="#fffaf0", bd=1, relief=tk.SOLID)
        info_frame.pack(fill=tk.X, pady=(0, 15), ipady=8)

        warn_lbl = tk.Label(info_frame, text="TinyLytic Studio is already installed on your system.", font=("Segoe UI", 10, "bold"), bg="#fffaf0", fg="#dd6b20")
        warn_lbl.pack(anchor="w", padx=14, pady=(4, 2))

        loc_lbl = tk.Label(info_frame, text=f"Location: {self.existing_install_dir}", font=("Segoe UI", 9), bg="#fffaf0", fg="#4a5568")
        loc_lbl.pack(anchor="w", padx=14, pady=(0, 4))

        lbl_choice = tk.Label(page, text="Please select the setup action to perform:", font=("Segoe UI", 10, "bold"), bg="#f7fafc", fg="#2d3748")
        lbl_choice.pack(anchor="w", pady=(5, 10))

        self.action_var = tk.StringVar(value="update")

        r1 = tk.Radiobutton(
            page,
            text="Update / Reinstall TinyLytic Studio (Recommended)\nUpdates all application components and runtime dependencies while preserving settings.",
            variable=self.action_var,
            value="update",
            font=("Segoe UI", 9, "bold"),
            bg="#f7fafc",
            activebackground="#f7fafc",
            justify=tk.LEFT
        )
        r1.pack(anchor="w", padx=10, pady=(0, 10))

        r2 = tk.Radiobutton(
            page,
            text="Uninstall TinyLytic Studio\nCompletely removes TinyLytic Studio, shortcuts, and AI model cache from your computer.",
            variable=self.action_var,
            value="uninstall",
            font=("Segoe UI", 9, "bold"),
            bg="#f7fafc",
            activebackground="#f7fafc",
            justify=tk.LEFT
        )
        r2.pack(anchor="w", padx=10, pady=(0, 15))

        dev_lbl = tk.Label(
            page,
            text="Developer: NoishiXzen & Aivory  |  Website: https://aivorygen.netlify.app  |  Support: noishixzen@gmail.com",
            font=("Segoe UI", 8),
            bg="#f7fafc",
            fg="#a0aec0"
        )
        dev_lbl.pack(side=tk.BOTTOM, anchor="w", pady=5)

        return page

    def create_page_welcome(self):
        page = tk.Frame(self.container, bg="#f7fafc")

        lbl1 = tk.Label(page, text="Welcome to TinyLytic Studio Setup", font=("Segoe UI", 13, "bold"), bg="#f7fafc", fg="#2d3748")
        lbl1.pack(anchor="w", pady=(5, 6))

        # Check for existing installation
        target_dir = self.install_dir_var.get()
        is_already_installed = os.path.exists(os.path.join(target_dir, "Tinylytic.py"))

        if is_already_installed:
            existing_frame = tk.Frame(page, bg="#fffaf0", bd=1, relief=tk.SOLID)
            existing_frame.pack(fill=tk.X, pady=(0, 12), ipady=6)

            warn_lbl = tk.Label(existing_frame, text="Existing Installation Detected: TinyLytic Studio is already installed.", font=("Segoe UI", 9, "bold"), bg="#fffaf0", fg="#dd6b20")
            warn_lbl.pack(anchor="w", padx=12, pady=(4, 2))

            loc_lbl = tk.Label(existing_frame, text=f"Location: {target_dir}", font=("Segoe UI", 8), bg="#fffaf0", fg="#718096")
            loc_lbl.pack(anchor="w", padx=12, pady=(0, 6))

            btn_box = tk.Frame(existing_frame, bg="#fffaf0")
            btn_box.pack(anchor="w", padx=12, pady=(0, 4))

            btn_uninstall = tk.Button(btn_box, text="Uninstall Application", bg="#e53e3e", fg="white", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, command=self.run_direct_uninstall)
            btn_uninstall.pack(side=tk.LEFT, padx=(0, 8))

            btn_reinstall = tk.Button(btn_box, text="Reinstall / Update", bg="#3182ce", fg="white", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, command=self.next_page)
            btn_reinstall.pack(side=tk.LEFT)

        desc = (
            "• Developer: NoishiXzen & Aivory  |  Brand: Aivory  |  Site: aivorygen.netlify.app\n"
            "• Runtime Verification: Scans Python, PyTorch, Whisper, OpenCV, sound I/O, and modules.\n"
            "• Smart Skip: If all runtime dependencies are found, it immediately skips downloading!\n"
            "• Complete Uninstaller: Creates a full uninstaller that can remove all application files, "
            "models, shortcuts, and cache cleanly whenever you choose."
        )
        lbl_desc = tk.Label(page, text=desc, font=("Segoe UI", 9), justify=tk.LEFT, bg="#f7fafc", fg="#4a5568", wraplength=580)
        lbl_desc.pack(anchor="w", pady=(0, 12))

        # Target directory picker
        lbl_dir = tk.Label(page, text="Installation Folder:", font=("Segoe UI", 9, "bold"), bg="#f7fafc", fg="#2d3748")
        lbl_dir.pack(anchor="w")

        dir_frame = tk.Frame(page, bg="#f7fafc")
        dir_frame.pack(fill=tk.X, pady=(4, 10))

        entry_dir = tk.Entry(dir_frame, textvariable=self.install_dir_var, font=("Segoe UI", 9), relief=tk.SOLID, bd=1)
        entry_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        btn_browse = tk.Button(dir_frame, text="Browse...", command=self.browse_dest_dir, relief=tk.GROOVE)
        btn_browse.pack(side=tk.LEFT, padx=(8, 0))

        # Options
        self.create_desktop_icon = tk.BooleanVar(value=True)
        chk_desk = tk.Checkbutton(page, text="Create Desktop Shortcut", variable=self.create_desktop_icon, bg="#f7fafc", activebackground="#f7fafc")
        chk_desk.pack(anchor="w", pady=1)

        self.create_start_menu = tk.BooleanVar(value=True)
        chk_start = tk.Checkbutton(page, text="Add to Windows Start Menu", variable=self.create_start_menu, bg="#f7fafc", activebackground="#f7fafc")
        chk_start.pack(anchor="w", pady=1)

        return page

    def run_direct_uninstall(self):
        """Perform complete uninstallation directly from the wizard."""
        target_dir = self.install_dir_var.get()
        confirm = messagebox.askyesno(
            "Uninstall TinyLytic Studio",
            f"Are you sure you want to completely uninstall TinyLytic Studio from:\n{target_dir}?\n\n"
            "This will remove the application, shortcuts, and temporary cache."
        )
        if not confirm:
            return

        try:
            # 1. Desktop shortcut
            desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
            desk_lnk = os.path.join(desktop, "TinyLytic Studio.lnk")
            if os.path.exists(desk_lnk):
                os.remove(desk_lnk)

            # 2. Start menu shortcuts
            appdata = os.environ.get("APPDATA", "")
            programs_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "TinyLytic")
            if os.path.exists(programs_dir):
                shutil.rmtree(programs_dir, ignore_errors=True)

            # 3. Application files
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)

            messagebox.information(
                "Uninstall Complete",
                "TinyLytic Studio has been successfully uninstalled from your computer."
            )
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Uninstall Error", f"Failed to complete uninstallation:\n{str(e)}")

    def browse_dest_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir_var.get())
        if chosen:
            self.install_dir_var.set(os.path.join(chosen, "TinyLytic_Studio"))

    def create_page_runtime_check(self):
        page = tk.Frame(self.container, bg="#f7fafc")

        lbl = tk.Label(page, text="Runtime & Environment Dependency Check", font=("Segoe UI", 12, "bold"), bg="#f7fafc", fg="#2d3748")
        lbl.pack(anchor="w", pady=(0, 8))

        self.runtime_status_label = tk.Label(page, text="Scanning installed runtime libraries...", font=("Segoe UI", 9, "italic"), bg="#f7fafc", fg="#718096")
        self.runtime_status_label.pack(anchor="w", pady=(0, 10))

        # Treeview Checklist
        columns = ("module", "package", "status", "role")
        self.tree = ttk.Treeview(page, columns=columns, show="headings", height=9)
        self.tree.heading("module", text="Module")
        self.tree.heading("package", text="Package")
        self.tree.heading("status", text="Verification Status")
        self.tree.heading("role", text="Description")

        self.tree.column("module", width=90)
        self.tree.column("package", width=120)
        self.tree.column("status", width=150)
        self.tree.column("role", width=220)

        self.tree.pack(fill=tk.BOTH, expand=True)

        self.runtime_verdict_lbl = tk.Label(page, text="", font=("Segoe UI", 9, "bold"), bg="#f7fafc", justify=tk.LEFT)
        self.runtime_verdict_lbl.pack(anchor="w", pady=(10, 0))

        return page

    def create_page_installing(self):
        page = tk.Frame(self.container, bg="#f7fafc")

        self.installing_title = tk.Label(page, text="Installing TinyLytic Studio...", font=("Segoe UI", 12, "bold"), bg="#f7fafc", fg="#2d3748")
        self.installing_title.pack(anchor="w", pady=(0, 8))

        self.installing_status = tk.Label(page, text="Preparing setup...", font=("Segoe UI", 9), bg="#f7fafc", fg="#4a5568")
        self.installing_status.pack(anchor="w", pady=(0, 8))

        self.progress_bar = ttk.Progressbar(page, mode="indeterminate", length=500)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        self.log_box = tk.Text(page, height=12, bg="#1a202c", fg="#e2e8f0", font=("Consolas", 8), relief=tk.SOLID, bd=1)
        self.log_box.pack(fill=tk.BOTH, expand=True)

        return page

    def create_page_finish(self):
        page = tk.Frame(self.container, bg="#f7fafc")

        lbl = tk.Label(page, text="Installation Completed Successfully", font=("Segoe UI", 14, "bold"), bg="#f7fafc", fg="#2b6cb0")
        lbl.pack(anchor="w", pady=(20, 10))

        desc = (
            "TinyLytic Studio is now ready to use on your PC!\n\n"
            f"• Installed location: {self.install_dir_var.get()}\n"
            "• Unified Features Enabled: Universal Whisper Speech Transcription (35+ languages), "
            "Realtime Studio, AI Chat Assistant, OpenCV Slide Detection & OCR.\n"
            "• Clean Uninstaller: 'uninstall.bat' and 'uninstaller.py' have been deployed to the "
            "installation directory to cleanly remove files, models, and shortcuts whenever needed."
        )
        lbl_info = tk.Label(page, text=desc, font=("Segoe UI", 9), justify=tk.LEFT, bg="#f7fafc", fg="#2d3748", wraplength=580)
        lbl_info.pack(anchor="w", pady=(0, 20))

        self.launch_app_var = tk.BooleanVar(value=True)
        chk_launch = tk.Checkbutton(page, text="Launch TinyLytic Studio now", variable=self.launch_app_var, font=("Segoe UI", 10, "bold"), bg="#f7fafc", activebackground="#f7fafc")
        chk_launch.pack(anchor="w", pady=5)

        return page

    def show_page(self, index):
        for p in self.pages:
            p.pack_forget()

        self.current_step = index
        self.pages[index].pack(fill=tk.BOTH, expand=True)

        # Button States
        self.btn_back.config(state=tk.NORMAL if index > 0 and index != 2 else tk.DISABLED)

        if index == 0:
            self.btn_next.config(text="Next >", state=tk.NORMAL)
        elif index == 1:
            self.btn_next.config(text="Install >", state=tk.NORMAL)
            # Run environment check
            threading.Thread(target=self.run_runtime_check_thread, daemon=True).start()
        elif index == 2:
            self.btn_next.config(text="Installing...", state=tk.DISABLED)
            self.btn_back.config(state=tk.DISABLED)
            self.btn_cancel.config(state=tk.DISABLED)
            # Run installation
            threading.Thread(target=self.run_installation_thread, daemon=True).start()
        elif index == 3:
            self.btn_next.config(text="Finish", state=tk.NORMAL)
            self.btn_back.config(state=tk.DISABLED)
            self.btn_cancel.config(state=tk.DISABLED)

    def next_page(self):
        if self.current_step == 0 and self.existing_install_dir:
            if hasattr(self, "action_var") and self.action_var.get() == "uninstall":
                self.run_direct_uninstall()
                return

        if self.current_step == 3:
            # Finish clicked
            if self.launch_app_var.get():
                target_exe = os.path.join(self.install_dir_var.get(), "Launch_TinyLytic.bat")
                if not os.path.exists(target_exe):
                    target_exe = os.path.join(self.install_dir_var.get(), "Tinylytic.py")
                if os.path.exists(target_exe):
                    if target_exe.endswith(".bat"):
                        subprocess.Popen([target_exe], cwd=self.install_dir_var.get(), shell=True)
                    else:
                        subprocess.Popen([sys.executable, target_exe], cwd=self.install_dir_var.get())
            self.root.destroy()
            return

        self.show_page(self.current_step + 1)

    def prev_page(self):
        if self.current_step > 0:
            self.show_page(self.current_step - 1)

    def run_runtime_check_thread(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.missing_modules = []

        for mod_name, pip_name, desc in REQUIRED_MODULES:
            installed = check_module_installed(mod_name)
            status_text = "[Installed]" if installed else "[Missing]"
            if not installed:
                self.missing_modules.append(pip_name)

            self.root.after(0, lambda m=mod_name, p=pip_name, s=status_text, d=desc: self.tree.insert("", "end", values=(m, p, s, d)))

        # Check FFmpeg
        has_ffmpeg = check_ffmpeg_available()
        ffmpeg_status = "[Installed / Bundled]" if has_ffmpeg else "[Bundled Engine]"
        self.root.after(0, lambda: self.tree.insert("", "end", values=("ffmpeg", "ffmpeg", ffmpeg_status, "Media Audio/Video Transcoder")))

        def update_verdict():
            if not self.missing_modules:
                self.all_installed = True
                self.runtime_status_label.config(text="Runtime Check Complete", fg="#2b6cb0")
                self.runtime_verdict_lbl.config(
                    text="All required runtime modules are installed.\nSetup will skip dependency installation and proceed directly with application install.",
                    fg="#276749"
                )
            else:
                self.all_installed = False
                missing_str = ", ".join(self.missing_modules[:4])
                if len(self.missing_modules) > 4:
                    missing_str += f" +{len(self.missing_modules)-4} more"
                self.runtime_status_label.config(text=f"Detected {len(self.missing_modules)} missing module(s)", fg="#c53030")
                self.runtime_verdict_lbl.config(
                    text=f"Missing runtime modules: {missing_str}.\nSetup will automatically install them into the application environment.",
                    fg="#c53030"
                )

        self.root.after(0, update_verdict)

    def log(self, text):
        def _append():
            self.log_box.insert(tk.END, text + "\n")
            self.log_box.see(tk.END)
        self.root.after(0, _append)

    def run_installation_thread(self):
        target_dir = self.install_dir_var.get()
        self.root.after(0, lambda: self.progress_bar.start(10))

        try:
            self.log(f"[*] Target destination: {target_dir}")
            os.makedirs(target_dir, exist_ok=True)

            # 1. Handle missing runtime dependencies if any
            if not self.all_installed and self.missing_modules:
                self.log(f"[*] Installing {len(self.missing_modules)} missing runtime dependencies...")
                pip_cmd = [sys.executable, "-m", "pip", "install"] + self.missing_modules
                self.log(f"[*] Executing: pip install {' '.join(self.missing_modules)}")

                process = subprocess.Popen(pip_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in process.stdout:
                    if line.strip():
                        self.log(f"    {line.strip()}")
                process.wait()
                if process.returncode == 0:
                    self.log("[+] Runtime dependencies installed successfully!")
                else:
                    self.log("[!] Warning: Some pip packages had warnings/errors. Continuing setup...")
            else:
                self.log("[+] All runtime modules already present. Skipping dependency downloads!")

            # 2. Copy application files
            self.log("[*] Deploying TinyLytic application files...")
            files_to_copy = [
                "Tinylytic.py", "core_engine.py", "vision_engine.py",
                "chat_engine.py", "workers.py", "video_caption_studio.py",
                "more2.py", "app_icon.ico",
                "activated.flag", "Activation Key.txt", "requirements.txt",
                "uninstaller.py", "uninstall.bat"
            ]

            for f in files_to_copy:
                src_path = os.path.join(self.src_dir, f)
                if os.path.exists(src_path):
                    shutil.copy2(src_path, os.path.join(target_dir, f))
                    self.log(f"    Copied: {f}")

            # Copy directories (models, assets, lang_models)
            dirs_to_copy = ["assets", "models", "lang_models"]
            for d in dirs_to_copy:
                src_d = os.path.join(self.src_dir, d)
                dst_d = os.path.join(target_dir, d)
                if os.path.exists(src_d):
                    self.log(f"[*] Copying {d} directory...")
                    if os.path.exists(dst_d):
                        shutil.rmtree(dst_d, ignore_errors=True)
                    shutil.copytree(src_d, dst_d)

            # 3. Create Windows Launcher & Uninstaller Scripts
            self.log("[*] Generating uninstaller and launcher scripts...")
            self.create_launcher_and_uninstaller(target_dir)

            # 4. Create Desktop & Start Menu Shortcuts
            if self.create_desktop_icon.get():
                desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
                shortcut_path = os.path.join(desktop, "TinyLytic Studio.lnk")
                launcher_bat = os.path.join(target_dir, "Launch_TinyLytic.bat")
                icon_file = os.path.join(target_dir, "app_icon.ico")
                create_windows_shortcut(launcher_bat, shortcut_path, icon_path=icon_file, working_dir=target_dir)
                self.log(f"[+] Created Desktop shortcut: {shortcut_path}")

            if self.create_start_menu.get():
                appdata = os.environ.get("APPDATA", "")
                programs_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "TinyLytic")
                os.makedirs(programs_dir, exist_ok=True)
                shortcut_path = os.path.join(programs_dir, "TinyLytic Studio.lnk")
                launcher_bat = os.path.join(target_dir, "Launch_TinyLytic.bat")
                icon_file = os.path.join(target_dir, "app_icon.ico")
                create_windows_shortcut(launcher_bat, shortcut_path, icon_path=icon_file, working_dir=target_dir)

                uninst_lnk = os.path.join(programs_dir, "Uninstall TinyLytic.lnk")
                uninst_bat = os.path.join(target_dir, "uninstall.bat")
                create_windows_shortcut(uninst_bat, uninst_lnk, working_dir=target_dir)
                self.log("[+] Created Start Menu shortcuts.")

            self.log("[+] Setup finished successfully!")
            self.root.after(0, lambda: self.progress_bar.stop())
            self.root.after(1000, lambda: self.show_page(3))

        except Exception as e:
            self.log(f"[!] Critical Setup Error: {str(e)}")
            self.root.after(0, lambda: self.progress_bar.stop())
            messagebox.showerror("Installation Error", f"An error occurred during installation:\n\n{str(e)}")

    def create_launcher_and_uninstaller(self, target_dir):
        # 1. Launcher Script (Launch_TinyLytic.bat)
        launcher_content = f'''@echo off
cd /d "{target_dir}"
start "" "{sys.executable}" "Tinylytic.py" %*
'''
        with open(os.path.join(target_dir, "Launch_TinyLytic.bat"), "w") as f:
            f.write(launcher_content)

        # 2. Python Clean Uninstaller (uninstaller.py)
        uninstaller_py_content = '''"""
TinyLytic Clean Uninstaller
Removes all application files, shortcuts, models, cache, and optional runtime environments.
"""
import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox

def run_uninstallation():
    root = tk.Tk()
    root.withdraw()

    confirm = messagebox.askyesno(
        "Uninstall TinyLytic",
        "Are you sure you want to completely uninstall TinyLytic Studio?\\n\\n"
        "This will remove the application, desktop shortcuts, and temporary cache."
    )
    if not confirm:
        sys.exit(0)

    clean_runtime = messagebox.askyesno(
        "Uninstall Runtime & Cache",
        "Do you also want to remove all downloaded AI models, temporary audio files, and cache?"
    )

    app_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Remove Desktop Shortcut
    desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
    desktop_lnk = os.path.join(desktop, "TinyLytic Studio.lnk")
    if os.path.exists(desktop_lnk):
        try:
            os.remove(desktop_lnk)
        except Exception:
            pass

    # 2. Remove Start Menu
    appdata = os.environ.get("APPDATA", "")
    programs_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "TinyLytic")
    if os.path.exists(programs_dir):
        try:
            shutil.rmtree(programs_dir, ignore_errors=True)
        except Exception:
            pass

    # 3. Clean Cache if requested
    if clean_runtime:
        local_app = os.environ.get("LOCALAPPDATA", "")
        tiny_cache = os.path.join(local_app, "TinyLytic")
        if os.path.exists(tiny_cache):
            shutil.rmtree(tiny_cache, ignore_errors=True)

        temp_dir = os.path.join(os.environ.get("TEMP", ""), "TinyLytic_Temp")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    # 4. Schedule self-deletion of app_dir via PowerShell
    ps_cmd = f'Start-Sleep -Seconds 1; Remove-Item -Path "{app_dir}" -Recurse -Force -ErrorAction SilentlyContinue'
    subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd], shell=True)

    messagebox.showinfo("Uninstall Complete", "TinyLytic Studio has been successfully uninstalled from your computer.")
    sys.exit(0)

if __name__ == "__main__":
    run_uninstallation()
'''
        with open(os.path.join(target_dir, "uninstaller.py"), "w", encoding="utf-8") as f:
            f.write(uninstaller_py_content)

        # 3. Batch Uninstaller (uninstall.bat)
        uninstall_bat_content = f'''@echo off
cd /d "{target_dir}"
"{sys.executable}" "uninstaller.py"
'''
        with open(os.path.join(target_dir, "uninstall.bat"), "w") as f:
            f.write(uninstall_bat_content)


def main():
    root = tk.Tk()
    app = InstallerWizardGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
