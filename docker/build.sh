#!/bin/bash

# Before running this, make sure that
# -1) The machine you install the docker container from can download and
# install all packages listed in the conda_ci_env.yml file.

if [ `id -u` -ne 0 ]; then
  echo "ERROR: Please run the script $(basename "$0") with sudo!"
  exit 1
fi

# Tag/branch/commit in https://git.eodc.eu/cci-sm-work/cci_sm_ecvps_py_src
GIT_BRANCH_TAG_COMMIT=$1

GIT_URL="https://github.com/TUW-GEO/smos.git"

echo "Calling Dockerfile at $this_dir/docker/Dockerfile"
echo "Checking out source tag $GIT_BRANCH_TAG_COMMIT"
SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
echo "This DIR: $SCRIPTPATH"

sudo docker build -t smos:$GIT_BRANCH_TAG_COMMIT \
    --progress=plain \
    --build-arg GIT_BRANCH_TAG_COMMIT=$GIT_BRANCH_TAG_COMMIT \
    --build-arg GIT_URL=$GIT_URL \
    . 2>&1 | tee build.log