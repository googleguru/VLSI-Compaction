# Rule-110 CA Guided Layout Compaction Framework
# Includes: Yosys (synthesis), Perl (Cell-Based-Layout-Compaction backend),
#           Python 3.11 (CA planner + evaluation)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# ── System packages ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Yosys and build dependencies
    yosys \
    # Perl for Cell-Based-Layout-Compaction backend
    perl \
    perl-modules \
    cpanminus \
    # Python
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-venv \
    # Utilities
    git \
    make \
    curl \
    wget \
    libgd-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# ── Perl modules ───────────────────────────────────────────────────────────
RUN cpanm --notest \
    List::Util \
    POSIX \
    Getopt::Long \
    File::Basename

# ── Python virtualenv ──────────────────────────────────────────────────────
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .
RUN pip install --no-cache-dir -e .

# ── Vendor backend ─────────────────────────────────────────────────────────
# cellCompaction.pl must be mounted or copied from
# https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction
RUN mkdir -p vendor && \
    if [ ! -f vendor/cellCompaction.pl ]; then \
        printf '#!/usr/bin/env perl\n# Placeholder.\n# Mount the real cellCompaction.pl at /app/vendor/.\n# See https://github.com/AmeerAbdelhadi/Cell-Based-Layout-Compaction\ndie "cellCompaction.pl not installed. See vendor/README.md\\n";\n' \
            > vendor/cellCompaction.pl; \
        chmod +x vendor/cellCompaction.pl; \
    fi

# ── Output directories ──────────────────────────────────────────────────────
RUN mkdir -p outputs/{figures,compacted,compacted_layouts,tables,logs,reports,netlists,geometry}

# ── Verify Yosys installation ───────────────────────────────────────────────
RUN yosys -version || echo "WARNING: yosys not available — synthesis will be skipped"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["help"]
