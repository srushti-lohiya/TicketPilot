"""Tests the LLM tool-use loop with a fake client (no API key, no network)."""
from types import SimpleNamespace as NS
from src import agent, store


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        usage = NS(input_tokens=100, output_tokens=20)
        if self.calls == 1:   # first turn: the model asks for a tool
            return NS(stop_reason="tool_use", usage=usage,
                      content=[NS(type="tool_use", id="t1", name="lookup_order", input={"order_id": "10233"})])
        # second turn: it must have received the tool result
        assert kw["messages"][-1]["content"][0]["type"] == "tool_result"
        return NS(stop_reason="end_turn", usage=usage, content=[NS(type="text",
                  text="Your lamp (order 10233) has shipped, tracking 1Z999AA10233.\nCITATIONS: shipping#tracking")])


def test_llm_agent_loop(monkeypatch):
    store.init_db()
    fake = FakeClient()
    monkeypatch.setattr(agent, "client", lambda: fake)
    hits = [{"id": "shipping#tracking", "title": "Shipping - Tracking", "text": "A tracking number is emailed."}]
    out = agent.LLMAgent().run("where is order 10233", {"intent": "track_order", "confidence": 0.9, "priority": "P4"}, hits)
    assert out["citations"] == ["shipping#tracking"]
    assert out["actions"][0]["tool"] == "lookup_order" and out["actions"][0]["output"]["status"] == "Shipped"
    assert out["tokens_in"] == 200 and "CITATIONS" not in out["reply"]
