---
TITLE: Matching Applicant and Land Records
TRIGGER: project.land.required == true
CONTENT:
The interoperability workflow should verify that the organization applying for the industrial project can be associated with the land record being checked. Department systems may use different identifiers and names. For example, a land system may contain a registered owner name and survey number, while the project application may contain an organization identifier and legal business name. The platform should therefore perform controlled matching rather than assuming that two differently formatted names represent different entities.

Typical verification information includes the organization name, landowner or registered-holder name, survey or plot number, district, and recorded area. Supporting documents can include a title document, property record extract, property card, or mutation entry, depending on the jurisdiction. The chatbot should ask for the minimum information needed to locate the record and should request an additional identifier when an initial match is ambiguous. The result should indicate verified, mismatch, or unable to verify rather than silently accepting uncertain data. This approach also demonstrates why a canonical identity and schema-mapping layer is useful when connecting heterogeneous departmental systems.
---
