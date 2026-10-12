from brain_v12.azure_emulator.handoff import HandoffLedger, certify_default_handoff

def test_handoff_ledger_consumes_once(tmp_path):
    c=certify_default_handoff()
    ledger=HandoffLedger(tmp_path/"handoff.db")
    # Reproduce a valid evidence/plan through the public certificate shape is intentionally impossible:
    # consumption requires a ledger-issued certificate, so issue one from the same emulator helper internals.
    from brain_v12.azure_emulator.service import AzureEmulator
    cloud=AzureEmulator(free_only=True); cloud.create_windows_server_2025_vm("vm")
    ev=cloud.health_evidence("vm"); plan={"location":"emulated","vm_size":"small","os_image":"Windows Server 2025","free_only":True}
    c=ledger.issue(ev,plan)
    row=ledger.consume(c["certificate_id"])
    assert row["status"]=="ISSUED"
    try: ledger.consume(c["certificate_id"])
    except RuntimeError as e: assert str(e)=="HANDOFF_ALREADY_CONSUMED"
    else: raise AssertionError("handoff replay accepted")
    ledger.close()

def test_handoff_expiry_is_fail_closed(tmp_path):
    ledger=HandoffLedger(tmp_path/"handoff.db")
    from brain_v12.azure_emulator.service import AzureEmulator
    cloud=AzureEmulator(free_only=True); cloud.create_windows_server_2025_vm("vm")
    ev=cloud.health_evidence("vm"); plan={"location":"emulated","vm_size":"small","os_image":"Windows Server 2025","free_only":True}
    c=ledger.issue(ev,plan,ttl_seconds=1)
    try: ledger.consume(c["certificate_id"],now=c["expires_at"]+1)
    except RuntimeError as e: assert str(e)=="HANDOFF_EXPIRED"
    else: raise AssertionError("expired handoff accepted")
    ledger.close()
