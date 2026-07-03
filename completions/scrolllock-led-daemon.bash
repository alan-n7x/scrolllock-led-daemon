#!/usr/bin/env bash

_scrolllock_led_daemon()
{
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    case $prev in
        --device)
            COMPREPLY=($(compgen -G "/dev/input/event*" -- "$cur"))
            return 0
            ;;
        --led)
            COMPREPLY=($(compgen -W "scrolllock capslock numlock" -- "$cur"))
            return 0
            ;;
        --key)
            COMPREPLY=($(compgen -W "
                KEY_SCROLLLOCK KEY_CAPSLOCK KEY_NUMLOCK
                KEY_F1 KEY_F2 KEY_F3 KEY_F4 KEY_F5 KEY_F6
                KEY_F7 KEY_F8 KEY_F9 KEY_F10 KEY_F11 KEY_F12
                KEY_PAUSE KEY_POWER KEY_SLEEP KEY_WAKEUP
            " -- "$cur"))
            return 0
            ;;
        --set)
            COMPREPLY=($(compgen -W "on off" -- "$cur"))
            return 0
            ;;
        --config)
            COMPREPLY=($(compgen -f -- "$cur"))
            return 0
            ;;
    esac

    if [[ $cur == -* ]]; then
        local opts="--device --led --key --set --toggle --list --config --verbose --version --help"
        COMPREPLY=($(compgen -W "$opts" -- "$cur"))
        return 0
    fi
} &&
complete -F _scrolllock_led_daemon scrolllock-led-daemon
