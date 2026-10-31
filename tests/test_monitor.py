"""Layer 6 (split discipline) + monitor mechanics. Deliberately asserts NOTHING about test families."""
import hashlib
import inspect
import unittest
from pathlib import Path

from attacks.placement import apply_payload
from data.generate import generate
from defense import monitor as M
from defense.monitor import Monitor, _parse_verdict, regex_screen
from harness import config


class MonitorDiscipline(unittest.TestCase):
    def test_regex_catches_train_canonical_payloads(self):
        for s in range(5):
            c = generate(s)
            for fam in config.TRAIN_FAMILIES:
                corp, meta = apply_payload(c, fam)
                self.assertTrue(regex_screen(corp.doc(meta["host_id"]).text), (s, fam))

    def test_regex_zero_hits_on_clean_docs(self):
        fps = []
        for s in range(10):
            for d in generate(s).docs:
                h = regex_screen(d.text)
                if h:
                    fps.append((s, d.id, d.kind, h))
        self.assertEqual(fps, [])

    def test_no_peeking_at_test_families(self):
        """Regexes and classifier prompt must not key on test-family-specific vocabulary."""
        src = inspect.getsource(M).lower()
        for banned in ["disable_account", "send_email", "retention", "archive", "callback", "supplementary", "ir-7", "containment"]:
            self.assertNotIn(banned, src, "monitor source mentions test-family vocabulary: " + banned)

    def test_withhold_replaces_text(self):
        c = generate(0)
        corp, meta = apply_payload(c, "override")
        mon = Monitor(classifier=None)      # regex-only mode
        text, m = mon.on_read(corp.doc(meta["host_id"]), step=3)
        self.assertTrue(m["fired"] and m["withheld"])
        self.assertIn("withheld", text)
        self.assertNotIn(meta["payload_text"][:40], text)
        self.assertEqual(mon.events[0]["step"], 3)
        text2, m2 = mon.on_read(corp.doc(corp.host_peripheral_id), step=4)
        self.assertFalse(m2["fired"])
        self.assertEqual(text2, corp.doc(corp.host_peripheral_id).text)

    def test_monitor_source_unchanged_since_freeze(self):
        """The hash recorded in defense/TUNING_LOG.md at freeze time must match the file (Fork 4)."""
        src = Path(__file__).resolve().parents[1] / "defense" / "monitor.py"
        frozen = "c3dde85eaf2e6490e7c26fe8f055671645ca3dd8aa72b67bd978e83e6533199f"
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), frozen,
                         "defense/monitor.py changed after the tuning freeze; log it in TUNING_LOG.md and re-run every defended arm")

    def test_parse_verdict(self):
        self.assertEqual(_parse_verdict('{"injection": true, "confidence": 0.9, "reason": "x"}'), {"injection": True, "confidence": 0.9})
        self.assertEqual(_parse_verdict('Sure. {"injection": false, "confidence": 0.2}')["injection"], False)
        self.assertEqual(_parse_verdict("garbage")["injection"], False)


if __name__ == "__main__":
    unittest.main()
