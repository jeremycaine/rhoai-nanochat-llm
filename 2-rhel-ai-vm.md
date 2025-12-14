# 2. Use the Nanochat model on RHEL AI

## Virtual Server
Creat a GPU enabled Virtual Server for nanochat model training.

- Create Virtual Server for VPC
    - location `us-east-2`
    - name `nanochat-vsi`
    - Profile > GPU 
        - profile name: `gx3-16x80x1l4	`
        - gpu: 1 x NVIDIA L4 24 GB
        - instance storage: -
        - spec: 16 vCPUS, 80 GB RAM, 32 Gbps badwidth
    - Image
        - features AI
        - name: `ibm-redhat-ai-nvidia-1-5-2-amd64-1`
        - type: Red Hat Enterprise Linux AI, NVIDIA bundle
        - SSH key: `caine-ssh`
            - generate a pair key for me
            - copy key .prv file to local `~/.ssh`

Assign a floating IP
- `caine-float-ip` bind to `nanochat-vsi` e.g. `169.59.166.69`

## SSH key setup
On local laptop
```
chmod 600 ~/.ssh/your-key-name.prv
ssh -i ~/.ssh/your-key-name.prv cloud-user@YOUR_VM_PUBLIC_IP

# e.g.
ssh -i ~/.ssh/caine-ssh_rsa.prv cloud-user@169.59.166.69
```

On IBM Cloud different type of operating system image give you different default user account: https://cloud.ibm.com/docs/vpc?topic=vpc-vsi_is_connecting_linux

## Red Hat Subscription
Configuration of subscription to Red Hat managed packages
```
# return nothing since no subscription setup after VSI created
sudo subscription-manager status
sudo subscription-manager repos --list
```

With your Red Hat account
```
sudo subscription-manager register --username YOUR_RED_HAT_USERNAME --password YOUR_PASSWORD
```

There are many ways to set up subscription manager
```
# Backup original
sudo cp /etc/yum.repos.d/redhat.repo /etc/yum.repos.d/redhat.repo.backup

# Remove it
sudo rm /etc/yum.repos.d/redhat.repo

# Regenerate with only what you need
sudo subscription-manager repos --disable='*'
sudo subscription-manager repos \
  --enable rhel-9-for-x86_64-baseos-rpms \
  --enable rhel-9-for-x86_64-appstream-rpms

# Refresh
sudo subscription-manager refresh
```

Next, test rpm-ostree
```
# Clean and refresh
sudo rpm-ostree cleanup -m
sudo rpm-ostree refresh-md

# Try installing vim to test
sudo rpm-ostree install vim
```

## rclone
### via rpm-ostree
Use rpm to install `rclone` on the VSI
```
# Install EPEL first (if not already done):
sudo rpm-ostree install epel-release

# Install rclone:
sudo rpm-ostree install rclone

# Apply changes (reboot):
sudo systemctl reboot
```
Then check with `rclone version`

### manual install
```
cd /var/home/cloud-user
curl -O https://downloads.rclone.org/v1.64.2/rclone-v1.64.2-linux-amd64.zip
python3 -m zipfile -e rclone-v1.64.2-linux-amd64.zip .
cd rclone-v1.64.2-linux-amd64

# Create personal bin directory
mkdir -p ~/bin

# Copy rclone there
cp ~/rclone-v1.64.2-linux-amd64/rclone ~/bin/
chmod 755 ~/bin/rclone

# Add to PATH
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```
Then check with `rclone version`

## Use rclone to access S3 bucket
Use `rclone config`
- n - new
- name: ibmcloud
- type: s3
- provder: 11 (IBMCOS)
- access key, secret access key
- region: blank
- endpoint: s3.us-east.cloud-object-storage.appdomain.cloud

Test rclone and mount as filesystem
```
rclone lsd ibmcloud:nanochat-llm

mkdir -p /var/mnt/caine-data/s3-mount
cd /var/mnt/caine-data/s3-mount

# Add user_allow_other to fuse.conf
echo "user_allow_other" | sudo tee -a /etc/fuse.conf

# Verify it was added
cat /etc/fuse.conf

rclone mount ibmcloud:nanochat-llm /var/mnt/caine-data/s3-mount --vfs-cache-mode full --allow-other --daemon
```

## Use the Nanochat model
The Nanochat repo where the app code is on the S3 bucket mount. Since we are going to be running python and install packages, `uv` has trouble working with S3 mounted filesystems.

Therefore we need to copy onto the local VSI disk.
```
cd /var/mnt/caine-data/s3-mount
cd nanochat-repo-20251115
deactivate

# copy local to VSI disk
cd /var/mnt/caine-data
cp -r /var/mnt/caine-data/s3-mount/nanochat-repo-20251115 nanochat-local
cd nanochat-local

# clean start
deactivate 2>/dev/null || true
rm -rf .venv
unset VIRTUAL_ENV
uv venv
source .venv/bin/activate

# install packages we need
uv pip install torch torchvision torchaudio flask numpy tiktoken tqdm fastapi uvicorn tokenizers
```

The configuration of the Nanochat app looks for a `.cache` base. A simple hack is to create symbolic links to the model folders on S3 that we need.
```
mkdir -p ~/.cache/nanochat

ln -s /var/mnt/caine-data/s3-mount/nanochat-complete-run-20251115/chatsft_checkpoints ~/.cache/nanochat/chatsft_checkpoints
ln -s /var/mnt/caine-data/s3-mount/nanochat-complete-run-20251115/tokenizer ~/.cache/nanochat/tokenizer
```

Now we can start the chat web app that Nanochat has provided. It spins up on port 8000 and becuase you have public IP and security rules to expose 8000 then you can get to it from your laptop.
```
python -m scripts.chat_web -i sft -g d20 -s 700
```

Test at e.g. `http://169.59.166.69:8000/`
