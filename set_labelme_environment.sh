#!/bin/bash

sudo apt-get install -y curl

INSTALL_DIR=$(pwd)

if [ -e $INSTALL_DIR/.anaconda3 ]; then
  echo "Anaconda3 is already installed: $INSTALL_DIR/.anaconda3"
  exit 0
fi

TMPDIR=$(mktemp -d)
cd $TMPDIR

if [ "$(uname)" = "Linux" ]; then
  wget -q 'https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh' -O miniconda2.sh
elif [ "$(uname)" = "Darwin" ]; then
  wget -q 'https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh' -O miniconda2.sh
else
  echo "[$(basename $0)] Unsupported platform: $(uname)"
  exit 0
fi

bash ./miniconda2.sh -p $INSTALL_DIR/.anaconda3 -b
cd -
rm -rf $TMPDIR

source $INSTALL_DIR/.anaconda3/bin/activate
conda update -n base -y conda
conda install -n base -y pip  # pip is uninstalled when conda is updated
source $INSTALL_DIR/.anaconda3/bin/deactivate

source .anaconda3/bin/activate
pip install -e .

pip install lxml

labelme_path=(`pwd`)
echo "" >> ~/.bashrc
echo "# labelme" >> ~/.bashrc
echo "alias labelme='cd $labelme_path && source .anaconda3/bin/activate && labelme'" >> ~/.bashrc
echo "alias labelme-cli='cd $labelme_path && source .anaconda3/bin/activate && cd labelme/cli'" >> ~/.bashrc
source ~/.bashrc
