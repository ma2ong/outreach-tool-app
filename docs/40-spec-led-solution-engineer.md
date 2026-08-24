# Spec 40 — LED Solution Engineer

## Purpose

Add a deterministic internal LED project configuration engineer on top of the approved-product knowledge introduced in Spec 39. The Agent may calculate physical layout and engineering quantities only from explicit CRM/project facts and explicitly Agent-approved product facts. It must not invent product specifications, electrical limits, controller capacity, commercial terms, price, lead time, certification or warranty.

## Product engineering facts

The existing `products` table remains the single product source of truth. Additive structured fields are added because free-text `cabinet_size` is not precise enough for deterministic engineering math:

- cabinet width / height in mm;
- cabinet resolution width / height in pixels;
- module width / height in mm;
- maximum and average cabinet power in watts.

All existing rows keep these fields null. Approval remains explicit through `agent_approved`; approval never fills a missing engineering fact.

## Project engineering inputs

The existing `opportunities` table remains the project source of truth. Additive project-specific fields:

- AC input voltage;
- controller total pixel capacity;
- controller output-port count;
- maximum pixels per output port;
- spare percentage used for internal planning.

These values are optional. Missing values produce visible engineering gaps, never guessed defaults.

## Deterministic calculations

For an opportunity and one approved compatible product, the engineer may calculate:

1. **Cabinet layout**
   - requested target width / height;
   - fit-inside, closest and cover-target cabinet grids;
   - actual physical width / height;
   - dimensional delta in mm and percent;
   - cabinets per screen and total cabinets for project quantity.

2. **Resolution**
   - calculated only from exact cabinet resolution fields;
   - screen width / height pixels;
   - total pixels per screen and for all identical screens.
   - Never derive exact resolution from nominal pixel-pitch text such as `P1.86`.

3. **Power**
   - maximum and average screen/project watts from exact per-cabinet product facts;
   - theoretical current only when project input voltage is explicitly supplied;
   - current is labelled planning math, not breaker/cable/phase design.

4. **Control capacity**
   - minimum controller units per screen from explicit controller pixel capacity;
   - when port count and max pixels/port are both supplied, required ports and port-constrained minimum controller units;
   - the final minimum is the stricter capacity/port result;
   - no hard-coded Novastar or other controller specifications.

5. **Spares**
   - only when the opportunity contains an explicit spare percentage;
   - cabinet spares from total cabinet quantity;
   - module spares only when exact module dimensions divide the exact cabinet dimensions cleanly.

## Product selection gate

- Automatic product selection is allowed only when Product Advisor says `ready_to_recommend=true`.
- A manually selected product must still be `agent_approved=1` and must not explicitly conflict with the opportunity.
- An unapproved or conflicting product never enters the engineering calculation.

## Output and safety

The Solution Engineer result is an **internal engineering proposal**. It includes:

- product used;
- facts used;
- layout options;
- selected closest-layout summary;
- resolution / power / control / spares sections;
- missing facts and risks;
- explicit safety notes.

It does not create a quote, choose a price, promise lead time, choose payment terms, or send a customer message.

## UI

The `报价订单` page gains an **LED Solution Engineer / 项目配置工程师** workbench:

- choose an open opportunity;
- optionally choose one approved compatible product;
- save project engineering inputs;
- calculate and display layout, actual screen size, resolution, cabinets, power, control capacity and spares;
- clearly show missing product/project facts.

The product knowledge form also exposes the new exact engineering product fields.

## CRM task provenance fix

Agent-created `create_task` executions must be stored with `source='agent'`, not `source='manual'`. The sales-task UI must label those rows as `Agent`. Existing historical rows are left unchanged because provenance cannot be reconstructed safely after the fact.

## Acceptance criteria

- legacy databases migrate additively;
- unapproved products cannot be engineered;
- explicit technical conflict blocks engineering;
- no exact resolution is calculated without exact cabinet resolution;
- no current is calculated without explicit voltage;
- no controller model capacity is hard-coded;
- no numeric spares are produced without explicit spare percentage;
- task source from Agent proposals is `agent`;
- backend regression suite and frontend production build stay green.
