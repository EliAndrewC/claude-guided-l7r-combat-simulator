# L7R Combat Simulator

## Live site

This can be found at https://l7r-combat-sim.fly.dev/

## Development

```
podman run --interactive --tty --rm \
    --name combat-simulator \
    --uidmap 0:1:1000 \
    --uidmap 1000:0:1 \
    --uidmap 1001:1001:64536 \
    --gidmap 0:1:1000 \
    --gidmap 1000:0:1 \
    --gidmap 1001:1001:64536 \
    --env HOME=/home/agent \
    --volume "$(pwd)":/workspace:Z \
    --volume /home/eli/l7r:/host-l7r-repo:Z \
    --volume "$HOME/.claude":/home/agent/.claude:z \
    --volume "$HOME/.claude.json":/home/agent/.claude.json:z \
    --workdir /workspace \
    --memory 8g \
    --memory-swap 8G \
    --publish 8501 \
    docker.io/docker/sandbox-templates:claude-code \
    bash
```
