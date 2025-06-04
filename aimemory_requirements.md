
# AIMemory MVP Requirements
*Version 0.3 – incorporates feedback on scope, channels, and terminology*

---

## 1 Purpose  
AIMemory is a **Python library** that provides governed, Redis‑backed conversational memory for Itaú AI components (orchestrator, GPT fallback, domain agents).  
This document defines the MVP feature‑set and acceptance criteria.

---

## 2 Scope  
| In scope (MVP) | Out of scope (future) |
| --- | --- |
| Redis‑backed channels (user‑defined) | Cosmos vector store (`semantic`, `long_term`) |
| Sync **and** async client classes | Promotion job (working → semantic) |
| YAML channel config (TTL, encryption, quota) | Full PII NER detector |
| Policy enforcement, quotas, AES toggle | Sphinx docs |
| Base metrics capturing | Audit stream and Multi‑endpoint balancing |

---

## 3 Architecture Snapshot  

```
Caller → AIMemory Facade
         │
         ▼
 PolicyEngine  (TTL / quota / PII)
 ContentProcessor chain (redact / enrich)  [optional]
         │
         ▼
 RedisAdapter  (sync / async)
         │
         ▼
Azure Cache for Redis
```

An **AuditSink** mirrors every operation as JSON into a Redis Stream (TTL 365 d).

---

## 4 MemoryScope & Key Scheme  

### 4.1 MemoryScope  

```python
scope = MemoryScope(
    agent_id="invest_agent",
    user_id="u12345",      # hashed customer id
    session_id="s98765",   # chat session uuid
    env="prod"             # optional, defaults to 'prod'
)
```

*Why an `env` field?*  
Many teams deploy the **same code** to *dev*, *stg*, and *prod* AKS namespaces while sharing a single Redis endpoint.  
Including `env` (default `"prod"`) in the key lets us isolate data per environment without additional Redis clusters.  
If you don’t need it, leave it as the default or set it to `""`.


### 4.2 Key format  

```
{env}:{agent_id}:{user_id}:{session_id}:{channel}:{uuid}
```

A sorted‑set index `<env>:<agent>:<user>:<sess>:<channel>:index` stores `(score=epoch_ts, member=uuid)`.

---

## 5 Channels  

AIMemory does **not** hard‑code channels; each team declares what it needs in YAML:

```yaml
channels:
  working:          # recent dialogue
    ttl_sec: 14400
    encrypt: true

  procedure:        # workflow checkpoints
    ttl_sec: 604800
    encrypt: true

  routing:          # breadcrumbs, classifier hints
    ttl_sec: 86400
    encrypt: false
```

- **Orchestrator** typically uses `routing` and `working`.  
- **GPT fallback** may use `working` plus future `semantic`.  
- **Domain agents** usually need `working` (their own turns) and `procedure`.  
New channels can be added by editing YAML or programmatically:

```python
mem.register_channel("scratch", ttl_sec=60, encrypt=False)
```

---


### 7.1  Dynamic Channel Registration

`register_channel()` lets callers create or tweak a channel **at runtime** without touching `channels.yaml`:

```python
mem.register_channel(
    name="scratch",
    ttl_sec=60,        # 1 minute
    encrypt=False,     # server‑side encryption only
    quota_bytes=1_000_000  # optional
)
```

Rules:

* Name must be unique and snake‑case (`[a‑z_]+`).  
* `ttl_sec` must be positive and **≤** 7 days.  
* If an existing name is re‑registered, `ChannelAlreadyExists` is raised.  
* Settings apply immediately; they live only in memory. Add the same entry to `channels.yaml` for persistence.

Use‑cases: ad‑hoc scratchpads during data‑science exploration, temporary debug logs, load‑testing channels.


## 6 Public API (sync)  

```python
class AIMemory:
    def write(self, scope: MemoryScope, channel: str,
              content: str | bytes, *,
              pii: bool = False,
              ttl_override: int | None = None,
              auto_pii: bool = False) -> str

    def read(self, scope: MemoryScope, channel: str, *,
             since_sec: int | None = None,
             max_bytes: int | None = None,
             max_msgs: int | None = None,
             max_tokens: int | None = None) -> (list[str], dict)

    def checkpoint(self, scope: MemoryScope, key: str, payload: dict) -> None

    def checkpoint_atomic(self, scope: MemoryScope, key: str,
                          update_fn: Callable[[dict|None], dict]) -> dict

    def bulk_erase(self, scope: MemoryScope) -> int
    def count_bytes(self, scope: MemoryScope, channel: str) -> int
    def register_channel(self, name: str, *, ttl_sec: int, encrypt: bool, quota_bytes: int | None = None) -> None
```

### Token-based truncation  
`max_tokens` lets callers cap the token budget for LLM prompts. AIMemory will truncate **oldest** records first until the budget is met (token counter pluggable).

---

## 7 Policy Rules (MVP)  

| Rule | Behaviour |
| --- | --- |
| TTL | `ttl_override` ≤ channel TTL. |
| Encryption | If record PII flagged, channel must `encrypt: true`. |
| Quota | Daily bytes per `(agent,user,channel)`; exceed → `QuotaExceeded`. |
| Auth | Agent must appear in Manifest Cache for channel. |

---

## 8 Content Processor Plug‑in  

Optional chain for redaction/enrichment. MVP stub logs when `auto_pii=True`; real masking later.

---

## 9 Encryption Strategy  

MVP: Default: rely on Azure Cache encryption‑at‑rest.  
Out of Scopr: Client‑side AES‑256‑GCM available by setting `encrypt: true` in YAML.  
  - **Question for SecOps**: Is server‑side encryption sufficient for <24 h conversational text with PII?

---

## 10 Metrics & Audit  

- Prometheus counters (`ai_mem_write_total`, `ai_mem_read_total`)  
- Latency histograms by channel 

---

## 11 Testing  

- `pytest` + `fakeredis` for unit tests  
- Optional docker‑compose redis for integration

---

## 12 Acceptance Criteria (Sprint‑1)  

1. `write/read` round‑trip for `routing` and `working`.  
2. Policy blocks PII into non‑encrypted channel.  
3. Quota configurable via YAML.  
4. Async demo script succeeds.  
5. README with install and YAML sample.

---
