---
TITLE: Electricity Load and Capacity Check
TRIGGER: project.electricity.required == true AND project.electricity.required_load_kw > 500
CONTENT:
For a higher-load industrial project, electricity verification should go beyond checking whether an account exists. The system should compare the project's expected load with the sanctioned and connected capacity recorded by the electricity service. A significant difference may indicate that the organization needs a load enhancement, a new connection, or a separate feasibility assessment before the project can operate at its planned capacity.

The chatbot should therefore ask for the expected maximum load in kilowatts and whether the organization already has an industrial electricity connection. For prototype logic, requirements above 500 kW can trigger a detailed capacity question, while requirements below or equal to 500 kW can use the standard connection workflow. This is a demonstration threshold and must not be presented as an official universal rule. Typical utility information includes consumer number, tariff or connection category, sanctioned load, connected load, meter status, and connection status. The interoperability platform should normalize different utility field names and return a clear result showing requested capacity, available or sanctioned capacity, and whether an additional electricity process may be required.
---
