import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / "workflows"


def workflow_files():
    return sorted(WORKFLOWS.rglob("*.json"))


@pytest.mark.parametrize("path", workflow_files(), ids=lambda path: str(path.relative_to(ROOT)))
def test_workflow_json_and_graph_references_are_valid(path: Path):
    workflow = json.loads(path.read_text(encoding="utf-8"))
    if "nodes" in workflow:
        _validate_ui_workflow(workflow)
    else:
        _validate_api_graph(workflow)


def _validate_ui_workflow(workflow: dict) -> None:
    nodes = {node["id"]: node for node in workflow["nodes"]}
    raw_links = workflow["links"]
    if raw_links and isinstance(raw_links[0], dict):
        links = {
            link["id"]: (
                link["id"],
                link["origin_id"],
                link["origin_slot"],
                link["target_id"],
                link["target_slot"],
                link["type"],
            )
            for link in raw_links
        }
    else:
        links = {link[0]: link for link in raw_links}
    assert len(nodes) == len(workflow["nodes"])
    assert len(links) == len(raw_links)

    for subgraph in workflow.get("definitions", {}).get("subgraphs", []):
        _validate_ui_workflow(subgraph)

    input_node = workflow.get("inputNode", {}).get("id")
    output_node = workflow.get("outputNode", {}).get("id")
    for link_id, (_, source_id, source_slot, target_id, target_slot, _type) in links.items():
        if source_id == input_node:
            assert source_slot < len(workflow.get("inputs", [])), link_id
        else:
            assert source_id in nodes, link_id
            assert source_slot < len(nodes[source_id].get("outputs", [])), link_id
        if target_id == output_node:
            assert target_slot < len(workflow.get("outputs", [])), link_id
        else:
            assert target_id in nodes, link_id
            assert target_slot < len(nodes[target_id].get("inputs", [])), link_id

    for node in nodes.values():
        for input_spec in node.get("inputs", []):
            if input_spec.get("link") is not None:
                assert input_spec["link"] in links
        for output_spec in node.get("outputs", []):
            for link_id in output_spec.get("links") or []:
                assert link_id in links


def _validate_api_graph(graph: dict) -> None:
    assert graph
    for node_id, node in graph.items():
        assert node.get("class_type"), node_id
        for value in node.get("inputs", {}).values():
            if (
                isinstance(value, list)
                and len(value) == 2
                and isinstance(value[0], str)
                and value[0].isdigit()
            ):
                assert value[0] in graph, (node_id, value)
                assert isinstance(value[1], int), (node_id, value)
