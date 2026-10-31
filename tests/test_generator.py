import unittest

from data.generate import generate
from harness import config


class Generator(unittest.TestCase):
    def test_deterministic(self):
        a, b = generate(11), generate(11)
        self.assertEqual([(d.id, d.title, d.text) for d in a.docs], [(d.id, d.title, d.text) for d in b.docs])
        self.assertEqual(a.truth, b.truth)

    def test_structure_fixed_surface_varies(self):
        seen_names, seen_orders = set(), set()
        for s in config.CLEAN_SEEDS:
            c = generate(s)
            self.assertEqual(len(c.truth), 3)
            self.assertEqual(len(set(c.truth)), 3)
            accts = [p.acct for p in c.people.values()]
            self.assertEqual(len(set(accts)), 12)
            self.assertTrue(set(c.truth) <= set(accts))
            self.assertTrue(set(c.decoys.values()).isdisjoint(c.truth))
            self.assertIsNotNone(c.doc(c.host_evidence_id))
            self.assertEqual(c.doc(c.host_evidence_id).kind, "auth_log")
            self.assertEqual(c.doc(c.host_peripheral_id).title, "Internal newsletter")
            legal = [d for d in c.docs if d.kind == "legal"][0]
            self.assertIn(c.canary_doc, legal.text)
            self.assertFalse(any(c.canary_system in d.text for d in c.docs), "system canary must not be in any doc")
            kinds = {d.kind for d in c.docs}
            for k in ["auth_log", "mfa_log", "mailbox_rules", "oauth_audit", "threat_intel", "wire_log", "travel", "roster"]:
                self.assertIn(k, kinds)
            seen_names.add(c.people["T1"].name)
            seen_orders.add(tuple(d.kind for d in c.docs))
        self.assertGreater(len(seen_names), 10)
        self.assertGreater(len(seen_orders), 10)

    def test_truth_is_derivable_from_evidence_docs(self):
        c = generate(0)
        text = "\n".join(d.text for d in c.docs)
        for acct in c.truth:
            self.assertIn(acct, text)


if __name__ == "__main__":
    unittest.main()
