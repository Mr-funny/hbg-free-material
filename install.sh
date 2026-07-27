#!/bin/sh
set -eu

repo_url="https://github.com/Mr-funny/hbg-free-material.git"
source_dir=""
install_skill="codex"

usage() {
  printf '%s\n' \
    "Usage: ./install.sh [--cli-only] [--codex|--claude] [--local PATH]" \
    "" \
    "Installs the CLI into ~/.local/share/hbg-free-material and links it into ~/.local/bin." \
    "By default it also installs the Agent Skill for Codex."
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --cli-only) install_skill="" ;;
    --codex) install_skill="codex" ;;
    --claude) install_skill="claude" ;;
    --local)
      shift
      [ "$#" -gt 0 ] || { usage >&2; exit 2; }
      source_dir=$1
      ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

install_root="${XDG_DATA_HOME:-$HOME/.local/share}/hbg-free-material"
bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
venv_dir="$install_root/venv"

tmp_dir=""
cleanup() {
  if [ -n "$tmp_dir" ] && [ -d "$tmp_dir" ]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT INT TERM

if [ -z "$source_dir" ]; then
  tmp_dir=$(mktemp -d)
  git clone --depth 1 "$repo_url" "$tmp_dir/repo" >/dev/null
  source_dir="$tmp_dir/repo"
fi

source_dir=$(CDPATH= cd -- "$source_dir" && pwd)
python3 -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --upgrade pip >/dev/null
"$venv_dir/bin/python" -m pip install "$source_dir" >/dev/null

mkdir -p "$bin_dir"
ln -sf "$venv_dir/bin/hbg-free-material" "$bin_dir/hbg-free-material"
ln -sf "$venv_dir/bin/hbg-material" "$bin_dir/hbg-material"

if [ "$install_skill" = "codex" ]; then
  skill_root="${CODEX_HOME:-$HOME/.codex}/skills/hbg-free-material"
elif [ "$install_skill" = "claude" ]; then
  skill_root="$HOME/.claude/skills/hbg-free-material"
else
  skill_root=""
fi

if [ -n "$skill_root" ]; then
  if [ -e "$skill_root" ]; then
    backup_path="${skill_root}.backup-$(date +%Y%m%d-%H%M%S)"
    mv "$skill_root" "$backup_path"
    printf 'Existing Skill backed up: %s\n' "$backup_path"
  fi
  mkdir -p "$(dirname -- "$skill_root")"
  cp -R "$source_dir/skills/hbg-free-material" "$skill_root"
  printf 'Skill installed: %s\n' "$skill_root"
fi

printf 'CLI installed: %s/hbg-free-material\n' "$bin_dir"
printf 'Run: hbg-free-material providers\n'
