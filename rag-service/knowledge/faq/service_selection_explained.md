---
TITLE: Why Does the Assistant Select Different Services?
TRIGGER: service_selection.completed == true
CONTENT:
The assistant selects services from the project profile rather than calling every available department for every project. The profile contains information such as project type, location, land requirement, electricity requirement, expected load, emissions, and hazardous-waste characteristics. Deterministic rules then identify which departmental services are relevant. For example, a project using a specific industrial site normally triggers Land/Revenue verification, while a project requiring electricity triggers the Electricity service. A project reporting industrial emissions or hazardous waste triggers the Pollution/Environment service.

This approach reduces unnecessary requests and makes the workflow easier to explain. The chatbot can tell the user, in one sentence, why each service was selected. For example: "Land verification is needed to confirm the proposed site's recorded ownership and area." It can also explain why a service was skipped: "Detailed pollution verification was not selected because you reported no industrial emissions or hazardous waste." The rules in this prototype are illustrative and should not be presented as legal advice or as an authoritative determination of regulatory obligations.
---
