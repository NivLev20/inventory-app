# Multi-stage: Node builds the static bundle; only dist/ is shipped in the nginx image.
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Runs nginx as a non-root user on port 8080
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Apply OS security fixes published after the base image was built (found by Trivy)
USER root
RUN apk upgrade --no-cache
USER 101

ENV BACKEND_URL=http://backend:5000

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
