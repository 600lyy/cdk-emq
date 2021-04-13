#!/bin/bash
wget https://github.com/emqx/emqx/releases/download/v4.3-rc.3/emqx-ubuntu18.04-4.3-rc.3-amd64.deb
sudo apt install ./emqx-ubuntu18.04-4.3-rc.3-amd64.deb
sudo emqx start