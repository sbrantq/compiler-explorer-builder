# syntax=docker/dockerfile:1.19

FROM ubuntu:24.04 AS node_base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && apt-get autoremove -y --purge \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

FROM node_base AS build_deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends make rsync git python3-jinja2 \
    && apt-get autoremove -y --purge \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

FROM build_deps AS build

# Add the following line if you want to enable all the nice
# cache-busting features, at the cost of making builds get invalidated
# after every commit. Also remove the `--exclude=.git` on the
# subsequent line.
# COPY .git /src/.git
COPY --exclude=.git compiler-explorer /src/compiler-explorer
COPY files/ /src/compiler-explorer/
COPY template_files/ /src/template_compiler-explorer/
COPY scripts/ /src/scripts/
COPY ./data/ /ver_data

# Copy enzyme-specific overrides
WORKDIR /src/compiler-explorer
RUN python3 /src/scripts/update-versions.py /ver_data /src/template_compiler-explorer/etc/config /src/compiler-explorer/etc/config
RUN sed -i 's|\${req.get('\''host'\'')}|enzyme.mit.edu/explorer|g' lib/shortener/tinyurl.ts
RUN make prebuild

FROM node_base AS with_devtools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libc6-dev \
       libstdc++-12-dev \
       libc++-15-dev \
       binutils \
       lsb-release \
       software-properties-common \ 
       file \
       libmpfr6 \
    && apt-get autoremove -y --purge \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /ver_data /ver_data
COPY install_clang.sh /install_clang.sh
RUN /install_clang.sh

FROM with_devtools
# Built output
COPY --from=build /src/compiler-explorer/out /app/out
COPY --from=build /src/compiler-explorer/node_modules /app/node_modules
# Necessary files
COPY --from=build /src/compiler-explorer/examples /app/examples
COPY --from=build /src/compiler-explorer/etc /app/etc
COPY --from=build /src/compiler-explorer/views /app/views
COPY --from=build /src/compiler-explorer/public /app/public

ENV JULIA_DEPOT_PATH=/local/juliapackages:/opt/compiler-explorer/juliapackages
ENV JULIA_PKG_SERVER=http://package-proxy
ENV NODE_ENV=production
ENV PATH="$PATH:/opt/compiler-explorer/cuda/12.9.1/bin"

LABEL org.opencontainers.image.source=https://github.com/EnzymeAD/compiler-explorer-builder
LABEL org.opencontainers.image.description="Enzyme Explorer"
WORKDIR /app
ENTRYPOINT ["node", "./out/dist/app.js", "--static", "./out/webpack/static", "--env", "enzyme"]
