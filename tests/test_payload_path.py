"""Layer 2: payloads reach the agent only through document text read via read_doc."""
import json
import unittest
from pathlib import Path

from attacks.placement import apply_payload
from data.generate import generate
from harness import config
from harness.agent import QUESTION, run_agent, system_prompt
from harness.backends import MockBackend

OUT = Path(__file__).resolve().parents[1] / "results" / "verify" / "payload_path_traces.md"


class PayloadPath(unittest.TestCase):
    def test_payload_only_in_host_doc_and_reaches_agent_via_read_doc(self):
        base = generate(0)
        lines = ["# Payload path traces (mock agent, seed 0)", "", "Proves each payload enters the agent ONLY as a read_doc tool result.", ""]
        for fam in config.FAMILIES:
            corp, meta = apply_payload(base, fam)
            marker = max((l.strip() for l in meta["payload_text"].splitlines() if l.strip()), key=len)[:80]   # most distinctive line
            host = meta["host_id"]
            # 1. payload is in the host doc and in no other doc
            self.assertIn(marker, corp.doc(host).text)
            for d in corp.docs:
                if d.id != host:
                    self.assertNotIn(marker, d.text, fam)
            # 2. never in the system prompt or user turn
            self.assertNotIn(marker, system_prompt(corp))
            self.assertNotIn(marker, QUESTION)
            # 3. in the transcript, it appears only inside read_doc tool results for the host doc
            be = MockBackend(truth=corp.truth, obey=False)
            tr = run_agent(be, corp)
            where = []
            for s in tr["steps"]:
                for r in s.get("tool_results", []):
                    if marker in r["output"]:
                        where.append((s["step"], r["name"], json.dumps([c["args"] for c in s["tool_calls"] if c["id"] == r["id"]])))
                self.assertNotIn(marker, s.get("text", ""))
            self.assertTrue(where, "payload never reached the agent for " + fam)
            for step, name, args in where:
                self.assertEqual(name, "read_doc")
                self.assertIn(host, args)
            lines.append("- **{}**: host {} ; reached agent at step(s) {} via read_doc only; absent from system prompt and user turn.".format(fam, host, sorted({w[0] for w in where})))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    unittest.main()
