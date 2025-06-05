#!/bin/bash

if [ $# -lt 1 ]; then
    echo "You need to specify a action."
    echo "Usage: $0 <cpu|upload|get|reload|remove|upload-hook>"
    exit -1
fi

[ ! -f ".env" ] || export $(grep -v '^#' '.env' | xargs)

username="$PYTHONANYWHERE_USER"
api_key="$PYTHONANYWHERE_API_TOKEN"
auth_header="Authorization: Token $api_key"

host="${PYTHONANYWHERE_HOST:-https://www.pythonanywhere.com/}"
api_host=$host"api"
webhost=$username".pythonanywhere.com"

site_path="${PYTHONANYWHERE_SITE_PATH:-mysite}"
base_path="/home/$username/$site_path"

cpu_info() {
    res=$(curl -s -X GET $api_host"/v0/user/$username/cpu/" \
        -H "$auth_header")
    echo $res | jq -r 'to_entries | .[] | "\(.key) = \(.value)"'
}

get_file() {
    if [ $# -lt 2 ]; then
        echo "You need to specify a file path."
        echo "Usage: $0 $1 <fileName>"
        exit -2
    fi

    file_path=$2
    dirname=$(dirname "$file_path")
    res=$(curl -i -s -X GET $api_host"/v0/user/$username/files/path/$base_path/$file_path" \
        -H "$auth_header" | tr -d '\r')

    headers=$(echo -n "$res" | sed '/^$/q')
    content_type=$(echo -n "$headers" | grep 'Content-Type:' | cut -d ' ' -f2)

    content=$(echo -n "$res" | sed '1,/^$/d')
    if [[ "$content_type" == "application/json" ]]; then
        echo "$content" | jq -r 'if has("detail") then .detail else to_entries | .[] | if .value.type == "directory" then "󰉋 \(.key)" else "󰈔 \(.key)" end end'
        if [ ! $? -eq 0 ]; then
            echo "Unknown response:"
            echo "$content"
        fi
    else
        echo "$content"
        mkdir -p "$dirname"
        echo -n "$content" > "$file_path"
    fi
}

upload_file() {
    if [ $# -lt 2 ]; then
        echo "You need to specify a file path."
        echo "Usage: $0 $1 <fileName>"
        exit -2
    fi

    file_path=$2
    if [[ ! -e "$file_path" ]]; then
        echo "The file '$file_path' doesn't exist."
        exit -3
    fi

    res=$(curl -s -o /dev/null -w "%{http_code}" -X POST $api_host"/v0/user/$username/files/path/$base_path/$file_path" \
        -H "$auth_header" \
        -F "content=@"$file_path)
    if [ "$res" -eq 200 ]; then
        echo "File '$file_path' was updated."
    else
        echo "File '$file_path' was created."
    fi
}

remove_file() {
    if [ $# -lt 2 ]; then
        echo "You need to specify a file path."
        echo "Usage: $0 $1 <fileName>"
        exit -2
    fi

    file_path=$2
    read -n1 -p "Are you sure you want to delete the file '$file_path'? Y/N (N) " answer
    echo
    if [[ "$answer" == 'Y' ]]; then
        resfile=$(mktemp)
        status=$(curl -w "%{http_code}" -o "$resfile" -s -X DELETE $api_host"/v0/user/$username/files/path/$base_path/$file_path" \
            -H "$auth_header")

        if [ "$status" -eq 204 ]; then
            echo "The file '$file_path' was deleted."
        else
            cat "$resfile" | jq -r '"ERROR: \(.message)"'
        fi

        rm "$resfile"
    fi
}

reload_webpage() {
    res=$(curl -s -X POST $api_host"/v0/user/$username/webapps/$webhost/reload/" \
        -H "$auth_header")
    echo $res | jq -r 'if has("status") then "Status: \(.status)" else "Unknown response:\n\(.)" end'
}

set_pre_commit() {
    hook_code="#!/bin/bash
staged_files=\$(git diff --cached --name-only)

for file in \$staged_files; do
    $0 upload "\$file"
done"
    mkdir -p .git/hooks
    echo "$hook_code" >> ".git/hooks/pre-commit"
    chmod +x ".git/hooks/pre-commit"
}

case "$1" in
    cpu)
        cpu_info
        ;;
    get)
        get_file $@
        ;;
    upload)
        upload_file $@
        ;;
    upload-hook)
        set_pre_commit $@
        ;;
    reload)
        reload_webpage $@
        ;;
    remove)
        remove_file $@
        ;;
    *)
        echo "Unknown action '$1'"
        ;;
esac
