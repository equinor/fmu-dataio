FROM nginxinc/nginx-unprivileged:alpine

ARG uriprefix
ENV URIPREFIX=${uriprefix}

WORKDIR /app
COPY . .

USER 0

RUN chown -R 101 .
RUN apk update && apk upgrade && apk add jq

COPY tools/modify-schema-files.sh /docker-entrypoint.d/50-modify-schema-files.sh
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER 101
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
