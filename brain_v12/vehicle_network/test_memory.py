from brain_v12.vehicle_network.memory import initialize, summary


def test_honda_network_memory_initializes_and_persists(tmp_path):
    db_path = tmp_path / "state" / "honda.sqlite3"

    initialize(db_path)
    first = summary(db_path)

    assert first["vehicle"]["model"] == "e:NP1"
    assert first["head_unit"]["software_version"] == "01.000.400"
    assert first["phone"]["phone_model"] == "Realme RMX3710 / C66"
    assert first["primary_goal"]["status"] == "active"
    assert {item["blocker_key"] for item in first["blockers"]} == {
        "usb_tethering", "carlife_video", "connect_qr"
    }

    initialize(db_path)
    second = summary(db_path)
    assert len(second["blockers"]) == 3
    assert len(second["blockers"]) == len(first["blockers"])


def test_status_summary_on_uninitialized_database_is_safe(tmp_path):
    db_path = tmp_path / "new.sqlite3"
    initialize(db_path)
    result = summary(db_path)
    assert result["primary_goal"]["title"].startswith("Enable reliable Android app connectivity")
