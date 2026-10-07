# Service playbook

Read the section for every selected layer before implementing it. Follow the linked official guide for the app's framework and installed package versions; these instructions are not a substitute for a compatibility check.

## Choose the fit first

1. Inspect the existing app, deployment, data model and authentication. Keep working services unless a concrete requirement justifies a migration. Add only layers the product needs.
2. For a new TypeScript MVP, a static React/Vite frontend on Workers assets, Convex functions/reactive queries, and the documented Better Auth component form one possible path. Add PostHog and R2 only when activation measurement and file storage are required. A static frontend can call cloud APIs; it does not make the backend local or offline.
3. Compare requirements, not just plan names. Vercel/Netlify can fit framework-specific hosting; Supabase can fit PostgreSQL and SQL tooling; Clerk/Auth0 can fit managed identity; Mixpanel/Amplitude can fit existing analytics; S3 can fit required AWS features. These alternatives have free offerings or allowances too. Paid plans may buy useful capacity, support or features, rather than being unnecessary by definition.

Before changing providers, account for data export/import, stable ownership IDs, active sessions, OAuth callbacks, event definitions and storage API differences. Preserve a working framework/adapter; do not migrate it just to match this stack. Obtain authorization before provisioning services, purchases or account/billing changes.

## Cloudflare: frontend and runtime

