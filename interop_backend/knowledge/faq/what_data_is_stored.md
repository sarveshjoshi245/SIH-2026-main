---
TITLE: What Information Does the Interoperability Platform Store?
TRIGGER: user.question_about_data_storage == true
CONTENT:
The prototype should not create a central copy of every departmental record. Each mock department represents a separate source system and retains its own source data. The interoperability platform stores the information needed to coordinate the workflow, such as the project profile, service configuration, approved schema mappings, consent metadata, transaction status, and audit events. Responses from departmental services can be transformed into a temporary or controlled canonical representation for the current workflow without becoming a permanent central government database.

The chatbot should therefore explain that its purpose is to coordinate authorized service requests rather than replace departmental systems. A typical audit record can contain a transaction identifier, service name, request purpose, timestamp, response status, and latency. The platform should avoid storing unnecessary sensitive response payloads. In a real deployment, retention, consent, access control, and data-protection requirements would be determined by the applicable organization and regulations. The prototype uses synthetic data and mock departmental APIs, so its storage design demonstrates the interoperability pattern rather than representing an official government data architecture.
---
