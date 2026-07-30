# Glossary

Short definitions for terms used across OpenAdapt.

## BYOC

**Bring your own cloud (BYOC)** is the existing OpenAdapt connector and
configuration name for a customer-owned cloud runner and storage boundary.

OpenAdapt Cloud can send bounded authorization and control metadata to that
runner. Cloud receives only the declared result and evidence permitted by the
deployment data boundary. Live screenshots, sensitive parameters, and verifier
values can remain inside the customer boundary.

The broader public term is **customer-controlled execution**. A
customer-controlled runner can also run on a workstation, server, or
on-premises virtual machine. Those deployments do not have to use BYOC.

BYOC does not mean bring your own compute. It does not mean customer-provided
source code. It does not grant unrestricted access to OpenAdapt Cloud.

See [Deployment boundaries](../commercial/deployment-boundaries.md) and
[Integrate OpenAdapt Execute](../commercial/execute-api.md).
