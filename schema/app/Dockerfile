FROM nginxinc/nginx-unprivileged:1.18

ARG uriprefix
ENV URIPREFIX=${uriprefix}

WORKDIR /app
USER 0

RUN apt update
RUN apt install -y jq

# relative to Dockerfile??
COPY ../definitions definitions/

# relative to Dockerfile??
COPY install-schema-files.sh /docker-entrypoint.d/50-install-schema-files.sh
RUN chmod +x /docker-entrypoint.d/50-install-schema-files.sh

# relative to Dockerfile??
COPY fmu-schemas.conf /etc/nginx/conf.d

RUN rm /etc/nginx/conf.d/default.conf

EXPOSE 8080
USER 101
CMD ["nginx", "-g", "daemon off;"]

# CMD "/bin/sh"
