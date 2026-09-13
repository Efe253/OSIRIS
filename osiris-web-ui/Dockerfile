# OSIRIS Web UI — statik derleme + nginx sunumu (3000)
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Compose 3000 bekler; varsayılan 80'i çevir
RUN sed -i 's/listen\(.*\)80;/listen\13000;/' /etc/nginx/conf.d/default.conf
EXPOSE 3000
