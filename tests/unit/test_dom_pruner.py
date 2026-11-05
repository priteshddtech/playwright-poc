from framework.capture.dom_pruner import DomPruner


def test_pruner_keeps_interactive_tags() -> None:
    html = "<html><body>" + ("x" * 200_000) + '<button id="save">Save</button></body></html>'
    pruner = DomPruner(max_bytes=5000)
    pruned = pruner.prune(html, "#save")
    assert "<button" in pruned
    assert len(pruned.encode("utf-8")) <= 5000
