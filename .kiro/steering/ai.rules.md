---
inclusion: always
---

# NeuroTwin AI Behavior Rules

Rules for implementing Twin AI response generation and cognitive behavior.

## Cognitive Blend (0-100%)

The Blend slider controls human-like vs AI-logical responses:
- **0-30%**: Pure AI logic, minimal personality mimicry
- **31-70%**: Balanced blend of user personality + AI reasoning
- **71-100%**: Heavy personality mimicry, requires confirmation before actions

When implementing Blend:
- Always fetch current Blend value before generating responses
- Apply personality profile proportionally to Blend percentage
- Log Blend value used in each response for audit

## Memory Integrity

- Only reference memories that exist in the Vector Memory Engine
- Never fabricate or infer memories not explicitly stored
- When memory is uncertain, acknowledge gaps rather than guess
- All memory reads must include source timestamp validation

## Action Confirmation

Require explicit user confirmation when:
- Cognitive Blend > 80%
- Action involves external integrations (email, calendar, messaging)
- Action could be interpreted as impersonation
- Any irreversible or high-impact operation

## Personality Matching

- Load CSM (Cognitive Signature Model) profile before response generation
- Match tone, vocabulary, and communication patterns from profile
- Respect user-defined boundaries in personality settings
- Never override user's stated preferences with inferred behavior

## Impersonation Boundaries

- Twin may draft content in user's style (with disclosure)
- Twin may NOT send communications as user without `permission_flag=True`
- Voice cloning requires separate explicit approval per session
- Always distinguish Twin-generated content from user-authored content
