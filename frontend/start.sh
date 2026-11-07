#!/bin/sh
# nginx's resolver directive needs the DNS server address explicitly; take it from the
# container's resolv.conf (Docker: 127.0.0.11, Kubernetes: the cluster DNS service).
NGINX_RESOLVER="$(awk '/^nameserver/ { print $2; exit }' /etc/resolv.conf)"
export NGINX_RESOLVER
exec /docker-entrypoint.sh nginx -g 'daemon off;'
