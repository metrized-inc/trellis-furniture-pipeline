# Makefile for installing UV and dependencies
# Usage: make install

# Set required environment variables (adjust paths as needed)
export HF_HOME=huggingface
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_CACHE_DIR=1
export UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu124
export UV_NO_BUILD_ISOLATION=1
export UV_NO_CACHE=0
export UV_LINK_MODE=symlink
export GIT_LFS_SKIP_SMUDGE=1

.PHONY: server
server: venv
	@echo "Starting server with uvicorn..."
	uv run uvicorn "server:app" --reload 

.PHONY: install venv install_main install_vox2seq install_kaolin install_diffoctreerast install_diff_gaussian install_rembg install_bpy

install: install_uv venv install_main install_vox2seq install_kaolin install_diffoctreerast install_diff_gaussian install_rembg install_bpy
	@echo "Install finished."

# install_uv: Check if uv is installed. If not, try installing it.
install_uv:
	@echo "Checking if uv is installed..."
	@if command -v uv > /dev/null 2>&1; then \
		echo "uv is installed."; \
	else \
		echo "uv not found. Installing uv..."; \
		UNAME_S="$$(uname -s)"; \
		if [[ "$$UNAME_S" == *"MINGW"* || "$$UNAME_S" == *"MSYS"* || "$$UNAME_S" == *"CYGWIN"* ]]; then \
			echo "Detected Windows. Installing uv via PowerShell..."; \
			powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"; \
		else \
			echo "Detected non-Windows OS. Installing uv via shell..."; \
			curl -sL https://astral.sh/uv/install.sh | sh; \
		fi; \
		if ! command -v uv > /dev/null 2>&1; then \
			echo "uv installation failed. Please install uv manually from https://astral.sh/uv/"; \
			exit 1; \
		else \
			echo "uv installed successfully."; \
		fi; \
	fi

# Create or use existing virtual environment
venv:
	@if [ -d "./.venv" ]; then \
        echo "Using existing .venv"; \
	else \
		echo "Creating .venv"; \
		uv venv -p 3.10; \
	fi

install_main:
	@echo "Installing main requirements..."
	uv pip install --upgrade setuptools wheel
	uv pip sync requirements-uv.txt --index-strategy unsafe-best-match

install_vox2seq:
	@echo "Installing vox2seq..."
	-uv pip install https://github.com/iiiytn1k/sd-webui-some-stuff/releases/download/diffoctreerast/vox2seq-0.0.0-cp310-cp310-win_amd64.whl || \
		(uv pip install --no-build-isolation -e extensions/vox2seq/)

install_kaolin:
	@echo "Installing kaolin..."
	uv pip install kaolin -f https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.5.1_cu124.html

install_diffoctreerast:
	@echo "Installing diffoctreerast..."
	-uv pip install https://github.com/iiiytn1k/sd-webui-some-stuff/releases/download/diffoctreerast/diffoctreerast-0.0.0-cp310-cp310-win_amd64.whl || \
		(uv pip install --no-build-isolation git+https://github.com/JeffreyXiang/diffoctreerast.git)

install_diff_gaussian:
	@echo "Installing diff-gaussian-rasterization..."
	-uv pip install https://github.com/sdbds/diff-gaussian-rasterization/releases/download/diff-gaussian-rasterization/diff_gaussian_rasterization-0.0.0-cp310-cp310-win_amd64.whl || \
		(uv pip install git+https://github.com/sdbds/diff-gaussian-rasterization)

install_rembg:
	@echo "Installing rembg..."
	uv pip install rembg

install_bpy:
	@echo "Installing bpy..."
	uv pip install bpy