"""
TinyLytic Studio Clean Uninstaller
Developed by: NoishiXzen & Aivory
Website: https://aivorygen.netlify.app | Contact: noishixzen@gmail.com
"""

import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

def run_uninstallation():
    root = tk.Tk()
    root.title("TinyLytic Studio - Uninstaller")
    root.geometry("540x360")
    root.resizable(False, False)

    # Styling
    style = ttk.Style()
    style.theme_use("clam")

    app_dir = os.path.dirname(os.path.abspath(__file__))
    icon_file = os.path.join(app_dir, "app_icon.ico")
    if os.path.exists(icon_file):
        try:
            root.iconbitmap(icon_file)
        except Exception:
            pass

    # Header
    header = tk.Frame(root, bg="#1a202c", height=70)
    header.pack(fill=tk.X, side=tk.TOP)

    title_lbl = tk.Label(header, text="Uninstall TinyLytic Studio", font=("Segoe UI", 14, "bold"), fg="#fc8181", bg="#1a202c")
    title_lbl.pack(anchor="w", padx=20, pady=(12, 2))

    sub_lbl = tk.Label(header, text="NoishiXzen & Aivory | aivorygen.netlify.app | noishixzen@gmail.com", font=("Segoe UI", 8), fg="#a0aec0", bg="#1a202c")
    sub_lbl.pack(anchor="w", padx=20, pady=(0, 10))

    # Body
    body = tk.Frame(root, bg="#f7fafc", padx=20, pady=15)
    body.pack(fill=tk.BOTH, expand=True)

    warn_lbl = tk.Label(
        body,
        text="Are you sure you want to completely uninstall TinyLytic Studio?\n\n"
             "This will remove all application files, desktop shortcuts, and Start Menu entries.",
        font=("Segoe UI", 9),
        bg="#f7fafc",
        fg="#2d3748",
        justify=tk.LEFT,
        wraplength=490
    )
    warn_lbl.pack(anchor="w", pady=(5, 12))

    loc_lbl = tk.Label(body, text=f"Installed at: {app_dir}", font=("Segoe UI", 8), bg="#f7fafc", fg="#718096")
    loc_lbl.pack(anchor="w", pady=(0, 12))

    remove_cache_var = tk.BooleanVar(value=True)
    chk_cache = tk.Checkbutton(
        body,
        text="Also remove downloaded Whisper AI models, temporary audio files, and cache",
        variable=remove_cache_var,
        bg="#f7fafc",
        font=("Segoe UI", 9)
    )
    chk_cache.pack(anchor="w", pady=(0, 15))

    status_lbl = tk.Label(body, text="", font=("Segoe UI", 9, "bold"), bg="#f7fafc", fg="#c53030")
    status_lbl.pack(anchor="w")

    # Bottom Buttons
    btn_bar = tk.Frame(root, bg="#edf2f7", height=50)
    btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def do_uninstall():
        status_lbl.config(text="Removing application shortcuts and files...", fg="#2b6cb0")
        root.update()

        try:
            # 1. Desktop shortcut
            desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
            desk_lnk = os.path.join(desktop, "TinyLytic Studio.lnk")
            if os.path.exists(desk_lnk):
                try:
                    os.remove(desk_lnk)
                except Exception:
                    pass

            # 2. Start menu shortcuts
            appdata = os.environ.get("APPDATA", "")
            programs_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "TinyLytic")
            if os.path.exists(programs_dir):
                try:
                    shutil.rmtree(programs_dir, ignore_errors=True)
                except Exception:
                    pass

            # 3. Cache & Models if selected
            if remove_cache_var.get():
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

            messagebox.showinfo(
                "Uninstall Complete",
                "TinyLytic Studio has been successfully uninstalled from your computer."
            )
            root.destroy()
            sys.exit(0)

        except Exception as e:
            messagebox.showerror("Uninstall Error", f"An error occurred during uninstallation:\n\n{str(e)}")

    btn_cancel = tk.Button(btn_bar, text="Cancel", command=root.destroy, width=10, relief=tk.GROOVE)
    btn_cancel.pack(side=tk.RIGHT, padx=(5, 20), pady=10)

    btn_uninstall = tk.Button(btn_bar, text="Uninstall Application", bg="#e53e3e", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, command=do_uninstall)
    btn_uninstall.pack(side=tk.RIGHT, padx=5, pady=10)

    root.mainloop()

if __name__ == "__main__":
    run_uninstallation()