Use [Workers framework guides](https://developers.cloudflare.com/workers/framework-guides/) and [static asset billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/). For an existing Pages app, use its [platform limits](https://developers.cloudflare.com/pages/platform/limits/) and current deployment configuration.

1. Classify routes as static assets, client-side navigation, or dynamic SSR/API work. Prefer static React/Vite assets when that satisfies the product. Configure the actual build output, SPA fallback/deep links, asset paths and production environment rather than uploading a development server.
2. If SSR is required, choose the documented deployment path for this framework/version and check runtime APIs, native modules, filesystem assumptions, middleware and image/cache features. Workers is not a full Node.js process. As of 2026-10-07, Cloudflare's [Next.js guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/) recommends **beta vinext**; its [OpenNext guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/opennext/) covers existing OpenNext apps. Keep a working adapter and choose any migration explicitly based on compatibility, not this recommendation alone.
3. Keep deployment credentials and server secrets outside the browser bundle. Expose only intended public endpoint identifiers. Separate development/production Convex URLs and configure the production hostname, TLS, trusted auth origins and redirects together with the auth layer.
4. Estimate dynamic requests and CPU separately from direct static serving. Pages Functions count as Workers requests; `run_worker_first` invokes code even for matching assets, and Workers Caching can meter cached requests. A free 10 ms CPU limit is not proof that an SSR workload fits. Check builds, asset limits and any extra Cloudflare products too.
5. Exercise the production-runtime build, direct navigation to a nested route, missing routes, assets, auth redirects and a real backend call. For SSR, smoke the runtime-dependent routes on the actual target, not just the framework's Node.js dev server. Record unsupported features and measured request/CPU headroom before calling the deployment ready.

Vercel/Netlify may reduce adaptation work for an app already using their platform features. Moving hosts still requires checking feature support, commercial-use terms, redirects, environment variables and deployment behavior.

## Convex: schema, authorization and reactive calls

Use [schemas](https://docs.convex.dev/database/schemas), [React integration](https://docs.convex.dev/client/react/overview), [authentication in functions](https://docs.convex.dev/auth/functions-auth), and [usage accounting](https://docs.convex.dev/production/state/limits).

1. Define `convex/schema.ts` with validators for the actual records and stable owner/team identifiers. Add indexes matching real access paths, such as owner plus creation time; use indexed bounded queries and pagination instead of full-table scans. Indexes also consume database storage and I/O.
2. Implement typed queries for reads, mutations for transactional writes, and actions for external work. Validate public arguments. At each public entry point, obtain the verified identity with the configured auth integration and check record ownership or team membership. Derive an owner from that identity, not a client-supplied `userId`. Authentication alone does not authorize a document ID.
3. Use the generated API with the documented client (`useQuery`/`useMutation` in React). Let subscriptions supply live updates; do not add polling or a second WebSocket layer to duplicate them. Handle loading, signed-out, empty and failure states. Integrate the Better Auth provider when that is the chosen auth layer.
4. Budget the whole team, including other projects and development deployments where the meter applies. Calls include explicit requests, subscription updates, scheduled executions and file accesses. Also track action GB-hours, database storage/I/O, file storage/egress, and applicable search/deployment limits. Avoid broad subscriptions that reread large data sets on every change. Free resource caps and Starter's paid overages are different plans.
5. Prove that an authorized mutation updates a second subscribed client without refresh. Prove a signed-out request and another user's read/write are rejected server-side. Check the deployed usage dashboard and report measured consumption; do not translate a count of users into a call estimate without their actual behavior.

Supabase/PostgreSQL is a valid choice for SQL, relational tools or existing schemas. Migrating to Convex changes the database model, queries, API functions and authorization approach; it is not a connection-string swap. A separate API/database/realtime stack remains valid when requirements demand it, but brings integration work a new Convex-fitting MVP may not need.

## Better Auth: component, routes and sessions

Use the [official Convex integration](https://better-auth.com/docs/integrations/convex) and the [Convex-maintained component's framework guides](https://labs.convex.dev/better-auth). For the static React/Vite path, read the [React SPA guide](https://labs.convex.dev/better-auth/framework-guides/react); do not copy Next.js-only server helpers into it.

1. Select the supported component/Better Auth/Convex versions in that guide, including its Better Auth version pin. Install `@convex-dev/better-auth` with Better Auth, register the component in `convex/convex.config.ts`, configure the auth provider, and create the server instance using the component's database adapter and Convex plugin. Installing `better-auth` alone does not connect auth to Convex.
2. Mount the component's auth HTTP routes in `convex/http.ts`. Use the framework's documented client/provider and any required server proxy/helpers. For React SPAs, configure the server/client cross-domain plugins, CORS route handling and `ConvexBetterAuthProvider` described by the SPA guide. Use the `.convex.site` HTTP endpoint for auth and the `.convex.cloud` client endpoint for Convex calls; they are not interchangeable.
3. Store the auth secret and OAuth client secrets in the server/deployment environment. Configure actual base URLs, trusted origins and production HTTPS/session behavior. Use explicit approved development/production origins, not a wildcard. Set OAuth callback URLs for the auth endpoint the guide uses; the SPA callback can live on the Convex site domain rather than the frontend domain.
4. Implement only required sign-in methods, sign-out, session restoration and server-side identity checks. For email/password, implement verification and password-reset delivery when required, rather than treating a guide's nonverified demo as a production policy. OAuth providers have registration/approval requirements; email/SMS providers have their own quotas and fees. The framework does not include managed hosting, delivery or free unlimited infrastructure.
5. Exercise sign-up/sign-in, refresh/session restoration, sign-out, expiry, denied origins and an authorized Convex call in the deployed environment. For selected OAuth/email flows, exercise callback and delivery behavior too. Verify that a cleared or expired session cannot read/write private records; UI session state is not the authorization boundary.

Clerk/Auth0 provide managed identity rather than making the app own this implementation. They can be preferable for needed features or an existing working integration, and have free plans too. An auth migration must map identities, handle provider-specific credential export limits, define how old sessions end, and update every backend ownership check and OAuth callback.

## PostHog: activation, consent and privacy

Use [data collection controls](https://posthog.com/docs/privacy/data-collection), [replay privacy](https://posthog.com/docs/session-replay/privacy), [pricing](https://posthog.com/pricing) and [per-product billing limits](https://posthog.com/docs/billing/limits-alerts).

1. Define activation as an actual successful value-producing action in this product. For a collaboration MVP, an illustrative funnel is `signup_completed` → `workspace_created` → `first_document_shared`; choose the app's real equivalent. Emit success events after the action succeeds, not on a button click. Document properties, exclude test accounts, and avoid double-counting a server/client event.
2. Initialize the SDK for the selected region and environment. Use an opaque stable user identifier after authentication and reset identity on sign-out. Send only the properties the funnel needs. The browser project token is not the personal API key; keep personal API keys and backend credentials server-side.
3. Apply the app's lawful consent policy before capture. Where opt-in consent is required, initialize opted out by default and wire grant/withdrawal to the documented capture controls. Verify that both events and replay respect denial and withdrawal. Do not treat cookieless configuration or vendor marketing as a legal-compliance guarantee.
4. Keep autocapture/replay off unless needed. For replay, mask inputs and sensitive page text before it leaves the browser (`maskAllInputs`, `maskTextSelector` and `ph-no-capture` are documented controls). Inspect event properties, URLs, query strings, network recordings and console capture for tokens, signed file URLs, emails, payments and private content; input masking alone does not cover them. Enable only required products and persist/check a billing limit for each on paid accounts. Data rejected at a cap is permanently lost.
5. Exercise one real activation path and verify its events form the intended funnel in PostHog. Inspect captured payloads and any replay for sensitive data, including a password displayed as text. Verify consent-denied traffic sends no captured data and a logout does not link the next user's events. Report observed event/recording usage and the account's saved limits.

Mixpanel/Amplitude may already cover the required event analysis; replacing them requires remapping identities, events, funnels and retention/history requirements. Compare the products and meters actually enabled, not just a vendor's headline free allowance.

## Cloudflare R2: private objects and controlled uploads

Use [R2 pricing](https://developers.cloudflare.com/r2/pricing/), [presigned URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/) and the [S3 compatibility matrix](https://developers.cloudflare.com/r2/api/s3/api/).

1. Select **Standard** storage for the documented free allowance; Infrequent Access has no such free tier and adds retrieval/minimum-duration charges. Keep user buckets private. Use a server-side Worker binding or narrowly scoped S3 credentials; never put R2 access keys in the client or publish a bucket to bypass authentication.
2. Authenticate the request to the signing/access endpoint. Generate object keys server-side and keep an owner-bound metadata record in the backend. Check ownership/team permissions before issuing upload, download or delete access. A guessed key or user-controlled key prefix is not permission. Use short-lived URLs scoped to one object and operation, or an authenticated Worker route.
3. Define accepted types, maximum bytes, per-user storage/upload quotas and permitted operations at the server boundary. For direct PUT, sign the expected content type and restrict CORS to approved origins; neither proves file content or ownership. Verify the stored size/type before marking an upload available, rejecting/deleting invalid objects. Use an authenticated upload route that enforces bytes while receiving them if a hard pre-storage size limit is required. Control rate/quota before granting access so valid users cannot generate unlimited billable uploads.
4. Treat signed URLs as reusable bearer credentials until expiry, not one-time links. Keep them out of analytics/logs and private content out of public caching. R2 presigned URLs use the S3 API domain, not a custom domain, and HTML-form presigned POST is not supported. Check every required S3 feature before promising a drop-in replacement.
5. Exercise authorized upload/read/delete, unauthenticated access, another user's object, expired access, and oversized/disallowed uploads. Count stored GB-month, writes/listing/multipart Class A operations and reads/metadata Class B operations, plus any Worker/backend processing. Free direct internet egress does not cap these meters; no account-wide R2 hard spending cap is established here. Report the remaining bill exposure.

S3 is valid when AWS integration or a missing S3 feature matters. Moving to R2 changes endpoints, signing, feature support and billing; moving objects can incur source-side transfer/operation charges. Private access must survive the move rather than becoming public for convenience.

## Dated free-allowance reference

Checked **2026-10-07**; recheck official sources and the actual account plan before setup. Monthly values reset on the provider's applicable billing period, and additional product/platform limits apply.

| Layer | Included free allowance | Source |
|---|---|---|
| Cloudflare | Direct static serving: free/unlimited; Workers Free: 100,000 dynamic requests/day and 10 ms CPU/invocation; Pages: 500 builds/month. | [Workers](https://developers.cloudflare.com/workers/platform/pricing/), [Pages](https://developers.cloudflare.com/pages/platform/limits/) |
| Convex Free | 1M calls/month; 20 GB-hours action compute/month; 0.5 GB database; 1 GB database I/O/month; 1 GB file storage; 1 GB file egress/month. Generally per team; calls include subscription updates. | [Limits/accounting](https://docs.convex.dev/production/state/limits) |
| Better Auth | Free open-source framework, not a managed hosting or monthly-active-user plan. Backend, OAuth requirements, email/SMS and maintenance are separate. | [Convex integration](https://better-auth.com/docs/integrations/convex) |
| PostHog | 1M product analytics events/month; 5,000 session recordings/month. Other products/add-ons have independent allowances. | [Pricing](https://posthog.com/pricing) |
| R2 Standard | 10 GB-month storage, 1M Class A and 10M Class B operations/month; free direct internet egress. Infrequent Access is excluded. | [Pricing](https://developers.cloudflare.com/r2/pricing/) |

Convex Free caps resources; Starter permits paid overages. PostHog's no-card Free plan stops at limits; paid accounts need saved product-specific caps. Alerts are not spending caps. Include domains, transactional email/SMS, payment processing, external API usage and any attached metered services in the budget. Report what is measured, what is estimated and what remains uncapped.

## Dated paid-plan comparison

Checked **2026-10-07**; USD before tax. Compare the required features and actual billing mode. These are optional alternatives, not interchangeable bundles or a claim that every MVP needs paid plans.

| Layer | Current named alternative | Billing qualification |
|---|---|---|
| Frontend | [Vercel Pro](https://vercel.com/pricing): $20/month platform fee. | Includes one deploying seat and $20/month infrastructure-usage credit; additional deploying seats are $20/month each. Usage above credit and add-ons can cost more. [Hobby is free for personal/non-commercial use](https://vercel.com/docs/plans/pro-plan). |
| Backend/database | [Supabase Pro](https://supabase.com/pricing): $25/month base. | Its $10/month compute credit covers one Micro project and is per organization, not per project. [Hourly compute](https://supabase.com/docs/guides/platform/manage-your-usage/compute) and quota overages can add charges. Free exists; it has at most two active projects and pauses after a week of inactivity. |
| Authentication | [Clerk Pro](https://clerk.com/pricing): $25/month on monthly billing. | $20/month is the annual-billing equivalent. Includes 50,000 monthly retained users (MRU)/app; first-tier overage is $0.02/MRU/month. Hobby is free through 50,000 MRU. SMS, SSO and other add-ons can be separate; MRU is not MAU. |
| Analytics | [Amplitude Plus](https://amplitude.com/pricing) starts at $0 with the first 2M events/month free; [Mixpanel Enterprise](https://mixpanel.com/pricing/) is sales-quoted. | Amplitude's paid event/MTU rate depends on the checkout selection; no fixed monthly rate is asserted here. [Terms](https://amplitude.com/plus-plan-terms) support monthly or 12-month auto-renewing commitments. Mixpanel also offers Free, up to 20M events and 500,000 replays/month. Obtain the actual paid quote rather than using an old subscription floor. |
| Files | [AWS S3 Standard](https://aws.amazon.com/s3/pricing/): pay-as-you-go, no subscription minimum. | US East (N. Virginia), first 50 TB: $0.023/GiB-month; PUT/COPY/POST/LIST $0.005/1,000 and GET/other $0.0004/1,000. Direct internet transfer's first paid tier is $0.09/GB above a [shared 100 GB/month allowance](https://aws.amazon.com/about-aws/global-infrastructure/global-network/faqs/) (not per bucket/service/region; excludes China/GovCloud). Eligible new-account credits are temporary, not a recurring allowance. |

An illustrative **frontend + database subtotal is $45/month**: Vercel Pro $20 + Supabase Pro $25. Assume one deploying seat, one Micro project covered by Supabase's compute credit, Vercel usage within its infrastructure credit, all included quotas respected and no paid add-ons. These credits cover eligible usage, not the base plan fee.

The subtotal excludes extra seats/projects/compute, overages, separately billed storage/requests/transfer, email/SMS, domains/renewals and taxes. Supabase Auth may already meet the app's needs; do not automatically add paid Clerk. This is an optional plan subtotal, not measured savings or a universal production bill. Free included provider usage can have no charge only while the app fits every relevant allowance/runtime constraint; external costs and uncapped usage still matter.

## Local development versus production

[Supabase's self-hosting guide](https://supabase.com/docs/guides/self-hosting) explicitly warns that its CLI local development stack is not hardened for production and must not be exposed externally. Use the documented production self-hosting path when choosing that option.

1. Identify what runs locally and what still uses a hosted API/database/auth service. A frontend dev server is neither an offline backend nor a public deployment. For a genuinely offline product, its required data, auth and storage paths must work without cloud access.
2. For public self-hosting, arrange a listening interface, firewall rules, a reachable address and router/NAT forwarding or a tunnel. `localhost` is same-device only; carrier-grade NAT can prevent inbound forwarding. A tunnel solves reachability, not record authorization or database recovery.
3. Configure a public hostname, TLS/certificate renewal, trusted auth origins, CORS and OAuth callback URLs. Test sessions on the real origin. Keep the host, power and network online through sleep, reboots and updates; arrange monitoring and off-host backups, then exercise restoration.
4. Maintain the actual API, database and realtime integration, including container/native-process lifecycle, schema changes, secrets, object storage and email delivery. Existing hardware can avoid a rental line item, but electricity, replacement and operating work remain. A rented server adds rental cost; do not present the two as equal prices.
5. Choose self-hosting when control, offline operation, data residency or compliance requirements justify the work. Choose managed services when their runtime and limits fit and managed operations are useful. Either choice still needs app-level authorization, privacy and a backup/recovery plan.

## Completion report

Report selected/reused layers, the exercised deployed path and rejection cases, runtime/migration constraints, measured meter headroom, saved billing controls, uncapped/external costs and any untested integrations. Do not report a $0 production bill merely because the source is open, the frontend is local or one provider advertises a free tier.
