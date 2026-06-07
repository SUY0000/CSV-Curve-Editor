#!/bin/zsh
set -e

cd "$(dirname "$0")"

if ! command -v conda >/dev/null 2>&1; then
  if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
  elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
  else
    echo "未找到 conda。请先安装 Conda，或在终端中手动运行："
    echo "PYTHONPATH=src python -m csv_curve_editor.main"
    read -k 1 "?按任意键退出..."
    exit 1
  fi
fi

conda activate csv-curve-editor
PYTHONPATH=src python -m csv_curve_editor.main
