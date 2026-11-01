FROM eclipse-mosquitto:2

COPY mosquitto.conf /mosquitto/config/mosquitto.conf

COPY certs /mosquitto/certs

# Create directories for data and logs
RUN mkdir -p /mosquitto/data /mosquitto/log