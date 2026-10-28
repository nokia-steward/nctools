import re

from ncproxy import ModifierRule, apply_modifiers


def test_apply_modifier_replaces_capability():
    msg = b"<capability>urn:ietf:params:netconf:base:1.1</capability>"
    rules = [
        ModifierRule(
            regex=re.compile(r"base:1\.1"),
            patch="<!-- removed -->",
        )
    ]
    out = apply_modifiers(msg, rules)
    assert b"removed" in out
    assert b"base:1.1" not in out
