---
TITLE: Warehouse Project Service Applicability
TRIGGER: project.project_type == "WAREHOUSE"
CONTENT:
A warehouse normally requires a physical site, so Land/Revenue verification typically applies. The chatbot should ask for the proposed location, approximate area, survey or plot identifier when available, and whether the organization owns or has lawful rights to use the site. A warehouse may also require electricity verification for lighting, refrigeration, material-handling equipment, security systems, or other operations. The expected electrical load should determine whether the standard or detailed electricity workflow is used.

Pollution/Environment verification is not automatically required for every warehouse in this prototype. If the warehouse only stores ordinary goods and the user reports no industrial emissions, hazardous materials, significant wastewater, or similar environmental characteristics, the detailed pollution interview can normally be skipped. If hazardous materials are stored or the project has environmental impacts, the pollution service should be selected. For demonstration, land areas of 1 hectare or more can trigger detailed land questions, and electricity requirements above 500 kW can trigger detailed capacity questions. These thresholds are illustrative rules for the prototype, not statements of universal legal requirements.
---
