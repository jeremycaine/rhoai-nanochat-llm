## 4. Explore vLLM
The IBM AI enabled Virtual Server instance uses a RHEL AI operating system image `ibm-redhat-ai-nvidia-1-5-2-amd64-1`.

vLLM is not installed but rather is included in the container image that's part of the OS.

```
podman images | grep rhelai
# shows
registry.redhat.io/rhelai1/instructlab-nvidia-rhel9
```

## Run the container and check GPU access
Run the container interactively
```
podman run -it --rm \
  --device nvidia.com/gpu=all \
  --security-opt label=disable \
  registry.redhat.io/rhelai1/instructlab-nvidia-rhel9:1.5.2 \
  /bin/bash
```

With `--security-opt label=disable`:
- Disables SELinux labeling for this specific container
- Container can access GPU devices
- Trade-off: Less secure, but necessary for GPU access

For production, you'd configure proper SELinux policies. For development/testing, this is fine.


Inside the container
```
[root@pytorch /]# nvidia-smi
Tue Dec 16 22:59:44 2025
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 550.163.01             Driver Version: 550.163.01     CUDA Version: 12.4     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA L4                      On  |   00000000:04:01.0 Off |                    0 |
| N/A   40C    P8             16W /   72W |       1MiB /  23034MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI        PID   Type   Process name                              GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+

[root@pytorch /]# vllm --version
INFO 12-16 23:00:48 [__init__.py:239] Automatically detected platform cuda.
0.8.4
```

## Test vLLM with a real model
Run vLLM serving a small model
```
podman run -d \
  --name vllm-test \
  --device nvidia.com/gpu=all \
  --security-opt label=disable \
  -p 8000:8000 \
  registry.redhat.io/rhelai1/instructlab-nvidia-rhel9:1.5.2 \
  vllm serve facebook/opt-125m \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.5

```
Inside the container check the logs with `podman logs -f vllm-test` until you see "Application startup complete".

In another terminal on the VSI, test it
```
curl http://localhost:8000/v1/models

{"object":"list","data":[{"id":"facebook/opt-125m","object":"model","created":1765926465,"owned_by":"vllm","root":"facebook/opt-125m","parent":null,"max_model_len":2048,"permission":[{"id":"modelperm-cad64c75ee684517aa9246382c759310","object":"model_permission","created":1765926465,"allow_create_engine":false,"allow_sampling":true,"allow_logprobs":true,"allow_search_indices":false,"allow_view":true,"allow_fine_tuning":false,"organization":"*","group":null,"is_blocking":false

curl http://localhost:8000/v1/completions \://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "facebook/opt-125m",
    "prompt": "San Francisco is a",
    "max_tokens": 20
  }'
{"id":"cmpl-83e177549ca64f63ae4e7264756b00d5","object":"text_completion","created":1765926480,"model":"facebook/opt-125m","choices":[{"index":0,"text":" Bay Area city with Tower City. A huge part of being SF Garden City becomes the much larger SF","logprobs":null,"finish_reason":"length","stop_reason":null,"prompt_logprobs":null}],"usage":{"prompt_tokens":5,"total_tokens":25,"completion_tokens":20,"prompt_tokens_details":null}}
```
