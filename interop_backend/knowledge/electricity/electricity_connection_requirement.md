---
TITLE: Industrial Electricity Connection Verification
TRIGGER: project.electricity.required == true
CONTENT:
Industrial projects commonly need electricity-service verification because the proposed facility may require a new connection, increased sanctioned load, or confirmation that an existing connection can support the project. A distribution utility or electricity department may maintain information such as consumer number, connection category, sanctioned load, connected load, meter status, and outstanding dues. The exact process depends on the local utility and project.

The chatbot should ask whether electricity is required and, if so, obtain an approximate expected load. For a prototype, a project requiring more than 500 kW should trigger additional questions about sanctioned capacity, proposed load increase, and connection or feasibility status. Smaller requirements can follow a simpler connection check. The 500 kW value is an illustrative prototype threshold, not a universal regulatory threshold. The interoperability layer should retrieve the relevant electricity record and convert utility-specific fields into the common model, such as required load, sanctioned load, connected load, and connection status. The purpose is to identify whether the existing or proposed electricity arrangement is consistent with the project's stated requirement.
---
