# ---- Frontend image: static dashboard served by nginx ----
# "unprivileged" image runs nginx as a regular user on port 8080 (security best practice)
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Where nginx forwards /api requests. Can be overridden by docker-compose or Kubernetes.
ENV BACKEND_URL=http://backend:5000

# The official nginx image fills ${VARIABLES} in templates on startup
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY index.html style.css app.js /usr/share/nginx/html/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
