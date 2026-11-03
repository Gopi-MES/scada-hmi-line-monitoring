"""Exposes the simulated line as an OPC-UA server so a real SCADA platform
(e.g. Ignition) can connect to it as an OPC-UA client.

Node IDs use string identifiers in namespace 2, for example:
    ns=2;s=Line1/FILLER/StateCode
    ns=2;s=Line1/LINE/TankLevel

Run: python opcua_server.py   ->  opc.tcp://0.0.0.0:4841/linesim/
"""
import asyncio
import logging
import os

from asyncua import Server, ua

from line_simulator import STATIONS, LineSimulator, configure
from tags import TagDB

ENDPOINT = os.getenv("OPCUA_ENDPOINT", "opc.tcp://0.0.0.0:4841/linesim/")
STATE_CODES = {"IDLE": 0, "RUNNING": 1, "FAULT": 2}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("opcua")


def node_layout():
    """(tag-db name, OPC path, variant type) for every exposed node."""
    rows = []
    for s in STATIONS:
        rows += [
            (f"{s}.State", f"Line1/{s}/State", ua.VariantType.String),
            (f"{s}.State", f"Line1/{s}/StateCode", ua.VariantType.Int32),
            (f"{s}.Count", f"Line1/{s}/Count", ua.VariantType.Int32),
            (f"{s}.MotorTemp", f"Line1/{s}/MotorTemp", ua.VariantType.Double),
        ]
    rows += [
        ("LINE.Speed", "Line1/LINE/Speed", ua.VariantType.Double),
        ("LINE.TankLevel", "Line1/LINE/TankLevel", ua.VariantType.Double),
    ]
    return rows


def convert(path, value, vtype):
    if path.endswith("StateCode"):
        return STATE_CODES.get(value, -1)
    if vtype == ua.VariantType.Int32:
        return int(value)
    if vtype == ua.VariantType.Double:
        return float(value)
    return str(value)


async def main(period=1.0):
    db = TagDB("alarms.db")
    configure(db)
    LineSimulator(db, period=period).start()

    server = Server()
    await server.init()
    server.set_endpoint(ENDPOINT)
    server.set_server_name("LineSim OPC-UA Server")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    idx = await server.register_namespace("urn:linesim")

    folders, nodes = {}, []
    for tag, path, vtype in node_layout():
        parent_path = path.rsplit("/", 1)[0]
        if parent_path not in folders:
            parent = server.nodes.objects
            built = ""
            for part in parent_path.split("/"):
                built = f"{built}/{part}" if built else part
                if built not in folders:
                    folders[built] = await parent.add_folder(ua.NodeId(built, idx), part)
                parent = folders[built]
        initial = convert(path, db.tags[tag].value, vtype)
        node = await folders[parent_path].add_variable(
            ua.NodeId(path, idx), path.rsplit("/", 1)[1], ua.Variant(initial, vtype))
        nodes.append((tag, path, vtype, node))

    async with server:
        log.info("OPC-UA server at %s (%d nodes, namespace %d)", ENDPOINT, len(nodes), idx)
        while True:
            snap = db.snapshot()["tags"]
            for tag, path, vtype, node in nodes:
                await node.write_value(ua.Variant(convert(path, snap[tag]["value"], vtype), vtype))
            await asyncio.sleep(period)


if __name__ == "__main__":
    asyncio.run(main())
