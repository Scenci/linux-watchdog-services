#!/bin/bash

WATCH_DIRS=(
    "/storage-primary/media/movies"
    "/storage-primary/media/tvshows"
)

DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL"

BATCH_WINDOW_SECONDS=60
STATE_DIR="/tmp/plex-watcher-state"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

get_content_name() {
    local file_path="$1"
    
    if [[ "$file_path" == *"/movies/"* ]]; then
        echo "$file_path" | sed 's|.*/movies/||' | cut -d'/' -f1
    elif [[ "$file_path" == *"/tvshows/"* ]]; then
        echo "$file_path" | sed 's|.*/tvshows/||' | cut -d'/' -f1
    else
        basename "$file_path"
    fi
}

get_season_info() {
    local file_path="$1"
    local season=""
    
    if [[ "$file_path" =~ [Ss]eason[[:space:]]*([0-9]+) ]]; then
        season="${BASH_REMATCH[1]}"
    elif [[ "$file_path" =~ [Ss]([0-9]+)[Ee][0-9]+ ]]; then
        season="${BASH_REMATCH[1]}"
    fi
    
    if [[ -n "$season" ]]; then
        echo "$((10#$season))"
    else
        echo ""
    fi
}

get_episode_info() {
    local file_path="$1"
    local filename
    filename=$(basename "$file_path")
    local episode=""
    
    if [[ "$filename" =~ [Ss][0-9]+[Ee]([0-9]+) ]]; then
        episode="${BASH_REMATCH[1]}"
    elif [[ "$filename" =~ [^0-9]([0-9]{2})[^0-9] ]]; then
        episode="${BASH_REMATCH[1]}"
    fi
    
    if [[ -n "$episode" ]]; then
        echo "$((10#$episode))"
    else
        echo ""
    fi
}

get_file_details() {
    local file_path="$1"
    local season episode filename
    
    season=$(get_season_info "$file_path")
    episode=$(get_episode_info "$file_path")
    filename=$(basename "$file_path")
    
    if [[ -n "$season" && -n "$episode" ]]; then
        echo "S${season}E${episode}"
    elif [[ -n "$season" ]]; then
        echo "Season ${season}"
    elif [[ -d "$file_path" ]]; then
        basename "$file_path"
    else
        echo "${filename%.*}"
    fi
}

get_state_file() {
    local content_key="$1"
    echo "${STATE_DIR}/$(echo "$content_key" | sed 's/[^a-zA-Z0-9._-]/_/g')"
}

send_discord_notification() {
    local media_type="$1"
    local content_name="$2"
    local state_file="$3"
    
    local emoji
    if [[ "$media_type" == "Movie" ]]; then
        emoji="🎬"
    else
        emoji="📺"
    fi
    
    local details_array=()
    while IFS= read -r line; do
        details_array+=("$line")
    done < <(tail -n +3 "$state_file")
    
    local count=${#details_array[@]}
    
    if [[ $count -eq 0 ]]; then
        log "No details found in state file, skipping notification"
        return
    fi
    
    local message
    if [[ $count -eq 1 ]]; then
        message="${emoji} **New ${media_type} Added**\\n**${content_name}**\\n└ ${details_array[0]}"
    elif [[ $count -le 5 ]]; then
        message="${emoji} **New ${media_type} Content Added**\\n**${content_name}**"
        for detail in "${details_array[@]}"; do
            message+="\\n└ ${detail}"
        done
    else
        local seasons=()
        for detail in "${details_array[@]}"; do
            if [[ "$detail" =~ ^S([0-9]+)E ]]; then
                seasons+=("${BASH_REMATCH[1]}")
            fi
        done
        
        local unique_seasons
        unique_seasons=$(printf '%s\n' "${seasons[@]}" | sort -nu | tr '\n' ',' | sed 's/,$//')
        
        if [[ -n "$unique_seasons" ]]; then
            message="${emoji} **New ${media_type} Content Added**\\n**${content_name}**\\n└ ${count} episodes added (Season ${unique_seasons})"
        else
            message="${emoji} **New ${media_type} Content Added**\\n**${content_name}**\\n└ ${count} items added"
        fi
    fi
    
    log "Sending to Discord: $content_name ($count items)"
    
    local response
    response=$(curl -s -w "\n%{http_code}" -H "Content-Type: application/json" \
         -X POST \
         -d "{\"content\": \"${message}\"}" \
         "$DISCORD_WEBHOOK_URL" 2>&1)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | head -n -1)
    
    if [[ "$http_code" == "204" || "$http_code" == "200" ]]; then
        log "Discord notification sent successfully for: $content_name"
    else
        log "Discord notification failed (HTTP $http_code): $body"
    fi
    
    rm -f "$state_file"
}

schedule_flush() {
    local content_key="$1"
    local state_file="$2"
    
    (
        sleep "$BATCH_WINDOW_SECONDS"
        
        if [[ -f "$state_file" ]]; then
            local media_type content_name
            media_type=$(sed -n '1p' "$state_file")
            content_name=$(sed -n '2p' "$state_file")
            
            send_discord_notification "$media_type" "$content_name" "$state_file"
        fi
    ) &
    
    log "Scheduled flush for '$content_key' in ${BATCH_WINDOW_SECONDS}s (PID: $!)"
}

queue_notification() {
    local file_path="$1"
    
    local media_type="Media"
    if [[ "$file_path" == *"/movies/"* ]]; then
        media_type="Movie"
    elif [[ "$file_path" == *"/tvshows/"* ]]; then
        media_type="TV Show"
    fi
    
    local content_name content_key details state_file
    content_name=$(get_content_name "$file_path")
    content_key="${media_type}:${content_name}"
    details=$(get_file_details "$file_path")
    state_file=$(get_state_file "$content_key")
    
    if [[ -f "$state_file" ]]; then
        if grep -qxF "$details" "$state_file"; then
            log "Skipped duplicate: $content_name - $details"
        else
            echo "$details" >> "$state_file"
            log "Batched: $content_name - $details"
        fi
    else
        echo "$media_type" > "$state_file"
        echo "$content_name" >> "$state_file"
        echo "$details" >> "$state_file"
        log "Queued: $content_name - $details (waiting ${BATCH_WINDOW_SECONDS}s for more)"
        
        schedule_flush "$content_key" "$state_file"
    fi
}

log "=== Plex Updates Watcher starting ==="
log "Watching directories:"
for dir in "${WATCH_DIRS[@]}"; do
    log "  - $dir"
done
log "Batch window: ${BATCH_WINDOW_SECONDS}s"

mkdir -p "$STATE_DIR"
rm -f "$STATE_DIR"/* 2>/dev/null

for dir in "${WATCH_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        log "WARNING: Directory does not exist: $dir"
    fi
done

cleanup() {
    log "Shutting down..."
    rm -rf "$STATE_DIR"
    exit 0
}
trap cleanup SIGINT SIGTERM

inotifywait -m -r -q \
    --format '%w%f|%e' \
    -e create \
    -e moved_to \
    "${WATCH_DIRS[@]}" | while read -r line; do

    file_path=$(echo "$line" | cut -d'|' -f1)
    event=$(echo "$line" | cut -d'|' -f2)

    log "Event detected: $event on $file_path"

    if [[ -d "$file_path" ]] || [[ "$file_path" =~ \.(mkv|mp4|avi|mov|m4v|wmv)$ ]]; then
        queue_notification "$file_path"
    else
        log "Skipped (not a directory or video file): $file_path"
    fi
done

cleanup