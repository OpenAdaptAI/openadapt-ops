# Azure temporary-VM cost guard

This guard protects subscription `78add6c6-c92a-4a53-b751-eb644ac77e59`.
It is report-only by default. It never deletes an Azure resource.

## Run it

```bash
python scripts/azure_cost_guard.py
```

The guard reports each running VM that has either:

- `temporary:true`; or
- an `autostop` tag on the VM or its resource group.

It reports the resource ID, age in hours, power state, SKU, owner, lease expiry, and
the latest available daily compute cost from Azure Cost Management. The default
cost threshold is CAD 5.00 per day. Exit status `2` means that a running
temporary/autostop VM has no active owner lease. The report also states whether
its known cost reached the threshold. This fails visibly even when Azure cost
data arrives late.

## Scheduled monitor setup

`.github/workflows/azure-cost-guard.yml` runs once each day and only reports.
It becomes active when the repository secret `AZURE_CREDENTIALS` exists.

Use a service-principal JSON credential for the target subscription with these
minimum roles:

- `Reader` for resource state and tags.
- `Cost Management Reader` for the daily cost estimate.

Do not grant `Contributor` while the workflow stays report-only. The workflow
does not pass `--action deallocate`, `--apply`, or `--confirm-deallocate`.
The current repository has no `AZURE_CREDENTIALS` secret, so the scheduled job
will skip until this secret is added.

## Lease protection

Use both tags for an active qualification job:

```text
owner=qualification-openemr
lease_expires_at=2026-08-02T18:00:00Z
```

The guard treats a VM as protected only when both tags exist and the expiry is
in the future. A missing, malformed, or expired lease is not protected.

## Explicit deallocation

The guard can deallocate an unprotected candidate. It never deletes a VM,
disk, IP address, snapshot, or resource group.

```bash
python scripts/azure_cost_guard.py \
  --action deallocate --apply --confirm-deallocate \
  --recovery-snapshot-id /subscriptions/78add6c6-c92a-4a53-b751-eb644ac77e59/resourceGroups/openadapt-qualification-temp-20260726/providers/Microsoft.Compute/snapshots/openemr-qual-20260726-predeallocate-20260801
```

Use this only after the workflow owner confirms that the job ended. A VM can
still incur disk and static-IP cost after deallocation.

## OpenEMR qualification recovery note

The current temporary VM is:

```text
openemr-qual-20260726
openadapt-qualification-temp-20260726
```

Before any planned deallocation, verify the recovery snapshot:

```text
openemr-qual-20260726-predeallocate-20260801
```

Azure reports this exact resource as `Succeeded`:

```text
/subscriptions/78add6c6-c92a-4a53-b751-eb644ac77e59/resourceGroups/openadapt-qualification-temp-20260726/providers/Microsoft.Compute/snapshots/openemr-qual-20260726-predeallocate-20260801
```

The explicit deallocation path verifies this ID and state before it sends a VM
deallocation request. Record the VM ID, disk ID, snapshot ID, and the qualified
bundle/report hashes in the qualification record. Deallocation preserves the
VM disk. Delete the resource group only after the evidence export and recovery
decision.
