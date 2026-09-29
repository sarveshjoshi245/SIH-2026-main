---
TITLE: Pollution Consent and Validity Check
TRIGGER: project.environment.industrial_emissions == true OR project.environment.hazardous_waste == true
CONTENT:
When pollution or environmental verification is required, the platform should determine whether the organization has a relevant consent or environmental record and whether the returned status is currently valid according to the information available to the service. Typical records may distinguish consent to establish a project from consent to operate it, depending on the jurisdiction and stage of the project. A Pollution Control Board or environmental authority may issue or maintain these records.

The chatbot should ask whether an existing environmental consent or application is available. If yes, it can request an application or consent number and use that identifier to query the mock environmental service. If no record is available, the platform should report that verification could not be completed rather than assuming that approval exists. The response should include a status such as APPROVED, PENDING, EXPIRED, NOT_FOUND, or REQUIRES_REVIEW. A validity date can also be normalized when supplied. The prototype should not convert these statuses into legal conclusions; it should present them as service verification results and explain that actual requirements depend on the applicable authority and project category.
---
