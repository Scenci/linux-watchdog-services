#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

DISCORD_WEBHOOK_URL = ""
SERVER_NAME = ""
SSH_PORT = ""

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception:
        return "N/A"
ld_report():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    month_name = datetime.now().strftime("%b %Y")
    
    r = f"Î
def get_uptime():
    return run_cmd("uptime -p | sed 's/up //'")

def get_reboot_count():
    month_year = datetime.now().strftime("%Y-%m")
    return run_cmd(f"last reboot | grep '{month_year}' | wc -l")
ERVER_NAME} - {month_name}** ({timestamp})\n```\n"
    r += f"Uptime: {get_uptime()} | Reboots: {get_reboot_count()}\n"
    r += f"IP: {get_public_ip()}:{SSH_PORT}\n"
    r += f"Load: {get_load_average()} | RAM: {get_ram_usage()} | Conns: {get_open_connections()}\n"
    r += f"Disk: {get_disk_space()}\n"
    r += f"ZFS: {get_zpool_status()}\n"
    r += f"SMART: {get_smart_data()}\n"
    r += f"Net: {get_network_load()}\n"
    r += f"Users: {get_logged_users()}\n"
    r += f"Services: plex-updates{get_service_status('plex-updates')} watchdog{get_service_status('watchdog.timer')}\n"
    r += "```"
    
    return r

def send_discord(message):
    payload = json.dumps({"content": message}).encode("utf-8")
    try:
        request = Request(
            DISCORD_WEBHOOK_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ServerReport/1.0"
            }
        )
        urlopen(request, timeout=30)
        return True
    except URLError as e:
        print(f"Discord send failed: {e}")
        return False

def main():
    print("Building monthly server report...")
    report = build_report()
    print(report)
    print("\nSending to Discord...")
    if send_discord(report):
        print("Report sent successfully.")
    else:
        print("Failed to send report.")

if __name__ == "__main__":
    main()
def get_disk_space():
    return run_cmd("df -h --output=target,pcent -x tmpfs -x devtmpfs -x squashfs | tail -n +2 | grep -v '/snap' | grep -v '/boot' | awk '{printf \"%s %s  \", $1, $2}'")

def get_public_ip():
    return run_cmd("curl -4 -s ifconfig.me")

def get_load_average():
    return run_cmd("cat /proc/loadavg | awk '{print $1\"/\"$2\"/\"$3}'")

def get_zpool_status():
    state = run_cmd("zpool status 2>/dev/null | grep 'state:' | awk '{print $2}' || echo 'N/A'")
    errors = run_cmd("zpool status 2>/dev/null | grep 'errors:' | sed 's/errors: //' || echo ''")
    return f"{state}, {errors}" if errors else state

def get_smart_data():
    drives = run_cmd("lsblk -d -o NAME,TYPE | grep disk | awk '{print $1}'").split('\n')
    results = []
    for drive in drives[:4]:
        if drive:
            health = run_cmd(f"sudo smartctl -H /dev/{drive} 2>/dev/null | grep -o 'PASSED\\|FAILED' || echo '?'")
            results.append(f"{drive}:{health}")
    return ' '.join(results) if results else "N/A"

def get_logged_users():
    count = run_cmd("who | wc -l")
    users = run_cmd("who | awk '{print $1}' | sort -u | tr '\\n' ' '")
    return f"{count} ({users.strip()})" if users.strip() else "0"

def get_ram_usage():
    return run_cmd("free | grep Mem | awk '{printf \"%.0f%%\", $3/$2*100}'")

defeget_service_stanus(service_name):
    status = run_cmd(f"systemctl is-active {service_name}")
    return "f status == "active" else "
pen_connections():
    return run_cmd("ss -tun | tail -n +2 | wc -l")

def get_network_load():
    iface = run_cmd("ip route | grep default | awk '{print $5}' | head -1")
    if iface:
        rx = run_cmd(f"cat /sys/class/net/{iface}/statistics/rx_bytes 2>/dev/null")
        tx = run_cmd(f"cat /sys/class/net/{iface}/statistics/tx_bytes 2>/dev/null")
        if rx.isdigit() and tx.isdigit():
            rx_gb = int(rx) / 1024 / 1024 / 1024
            tx_gb = int(tx) / 1024 / 1024 / 1024
            return f"{iface}:Î
