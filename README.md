# L7R Combat Simulator

## Development

```bash
podman run --interactive --tty --rm \
  --name claude-guided \
  --userns keep-id \
  --volume "$(pwd)":/home/agent/workspace/l7r \
  --publish 8502:8501 \
  docker.io/docker/sandbox-templates:claude-code \
  bash
```
