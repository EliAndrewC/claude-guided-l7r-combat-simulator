# L7R Combat Simulator

## Development

```bash
podman run --interactive --tty --rm \
  --name claude-guided \
  --userns keep-id \
  --user 1000:1000 \
  --volume "$(pwd)":/home/agent/workspace/l7r \
  --publish 8502:8501 \
  docker.io/docker/sandbox-templates:claude-code \
  bash
```

or on Docker:

```
docker run -it --rm --name claude-guided -v "$(pwd):/workspace" -p 8502:8501 claude-code-sandbox:latest bash
```

## Fly.io Deployment

The app is deployed to https://l7r-combat-sim.fly.dev/ via Fly.io.

### Authenticating in a new container

flyctl is not installed globally; it needs to be installed and authenticated
each time a new container is created.

1. **Install flyctl:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```
   This installs to `~/.fly/bin/flyctl`.

2. **Authenticate via web login:**
   ```bash
   ~/.fly/bin/flyctl auth login
   ```
   This will print a URL (since the container has no browser). Open that URL
   in your local browser and complete the SSO login. The CLI will detect the
   successful login automatically.

3. **Verify:**
   ```bash
   ~/.fly/bin/flyctl auth whoami
   ```

### Deploying

```bash
~/.fly/bin/flyctl deploy
```
