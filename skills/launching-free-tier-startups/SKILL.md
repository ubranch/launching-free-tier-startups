---
name: launching-free-tier-startups
description: "Use when choosing or launching an early-stage startup stack with free-tier hosting, realtime TypeScript data, app-owned auth, product analytics, and S3-compatible storage."
---

# Launching free-tier startups

Use this five-layer stack when it fits a new MVP. Reuse working services in an existing app. Free allowances do not guarantee a $0 bill, and localhost development is not public production hosting.

## Five-layer reference

| Layer | Default | Fit and constraint |
|---|---|---|
| Frontend | Cloudflare Workers static assets; retain an existing Pages app | Separate static serving from SSR/Functions; verify framework and runtime compatibility. |
| Backend + database | Convex Free | Typed functions and reactive queries; shared team meters include subscription updates. |
| Authentication | Better Auth | Open-source framework, not managed auth; Convex requires its official component/adapter. |
| Analytics | PostHog | Actual activation events, consent and masking; independent product allowances and caps. |
| File storage | Cloudflare R2 Standard | Private owner-bound objects and authorized access; storage/operations still meter. |

## Apply it

1. Inspect the app's requirements and existing services. Select only needed layers; identify static versus SSR hosting and migration constraints.
2. Before implementing a selected layer, **read its section in [the service playbook](references/service-playbook.md)**. Read the fit, allowance and hosting guidance too when choosing or changing the stack. Use current official integration docs for the installed framework/package versions.
3. Recheck account plans, all applicable meters and saved billing controls. Include domains, email/SMS, payments and external services. Alerts are not caps; disclose uncapped exposure. Obtain authorization before provisioning, purchases or account/billing changes.
4. Implement one end-to-end path using the selected playbook sections: frontend, sign-in, authorized mutation, reactive update, an activation event, and private upload/read when required. Keep secrets server-side and derive ownership from verified identity.
5. Exercise the deployed path and rejection cases named in the playbook. Report measured quota headroom, remaining costs, runtime/migration constraints and untested integrations. Upgrade for observed demand or required features, not hypothetical scale.

## Sources

[Original video and caption](https://www.instagram.com/p/DeHYCIpColc/): frontend 00:11, backend 00:30, auth 00:54, analytics 01:16, storage 01:40; launch-before-scale principle 02:10–02:23. The workflow adds implementation and billing safeguards rather than treating promotional claims as guarantees.

Implementation instructions, dated allowances, alternative tradeoffs and official references are in [references/service-playbook.md](references/service-playbook.md). Recheck them before setup.
