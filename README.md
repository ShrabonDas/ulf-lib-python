## Local Python setup (uv)

This repository uses **uv** to manage a reproducible local Python environment.

### Prerequisites

- Python **3.12+**
- `uv` installed

### 1) Create the virtual environment

From the project root:

```bash
uv venv --python 3.12
```

This creates a `.venv/` directory using Python 3.12.

---

### 2) Install dependencies

```bash
uv sync
```

This installs **exact dependency versions** from `uv.lock` ensuring same environment.

---

### 3) Activate the environment

```bash
source .venv/bin/activate
```

---

### 4) Download oracle data

The test suite requires oracle data files that are hosted as GitHub release assets. Run the setup script to download them:

```bash
bash setup_data.bash
```

---

### 5) Run tests

```bash
export PYTHONPATH=.
python tests/test_syntactic_features.py
```

---

## Docker setup for legacy codebase using Quicklisp

This project provides a Docker environment that launches an interactive container with Quicklisp configured and mounts three local repositories into the container for testing.

### Prerequisites

- Docker
- Docker Compose v2

---

### 1) Clone required repositories

The container expects these repos to exist locally under `./repos/`:

```
repos/
├── gute/
├── ttt/
└── ulf-lib/
```

Clone them like this (from the project root):

```bash
mkdir -p repos
git clone https://github.com/genelkim/gute.git repos/gute
git clone https://github.com/genelkim/ttt.git repos/ttt
git clone https://github.com/genelkim/ulf-lib.git repos/ulf-lib
```

> **Important:** These repos are mounted into the container at runtime via Docker volumes.
> If they are missing, Docker may create empty directories and the container will not behave correctly.

---

### 2) Build the Docker image

From the project root (where the `Dockerfile` is located):

```bash
docker build -t data-augmentation:1.0 .
```

> Note: Building the image does **not** require the repos above. The repos are injected at runtime via volume mounts.

---

### 3) Start the container

Start the container in the background:

```bash
docker compose up -d
```

This starts a container named `semantic-parsing`

and opens an interactive bash environment with the working directory set to:

- `/root/quicklisp/local-projects/`

The following host directories are mounted into the container:

- `./repos/gute` → `/root/quicklisp/local-projects/gute`
- `./repos/ttt` → `/root/quicklisp/local-projects/ttt`
- `./repos/ulf-lib` → `/root/quicklisp/local-projects/ulf-lib`

---

### 4) Open a shell inside the running container

Make the helper script executable (first time only):

```bash
chmod +x get_shell.bash
```

Then open a shell:

```bash
./get_shell.bash
```

(Equivalent to: `docker exec -it semantic-parsing bash`)

---

### 5) Stop and remove the container

```bash
docker compose down
```
