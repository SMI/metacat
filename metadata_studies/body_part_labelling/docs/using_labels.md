# How to use the body part labels

## Where to find them

The body part labels are stored in a `labels` database alongside the `smi` database.  

The labels are organised in tables per modality of name `<MODALITY>_BodyPart_Mapping` of the following structure:

![body part labels schema](./img/smi_bodypart_labels_schema_horizontal.png)

The columns `StudyDescription`, `SeriesDescription` and `BodyPartExamined` form a composite Primary Key on these tables, meaning that each combination of these values is unique. The values of these columns are uncleaned, as found in the `smi` database, to enable the joining of tables for the extraction of `AccessionNumber`s and/or IDs required for cohort building.  

The `CombinationCount` column holds the number of studies with the combination of values for the above three columns. This is gathered with the following query:

```sql
SELECT St.StudyDescription, Se.SeriesDescription, Se.BodyPartExamined, COUNT(*) AS CombinationCount
FROM {modality}_StudyTable St
INNER JOIN {modality}_SeriesTable Se
ON St.StudyInstanceUID = Se.StudyInstanceUID
GROUP BY St.StudyDescription, Se.SeriesDescription, Se.BodyPartExamined;
```

All other columns represent the current set of body part labels. Their representative floating point values are indicative of the confidence percentage in the application of that label to the group. For example:

| StudyDescription | SeriesDescription | BodyPartExamined | head   | pelvis | spine | CombinationCount |
| ---------------- | ----------------- | ---------------- | ------ | ------ | ----- | ---------------- |
| cervical spine   | None              | cervical spin    | NULL   | 66.6%  | 33.3% | 100              |
| cranium          | skull             | head             | 100%   | NULL   | NULL  | 50               |

If only one of the three selected tags is labelled (e.g., `spine`), the confidence percentage is 33.3%, if two are in agreement (e.g., `pelvis`), the confidence percentage is 66.6%, and if all are in agreement (e.g., `head`), the confidence percentage is 100%.

## How to use them

The tables can be used on their own for queries about the potential size of a cohort matching a certain label, for example:

```sql
SELECT SUM(CombinationCount) FROM CR_BodyPart_Mapping WHERE chest >= 60;
+-----------------------+
| SUM(CombinationCount) |
+-----------------------+
|               4529246 |
+-----------------------+
1 row in set (0.040 sec)
```

This indicates that there are ~4.5 million studies where there is an over 60% confidence of `chest` appearing.

Using this in combination with a join on the modality's StudyTable allows the selection of `AccessionNumber`s and `StudyInstanceUID`s:

```sql
SELECT DISTINCT(St.StudyInstanceUID), St.AccessionNumber
FROM labels.XA_BodyPart_Mapping L
INNER JOIN smi.XA_StudyTable St ON St.StudyDescription = L.StudyDescription
INNER JOIN smi.XA_SeriesTable Se ON St.StudyInstanceUID = Se.StudyInstanceUID
WHERE Se.SeriesDescription = L.SeriesDescription
AND Se.BodyPartExamined = L.BodyPartExamined
AND L.chest >= 60;
```

## Known errors

There are a few known labelling errors that users of these tables should be aware of. For more details of these, see [the known errors log](./known_error_log.md).

>**Note:** If more issues are found at any point, please add them to the log and put in a request for any workarounds or solutions to be applied to the dictionary. Please note any changes to the dictionary will require re-labelling of all cases.
