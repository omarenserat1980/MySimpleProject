"""Read-only cloud provider discovery adapters.

This module never provisions, modifies, or deletes cloud resources. Provider
discovery is not proof of zero cost or immediately available capacity.
Unknown facts remain unknown so the capacity gate can fail closed.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

CommandRunner = Callable[[Sequence[str], int], tuple[int, str, str]]


def _subprocess_runner(command: Sequence[str], timeout: int) -> tuple[int, str, str]:
    try:
        result = subprocess.run(list(command), capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"


@dataclass(frozen=True)
class ProviderSnapshot:
    schema: str
    provider: str
    observed_at: str
    account_verified: bool
    subscription_id: str | None
    region: str
    sku: str
    sku_found: bool | None
    sku_restrictions: tuple[str, ...]
    vcpu_quota_limit: int | None
    vcpu_quota_used: int | None
    memory_mb: int | None
    storage_gb: int | None
    estimated_monthly_cost_usd: str | None
    free_tier_eligible: bool | None
    source_ref: str | None
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "provider": self.provider,
            "observed_at": self.observed_at,
            "account_verified": self.account_verified,
            "subscription_id": self.subscription_id,
            "region": self.region,
            "sku": self.sku,
            "sku_found": self.sku_found,
            "sku_restrictions": list(self.sku_restrictions),
            "vcpu_quota_limit": self.vcpu_quota_limit,
            "vcpu_quota_used": self.vcpu_quota_used,
            "memory_mb": self.memory_mb,
            "storage_gb": self.storage_gb,
            "estimated_monthly_cost_usd": self.estimated_monthly_cost_usd,
            "free_tier_eligible": self.free_tier_eligible,
            "provider_verified": self.account_verified and not self.errors,
            "source_ref": self.source_ref,
            "errors": list(self.errors),
            "provisioning_performed": False,
            "paid_fallback_allowed": False,
        }


class AzureReadOnlyProviderAdapter:
    """Read account, regional VM quota, and SKU metadata through Azure CLI.

    Requires an already-authenticated Azure CLI session. All commands are
    read-only. Price remains unknown because quota and SKU presence do not
    establish zero cost.
    """
    provider = "azure"

    def __init__(self, runner: CommandRunner | None = None, *, timeout_seconds: int = 20,
                 now: Callable[[], datetime] | None = None) -> None:
        if timeout_seconds < 1:
            raise ValueError("PROVIDER_TIMEOUT_INVALID")
        self._runner = runner or _subprocess_runner
        self._timeout = timeout_seconds
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _json(self, args: Sequence[str], errors: list[str]) -> Any | None:
        code, stdout, stderr = self._runner(["az", *args], self._timeout)
        if code != 0:
            errors.append(f"AZ_CLI_FAILED:{args[0]}:{(stderr or stdout).strip()[:240]}")
            return None
        try:
            return json.loads(stdout)
        except (json.JSONDecodeError, TypeError):
            errors.append(f"AZ_CLI_INVALID_JSON:{args[0]}")
            return None

    @staticmethod
    def _as_nonnegative_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        try:
            result = int(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return result if result >= 0 else None

    def inspect_region(self, region: str, sku: str) -> dict[str, Any]:
        """Read account, regional VM quota, and SKU metadata only."""
        if not region.strip() or not sku.strip():
            raise ValueError("PROVIDER_REGION_AND_SKU_REQUIRED")
        errors: list[str] = []
        account = self._json(["account", "show", "--output", "json"], errors)
        subscription_id = str(account.get("id")).strip() if isinstance(account, Mapping) and account.get("id") else None
        account_verified = bool(subscription_id and isinstance(account, Mapping))

        usages = self._json(["vm", "list-usage", "--location", region, "--output", "json"], errors)
        skus = self._json(["vm", "list-skus", "--location", region, "--all", "--output", "json"], errors)

        vcpu_limit = None
        vcpu_used = None
        if isinstance(usages, list):
            for item in usages:
                if not isinstance(item, Mapping) or not isinstance(item.get("name"), Mapping):
                    continue
                label = str(item["name"].get("value", "")).lower().replace(" ", "")
                if label in {"cores", "totalregionalvcpus", "standarddsfamilyvcpus"}:
                    vcpu_limit = self._as_nonnegative_int(item.get("limit"))
                    vcpu_used = self._as_nonnegative_int(item.get("currentValue"))
                    if label in {"cores", "totalregionalvcpus"}:
                        break

        matched_sku: Mapping[str, Any] | None = None
        if isinstance(skus, list):
            for item in skus:
                if isinstance(item, Mapping) and str(item.get("name", "")).lower() == sku.lower():
                    matched_sku = item
                    break

        restrictions: list[str] = []
        if matched_sku and isinstance(matched_sku.get("restrictions"), list):
            for restriction in matched_sku["restrictions"]:
                if isinstance(restriction, Mapping):
                    reason = restriction.get("reasonCode") or restriction.get("type") or "RESTRICTED"
                    restrictions.append(str(reason))

        source = f"azure-cli-readonly:{subscription_id}:{region}:{sku}" if account_verified and not errors else None
        snapshot = ProviderSnapshot(
            schema="brain.cloud-provider-snapshot.v1",
            provider=self.provider,
            observed_at=self._now().astimezone(timezone.utc).isoformat(),
            account_verified=account_verified,
            subscription_id=subscription_id,
            region=region,
            sku=sku,
            sku_found=(matched_sku is not None) if isinstance(skus, list) else None,
            sku_restrictions=tuple(restrictions),
            vcpu_quota_limit=vcpu_limit,
            vcpu_quota_used=vcpu_used,
            memory_mb=None,
            storage_gb=None,
            estimated_monthly_cost_usd=None,
            free_tier_eligible=None,
            source_ref=source,
            errors=tuple(errors),
        )
        return snapshot.to_dict()
