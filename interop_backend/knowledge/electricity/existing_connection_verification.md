---
TITLE: Existing Industrial Electricity Connection
TRIGGER: project.electricity.required == true AND project.electricity.existing_connection == true
CONTENT:
When a company already has an electricity connection at the proposed industrial site, the platform should first verify that connection instead of treating the project as a completely new connection. Typical information includes consumer or service number, registered organization name, connection category, sanctioned load, connected load, meter status, and current connection status. The electricity service may also indicate whether the account has outstanding issues that could affect the requested service.

The chatbot should ask whether an existing connection is available and, when the answer is yes, request the consumer or service identifier. It should then compare the organization and site information supplied during the interview with the record returned by the electricity service. If the proposed project requires substantially more capacity than the recorded sanctioned load, the workflow should move to a capacity-enhancement or feasibility path rather than simply returning an approval. This keeps the chatbot focused: users with no electricity requirement can skip these questions, while users with an existing connection provide an identifier that allows the interoperability layer to retrieve the relevant record.
---
