#!/usr/bin/env bash

src="$(readlink -f R vlcmd.py)"
ln -s  "$src" ~/bin/vlc_stop
ln -s  "$src" ~/bin/vlc_play