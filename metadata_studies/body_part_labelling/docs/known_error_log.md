# Log of known labelling errors

| No. | Error | Type | Identified during | Description | Workaround | Solution |
| --- | ----- | ---- | ----------------- | ----------- | ---------- | -------- |
| 1   | `cervical` identified as `pelvis` when in a `spine`/`neck` context | `double meaning` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | When accompanied by `spine` or `neck`, it refers to neck vertebrae but on its own there is a chance it refers to `pelvis`. | Removed `cervic,pelvis` from the dictionary - not ideal as legitimate references to the pelvis will be missed. | Suggested introducing some context awareness. |
| 2   | `mobile` idenified as `abdomen` | `false positive` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | It contains `bile`, which is a valid term. | - | Suggested introducing some context awareness or a denylist. |
| 3   | `femoral` identified as `head` | `false positive` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | It contains `oral`, which is a valid term. | - | Suggested introducing some context awareness or a denylist. |
| 4   | `starmap` identified as `upper_limb` | `false positive` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | It contains `arm`, which is a valid term. | - | Suggested introducing some context awareness or a denylist |
| 5   | `propeller` identified as `pelvis` | `false positive` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | It contains `pel`, which is a valid term. | - | Suggested introducing some context awareness or a denylist |
| 6   | `analysis` identified as `pelvis` | `false positive` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | It contains `anal`, which is a valid term. | - | Suggested introducing some context awareness or a denylist |
| 7   | `hippocamp` identified as `pelvis` | `false positive` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | It contains `hip`, which is a valid term. | - | Suggested introducing some context awareness or a denylist |
| 8   | `facet` identified as `head` | `false positive` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | It contains `face`, which is a valid term. | - | Suggested introducing some context awareness or a denylist |
| 9   | `temporal resolution` identified as `head` | `false positive` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | It contains `oral`, which is a valid term. | - | Suggested introducing some context awareness or a denylist |
| 10  | Missing `ch` -> `chest` and `ab` -> `abdomen` | `missed` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | Text is too short to add to the dictionary or make an informed decision on whether it does refer to a body part. | - | - |

## Solved errors

| No. | Error | Type | Identified during | Solution | Dictionary version containing implementation |
| --- | ----- | ---- | ----------------- | -------- | -------------------------------------------- |
| 1   | `optic` not identified as `head` | `missed` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | Added `optic,head` to the dictionary | b6e0216e |
| 2   | `hippocamp` not identified as `head` | `missed` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | Added `hippocamp,head` to the dictionary | b6e0216e |
| 3   | `ctpab` not identified as `abdomen` | `missed` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | Added `ctpab,abdomen` to the dictionary | b6e0216e |
| 4   | `mibg` identified as `abdomen` | `incorrect` | [tag level validation](../outputs/tag_labelling/run1/manual_validation_notes.md) | Removed `mibg,abdomen` from the dictionary | b6e0216e |
