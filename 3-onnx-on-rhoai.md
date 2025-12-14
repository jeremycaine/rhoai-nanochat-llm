# 3. Use the Nanochat model in Red Hat OpenShift AI

## Red Hat OpenShift AI
Red Hat OpenShift AI offers a number of ways to build and train data science projects and AI models. These environments are managed through a platform using OpenShift Kuberetes clusters.

In the Developer Sandbox edition there is only one type of model server available - `OpenVINO Model Server`.

With the model server instance created you can then deploy different types of AI model. These are:
- `openvino_ir - opsetl` (OpenVINO Intermediate Representation native model format, optimised for speed)
- `onnx - 1` (Open Neural Network Exchange models, best for framework-agnostic, models from PyTorch, scikit-learn etc)
- `tensorflow - 2` (native Tensorflow and Keras models)

In RHOAI create:
- Medium sized model server (4 CPU, 8GB RAM)

For our experimentation tests we can go with ONNX.

## Convert Nanochat model to ONNX
There are tools for converting Hugging Face models to ONNX format. But assisted code analysis with Claude showed that Nanochat has a number of specifics. It has a custom architecture in its layering and no HuggingFace transformer library.

You can use tools like Claude to understand the model processing. I used it to help me develop a script to convert Nanochat to ONNX format.

Transfer [this script](./export-to-onnx/export_to_onnx.py) to your VSI, or `cat > export_to_onnx.py << EOF...[pasted code]...EOF`

```
cd ~/nanochat-local 
source ~/nanochat-local/.venv/bin/activate
uv pip install onnx onnxruntime onnxscript
python export_to_onnx.py
```
The resulting ONNX model and tokeniser files are now in `~/nanochat-local/nanochat-onnx`.

Copy this to the S3 bucket so that Red Hat OpenShift AI can see them.
```
cp -r ~/nanochat-local/nanochat-onnx /var/mnt/caine-data/s3-mount/
```

## Deploy the ONNX model in Red Hat OpenShift AI
If you use the Developer Sandbox then a data science project is created for you by default.

In the project, under Models you create an instance of a model server:
- Add Model Server, give it a name
- there is only one option OpenVINO Server for serving runtime
- you only need 1 replica for experimenting
- a Medium sized server works well
- the make the deployed model available through an external route, but disable tokens (not how a production setup would be)
- "Add"

Next "Deploy Model" to your model server
- model name
- model framework `onnx - 1`
- select your S3 connection
- since this goes to the bucket e.g. `nanochat-llm`, then you only need to say where the folder is with the ONNX model in it e.g. `nanochat-onnx`
- "Deploy"

You will see internal and external endpoints generated.

Now you can test the model with curl.

```
# Your RHOAI endpoint
INFERENCE_URL="https://nanochat-model-jeremycaine-dev.apps.rm2.thpm.p1.openshiftapps.com/v2/models/nanochat-model/infer"

# Test with "Hello, how are you?" token IDs
# returns logits (raw scroes) data from the model for the input tokens
curl -X POST ${INFERENCE_URL} \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "input_ids",
        "shape": [1, 6],
        "datatype": "INT64",
        "data": [28578, 44, 635, 345, 348, 63]
      }
    ]
  }'

# you will find the endpoint as a Route in OpenShift as well
# this returns metadata on the deployed model
curl https://nanochat-model-jeremycaine-dev.apps.rm2.thpm.p1.openshiftapps.com/v2/models/nanochat-model

```

## Build a new chat app to use the model
Using the Nanochat repo as a guide, I vibed a new simple chat app. We can test this locally on the IBM VSI.

```
# Create app directory in S3 mount
cd /var/mnt/caine-data/s3-mount
mkdir -p nanochat-app
cd nanochat-app

# Copy tokenizer files
cp /var/home/cloud-user/.cache/nanochat/tokenizer/tokenizer.pkl ./
cp /var/home/cloud-user/.cache/nanochat/tokenizer/token_bytes.pt ./

cd /var/mnt/caine-data/s3-mount/nanochat-app

source ~/nanochat-local/.venv/bin/activate
uv pip install -r requirements.txt
python app.py
```

The chat app has a `simple_tokeniser` fix at runtime. This is because the pickle file breaks due to the environment mismatch from Lambda to the IBM Virtual Server.

The pickle approach uses `tiktoken` where Python uses references to C++ objects, and so the actual binary objects from compilation are lost in the movement across environments. This means the encoding needs to be rebuilt in the new environment.

Once it starts, you should see:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
Loading tokenizer from ./tokenizer.pkl
✓ Tokenizer loaded
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```
Test
```
ROUTE_URL="https://localhost:8080"

curl ${ROUTE_URL}/health

curl -X POST ${ROUTE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, who are you?"}
    ],
    "max_tokens": 10,
    "temperature": 0.8
  }'
```


## Deploy the app to OpenShift
The app is put in the `nanochat-app` folder in this repo. We use Import from Git in OpenShift Console to build the app in the Developer Sandbox.

OpenShift Console
- (top right) Import from Git
- repo: `https://github.com/jeremycaine/rhoai-nanochat`
- context dir: `/nanochat-app`
- resource type: Deployment
- "Create"

Then test the Nanochat API endpoint
-test

```
ROUTE_URL="https://rhoai-nanochat-jeremycaine-dev.apps.rm2.thpm.p1.openshiftapps.com"

curl ${ROUTE_URL}/health

curl -X POST ${ROUTE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, who are you?"}
    ],
    "max_tokens": 10,
    "temperature": 0.8
  }'
  curl -X POST ${ROUTE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is the capital of France"}
    ],
    "max_tokens": 10,
    "temperature": 0.8
  }'
```

## Final State

- Nanochat LLM built and trained
- Converted to ONNX format
- Used the Red Hat Developer Sandbox
- Deployed to an OpenVINO Server on Red Hat OpenShift AI
- with a chat app API endpoint a container running in the same OpenShift project


