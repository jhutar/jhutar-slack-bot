#!/bin/sh

# dnf install python3-wordcloud

for text_file in $( ls messages-*.txt ); do
    user=$( echo $text_file | sed 's/messages-\(U[0-9A-Z]\+\).txt/\1/' )
    rm -f wordcloud-$user.png
    wordcloud_cli --text messages-$user.txt --imagefile wordcloud-$user.png
done
