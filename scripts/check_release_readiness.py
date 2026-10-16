"""Publication gate. Technical tests cannot confirm ownership or old-cloud cleanup."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def blockers(state):
    conditions = {
        'ownership_authorization_confirmed': 'Source ownership and publication authorization remain unconfirmed',
        'old_private_repository_disposition_confirmed': 'Sensitive data in the old private repository remains unresolved',
        'experimental_release': 'Release must remain explicitly experimental',
    }
    return [message for key, message in conditions.items() if state.get(key) is not True]


def main():
    state = json.loads((ROOT / 'release-readiness.json').read_text(encoding='utf-8'))
    reasons = blockers(state)
    for reason in reasons:
        print(reason)
    print('Publication gate: ' + ('BLOCKED' if reasons else 'passed'))
    return 1 if reasons else 0


if __name__ == '__main__':
    sys.exit(main())
