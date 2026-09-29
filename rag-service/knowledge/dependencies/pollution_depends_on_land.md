---
TITLE: Pollution Service Dependency on Land Verification
TRIGGER: service_dependency.POLLUTION_SERVICE.depends_on == LAND_SERVICE
CONTENT:
Maharashtra Pollution Control Board's (MPCB) Consent to Establish process requires a verified Land Ownership Certificate as a submission prerequisite before the consent application can be meaningfully progressed. This creates a cross-department dependency: the Land/Revenue verification must be completed and its results available before the Pollution/Environment verification can proceed.

In practice, the Maharashtra Land Records department (Mahabhumi) exposes API services to authorized institutions for land record verification. Our platform is the proposed mechanism that resolves this dependency where authorized APIs and policy permit it. The platform retrieves and verifies land ownership data first, and only then initiates the MPCB consent verification with the verified land certificate data included.

This dependency means that in the execution plan, LAND_SERVICE must be placed in an earlier wave than POLLUTION_SERVICE. ELECTRICITY_SERVICE has no such dependency relationship with either department and can run in parallel with LAND_SERVICE. If only POLLUTION_SERVICE is required (without LAND_SERVICE), the dependency does not apply and POLLUTION_SERVICE can proceed independently — the dependency is only relevant when both services are required for the same project.
---
