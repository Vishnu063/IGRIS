# Authorized project creation — Step 21

Project planning covers websites, web apps, APIs, automation, dashboards and
commerce. Only the reviewed static website sample is materialized in this step;
planning another kind does not claim its application exists. No paid/payment
service, deployment or third-party dependency is installed.

create_sample is a trusted development utility requiring file-modify permission
and an operator-selected disposable parent. Names are constrained; existing
projects/symlinks are never overwritten. It is NOT exposed to an untrusted model
or the Guardian broker: runtime agent access would require a separate broker
handler and OS isolation. The operator is responsible for approving the parent;
Python permission checks alone are not hostile-code containment.
