---
TITLE: Environmental and Pollution Verification
TRIGGER: project.environment.industrial_emissions == true OR project.environment.hazardous_waste == true
CONTENT:
Industrial projects may require environmental or pollution-related verification when their activities can produce air emissions, wastewater, hazardous waste, or other regulated environmental impacts. Depending on the jurisdiction and project category, a Pollution Control Board or environmental authority may handle consent or related permissions. Typical records can include an application number, industry category, consent type, consent status, validity date, and compliance indicators.

The chatbot should therefore ask whether the proposed activity is expected to generate industrial emissions, wastewater, hazardous waste, or other significant environmental impacts. If the answer is yes, the pollution service should be included in the workflow. A project with no relevant environmental impact can follow a simplified path, although the prototype should make clear that actual regulatory applicability depends on the project and applicable rules. The platform should retrieve the relevant environmental record and normalize it into fields such as industry category, consent status, and validity. The purpose of this check is to establish whether the project's stated environmental permissions or compliance information is consistent with the project profile.

