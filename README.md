## ulf-lib-python

Python port of the Common Lisp [ulf-lib](https://github.com/genelkim/ulf-lib) library for
ULF (Unscoped Logical Form) semantic types.

---

## Using as a dependency in another project

`ulf-lib-python` has one required sibling dependency: **`ttt-py`**, the Python port of the
Tree-to-Tree Transduction library, expected at `~/research/ttt-py`.

### With uv (recommended)

Add both packages as path sources in your project's `pyproject.toml`:

```toml
[project]
dependencies = [
    "ulf-lib-python",
    "ttt-py",
]

[tool.uv.sources]
ulf-lib-python = { path = "../ulf-lib-python", editable = true }
ttt-py         = { path = "../ttt-py",         editable = true }
```

Then run:

```bash
uv sync
```

### With pip

```bash
pip install -e /path/to/ttt-py
pip install -e /path/to/ulf-lib-python
```

### Importing

```python
from ulf_py import (
    str2semtype, semtype2str, semtype_match,   # semtype parsing/matching
    atom_semtype,                               # lexical type lookup
    ulf_type, ulf_type_string,                 # ULF expression typing
    extended_compose_types,                    # extended composition
    left_right_compose_types,                  # surface-order composition
)
```

---

## Local development setup

Python 3.12+ managed with `uv`.

```bash
# 1. Create and populate the virtual environment
uv sync

# 2. Install ttt-py as an editable sibling dependency
source .venv/bin/activate
pip install -e ../ttt-py

# 3. Run tests
export PYTHONPATH=.
pytest tests/
```

All 288 tests should pass with no external data files required.

---

## Docker setup for Lisp validation

The original Lisp `ulf-lib` can be run in Docker for ground-truth comparison against the Python port.

### Prerequisites

- Docker and Docker Compose v2

### 1) Clone required repositories

```bash
mkdir -p repos
git clone https://github.com/genelkim/gute.git repos/gute
git clone https://github.com/genelkim/ttt.git repos/ttt
git clone https://github.com/genelkim/ulf-lib.git repos/ulf-lib
```

### 2) Build and start the container

```bash
docker build -t data-augmentation:1.0 .
docker compose up -d
```

### 3) Open a shell

```bash
chmod +x get_shell.bash   # first time only
./get_shell.bash
```

Inside the container:

```lisp
sbcl
(ql:quickload :ulf-lib)
(in-package :ulf-lib)
(semtype2str (str2semtype "({D|(D=>(S=>2))}^n=>(D=>(S=>2)))"))
```

### 4) Stop the container

```bash
docker compose down
```
