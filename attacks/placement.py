"""Insert a payload into the corpus at a parameterised placement. Returns a NEW corpus."""
from __future__ import annotations

from attacks.payloads import render_payload, render_placebo


def host_id(corpus, placement):
    return corpus.host_evidence_id if placement == "evidence" else corpus.host_peripheral_id


def inject_text(corpus, doc_id, text, position="end"):
    """Pure insertion into document text. The system prompt and user turn are never touched."""
    new = corpus.copy()
    d = new.doc(doc_id)
    if position == "end":
        d.text = d.text.rstrip() + "\n\n" + text.strip("\n") + "\n"
    else:
        d.text = text.strip("\n") + "\n\n" + d.text
    return new


def apply_payload(corpus, family, placement="evidence", framing="plain"):
    text, target, framing_used = render_payload(corpus, family, framing)
    hid = host_id(corpus, placement)
    new = inject_text(corpus, hid, text)
    meta = {"family": family, "placement": placement, "framing": framing_used, "host_id": hid,
            "payload_text": text, "payload_words": len(text.split()), "target": target}
    return new, meta


def apply_placebo(corpus, placement="evidence", n_words=60):
    hid = host_id(corpus, placement)
    text = render_placebo(corpus, n_words)
    new = inject_text(corpus, hid, text)
    return new, {"family": "placebo", "placement": placement, "framing": "plain", "host_id": hid,
                 "payload_text": text, "payload_words": n_words, "target": {}}
