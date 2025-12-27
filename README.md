# Linux Systemd Services

Lightweight monitoring and notification services for Linux servers using systemd.

## Services

### watchdog.py

Monitors target server availability via ping and TCP port checks. Alerts via Discord when target is unreachable.

**Features**
- ICMP ping and TCP port checks
- Retry logic with configurable delays
- State tracking across runs
- Alert cooldown to prevent spam
- Recovery notifications

**Required Configuration**

| Variable | Description |
|----------|-------------|
| `TARGET_IP` | IP address of server to monitor |
| `TARGET_NAME` | Display name for target server |
| `SOURCE_NAME` | Display name for monitoring server |
| `TCP_PORTS` | List of TCP ports to check, e.g. `[22, 80]` |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL for alerts |

**Optional Configuration**

| Variable | Default | Description |
|----------|---------|-------------|
| `PING_COUNT` | 3 | Ping packets per attempt |
| `PING_TIMEOUT` | 5 | Ping timeout in seconds |
| `TCP_TIMEOUT` | 5 | TCP connection timeout in seconds |
| `MAX_RETRIES` | 5 | Retry attempts before failure |
| `RETRY_DELAY` | 50 | Seconds between retries |
| `STATE_FILE` | `/var/lib/watchdog/state.json` | State file path |
| `CONSECUTIVE_FAILURES_BEFORE_ALERT` | 2 | Failed runs before alerting |
| `ALERT_COOLDOWN_HOURS` | 2 | Hours between repeat alerts |

**Systemd Files**

`/etc/systemd/system/watchdog.service`
```ini
[Unit]
Description=Watchdog Service
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/watchdog.py

[Install]
WantedBy=timers.target
```

`/etc/systemd/system/watchdog.timer`
```ini
[Unit]
Description=Watchdog Timer

[Timer]
OnBootSec=3min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

---

### plex-updates.sh

Monitors directories for new media files and notifies via Discord. Uses inotify for instant detection.

**Requirements**
```bash
sudo apt install inotify-tools
```

**Required Configuration**

| Variable | Description |
|----------|-------------|
| `WATCH_DIRS` | Array of directories to monitor |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL for notifications |

**Optional Configuration**

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBOUNCE_SECONDS` | 30 | Seconds to ignore duplicate events |

**Systemd File**

`/etc/systemd/system/plex-updates.service`
```ini
[Unit]
Description=Plex Media Updates Watcher
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/plex-updates.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

### monthly-report.py

Generates a monthly server health report and sends it to Discord.

**Report Includes**
- Server uptime and reboot count
- Disk usage (excluding snaps)
- Public IP and SSH port
- System load average
- ZFS pool status
- SMART disk health
- Logged in users
- RAM usage
- Service status checks
- Open connections
- Network throughput

**Required Configuration**

| Variable | Description |
|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL for reports |
| `SERVER_NAME` | Display name for the server |
| `SSH_PORT` | SSH port number |

**Requirements**
```bash
sudo apt install smartmontools
```

**Systemd Files**

`/etc/systemd/system/monthly-report.service`
```ini
[Unit]
Description=Monthly Server Report
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/monthly-report.py

[Install]
WantedBy=timers.target
```

`/etc/systemd/system/monthly-report.timer`
```ini
[Unit]
Description=Monthly Server Report Timer

[Timer]
OnCalendar=*-*-01 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Installation

```bash
sudo cp watchdog.py /usr/local/bin/watchdog.py
sudo cp plex-updates.sh /usr/local/bin/plex-updates.sh
sudo cp monthly-report.py /usr/local/bin/monthly-report.py
sudo chmod +x /usr/local/bin/watchdog.py
sudo chmod +x /usr/local/bin/plex-updates.sh
sudo chmod +x /usr/local/bin/monthly-report.py

sudo cp watchdog.service /etc/systemd/system/
sudo cp watchdog.timer /etc/systemd/system/
sudo cp plex-updates.service /etc/systemd/system/
sudo cp monthly-report.service /etc/systemd/system/
sudo cp monthly-report.timer /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable watchdog.timer
sudo systemctl start watchdog.timer

sudo systemctl enable plex-updates.service
sudo systemctl start plex-updates.service

sudo systemctl enable monthly-report.timer
sudo systemctl start monthly-report.timer
```

## Logs

```bash
journalctl -u watchdog.service -f
journalctl -u plex-updates.service -f
journalctl -u monthly-report.service -f
```

## License

MIT
