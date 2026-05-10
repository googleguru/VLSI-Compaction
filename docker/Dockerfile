# Production Dockerfile for VLSI CA Compaction Framework
FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    perl \
    perl-modules \
    cpanminus \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-venv \
    git \
    make \
    curl \
    wget \
    libgd-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Perl modules
RUN cpanm --notest \
    List::Util \
    POSIX \
    Getopt::Long \
    File::Basename

# Python virtualenv
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .
RUN pip install --no-cache-dir -e .

# Vendor backend
RUN mkdir -p vendor && \
    if [ ! -f vendor/cellCompaction.pl ]; then \
        echo "# Placeholder - mount or copy cellCompaction.pl to /app/vendor/" > vendor/cellCompaction.pl; \
    fi

# Output directories
RUN mkdir -p outputs/{figures,compacted_layouts,tables,logs,reports}

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["help"]
