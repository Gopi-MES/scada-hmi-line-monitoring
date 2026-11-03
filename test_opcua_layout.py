import json

from opcua_server import convert, node_layout


def leaf_paths(folder):
    for t in folder["tags"]:
        if t["tagType"] == "Folder":
            yield from leaf_paths(t)
        else:
            yield t["opcItemPath"].split(";s=", 1)[1]


def test_every_ignition_tag_has_an_opc_node():
    with open("ignition_tags.json", encoding="utf-8") as f:
        tags = json.load(f)
    served = {path for _, path, _ in node_layout()}
    assert set(leaf_paths(tags)) <= served


def test_state_code_mapping():
    from asyncua import ua
    assert convert("Line1/FILLER/StateCode", "FAULT", ua.VariantType.Int32) == 2
    assert convert("Line1/FILLER/StateCode", "RUNNING", ua.VariantType.Int32) == 1
