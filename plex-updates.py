#!/bin/bash

WATCH_DIRS=(
    ""
    ""
)

DISCORD_WEBHOOK_URL=""

DEBOUNCE_SECONDS=30

declare -A LAST_NOTIFIED

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

send_discord_notification() {
    local event_type="$1"
    local file_path="$2"
    
    local media_type="Media"
    if [[ "$file_path" == *"/movies/"* ]]; then
        media_type="Movie"
        emoji="f [[ "$file_path" == *"/tvshows/"* ]]; then
        media_type="TV Show"
        emoji="нн
cal content_name
    if [[ "$media_type" == "Movie" ]]; then
        content_name=$(echo "$file_path" | sed 's|.*/movies/||' | cut -d'/' -f1)
    else
        content_name=$(echo "$file_path" | sed 's|.*/tvshows/||' | cut -d'/' -f1)
    fi
    
    local message="${emoji} **New ${media_type} Added**\\n${content_name}"
    
    curl -s -H "Content-Type: application/json" \
         -H "User-Agent: PlexUpdates/1.0" \
         -X POST \
         -d "{\"content\": \"${message}\"}" \
         "$DISCORD_WEBHOOK_URL" > /dev/null 2>&1
    
    log "Discord notification sent: $content_name"
}

should_notify() {
    local path="$1"
    local now
    now=$(date +%s)
    
    local content_key
    if [[ "$path" == *"/movies/"* ]]; then
        content_key=$(echo "$path" | sed 's|.*/movies/||' | cut -d'/' -f1)
    elif [[ "$path" == *"/tvshows/"* ]]; then
        content_key=$(echo "$path" | sed 's|.*/tvshows/||' | cut -d'/' -f1)
    else
        content_key="$path"
    fi
    
    local last_time="${LAST_NOTIFIED[$content_key]:-0}"
    local diff=$((now - last_time))
    
    if [[ $diff -lt $DEBOUNCE_SECONDS ]]; then
        log "Debounced: $content_key (${diff}s since last notification)"
        return 1
    fi
    
    LAST_NOTIFIED[$content_key]=$now
    return 0
}

log "=== Plex Updates Watcher starting ==="
log "Watching directories:"
for dir in "${WATCH_DIRS[@]}"; do
    log "  - $dir"
done

for dir in "${WATCH_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        log "WARNING: Directory does not exist: $dir"
    fi
done

inotifywait -m -r -q \
    --format '%w%f|%e' \
    -e create \
    -e moved_to \
    "${WATCH_DIRS[@]}" | while read -r line; do
    
    file_path=$(echo "$line" | cut -d'|' -f1)
    event=$(echo "$line" | cut -d'|' -f2)
    
    log "Event detected: $event on $file_path"
    
    if [[ -d "$file_path" ]] || [[ "$file_path" =~ \.(mkv|mp4|avi|mov|m4v|wmv)$ ]]; then
        if should_notify "$file_path"; then
            send_discord_notification "$event" "$file_path"
        fi
    fi
done
