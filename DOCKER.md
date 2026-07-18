# Running REIN with Docker

This document describes how to build and run the REIN benchmark using Docker and
Docker Compose. The containerized setup removes the need to manually install
PostgreSQL, Python 3.8, PyTorch, the FAHES C++ library, and the many pinned
dependencies on your host machine. It works on both x86_64 and Apple Silicon
(arm64) hosts.

> If you prefer a native (non-Docker) installation, see the **Setup** section in
> [README.md](README.md).

## Table of contents

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [What each file does](#what-each-file-does)
- [Services and ports](#services-and-ports)
- [Volumes and data locations](#volumes-and-data-locations)
- [Environment variables](#environment-variables)
- [Running benchmark scripts](#running-benchmark-scripts)
- [Rebuilding](#rebuilding)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- **Docker Engine** 20.10+ (or Docker Desktop on macOS / Windows)
- **Docker Compose v2** (`docker compose`, the plugin — not the legacy
  `docker-compose` binary)
- Roughly **8 GB** of free disk space for the image and its dependencies
- The first build takes **~15–20 minutes** on an x86_64 host (it compiles native
  extensions such as `scikit-sparse` and the FAHES C++ library), and
  **considerably longer on Apple Silicon**, where the app image is built as
  x86_64 under emulation — see
  [Apple Silicon (arm64) notes](#troubleshooting).

No local PostgreSQL, Python, or CUDA installation is required — everything runs
inside containers, and the build installs **CPU-only** PyTorch wheels.

## Quick start

From the repository root:

```shell
# 1. Build the rein application image (first time only, ~15-20 min)
docker compose build

# 2. Start PostgreSQL in the background
docker compose up -d db

# 3. Open an interactive shell inside the app container
docker compose run --rm rein bash
```

The entrypoint waits for PostgreSQL to accept connections before handing you the
shell, so the database is guaranteed to be ready. Inside the shell you can run
any benchmark script (see [Running benchmark scripts](#running-benchmark-scripts)).

To run a single script without opening a shell:

```shell
docker compose run --rm rein \
    python3 scripts/detect_errors.py --dataset_name nursery --detect_method mvdetector
```

To stop and remove the containers when you are done:

```shell
docker compose down
```

## What each file does

| File | Purpose |
| --- | --- |
| `Dockerfile` | Builds the `rein` application image on Ubuntu 20.04 / Python 3.8: system packages, a virtual environment, CPU PyTorch (architecture-aware), the pinned `requirements.txt`, the compiled FAHES C++ library, and the local editable packages (`rein`, `tools/error-generator`, `tools/Profiler`). |
| `docker-compose.yml` | Defines the two services (`db` and `rein`), their networking, volumes, and health checks. |
| `entrypoint.sh` | Container entrypoint. Waits for the PostgreSQL container to become reachable (`pg_isready`) before running the given command. |
| `init-db.sql` | Runs once on first database startup. Creates the secondary `holo` database and `holocleanuser` used by HoloClean. |
| `.dockerignore` | Excludes large / irrelevant paths (`rein-datasets`, `results`, `.git`, `venv`, `__pycache__`) from the build context. |
| `requirements.txt` | The pinned Python dependencies (also used by the native setup). |

## Services and ports

| Service | Image / build | Purpose | Port |
| --- | --- | --- | --- |
| `db` | `postgres:14-alpine` | PostgreSQL database backing the benchmark | Host `5432` → container `5432` |
| `rein` | built from `Dockerfile` | The REIN benchmark application | — |

If port `5432` is already in use on your host (e.g. a local PostgreSQL is
running), change the host side of the mapping in `docker-compose.yml`, for
example `"5433:5432"`.

## Volumes and data locations

The compose file uses three volumes:

- **`.:/rein`** — the repository is bind-mounted into the container, so source
  edits on the host are reflected inside the container without a rebuild.
- **`fahes_compiled` (named volume) → `/rein/cleaners/FAHES/src`** — protects the
  Linux `libFahes.so` compiled during the image build so it is not shadowed by
  the host directory.
- **`./rein-datasets → /rein/datasets`** — the code always looks for `datasets/`
  (hardcoded in `datasets_dictionary.py`); the host `rein-datasets/` directory is
  mounted to that expected path.
- **`postgres_data` (named volume)** — persists the PostgreSQL data across
  restarts.

Benchmark outputs are written to `results/` in the repository (bind-mounted), so
they persist on the host.

## Environment variables

The `rein` service receives the database connection settings from
`docker-compose.yml`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PGHOST` | `db` | Database host (the compose service name) |
| `PGPORT` | `5432` | Database port |
| `PGUSER` | `reinuser` | Database user |
| `PGPASSWORD` | `abcd1234` | Database password |
| `PGDATABASE` | `rein` | Primary database name |
| `DB_URL` | `postgresql://reinuser:abcd1234@db:5432/rein` | Full SQLAlchemy connection URL |

These defaults match the credentials configured for the `db` service. If you
change the database credentials, update **both** the `db` environment block and
the `rein` environment block, and remove the `postgres_data` volume so the
database is re-initialized (`docker compose down -v`).

> The default credentials are for local development only. Do not reuse them in
> any exposed or production deployment.

## Running benchmark scripts

Open a shell in the app container and run scripts as you would natively:

```shell
docker compose run --rm rein bash

# inside the container:
python3 scripts/detect_errors.py --dataset_name nursery --detect_method mvdetector
```

Or run them directly from the host in one command:

```shell
docker compose run --rm rein \
    python3 scripts/detect_errors.py --dataset_name nursery --detect_method mvdetector
```

`docker compose run --rm` starts a one-off container (and its `db` dependency, if
declared healthy) and removes it on exit.

## Rebuilding

Rebuild the image after changing the `Dockerfile` or `requirements.txt`:

```shell
docker compose build            # incremental, uses cache
docker compose build --no-cache # full clean rebuild
```

Bind-mounted source changes (Python files) do **not** require a rebuild.

## Troubleshooting

**The build fails while compiling `scikit-sparse` or FAHES.**
Ensure you are building on a supported platform and have enough memory allocated
to Docker (Docker Desktop → Settings → Resources; 4 GB+ recommended).

**`rein` starts before the database is ready.**
This should not happen: `depends_on … condition: service_healthy` plus the
`pg_isready` loop in `entrypoint.sh` gate startup on the database health check.
If you see connection errors, check the DB logs with `docker compose logs db`.

**Database schema/credentials look stale after a change.**
The `init-db.sql` script and `POSTGRES_*` variables only take effect on **first**
initialization of the `postgres_data` volume. To re-initialize:

```shell
docker compose down -v   # WARNING: deletes the postgres_data volume
docker compose up -d db
```

**Port 5432 is already allocated.**
Change the host port mapping in `docker-compose.yml` (e.g. `"5433:5432"`).

**Apple Silicon (arm64) notes.**
The `rein` service is pinned to `platform: linux/amd64` in `docker-compose.yml`,
so it builds and runs as x86_64 under emulation on Apple Silicon. This is
deliberate: several pinned dependencies publish no Linux arm64 wheels, most
notably `tensorflow==2.5.0` (arm64 wheels only exist from 2.10.0 onwards) and
`torch==1.10.2+cpu` (the `+cpu` wheels are Linux x86 only). Building natively on
arm64 fails with:

```
ERROR: Could not find a version that satisfies the requirement tensorflow==2.5.0
       (from versions: 2.10.0rc0, ..., 2.13.1)
```

Forcing amd64 keeps every dependency pin identical to the reference benchmark, so
results stay comparable to the published REIN numbers. The trade-off is speed:
the emulated build takes considerably longer than the ~15–20 min native figure,
and benchmark runtimes are slower. Absolute timings measured under emulation are
therefore not comparable to native ones — relative comparisons between methods
remain meaningful.

The `db` service is left native (the `postgres:14-alpine` image has arm64
support), so only the application container pays the emulation cost.
