#!/usr/bin/env bash

_scrolllock_led_daemon()
{
    local cur prev words cword
    _init_completion || return

    case $prev in
        --device)
            _filedir
            return
            ;;
        --led)
            _filedir
            return
            ;;
        --key)
            COMPREPLY=($(compgen -W "
                KEY_SCROLLLOCK KEY_CAPSLOCK KEY_NUMLOCK
                KEY_F1 KEY_F2 KEY_F3 KEY_F4 KEY_F5 KEY_F6
                KEY_F7 KEY_F8 KEY_F9 KEY_F10 KEY_F11 KEY_F12
                KEY_PAUSE KEY_POWER KEY_SLEEP KEY_WAKEUP
            " -- "$cur"))
            return
            ;;
        --set)
            COMPREPLY=($(compgen -W "on off" -- "$cur"))
            return
            ;;
        --config)
            _filedir
            return
            ;;
    esac

    if [[ $cur == -* ]]; then
        COMPREPLY=($(compgen -W "
            --device
            --led
            --key
            --set
            --toggle
            --list
            --config
            --verbose
            --version
            --help
        " -- "$cur"))
    fi
} &&
complete -F _scrolllock_led_daemon scrolllock-led-daemon
