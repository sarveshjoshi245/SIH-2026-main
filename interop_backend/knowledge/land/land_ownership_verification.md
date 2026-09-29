---
TITLE: Industrial Land Ownership and Record Verification
TRIGGER: project.land.required == true
CONTENT:
For an industrial project, the land record should be verified before other project checks are treated as complete. Typical verification compares the applicant or organization name with available land records and checks the survey or plot number, recorded area, land classification, and mutation status. Depending on the jurisdiction, records may be maintained by a Revenue Department or Land Records authority. Typical supporting information includes a land record extract, property card, title document, mutation record, or cadastral map reference.

The verification is intended to confirm that the proposed site is identifiable and that the applicant has the stated ownership or lawful right to use it. The chatbot should therefore ask for the location, survey or plot identifier, approximate area, and land-use status when land verification is required. A project that does not involve acquiring or using a specific site can normally skip detailed land-record questions. For prototype purposes, land below about 1 hectare may be treated as a simplified case, while larger industrial sites should trigger more detailed area and land-use questions. These are prototype rules, not official thresholds.
---
