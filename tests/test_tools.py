import unittest

from data.generate import generate
from harness.backends import ToolCall
from harness.tools import DOC_WRAPPER_CLOSE, ToolBox, wrap_doc


class ToolFaithfulness(unittest.TestCase):
    def setUp(self):
        self.c = generate(3)
        self.box = ToolBox(self.c)

    def call(self, name, **args):
        return self.box.execute(ToolCall("x", name, args), step=1)

    def test_list_docs_lists_every_doc_once(self):
        out = self.call("list_docs").splitlines()
        self.assertEqual(len(out), len(self.c.docs))
        for d, line in zip(self.c.docs, out):
            self.assertTrue(line.startswith(d.id) and d.title in line)

    def test_search_returns_real_hits_only(self):
        out = self.call("search", query="MailSync Pro")
        oauth = [d for d in self.c.docs if d.kind == "oauth_audit"][0]
        self.assertIn(oauth.id, out)
        for d in self.c.docs:
            if "mailsync pro" not in (d.title + d.text).lower():
                self.assertNotIn(d.id + "  ", out)
        self.assertIn("No documents match", self.call("search", query="zxqv-not-present"))

    def test_search_is_case_insensitive_and_multiword(self):
        # phrase "travel atypical" is absent; both words occur in the auth log -> all-words fallback must hit
        self.assertNotIn("No documents match", self.call("search", query="travel atypical"))
        self.assertIn("No documents match", self.call("search", query="impossible travel"))   # "impossible" occurs nowhere
        self.assertNotIn("No documents match", self.call("search", query="atypical travel"))
        self.assertEqual(self.call("search", query="ATYPICAL TRAVEL"), self.call("search", query="atypical travel"))

    def test_read_doc_returns_exact_text(self):
        for d in self.c.docs[:5]:
            self.assertEqual(self.call("read_doc", doc_id=d.id), wrap_doc(d))
            self.assertIn(d.text.rstrip(), self.call("read_doc", doc_id=d.id))
        self.assertEqual(self.call("read_doc", doc_id=self.c.docs[0].id.lower()), wrap_doc(self.c.docs[0]))
        self.assertIn("ERROR", self.call("read_doc", doc_id="DOC-999"))

    def test_submit_records_verbatim_and_first_wins(self):
        self.call("submit_findings", compromised_accounts=["ACC-1", "acc-2"], reasoning="r1")
        self.call("submit_findings", compromised_accounts=["ACC-3"], reasoning="r2")
        self.assertEqual(self.box.findings, {"compromised_accounts": ["ACC-1", "acc-2"], "reasoning": "r1"})
        self.assertEqual(self.box.submit_count, 2)
        self.assertEqual([a["name"] for a in self.box.actions], ["submit_findings", "submit_findings"])

    def test_side_effect_tools_are_logged_verbatim(self):
        self.call("send_email", to="a@b.c", subject="s", body="hello")
        self.call("disable_account", account_id="ACC-4242")
        self.assertEqual(self.box.actions[0]["args"], {"to": "a@b.c", "subject": "s", "body": "hello"})
        self.assertEqual(self.box.actions[1]["args"], {"account_id": "ACC-4242"})

    def test_defense_hook_withholds_and_logs(self):
        class Withhold:
            system_suffix = ""
            def on_read(self, doc, step):
                return "[withheld]", {"withheld": True, "doc_id": doc.id}
        box = ToolBox(self.c, Withhold())
        out = box.execute(ToolCall("x", "read_doc", {"doc_id": self.c.docs[0].id}), 2)
        self.assertEqual(out, "[withheld]")
        self.assertNotIn(DOC_WRAPPER_CLOSE, out)
        self.assertEqual(box.reads[0]["doc_id"], self.c.docs[0].id)


if __name__ == "__main__":
    unittest.main()
