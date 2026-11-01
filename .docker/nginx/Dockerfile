FROM nginx:stable-alpine

COPY nginx.conf /etc/nginx/nginx.conf

COPY trust.html /etc/nginx/trust.html

COPY certs /etc/nginx/certs

# Expose HTTP and HTTPS
EXPOSE 80 443