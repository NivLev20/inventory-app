# ---- Frontend image: multi-stage build ----
# Stage 1 (build): Node installs the libraries and compiles React into plain static files (dist/).
# Stage 2 (final): only those static files are copied into a small nginx image.
# Node, the source code and dev tools never reach the final image -> smaller and safer.

# ---------- Stage 1: build ----------
FROM node:22-alpine AS build
WORKDIR /app

# Install exactly the versions written in package-lock.json (reproducible build)
COPY package.json package-lock.json ./
RUN npm ci

# Copy the source and build the production bundle into /app/dist
COPY . .
RUN npm run build

# ---------- Stage 2: serve ----------
# "unprivileged" image runs nginx as a regular user on port 8080 (not root)
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Apply OS security fixes published after the base image was built (found by Trivy)
USER root
RUN apk upgrade --no-cache
USER 101

# Where nginx forwards /api requests. Overridden by docker-compose or Kubernetes.
ENV BACKEND_URL=http://backend:5000

# The nginx image fills ${VARIABLES} in templates on startup
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
