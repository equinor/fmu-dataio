FROM nginxinc/nginx-unprivileged:alpine

ARG uriprefix
ENV URIPREFIX=${uriprefix}

WORKDIR /app
USER 0

RUN apk update && apk upgrade && apk add jq

# See https://radix.equinor.com/docs/topic-docker/#running-as-non-root
RUN addgroup -S -g 1001 radix-non-root-group
RUN adduser -S -u 1001 -G radix-non-root-group radix-non-root-user
RUN chown -R 1001:1001 .

COPY tools/modify-schema-files.sh /docker-entrypoint.d/50-modify-schema-files.sh
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER 1001
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
