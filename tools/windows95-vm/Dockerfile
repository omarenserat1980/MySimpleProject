FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends qemu-system-x86 qemu-utils novnc websockify ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data /media
COPY start-vm.sh /usr/local/bin/start-vm
RUN chmod 0755 /usr/local/bin/start-vm

EXPOSE 6080
ENTRYPOINT ["/usr/local/bin/start-vm"]
