"""Local secrets only. Existing credentials are never printed or replaced."""
import json
import os
from pathlib import Path
import secrets
root = Path(__file__).resolve().parents[1]
p = root / 'user_data/runtime/api.json'
p.parent.mkdir(parents=True, exist_ok=True)
if not p.exists():
    config = {'api_server': {'username': 'owner', 'password': secrets.token_urlsafe(32),
                            'jwt_secret_key': secrets.token_urlsafe(48), 'ws_token': secrets.token_urlsafe(48)}}
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(config, f, indent=2); f.write('\n')
print('Local API credentials ready: user_data/runtime/api.json (excluded from Git).')
