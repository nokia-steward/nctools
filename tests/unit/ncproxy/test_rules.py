import json
from pathlib import Path

from ncproxy import load_rules


def test_load_json_rules(tmp_path: Path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(
        json.dumps(
            {
                "server-msg-modifier": [{"match": "a", "patch": "b"}],
                "client-msg-modifier": [],
                "auto-respond": [],
            }
        ),
        encoding="utf-8",
    )
    rules = load_rules(str(rules_file))
    assert len(rules.server_msg_modifier) == 1
    assert rules.client_msg_modifier == []
