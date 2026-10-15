---
trigger: model_decision
description: Applies to real Flow Music MVP probes, live-account diagnostics, Lyria model verification and investigations of music credit consumption or ambiguous results.
---
# Real experiment rules
Select the `flowmusic-mvp` skill. Never automatically execute live generation or account login just because a task mentions music. Use one deliberate run with a unique `request_id`, the operator's explicit confirmation of credit/terms, safe event logs and no retries. On uncertain response: `needs_review`, inspect the remote library manually. Keep prompt and OAuth details out of all logs.
