# Generic Page Types

These page types are optional building blocks, not a fixed taxonomy. Folder
names, required fields, headings, and page categories yield to the confirmed
student schema in `AGENTS.md`. Write titles, headings, and body text in the
student's or source's language as appropriate.

The frontmatter below uses only portable fields. A page may omit optional
sections when the source does not support them. Attribute claims and preserve
ambiguity in every page type.

## `topic`

Use for a concept, question, framework, theme, or other subject explained
through sources.

```yaml
---
type: topic
title: "Example title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft
sources:
  - example-source
---
```

Suggested body structure:

```markdown
# Example title

## Overview

State the subject and its scope with source attribution.

## Source-supported details

Preserve important definitions, evidence, qualifications, and disagreements.

## Related pages

- [Example entity](../entities/example-entity.md)

## Sources

- [Example source](../sources/example-source.md)
```

## `entity`

Use for people, organizations, places, objects, technologies, works, and other
domain entities.

```yaml
---
type: entity
title: "Example title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft
sources:
  - example-source
---
```

Suggested body structure:

```markdown
# Example title

## Overview

Identify the entity and explain its relevance with source attribution.

## Source-supported details

Record relevant attributes, activities, relationships, or changes over time.

## Related pages

- [Example topic](../topics/example-topic.md)

## Sources

- [Example source](../sources/example-source.md)
```

## `source`

A source page is mandatory for each ingested original. It is the audit trail
for that item and preserves source-bound notes that have not yet been
integrated elsewhere.

```yaml
---
type: source
title: "Example title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft
sources:
  - example-source
---
```

Suggested body structure:

```markdown
# Example title

## Source details

Record only known bibliographic, provenance, format, and locator information.
Flag missing or uncertain details rather than inventing them.

## Source-bound summary

Describe what this source contains without presenting synthesis as the
source's own claim.

## Notes and preserved material

Retain quotations, tables, page or timestamp references, unresolved ambiguity,
and notes awaiting integration.

## Linked pages and media

- [Example topic](../topics/example-topic.md)
- [Example media](../media/extracted/example-source/example-image.png)
```

## `article`

Use for synthesis across sources, including reviews, analyses, and comparisons.
Distinguish the synthesis from the claims of individual sources.

```yaml
---
type: article
title: "Example title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft
sources:
  - example-source
---
```

Suggested body structure:

```markdown
# Example title

## Scope and question

Explain what the synthesis examines and which sources support it.

## Synthesis

Compare or connect source-supported findings without erasing disagreement.

## Sources

- [Example source](../sources/example-source.md)
```

For comparisons, use parallel structures where useful, such as matching
subsections or a table with the same criteria for each item. Keep cells
attributed and add prose for qualifications that do not fit a table.

## `hub`

Use for navigation rather than new subject-matter claims.

```yaml
---
type: hub
title: "Example title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft
sources:
  - example-source
---
```

Suggested body structure:

```markdown
# Example title

## Pages

- [Example topic](../topics/example-topic.md) — Short navigation description.
- [Example entity](../entities/example-entity.md) — Short navigation description.

## Sources

- [Example source](../sources/example-source.md)
```

Update hubs when relevant pages are added, renamed, or removed. Do not set a
fixed page-count threshold unless the confirmed schema specifies one.

## `case`

Use optionally for a bounded event, artifact, observation, or instance when the
confirmed schema calls for one.

```yaml
---
type: case
title: "Example title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft
sources:
  - example-source
---
```

Suggested body structure:

```markdown
# Example title

## Context

Define the case and its boundaries with source attribution.

## Evidence

Preserve relevant chronology, attributes, observations, or interpretations.

## Analysis and alternative readings

Distinguish source claims from synthesis and retain competing explanations.

## Sources

- [Example source](../sources/example-source.md)
```
