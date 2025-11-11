# API Scoring – Module Rules

This document summarizes the rules that the _API Scoring_ engine applies when certifying a bundle.  
The rules are grouped by module (Design, Security, and Documentation) and are extracted from the linters defined in `apiscoring/api-scoring-engine/packages/certification-service`.

Each row lists the internal identifier of the rule, the severity with which it is reported, and the description implemented in the source code.

---

## 1. Design (OpenAPI)

| Rule | Severity | Description |
| --- | --- | --- |
| `contactEmail` | warn | Definition must have a contact email |
| `contactUrl` | error | Contact email should be a valid URI |
| `openapiVersion` | error | OpenAPI cannot be 3.1.X for the time being. |
| `errorResponseDefinitions` | warn | Define errors in your API following our version of the Problem Details RFC7807. |
| `errorResponseDefinitionsRfc7807Status` | warn | Define errors in your API following our version of the Problem Details RFC7807. |
| `mustUseSemanticVersioning` | warn | All the API will be versioned following the Semantic Versioning definition [32] |
| `ensureOperationsSummary` | warn | Put a summary in all operations [39] |
| `pathsParamExamples` | warn | Parameters must have examples[34] |
| `componentsParamExamples` | warn | Parameters must have examples[34] |
| `ensurePropertiesExamples` | warn | Properties must have examples, description and type [34.1] |
| `pathsUppercase` | warn | Urls should follow a lowercase pattern [15] |
| `pathsNoUnderscore` | warn | Use kebab-case naming in urls.[16] |
| `pathParametersCamelCase` | warn | Use camelCase naming for attributes in request/responses and definitions [17.2] |
| `queryCamelCase` | warn | Use camelCase naming for attributes in request/responses and definitions [17.1] |
| `camelCaseForProperties` | warn | Use camelCase naming for attributes in request/responses and definitions [17] |
| `dtoSchemaName` | warn | You SHOULD avoid ending your schemas (..schemas[*]~) with suffixes like {dto,DTO,Dto} |
| `deleteHttpStatusCodesResource` | warn | Each end point need to have defined the below error codes [29.7] |
| `getHttpStatusCodesCollections` | warn | Each end point need to have defined the below error codes [29.1] |
| `getHttpStatusCodesResource` | warn | Each end point need to have defined the below error codes [29.2] |
| `patchHttpStatusCodeResource` | warn | Each end point need to have defined the below error codes [29-8] |
| `postHttpStatusCodesCollections` | warn | Each end point need to have defined the below error codes [29.3] |
| `postHttpStatusCodesController` | warn | Each end point need to have defined the below error codes [29.4] |
| `postHttpStatusCodesResource` | warn | Each end point need to have defined the below error codes [29.4] |
| `putHttpStatusCodesResource` | warn | Each end point need to have defined the below error codes [29.6] |
| `standardHttpStatusCodes` | warn | MUST use standard HTTP status codes [29.10] |
| `wellUnderstoodHttpStatusCodes` | warn | HTTP response codes cannot be used on all HTTP verbs [29.9] |

> All these rules are applied via Spectral over OpenAPI/REST contracts.

---

## 2. Security (OpenAPI)

| Rule | Severity | Description |
| --- | --- | --- |
| `allowedAuthMethods` | warn | The API operation uses HTTP authentication method that is not included in IANA Authentication Scheme Registry |
| `allowedVerbs` | warn | Use always HTTP verbs to refer to actions in urls [13] |
| `arrayRequiredProperties` | warn | Array size should be limited to mitigate resource exhaustion attacks. This can be done using `maxItems` |
| `emptySchema` | error | The schema is empty. This means that your API accepts any JSON values. Or payload does not have any properties defined. |
| `emptySchemaHeaders` | warn | A header object does not define a schema for the accepted input or output. This means that you do not limit the what your API can accept or include in headers. Define schemas for all header objects to restrict what input or output is allowed |
| `ensureAuth` | warn | Authentication SHOULD support Basic and Bearer type [43] |
| `ensureSecuritySchemes` | warn | The security field of your API contract does not list any security schemes to be applied |
| `globalSecurity` | error | use the security field on the global level to set the default authentication requirements for the whole API |
| `implicitGrantOauth2` | warn | Do not use implicit grant flow in OAuth2 authentication. |
| `negotiateAuth` | warn | Do not use the security scheme negotiateAuth |
| `noAdditionalPropertiesDefined` | warn | While forbidding additionalProperties can create rigidity... it can also be leveraged to bypass validation. |
| `numericRequiredPropertiesMaxMin` | warn | Numeric values should be limited in size to mitigate resource exhaustion |
| `oauth1Auth` | error | One or more global security schemes in your API allows using OAuth 1.0 authentication |
| `resourceOwnerPasswordAuth` | error | The API operation uses resource owner password grant flow in OAuth2 authentication |
| `responseSchemaDefined` | warn | You have not defined any schemas for responses that should contain a body... |
| `schemaMandatoryParameters` | warn | One or more parameters in your API do not have schemas defined... |
| `securityEmpty` | warn | One or more of the objects defined in the global security field contain an empty security requirement |
| `securityScopesDefined` | warn | OAuth2 security requirement requires a scope not declared in the referenced security scheme |
| `serverHttps` | warn | Set all server objects to support HTTPS only so that all traffic is encrypted. |
| `stringParametersRequiredMaxLength` | warn | String should be limited and with a maxLength to avoid out of format inputs by attackers |
| `stringPropertiesRequiredMaxLength` | warn | String should be limited and with a maxLength to avoid out of format inputs by attackers |

> These rules are also executed on OpenAPI/REST contracts using Spectral, with an emphasis on security hardening.

---

## 3. Documentation (Markdownlint)

| Rule | Severity | Description |
| --- | --- | --- |
| `EX_MD050 / custom-mandatory-about` | warning (severity 1) | The API document must contain an “About” section as a first-level heading. |

> Supporting documentation is validated with Markdownlint; severity `1` corresponds to “warning” according to the `.markdownlint.json` configuration.

---

### References

- Source code: `apiscoring/api-scoring-engine/packages/certification-service/code/src/rules`
- OpenAPI linters: define the rules for the Design and Security modules.
- Markdownlint: validates the documentation attached to bundles (Documentation module).

