from brain_v12.blade_server import BladeServer
from brain_v12.brain.resource_fabric import ResourceFabric
from brain_v12.brain.resource_manager import ResourceManager
from brain_v12.brain.vdc_resource_provider import VirtualDatacenterResourceProvider
from brain_v12.brain.virtual_datacenter import BrainVirtualDatacenter
from brain_v12.virtual_hardware.computer import VirtualComputer


def _vdc_with_two_blades():
    vdc = BrainVirtualDatacenter()
    for index in range(2):
        blade_id = f"blade-test-{index}"
        blade = BladeServer(
            blade_id,
            VirtualComputer(
                blade_id,
                ram_size=8 * 1024**3,
                storage_size=128 * 1024**3,
            ),
        )
        blade.power_on()
        vdc.chassis.blades[blade_id] = blade
    return vdc


def test_server_components_are_colocated_and_accounted():
    vdc = _vdc_with_two_blades()
    fabric = ResourceFabric()
    vdc.sync_resource_fabric(fabric)
    provider = VirtualDatacenterResourceProvider(vdc, fabric)

    result = provider.compose_server(
        "vm-1",
        cpu_cores=1,
        ram_bytes=2 * 1024**3,
        storage_bytes=16 * 1024**3,
        network=True,
        gpu=True,
    )

    assert result["ok"] is True
    blade_id = result["blade_id"]
    allocation_blades = {
        fabric.resources[x["resource_id"]].attributes["blade_id"]
        for x in result["allocations"]
    }
    assert allocation_blades == {blade_id}
    assert vdc.resource_manager.reservations["vm-1"].blade_id == blade_id


def test_release_returns_capacity_to_both_layers():
    vdc = _vdc_with_two_blades()
    fabric = ResourceFabric()
    vdc.sync_resource_fabric(fabric)
    provider = VirtualDatacenterResourceProvider(vdc, fabric)

    result = provider.compose_server("vm-2", ram_bytes=2 * 1024**3, storage_bytes=16 * 1024**3)
    assert result["ok"] is True
    reservation_id = result["reservation_id"]
    assert len(fabric.inspect()["reservations"]) == 1
    assert "vm-2" in vdc.resource_manager.reservations

    released = provider.release(reservation_id)
    assert released["ok"] is True
    assert len(fabric.inspect()["reservations"]) == 0
    assert "vm-2" not in vdc.resource_manager.reservations


def test_fabric_sync_excludes_vdc_reserved_capacity():
    vdc = _vdc_with_two_blades()
    fabric = ResourceFabric()
    vdc.sync_resource_fabric(fabric)
    provider = VirtualDatacenterResourceProvider(vdc, fabric)

    result = provider.compose_server("vm-3", ram_bytes=2 * 1024**3, storage_bytes=16 * 1024**3)
    assert result["ok"] is True
    blade_id = result["blade_id"]

    fabric2 = ResourceFabric()
    vdc.sync_resource_fabric(fabric2)
    ram = fabric2.resources[f"vdc:{blade_id}:ram"]
    storage = fabric2.resources[f"vdc:{blade_id}:storage"]
    assert ram.capacity == 6
    assert storage.capacity == 112
