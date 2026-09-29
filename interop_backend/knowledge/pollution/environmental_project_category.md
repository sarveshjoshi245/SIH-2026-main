---
TITLE: Environmental Category and Project Characteristics
TRIGGER: project.environment.industrial_emissions == true OR project.environment.hazardous_waste == true
CONTENT:
Environmental requirements can depend on the type and scale of industrial activity rather than simply on whether a company calls itself a manufacturer. The chatbot should collect enough information to distinguish a low-impact activity from a process involving significant emissions, wastewater, hazardous substances, or waste generation. Useful interview fields include industry type, manufacturing process, expected emissions, wastewater generation, hazardous-waste generation, and approximate production scale.

For prototype logic, any project explicitly reporting industrial emissions or hazardous waste should trigger the Pollution/Environment service. A project reporting neither can normally skip detailed pollution-service questions unless another project rule requires them. Where a scale threshold is needed for demonstration, the prototype may use an illustrative production or waste threshold defined in its configuration rather than claiming that the value is legally applicable everywhere. The service-selection engine should rely on these explicit project-profile fields and documented rules. This makes the decision explainable: the platform can tell the user that environmental verification was selected because the project reported emissions or hazardous waste, rather than because an AI model made an unexplained decision.
---
