FROM nginxinc/nginx-unprivileged:alpine

WORKDIR /app
USER 0

RUN rm /etc/nginx/conf.d/default.conf
COPY schema/app/fmu-schemas.conf /etc/nginx/conf.d
COPY schema/definitions schemas/
RUN chown -R 101:101 .

EXPOSE 8080
USER 101
CMD ["nginx", "-g", "daemon off;"]
