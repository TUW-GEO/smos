FROM mambaorg/micromamba:1.3.1-alpine
MAINTAINER Wolfgang Preimesberger <wolfgang.preimesberger@geo.tuwien.ac.at>

USER root

ARG GIT_BRANCH_TAG_COMMIT
ARG GIT_URL

RUN apk update && \
    apk upgrade && \
    apk add git && \
    apk add build-base && \
    apk add g++ && \
    apk add bsd-compat-headers && \
    apk add tiff

RUN apk add lftp

# Check out the SMECV code at the chose tag using your credentials
RUN git clone --recursive $GIT_URL && \
    cd smos && \
    git checkout $GIT_BRANCH_TAG_COMMIT

ARG MAMBA_DOCKERFILE_ACTIVATE=1

RUN micromamba install -y -n base -c conda-forge python=3.12
RUN cd smos &&  micromamba update -y -n base -f environment.yml && pip install .

RUN micromamba clean --all --yes

# Clean up the src code, as it is installed now
RUN rm -rf smos

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]