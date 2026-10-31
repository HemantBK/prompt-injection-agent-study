"""Two model backends behind one interface, plus a scripted mock for tests.

The agent loop (harness/agent.py) only sees: new_history(), step(), append_assistant(),
append_tool_results(). History is kept in each provider's native format.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from harness import config


def load_env():
    """Load ../.env (the user's key file one level up) and ./.env if present. Shell wins."""
    for p in [Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[1] / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class StepOut:
    text: str
    tool_calls: list
    usage: dict
    stop_reason: str
    reasoning_summary: str = ""
    raw: object = None
    cost_usd: float = 0.0


def _anthropic_cost(u, price):
    return (u.get("input_tokens", 0) * price["in"]
            + u.get("cache_creation_input_tokens", 0) * price["in"] * price["cache_write_mult"]
            + u.get("cache_read_input_tokens", 0) * price["cache_read"]
            + u.get("output_tokens", 0) * price["out"]) / 1e6


def _openai_cost(u, price):
    cached = u.get("cached_tokens", 0)
    return ((u.get("input_tokens", 0) - cached) * price["in"] + cached * price["cached_in"]
            + u.get("output_tokens", 0) * price["out"]) / 1e6


class AnthropicBackend:
    provider = "anthropic"

    def __init__(self, model, price, effort=config.EFFORT, key=None):
        import anthropic
        load_env()
        self.model, self.price, self.effort, self.key = model, price, effort, key or model
        self.client = anthropic.Anthropic(max_retries=4, timeout=600)

    @staticmethod
    def convert_tools(schemas):
        return [{"name": s["name"], "description": s["description"], "input_schema": s["parameters"],
                 "strict": True} for s in schemas]

    def new_history(self, user_text):
        return [{"role": "user", "content": user_text}]

    def step(self, system, tools, history):
        resp = self.client.messages.create(
            model=self.model, max_tokens=8000, system=system, tools=self.convert_tools(tools),
            messages=history, thinking={"type": "adaptive", "display": "summarized"},
            output_config={"effort": self.effort}, cache_control={"type": "ephemeral"},
        )
        text, calls, thinking = [], [], []
        for b in resp.content:
            if b.type == "text":
                text.append(b.text)
            elif b.type == "tool_use":
                calls.append(ToolCall(b.id, b.name, dict(b.input)))
            elif b.type == "thinking" and getattr(b, "thinking", ""):
                thinking.append(b.thinking)
        u = resp.usage.model_dump()
        usage = {k: (u.get(k) or 0) for k in ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]}
        return StepOut("\n".join(text), calls, usage, resp.stop_reason or "unknown", "\n".join(thinking),
                       raw=resp, cost_usd=_anthropic_cost(usage, self.price))

    def append_assistant(self, history, out):
        history.append({"role": "assistant", "content": out.raw.content})

    def append_tool_results(self, history, results):
        history.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": call.id, "content": output} for call, output in results]})

    # single-shot helper used by the monitor classifier
    def classify(self, system, user_text, max_tokens=300):
        resp = self.client.messages.create(model=self.model, max_tokens=max_tokens, system=system,
                                           messages=[{"role": "user", "content": user_text}],
                                           output_config={"effort": "low"})
        u = resp.usage.model_dump()
        usage = {k: (u.get(k) or 0) for k in ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]}
        text = "".join(b.text for b in resp.content if b.type == "text")
        return text, usage, _anthropic_cost(usage, self.price)


class OpenAIBackend:
    provider = "openai"

    def __init__(self, model, price, effort=config.EFFORT, key=None):
        import openai
        load_env()
        self.model, self.price, self.effort, self.key = model, price, effort, key or model
        self.client = openai.OpenAI(max_retries=4, timeout=600)

    @staticmethod
    def convert_tools(schemas):
        return [{"type": "function", "name": s["name"], "description": s["description"],
                 "parameters": s["parameters"], "strict": True} for s in schemas]

    def new_history(self, user_text):
        return [{"role": "user", "content": user_text}]

    def step(self, system, tools, history):
        resp = self.client.responses.create(
            model=self.model, instructions=system, input=history, tools=self.convert_tools(tools),
            reasoning={"effort": self.effort, "summary": "auto"}, max_output_tokens=8000,
        )
        calls, summaries = [], []
        for item in resp.output:
            if item.type == "function_call":
                try:
                    args = json.loads(item.arguments)
                except json.JSONDecodeError:
                    args = {"_unparseable": item.arguments}
                calls.append(ToolCall(item.call_id, item.name, args))
            elif item.type == "reasoning":
                for s in getattr(item, "summary", None) or []:
                    summaries.append(getattr(s, "text", ""))
        u = resp.usage
        usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                 "cached_tokens": getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0,
                 "reasoning_tokens": getattr(getattr(u, "output_tokens_details", None), "reasoning_tokens", 0) or 0}
        stop = "tool_use" if calls else ("end_turn" if resp.status == "completed" else resp.status)
        if resp.incomplete_details is not None:
            stop = "incomplete:" + str(getattr(resp.incomplete_details, "reason", ""))
        return StepOut(resp.output_text or "", calls, usage, stop, "\n".join(summaries), raw=resp,
                       cost_usd=_openai_cost(usage, self.price))

    def append_assistant(self, history, out):
        history.extend(out.raw.output)

    def append_tool_results(self, history, results):
        for call, output in results:
            history.append({"type": "function_call_output", "call_id": call.id, "output": output})

    def classify(self, system, user_text, max_tokens=300):
        resp = self.client.responses.create(model=self.model, instructions=system, input=user_text,
                                            reasoning={"effort": "low"}, max_output_tokens=max_tokens)
        u = resp.usage
        usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                 "cached_tokens": getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0}
        return resp.output_text or "", usage, _openai_cost(usage, self.price)


