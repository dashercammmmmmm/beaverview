# BeaverView Deployment Assets

Reusable deployment templates for the Ubuntu VM target.

## Files

- `systemd/beaverview.service` — systemd unit for uvicorn on `127.0.0.1:8000`.
- `nginx/beaverview.conf.template` — nginx HTTPS reverse proxy template. Replace `__VM_IP__` with the VM IP before installing.
- `../scripts/render_nginx_config.sh` — validates a VM IP and renders the nginx template.

## Validate Locally

```bash
scripts/check_deployment_assets.sh
```

This checks that the templates exist and contain the expected service, proxy, TLS, and security-header settings. It does not require nginx or systemd on the Mac.

## Install On The VM

From `/home/beaverview/app` on the Ubuntu VM:

```bash
sudo cp deploy/systemd/beaverview.service /etc/systemd/system/beaverview.service
scripts/render_nginx_config.sh 192.168.1.50 /tmp/beaverview.nginx
sudo cp /tmp/beaverview.nginx /etc/nginx/sites-available/beaverview
```

Replace `192.168.1.50` with the VM's actual IP address.
