---
TITLE: Industrial Land Use and Site Details
TRIGGER: project.land.required == true AND project.land.area_hectare >= 1
CONTENT:
Land verification for an industrial project should establish whether the proposed site is suitable for the stated project and whether the recorded land information is consistent with the application. Typical checks include plot or survey number, district, recorded area, current land classification, and whether the stated use is compatible with the proposed industrial activity. A Revenue or Land Records authority may provide the underlying record, while land-use conversion or planning approval may involve a separate local authority.

The interview should ask for the approximate land area because the level of review can increase as the site becomes larger or the project becomes more complex. For a prototype, sites under 1 hectare can follow a simplified land-information path. Sites of 1 hectare or more should trigger questions about exact survey identification, land classification, and intended use. These thresholds are illustrative rather than official rules. The interoperability layer should retrieve the relevant land record from the mock Land/Revenue service and normalize fields such as survey number, owner name, area, and land type into the common project model.
---
