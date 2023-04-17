#!/bin/bash

host=${1:-jhutar-slack-bot-route-jenkins-csb-perf.apps.ocp.example.com}

page=1
while true; do
    url="http://$host/api/messages?page=$page"
    content="$( curl --silent "$url" )"
    count=$( echo "$content" | jq '.items | length' )
    if [ "0$count" -gt 0 ]; then
        echo "INFO On page $page processing $count messages"
    else
        echo "INFO All done"
        break
    fi
    users=$( echo "$content" | jq --raw-output .items[].user )
    for user in $users; do
        echo "DEBUG Processing messages from user $user"
        echo "$content" | jq --raw-output -c ".items[] | select(.user | contains(\"$user\")).message" >> messages-$user.txt
    done
    let page+=1
done
