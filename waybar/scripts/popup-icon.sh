#!/bin/bash
if [ -f /tmp/popup_state ] && [ "$(cat /tmp/popup_state)" = "1" ]; then
    echo '{"text": ""}'
else
    echo '{"text": ""}'
fi
