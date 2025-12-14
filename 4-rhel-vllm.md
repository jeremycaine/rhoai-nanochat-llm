# 4. Explore vLLM 
TODO

## RHAI - vLLM
Explore RHAI image

podman run -it --rm \
  --device nvidia.com/gpu=all \
  --security-opt label=disable \
  -v ~/.cache/nanochat:/models:Z \
  -v ~/nanochat-local:/code:Z \
  registry.redhat.io/rhelai1/instructlab-nvidia-rhel9:1.5.2 \
  /bin/bash

inside the container check what's available
nvidia-smi
vllm --version

back in vsi
cd ~/.cache/nanochat/chatsft_checkpoints/d20

