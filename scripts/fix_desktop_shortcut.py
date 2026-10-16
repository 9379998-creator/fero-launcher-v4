import os
import ctypes
import win32com.client

def fix_shortcut():
    sh = win32com.client.Dispatch("WScript.Shell")
    desktop = os.path.expanduser("~/Desktop")
    programs = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs")
    
    repo_root = os.path.abspath(r"C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4")
    vbs_path = os.path.join(repo_root, "run_launcher.vbs")
    ico_path = os.path.join(repo_root, "app", "frontend", "assets", "flauncher.ico")
    
    for folder in [desktop, programs]:
        if not os.path.exists(folder):
            continue
        lnk_path = os.path.join(folder, "F-Engineering Launcher.lnk")
        sc = sh.CreateShortcut(lnk_path)
        sc.TargetPath = r"C:\Windows\System32\wscript.exe"
        sc.Arguments = f'"{vbs_path}"'
        sc.WorkingDirectory = repo_root
        sc.Description = "F.E.R.O. Launcher v4"
        sc.IconLocation = f"{ico_path},0"
        sc.Save()
        
        # Verify
        sc_check = sh.CreateShortcut(lnk_path)
        print(f"Updated shortcut at: {lnk_path}")
        print(f"  Target: {sc_check.TargetPath}")
        print(f"  Args:   {sc_check.Arguments}")
        print(f"  Icon:   {sc_check.IconLocation}")

    # Notify explorer
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    print("Notified Windows shell of icon update.")

if __name__ == "__main__":
    fix_shortcut()
