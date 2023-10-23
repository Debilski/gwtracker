#!/bin/bash

# Define the repository URL
REPO_URL="https://github.com/debilski/gwtracker"

# Check if a target directory was provided as a command-line argument
if [ $# -eq 1 ]; then
  TARGET_DIR="$1"
else
  # If no target directory is provided, use the default (Desktop)
  TARGET_DIR="$HOME/Desktop/gwtracker"
fi

# Check if the target directory already exists
if [ -d "$TARGET_DIR" ]; then
  # The directory exists, so update the repository
  echo "Updating the existing clone in $TARGET_DIR..."
  cd "$TARGET_DIR"
  git pull origin main
else
  # The directory doesn't exist, so clone the repository
  echo "Cloning the repository to $TARGET_DIR..."
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
rm -rf venv/
python3 -m venv venv
. ./venv/bin/activate
pip install -e .

gwtracker

