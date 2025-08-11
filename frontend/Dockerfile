# syntax=docker/dockerfile:1
FROM node:18-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend /app
RUN npm run build

FROM nginx:1.25-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
# nginx default conf already serves static files
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
