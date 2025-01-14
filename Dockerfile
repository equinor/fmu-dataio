FROM nginxinc/nginx-unprivileged:alpine

WORKDIR /app
COPY . .

USER 0
RUN chown -R 101 .
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER 101
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
