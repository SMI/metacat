# Manual verification notes

>**Note:** In the case of using labelling for cohort building, having false positives is better than missing out on potential cases. The risk of giving the researcher more than what they requested is a current risk that would be reduced by the use of labels.

>**Note:** When validating, remember that a study can contain one or more series and a series one or more scans. This means that a description could have conflicting body parts or body parts that are not likely to be scanned together because there could be more than one sc
an. An example of this is `whole body chest`. There could be a whole body scan followed by a close-up of the chest.

## Supporting information

* [Annex 5 - interventional procedures](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2022/03/Annex-5-DID-Interventional-procedures-version-1.xlsx)

## Setup

Considering the tag labelling output for `BodyPartExamined`, `BodyPartExamined_labelled.csv` containing the following columns:

```csv
BodyPartExamined,Labels,Modalities,BodyPartExaminedCount
```

To make validation more manageable, the labelled lists were [split](../../../split.sh) by count. The split point was decided by looking at the [plots](../../../plot.py) and chosing the lower end of the group at which the percent of total studies represented by a value (total sum of `BodyPartExaminedCount`) outweighs the percent of unique values that were labelled. For example, looking at `BodyPartExamined` labelled values:

![BodyPartExamined_labelled_frequency_plot](./BodyPartExamined/BodyPartExamined_labelled_frequency_plot.png)

We can see that for values found in more than 10,000 studies, a smaller proportion of the total list of values (green) represents a higher proportion of the studies that were labelled (orange). This means that if we focus the validation on values where `BodyPartExaminedCount` is higher or equal to 10,000, we can cover a bigger proportion of studies.  

This method allows us to focus on values that have a bigger impact on study labelling by putting aside more than half of values (green spikes) found in only a few studies.  

```console
$ ./split.sh /home/shared/bodyparts/outputs/tag_labelling/BodyPartExamined/BodyPartExamined_labelled.csv 4 10000 /home/shared/bodyparts/outputs/tag_labelling/BodyPartExamined/BodyPartExamined_labelled_top_10000.csv
```

## Observations

1. `cervical` identified as `pelvis` when in a `spine`/`neck` context.
2. `mobile` idenified as `abdomen` because it contains `bile`.
3. `femoral` identified as `head` because it contains `oral`. Similarly with 2, `oral` is a valid term. This would be solved with some context awareness.
4. `starmap` identified as `upper_limb` because it contains `arm`.
5. `propeller` identified as `pelvis` because it contains `pel`.
6. `analysis` identified as `pelvis` because it contains `anal`.
7. `optic` is missed. Should it be labelled with `head` or is it likely to be used with a technical meaning?
8. `hippocamp` identified as `pelvis` because it contains `hip` but not identified as `head`.
9. `facet` identified as `head` because it contains `face`.
10. `femoral neck` identified as `neck` but refers to the neck of the femur. It is also identified as `head` because it contains `oral`.
11. `abdomen oral contrast` identified as `head` but it refers to contrast liquid administered orally before an abdominal scan. It does not mean that the mouth is included in the scan. How likely is it for this to be the case?
12. `temporal resolution` identified as `head` because of `temporal` and `oral` but refers to a setting.
13. `ctpab` is a renal scan and should subsequently be labelled with `abdomen`. Check [Annex5](#supporting-information) for more of these.
14. Missing `ch` -> `chest` and `ab` -> `abdomen`.
15. `Expert eye` identified as `head` because it contains `eye` but it sounds more like a method or hardware.
16. Incorrectly labelled `mibg` with `abdomen`. This is not an abdomen-specific technique.

## Improvement suggestions

### Double meanings

Observations: 1

The issue with the term cervical is the double meaning. When in context with spine, it can refer to the neck vertebrae but it can also refer to the cervix (pelvis).
As a workaround, the suggestion is to replace `cervic,pelvis` with `cervix,pelvis` and see the effects on missed cases.
As a more permanent solution, introducing some context awareness would likely yeld better results.

### False positives

Observations: 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 15

The problem is that all these terms are valid and should be in the dictionary against their assigned labels.
A possible workaround would be to have a way of marking known false positives such as a list of false positive terms to be ignored.
A better solution would be to introduce context awareness.

### Missing labels

Observations: 7, 8, 13, 14

An immediate solution would be to add `optic,head`, `hippocamp,head` and `ctpab,abdomen` to the dictionary.
For text that is too limited such as `ch` and `ab`, adding them to the dictionary would be too high-risk due to them being highly likely to appear in other words (e.g., `ab` appears in `ctpab`).

### Incorrect labels

Observations: 16

This was initially labelled by reading an article about it being applied to the abdomen. Unfortunately that source seems to have been from an endocrine surgery, which is bound to focus on abdominal scans. The [Annex5](#supporting-information) indicated that MIBG stands for meta-iodobenzylguanidine used in a number of procedures. This should be removed.

## Suggested dictionary changes

1. remove `cervic,pelvis`
2. add `optic,head`
3. add `hippocamp,head`
4. add `ctpab,abdomen`
5. remove `mibg,abdomen`
