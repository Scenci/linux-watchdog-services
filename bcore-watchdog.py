#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import socket
import json
import sys
import time
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError
from pathlib import Path

TARGET_IP = ""
TARGET_NAME = ""
SOURCE_NAME = ""

PING_COUNT = 3
PING_TIMEOUT = 5
TCP_PORTS = []
TCP_TIMEOUT = 5

MAX_RETRIES = 5
RETRY_DELAY = 50

STATE_FILE = Path("/var/lib/watchdog/state.json")
CONSECUTIVE_FAILURES_BEFORE_ALERT = 2

ALERT_COOLDOWN_HOURS = 2

DISCORD_WEBHOOK_URL = ""


def check_ping(ip):
    try:
        result = subprocess.run(
            ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT), ip],
            capture_output=True,
            timeout=PING_TIMEOUT * PING_COUNT + 10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception) as e:
        log(f"Ping exception: {e}")
        return False

GET_NAME} is back UP**\n"
        f"```\n"
        f"Source: {SOURCE_NAME} Watchdog\n"
        f"Target: {TARGET_IP}\n"
        f"Time:   {timestamp}\n"
        f"```"
    )


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def run_check_with_retries():
    last_reason = "Unknown"
    for attempt in range(1, MAX_RETRIES + 1):
        log(f"Check attempt {attempt}/{MAX_RETRIES}")
        results = perform_all_checks(TARGET_IP)
        is_healthy, reason = evaluate_health(results)
        last_reason = reason
        if is_healthy:
            log(f"SUCCESS: {reason}")
            return True, reason
        log(f"FAILED: {reason}")
        if attempt < MAX_RETRIES:
            log(f"Waiting {RETRY_DELAY}s before retry...")
            time.sleep(RETRY_DELAY)
    return False, last_reason


def main():
    log(f"=== Watchdog starting ===")
    log(f"Target: {TARGET_NAME} ({TARGET_IP})")
    
    state = load_state()
    previous_status = state.get("last_status")
    
    is_healthy, reason = run_check_with_retries()
    
    state["last_check_time"] = datetime.now().isoformat()
    state["last_status"] = "healthy" if is_healthy else "unhealthy"
    
    if is_healthy:
        if previous_status == "unhealthy" and state["consecutive_failures"] >= CONSECUTIVE_FAILURES_BEFORE_ALERT:
            log("Target recovered! Sending recovery notification.")
            send_discord_alert(format_recovery_message())
        state["consecutive_failures"] = 0
        save_state(state)
        log("=== Check complete: HEALTHY ===")
        sys.exit(0)
    else:
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        log(f"Consecutive failed runs: {state['consecutive_failures']}")
        
        should_alert = (
            state["consecutive_failures"] >= CONSECUTIVE_FAILURES_BEFORE_ALERT
            and not is_in_cooldown(state)
        )
        
        if should_alert:
            log("Threshold reached, sending alert...")
            alert_msg = format_alert_message(reason, state["consecutive_failures"])
            if send_discord_alert(alert_msg):
                state["last_alert_time"] = datetime.now().isoformat()
                log("Alert sent successfully.")
            else:
                log("Alert failed to send!")
        elif is_in_cooldown(state):
            log(f"In cooldown period (last alert: {state['last_alert_time']}). Skipping alert.")
        else:
            log(f"Not yet at alert threshold ({state['consecutive_failures']}/{CONSECUTIVE_FAILURES_BEFORE_ALERT})")
        
        save_state(state)
        log("=== Check complete: UNHEALTHY ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
def check_tcp_port(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TCP_TIMEOUT)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception as e:
        log(f"TCP check exception on port {port}: {e}")
        return False


def perform_all_checks(ip):
    results = {
        "ping": check_ping(ip),
        "tcp_ports": {}
    }
    for port in TCP_PORTS:
        results["tcp_ports"][port] = check_tcp_port(ip, port)
    return results


def evaluate_health(results):
    ping_ok = results["ping"]
    any_tcp_ok = any(results["tcp_ports"].values()) if results["tcp_ports"] else False
    
    if ping_ok and any_tcp_ok:
        return True, "All checks passed"
    elif ping_ok:
        return True, "Ping OK (TCP ports unresponsive)"
    elif any_tcp_ok:
        return True, "TCP OK (ping unresponsive)"
    else:
        failed_ports = [str(p) for p, ok in results["tcp_ports"].items() if not ok]
        return False, f"All checks failed (ping: FAIL, TCP ports {', '.join(failed_ports)}: FAIL)"


def load_state():
    default_state = {
        "consecutive_failures": 0,
        "last_alert_time": None,
        "last_check_time": None,
        "last_status": None
    }
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        log(f"Error loading state: {e}")
    return default_state


def save_state(state):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving state: {e}")


def is_in_cooldown(state):
    if not state.get("last_alert_time"):
        return False
    try:
        last_alert = datetime.fromisoformat(state["last_alert_time"])
        cooldown_end = last_alert + timedelta(hours=ALERT_COOLDOWN_HOURS)
        return datetime.now() < cooldown_end
    except Exception:
        return False


def send_discord_alert(message):
    payload = json.dumps({"content": message}).encode("utf-8")
    try:
        request = Request(
            DISCORD_WEBHOOK_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Watchdog/1.0"
            }
        )
        urlopen(request, timeout=30)
        return True
    except URLError as e:
        log(f"Discord alert failed: {e}")
        return False

GET_NAME} MAY BE DOWN**\n"
        f"```\n"
        f"Source:      {SOURCE_NAME} Watchdog\n"
        f"Target:      {TARGET_IP}\n"
        f"Reason:      {reason}\n"
        f"Failed runs: {consecutive_failures} consecutive\n"
        f"Time:        {timestamp}\n"
        f"```"
    )


def format_recovery_message():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Î
def format_alert_message(reason, consecutive_failures):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Î
