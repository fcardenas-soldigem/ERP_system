# syntax=docker/dockerfile:1
FROM node:18-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ /app
RUN npm run build

FROM nginx:1.25-alpine AS runtime

# === SECURITY: Run as non-root user ===
# Nginx en Alpine ya tiene usuario nginx (uid 101), lo usaremos

# Copiar archivos build
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Configuración de Nginx
RUN rm -f /etc/nginx/conf.d/default.conf
COPY --chown=nginx:nginx frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Crear directorios necesarios con permisos correctos
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d

# Cambiar a usuario no-root
USER nginx

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]