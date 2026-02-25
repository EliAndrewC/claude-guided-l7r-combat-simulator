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
