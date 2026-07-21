FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
COPY apps/web/package.json ./apps/web/
RUN npm install

COPY apps/web ./apps/web
RUN npm --prefix apps/web run build

FROM nginx:alpine

COPY --from=build /app/apps/web/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
