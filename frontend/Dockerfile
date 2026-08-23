# Multi-stage build for React frontend

FROM node:20-bookworm-slim AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build


FROM nginx:1.25-alpine


RUN apk add --no-cache curl


COPY nginx.conf /etc/nginx/conf.d/default.conf


RUN rm -rf /usr/share/nginx/html/*


COPY --from=builder /app/dist /usr/share/nginx/html


RUN addgroup -g 1001 -S nginx-app && \
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx-app nginx-app && \
    \
    mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp \
             /tmp/nginx && \
    \
    chown -R nginx-app:nginx-app \
        /usr/share/nginx/html \
        /var/cache/nginx \
        /var/log/nginx \
        /var/run \
        /tmp/nginx


# Change nginx PID location
RUN sed -i 's#pid.*;#pid /tmp/nginx/nginx.pid;#' /etc/nginx/nginx.conf


USER nginx-app


EXPOSE 80


HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost/ || exit 1


LABEL maintainer="QR Inventory Team"
LABEL version="1.0.0"


CMD ["nginx", "-g", "daemon off;"]