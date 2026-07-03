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
        --set)
            COMPREPLY=($(compgen -W "on off" -- "$cur"))
            return
            ;;
    esac

    if [[ $cur == -* ]]; then
        COMPREPLY=($(compgen -W "
            --device
            --led
            --set
            --toggle
            --verbose
            --version
            --help
        " -- "$cur"))
    fi
} &&
complete -F _scrolllock_led_daemon scrolllock-led-daemon
