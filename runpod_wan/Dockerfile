FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y python3 python3-pip git ffmpeg && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/Wan-Video/Wan2.1.git /opt/Wan2.1
RUN pip3 install --upgrade pip && pip3 install -r /opt/Wan2.1/requirements.txt && pip3 install runpod
COPY handler.py /handler.py
CMD ["python3", "/handler.py"]
