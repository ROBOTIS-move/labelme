#!/bin/bash

sudo apt-get install -y curl

curl -L https://github.com/wkentaro/dotfiles/raw/main/local/bin/install_anaconda3.sh | bash -s .
source .anaconda3/bin/activate
pip install -e .

labelme_path=(`pwd`)
echo "" >> ~/.bashrc
echo "# labelme" >> ~/.bashrc
echo "alias labelme='cd $labelme_path && labelme'" >> ~/.bashrc
echo "alias labelme-cli='cd $labelme_path && cd labelme/cli'" >> ~/.bashrc
source ~/.bashrc
