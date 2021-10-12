FROM continuumio/miniconda3:4.10.3

ARG DEBIAN_FRONTEND=noninteractive
ARG USER=user
ARG GROUP=user
ARG UID
ARG GID

ENV TERM="xterm-256color"
ENV HOME="/home/user"

RUN set -x \
  && mkdir -p ${HOME}/src \
  && \
    if [ -z "$(getent group ${GID})" ]; then \
      addgroup --system --gid ${GID} ${GROUP}; \
    else \
      groupmod -n ${GROUP} $(getent group ${GID} | cut -d: -f1); \
    fi \
  && \
    if [ -z "$(getent passwd ${UID})" ]; then \
      useradd \
        --system \
        --create-home --home-dir ${HOME} \
        --shell /bin/bash \
        --gid ${GROUP} \
        --groups sudo \
        --uid ${UID} \
        ${USER}; \
    fi \
  && touch ${HOME}/.hushlogin

RUN set -x \
  && chown -R ${USER}:${GROUP} ${HOME}

COPY morbidostat.yml ${HOME}/src/morbidostat.yml

WORKDIR ${HOME}/src

RUN set -x \
  && conda env create morb --file=morbidostat.yml

USER ${USER}

RUN set -x \
  && conda init bash \
  && echo "conda activate morb" >> ${HOME}/.bashrc
