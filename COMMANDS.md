```bash
# Doesn't work with python 3.10
source ~/miniconda3/bin/activate && conda create --prefix ./env python=3.12
source ~/miniconda3/bin/activate ./env

curl -sSL https://install.python-poetry.org | python3 -

pip install moatless-tree-search

brew install graphviz
export CFLAGS="-I $(brew --prefix graphviz)/include"
export LDFLAGS="-L $(brew --prefix graphviz)/lib"
poetry install --with dev
```