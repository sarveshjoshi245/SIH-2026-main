---
TITLE: Manufacturing and Chemical Project Service Applicability
TRIGGER: project.project_type == "MANUFACTURING" OR project.industry_type == "CHEMICAL"
CONTENT:
A manufacturing project normally requires a defined physical site, so Land/Revenue verification is typically applicable. The interview should collect the proposed location, survey or plot information when available, approximate land area, and ownership or lawful-use status. Electricity verification is also typically applicable because manufacturing facilities require electrical capacity for machinery and operations. The chatbot should ask for the expected load and whether an existing industrial connection is available.

Pollution/Environment verification is particularly relevant to chemical manufacturing or other processes that generate emissions, wastewater, hazardous substances, or regulated waste. If the user confirms industrial emissions or hazardous waste, the environmental service should be selected. For a manufacturing project that explicitly has no relevant emissions, wastewater, or hazardous waste, the detailed pollution interview can normally be skipped in the prototype, subject to applicable rules. A manufacturing project using a site of 1 hectare or more should trigger detailed land questions, while an expected electricity requirement above 500 kW should trigger detailed load questions. These thresholds are illustrative prototype rules and are not official regulatory thresholds.
---
