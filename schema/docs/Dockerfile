FROM node:lts-alpine

WORKDIR /app

COPY ./src /app/src 
COPY ./package.json /app/package.json

RUN npm install

EXPOSE 3000

USER 65534

CMD [ "node", "./src/index.js"]