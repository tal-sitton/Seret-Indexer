FROM ghcr.io/tal-sitton/seret-search:latest AS base

FROM ghcr.io/tal-sitton/heb-elastic:latest AS final
COPY --from=base /usr/share/elasticsearch/data /usr/share/elasticsearch/data