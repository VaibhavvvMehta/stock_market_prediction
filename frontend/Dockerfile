# Frontend Dockerfile (Vite build + Nginx serve)
FROM node:18-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --no-fund
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine AS prod
COPY --from=build /app/dist/ /usr/share/nginx/html/
# basic nginx config
RUN sed -i 's|/usr/share/nginx/html|/usr/share/nginx/html|g' /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
