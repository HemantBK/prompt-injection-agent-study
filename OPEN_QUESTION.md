# Sharpest open question

The study could not resolve whether any **read-time** defense can protect a document-reading
agent from forged records. Every instruction-style injection failed on its own (0/20 in five
families on two model families), and the monitor built to catch instructions had nothing to
catch; the one attack that worked was a single forged log line with no instruction in it, which
flipped 20/20 on both backends even though the agents had the clean mailbox audit in context and
could, in principle, have noticed that the forged row implied a rule the audit did not list. A
content classifier cannot flag a well-formed log line as "injection" without flagging every log
line, and the agents did not do the cross-document consistency check that would have exposed it.

The experiment that would settle it has two arms on the same seeds and the same forged rows.
Arm A: provenance at the corpus boundary — each record carries an integrity attestation (a
per-document signature or a hash chain), and the agent is told which records fail verification;
measure whether flip rate drops to the noise floor and what it costs in clean-task accuracy when
legitimate late exports are unsigned. Arm B: a consistency-checking step — before submission the
agent (or a cross-family checker) must list, for every accused account, the independent records
that corroborate each piece of evidence and name any record that should exist and does not (a
forwarding rule with no audit entry, a sign-in with no MFA event); measure the same flip rate and
the false-accusation rate on clean corpora. If A works and B does not, the problem is
epistemic and belongs to the data pipeline, not the model. If B works, the fix is a reasoning
procedure and the question becomes how it generalizes to forgeries that are internally
consistent across documents, which this corpus did not contain.
