#!/bin/bash
# Following https://researchcomputing.princeton.edu/jupyter
# Start a jupyter notebook and serve remotely
# through ssh

#$ -l tmem=4G
#$ -l h_mem=4G
#$ -l h_rt=00:05:00
#$ -j y
#$ -S /bin/bash
#$ -N jupyter-notebook
#$ -wd ~/

# get tunneling info
node=$(hostname -s)
user=$(whoami)
cluster="vic"
port=8889

# print tunneling instructions jupyter-log
echo -e "
Command to create ssh tunnel:
ssh -N -f -L ${port}:${node}:${port} ${user}@${cluster}.ucl.ac.uk

Use a Browser on your local machine to go to:
localhost:${port}  (prefix w/ https:// if using password)
"

# load modules or conda environments here
source /cluster/project9/MMD_FW_active_meta_learning/project_environment.source
# make jupyter command available
export export PATH=$PATH:~/.local/bin

# Run Jupyter
jupyter notebook --no-browser --port=${port} --ip=${node}
