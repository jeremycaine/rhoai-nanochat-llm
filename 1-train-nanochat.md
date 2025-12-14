# 1. Train Nanochat Model on Lambda Cloud
Use [Lambda](https://lambda.ai/instances)

## Launch a Lambda instance
- Instances > Launch Instance
    - 8XH100 node
    - Choose a region that has [Filesystem S3 Adapter endpoints](https://docs.lambda.ai/public-cloud/s3-adapter-filesystems/)
    - e.g. `us-south-3` (Central Texas)
    - it used the `Lambda stack 22.04` image
    - Create a new file system: e.g. like `caine-fs` in the same region
    - Global firewall rules are applied to all instances
    - Generate or use your SSH key
        - new key: like `caine-ssh`
        - save private key to desktop

A public IP address is assigned e.g. mine was `192.222.55.121`

## Connect to GPU VM via SSH
Usage: `ssh -i '<SSH-KEY-FILE-PATH>' ubuntu@<INSTANCE-IP>`

Set permissions for your key and then SSH in
```
chmod 400 caine-ssh.pem
ssh -i ~/.ssh/caine-ssh.pem ubuntu@192.222.55.121
```

Then you can check folders and the mounted file system.

## Prepare for training
We will clone the Nanochat repo and configure the training for our VM and S3 setup.

```
cd caine-fs

# see information about the GPU VM 
nvidia-smi

# clone the code
git clone https://github.com/karpathy/nanochat
cd nanochat
mkdir .cache
```
Now edit with `vi speedrun.sh`

Change 
`export NANOCHAT_BASE_DIR="$HOME/.cache/nanochat"` 
to 
`export NANOCHAT_BASE_DIR="$HOME/caine-fs/.cache/nanochat"`

This means the model output files that Nanochat training will land on the s3 filesystem which has sufficient space.

## Build and train the LLM
Launch the build and train pipeline in a new screen session.
```
screen -L -Logfile $HOME/caine-fs/nanochat/logs/speedrun.log -S speedrun bash speedrun.sh
```
On 8 x H100 GPUs this takes approximately 4 hours.

- Base Training (3.5h) → Creates language understanding
- Midtraining (15min) → Adds chat format + reasoning
- Supervised Fine Tuning (10min) → Final polish for assistant behavior

## Remote S3 bucket
Setup a target S3 bucket to receive the Nanochat files after training complete. 

e.g. IBM Cloud Object Storage `[object storage instance name]`
- Create bucket `nanochat-llm`
    - location `us-south`
- Credentials `nanochat-cred`
    - Not controlled by Secrets Manager
    - HMAC credential included

Endpoint: `s3.us-east.cloud-object-storage.appdomain.cloud`

`nanochat-cred`
```
{
    "apikey": ...,
    "cos_hmac_keys": {
        "access_key_id": ...,
        "secret_access_key": ...
    },
    ...,
    ...,
    "resource_instance_id": ...
}
```

## rclone on Lambda VM
Whilst model is training, setup `rclone` and test file transfer to the IBM COS S3 bucket.

```
curl https://rclone.org/install.sh | sudo bash
rclone version
rclone config
```

Configure using `rclone config`
  - n: new remote
  - name: `ibmcos-ceh-object-storage`
  - Storage: s3
  - Provider: IBMCOS
  - 1 enter manually
  - access_key
  - secret_access_key
  - region: `us-east`
  - endpoint: `s3.us-east.cloud-object-storage.appdomain.cloud`
  - location constraint: 
  - acl: 1 get full control
  - ibm_api_key: IBM Cloud API Key
  - ibm_resource_instance_id: 

List contents of IBM COS bucket `nanochat-llm` (will be empty)
```
rclone lsd ibmcos-ceh-object-storage:nanochat-llm

# create test file and transfer
echo hello > hello.txt
rclone copy ./hello.txt ibmcos-ceh-object-storage:nanochat-llm
```

## Test the LLM
Nanochat provides a chat web app for testing

```
cd ~/caine-fs/nanochat
source .venv/bin/activate
export NANOCHAT_BASE_DIR="$HOME/caine-fs/.cache/nanochat"
python -m scripts.chat_cli -p "Why is the sky blue?"
```

## Copy the Nanochat files
Next we copy all the produced files to another S3 bucket because we will be decommissining the Lambda environment.

Lambda object storage to IBM Cloud Object Storage
```
rclone copy <SOURCE-REMOTE>:<BUCKET-NAME>/<PATH> <TARGET-REMOTE>:<BUCKET-NAME>/<PATH> --progress
```

## Decommission Lambda environment
Once the files have been moved, you can delete the GPU VM instance and the associated filesystem to save on costs.