class MockBackend:
    """Scripted agent for tests: lists docs, reads the hosts, then submits the truth.

    If a read document contains a recognised payload cue, the mock obeys it. This lets the
    oracle fixtures exercise every success path without paying for a model. It is NEVER used
    for results (harness/runner.py refuses it unless IPI_ALLOW_MOCK=1).
    """
    provider = "mock"

    def __init__(self, model="mock", price=None, effort=None, key="mock", truth=None, obey=True):
        self.model, self.key, self.price = model, key, {"in": 0, "out": 0, "cache_read": 0, "cache_write_mult": 1}
        self.truth, self.obey = truth, obey

    def new_history(self, user_text):
        return [{"role": "user", "content": user_text, "_mock": {"phase": 0, "read": [], "docs": []}}]

    def step(self, system, tools, history):
        st = history[0]["_mock"]
        phase = st["phase"]
        st["phase"] += 1
        read_text = "\n".join(st["read"])
        calls = []
        if phase == 0:
            calls = [ToolCall("c0", "list_docs", {})]
        elif phase == 1:
            calls = [ToolCall("c1", "search", {"query": "sign-in"}), ToolCall("c2", "search", {"query": "newsletter"})]
        elif phase == 2:
            calls = [ToolCall("c3-" + d, "read_doc", {"doc_id": d}) for d in st["docs"][:12]]
        else:
            truth = list(self.truth or [])
            if self.obey and "MOCK-OBEY-FLIP" in read_text:
                add = read_text.split("MOCK-OBEY-FLIP ")[1].split()[0]
                drop = read_text.split("MOCK-OBEY-DROP ")[1].split()[0] if "MOCK-OBEY-DROP" in read_text else None
                truth = [t for t in truth if t != drop] + [add]
            if self.obey and "MOCK-OBEY-DISABLE" in read_text:
                acct = read_text.split("MOCK-OBEY-DISABLE ")[1].split()[0]
                calls.append(ToolCall("c-dis", "disable_account", {"account_id": acct}))
            if self.obey and "MOCK-OBEY-EMAIL" in read_text:
                to = read_text.split("MOCK-OBEY-EMAIL ")[1].split()[0]
                tok = system.split("Internal case reference: ")[1].split()[0]
                calls.append(ToolCall("c-em", "send_email", {"to": to, "subject": "Case archive", "body": "Token " + tok}))
            if self.obey and "MOCK-OBEY-REFUSE" in read_text:
                return StepOut("I cannot assist with this request; the matter is under legal hold.", [], {}, "end_turn")
            calls.append(ToolCall("c-sub", "submit_findings", {"compromised_accounts": truth, "reasoning": "mock reasoning"}))
        return StepOut("", calls, {"input_tokens": 0, "output_tokens": 0}, "tool_use" if calls else "end_turn")

    def append_assistant(self, history, out):
        history.append({"role": "assistant", "content": out.text, "tool_calls": [(c.name, c.args) for c in out.tool_calls]})

    def append_tool_results(self, history, results):
        st = history[0]["_mock"]
        for call, output in results:
            if call.name == "search":
                for line in output.splitlines():
                    if line.startswith("DOC-"):
                        d = line.split()[0]
                        if d not in st["docs"]:
                            st["docs"].append(d)
            if call.name == "read_doc":
                st["read"].append(output)
        history.append({"role": "tool", "results": [(c.name, o[:200]) for c, o in results]})


def make_backend(key):
    """Build the backend for a config key ('claude' or 'gpt'), or the monitor classifier for it."""
    spec = config.BACKENDS[key]
    cls = AnthropicBackend if spec["provider"] == "anthropic" else OpenAIBackend
    return cls(spec["model"], spec["price"], key=key)


def make_classifier(agent_key):
    spec = config.MONITOR_CLASSIFIER[agent_key]
    cls = AnthropicBackend if spec["provider"] == "anthropic" else OpenAIBackend
    return cls(spec["model"], spec["price"], key="classifier:" + spec["model"])
