# zookeeper

`stingray-zookeeper` on PyPI

This package lets you swiftly create & configure Stingray containers.

## Installation & Use

```bash
# Install pipx to run stingray-zookeeper in a virtual environment
pip install pipx

# Run this command for an explanation of the available arguments
pipx run stingray-zookeeper --help

# Run stingray-zookeeper
# Notes: your pterodactyl token will be longer than the example.
#        nginxproxymanager tokens are long as shit because of their great amount of encoded json and large key
#        these (obviously) aren't real keys.
#        your nest, egg, and proxy ids will be different. 
#        check your pterodactyl settings & nginxproxymanager frontend.
pipx run stingray-zookeeper \
  --name "StingRay" \
  --nest 12 \
  --egg 45 \
  --proxy 43 \
  --panel-url "https://ptero.regulad.xyz" \
  --panel-key "ptla_wordswordswords" \
  --proxy-url "https://nginx.local.regulad.xyz" \
  --proxy-token "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcGkiLCJzY29wZSI6WyJ1c2VyIl0sImF0dHJzIjp7ImlkIjoxfSwiZXhwaXJlc0luIjoiMWQiLCJqdGkiOiJUdFlQaGhiRiIsImlhdCI6MTY3MjA5Mjk1NSwiZXhwIjoxNjcyMTc5MzU1fQ.rZFs0iT0PgvCOq5tWQd0dq-kP9GJ7_jbXnuwPS-GwHU"
 ```
