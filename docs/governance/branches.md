# Branch governance recommendations

## Repository identity and foundation

Use the existing authorized repository `Vishnu063/IGRIS`. Do not create, rename,
or change other repositories. Step 2 creates an initial commit on `develop`.
The empty clone's `main` name did not represent an existing commit or branch ref.
A local `main` ref is established at the foundation commit after verification.
Local refs and remote refs must be reported separately.

## Recommended hosting settings (not applied)

- Protect `main`: require pull requests, at least one independent review,
  dismissal of stale approvals, and resolution of review conversations.
- Require successful CI checks once Step 24 supplies and verifies real workflows.
  Do not configure nonexistent status checks or claim CI currently runs.
- Block force pushes and branch deletion; apply rules to administrators where
  supported. Restrict bypass rights and document any emergency procedure.
- Protect `develop` against force pushes and deletion; merge small reviewed
  changes through pull requests once a remote baseline is available.
- Keep the repository private if future work contains confidential business
  details. Current visibility was observed as public during Step 1; changing it
  is outside this step. Never commit credentials even to private repositories.
- Check GitHub plan support: enforcement for private repositories may depend on
  account plan. Recommendations do not prove server-side enforcement.

## Development procedure

Execute one numbered implementation step at a time. Record implementation,
verification, review, commit evidence, and limitations before advancing.
Use topic branches from `develop` for subsequent reviewed changes when useful.
Do not force push, delete existing branches, or deploy to production.
Production deployment requires explicit approval of target, version, and scope.

Ignore patterns only reduce accidental commits; they are not secret scanning or
Guardian enforcement. Guardian implementation starts in Step 6.
