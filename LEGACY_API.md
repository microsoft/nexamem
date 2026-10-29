# Legacy APIs and Migration

## V1 Compatibility Policy

NexaMem 1.x follows semantic versioning for its documented Python interfaces: the sync/async memory facades, configuration constructors, storage contracts, and optional integration classes. Patch releases correct defects; minor releases add backward-compatible functionality. Breaking documented interface changes and removal of retained legacy entry points require a future major release and migration notes. Bug fixes can correct behavior that contradicts documented guarantees; review each release's changelog before upgrading.

The compatibility entry points listed below remain supported throughout 1.x. Any planned removal will be announced in the changelog and migration guide before a future major release; no removal is scheduled for 1.0. Private names, undocumented implementation details, and protected internals of third-party SDKs are not extension contracts. Framework compatibility is limited to the supported dependency ranges and contracts in the [integration guide](INTEGRATIONS.md), not arbitrary upstream versions.

API compatibility does not promise automatic on-disk migration or stronger authorization, retention, concurrency, or encryption guarantees. The storage and channel migrations below still apply when moving from an older release to 1.0. Back up data and test the upgrade in a separate environment first.

## Retained APIs

The top-level `AIMemory` and `AsyncAIMemory` names refer to the configuration-driven API. Existing Redis-oriented classes remain available as `LegacyAIMemory` and `LegacyAsyncAIMemory`, or from `nexamem.aimemory`. This stabilization does not remove them.

`initialize`, `get_config`, and `ChatHistory` remain supported compatibility entry points. Initialization now loads the actual legacy configuration implementation instead of a silent no-op fallback.

```python
from nexamem import ChatHistory, initialize

initialize({"history_storage": "memory"})
history = ChatHistory()
history.add_user_message("Hello")
history.add_assistant_message("How can I help?")
assert len(history.get_history()) == 2
```

Legacy initialization is process-global. Configure it once per application and isolate tests that reset configuration. `ChatHistory` supports memory, file, SQLite, and Redis storage through that configuration. Caller-supplied SQL filter fragments must never be treated as safe for untrusted input.

The new facades' channel methods are compatibility conveniences, not a guarantee of the legacy Redis policy behavior. See [architecture](NEW_ARCHITECTURE.md) for unenforced options and retention limitations.

New-facade writes now apply channel TTL or a positive explicit override. Generic records support `default_ttl_sec` and per-write `ttl_sec`. Expiry is recorded in reserved metadata `_nexamem_expires_at`; old records without it remain nonexpiring until explicitly rewritten with a TTL. Legacy classes and direct backend APIs do not inherit this logical-expiry contract. Plan migration and audit/backup retention explicitly rather than assuming old data disappears after upgrade.

## Python and Dependencies

NexaMem 1.0 requires Python 3.11 or newer and upgrades dependency ranges. Applications using 3.8, 3.9, or 3.10 must upgrade their runtime before adopting 1.0. Legacy import names are retained; support for those older runtimes is not. The stable release passed the Python 3.11, 3.12, and 3.13 matrix on Linux, macOS, and Windows; see [release verification](PROJECT_STATUS.md).

## File Storage Migration

Memory IDs and scope names are now encoded before use as filenames. Ordinary safe filenames are unchanged. Identifiers containing colons, percent signs, path separators, or Windows device names can map to different filenames than older versions.

Back up existing stores before upgrading. Export records with the old version in a separate environment, then re-store them with the new version into a new directory, preserving logical IDs, metadata, scope, and any timestamps your migration requires. Do not blindly rename only memory files: scope indexes and audit references may also need rebuilding. There is no automatic on-disk migration utility, and re-storing through public CRUD generates new timestamps.

Windows paths are case-insensitive by default; avoid IDs that differ only by case. Respect filesystem filename limits. Atomic replacement of one record does not make concurrent multi-file updates transactional.

## Channel Scope Migration

New-facade compatibility channel keys now include `env`. Older records used `agent:user:session:channel` and could mix environments. New readers intentionally do not fall back to those ambiguous keys.

Before upgrading an existing store, export and classify affected records using trusted application context, then re-store them into the correct environment scopes. Do not infer the original environment from an ambiguous old key alone. The metadata `scope_dict` may help, but should be verified before trusting it for migration. No automatic channel-key migration is supplied.

Keep delimiter-free, application-validated scope identifiers and channel names. Prefix construction is a naming scheme, not authorization or protection against adversarial delimiter/glob inputs.

## Behavior Repairs

- Overwriting memory preserves creation time and removes stale scope-index membership.
- UTF-8 bytes passed to the new facade's `write()` are decoded as text; invalid UTF-8 raises rather than storing a Python bytes representation.
- Failed JSON serialization no longer overwrites an existing file record.
- Redis generic-memory overwrite operations update scope membership; collection erasure removes only the requested user's/session's message fields and indexes.
- Legacy Redis queries skip non-string index keys, and sync audit reads use the Redis stream range API correctly.
- New facades support owned-resource context managers; DI-supplied storage remains borrowed. Async file/SQLite data operations offload I/O and wait for an in-flight worker before propagating cancellation.
- Optional framework adapters are independent of legacy `ChatHistory`; see [their public contracts](INTEGRATIONS.md).

Test application-specific ordering, storage formats, and retention assumptions on a copy of production data before rollout.