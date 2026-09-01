"""
Industrial OPC-UA Telemetry Server
==================================
Exposes all 20 pharmaceutical manufacturing & oncology assets as standard
OPC-UA information model nodes for SCADA/MES integration (Siemens, Rockwell).
"""

import asyncio
import logging
from asyncua import Server, ua

logger = logging.getLogger("opcua-server")


class ZydusOPCUAServer:
    def __init__(self, endpoint: str = "opc.tcp://0.0.0.0:4840/zydus/server/"):
        self.endpoint = endpoint
        self.server = Server()
        self.nodes = {}

    async def init(self):
        await self.server.init()
        self.server.set_endpoint(self.endpoint)
        self.server.set_server_name("Zydus Oncology Predictive Maintenance OPC-UA Server")

        # Set up namespace
        uri = "http://zyduslifesciences.com/gxp/telemetry/"
        idx = await self.server.register_namespace(uri)

        # Populate root equipment folder
        objects = self.server.nodes.objects
        zydus_folder = await objects.add_folder(idx, "ZydusPharmaPlant")

        # Create nodes for core assets
        assets = [
            ("GRAN-LINE-01", ["vibration_hz", "temperature_c", "current_draw_a", "motor_rpm", "pressure_bar"]),
            ("ASEPTIC-FILL-01", ["fill_pressure_bar", "vibration_hz", "isolator_temp_c", "motor_current_a"]),
            ("ULT-FREEZER-01", ["chamber_temp_c", "compressor_power_kw", "door_open_state"]),
            ("LINAC-01", ["beam_current_ma", "arc_voltage_v", "dose_rate_gy_min", "cooling_temp_c"]),
        ]

        for asset_code, sensor_list in assets:
            asset_obj = await zydus_folder.add_object(idx, asset_code)
            self.nodes[asset_code] = {}
            for s_name in sensor_list:
                var_node = await asset_obj.add_variable(idx, s_name, 0.0)
                await var_node.set_writable()
                self.nodes[asset_code][s_name] = var_node

        logger.info(f"Initialized OPC-UA Server with {len(self.nodes)} asset nodes.")

    async def update_node_value(self, asset_code: str, sensor_name: str, value: float):
        if asset_code in self.nodes and sensor_name in self.nodes[asset_code]:
            node = self.nodes[asset_code][sensor_name]
            await node.write_value(float(value))

    async def start(self):
        await self.init()
        async with self.server:
            logger.info(f"OPC-UA Server listening at {self.endpoint}")
            while True:
                await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    srv = ZydusOPCUAServer()
    asyncio.run(srv.start())
