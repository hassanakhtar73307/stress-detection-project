# Architecture Evaluation and User Acceptance Testing Materials

## 1. Architecture Evaluation (Design Trade-off Discussion)

*(Insert into the Software Engineering Evaluation section, alongside the existing
maintainability/scalability/security content.)*

The deployed system uses a two-tier architecture: a stateless Flask REST API (serving the
trained XGBoost model) and a separate React single-page application (the dashboard), communicating
over HTTP/JSON. This section evaluates that architectural choice against the alternatives it
was chosen over.

**Monolith vs. microservices.** A microservices split (e.g., separating authentication,
prediction, and model-insights into independently deployable services) was considered but
rejected. For a system with a single ML model, low expected request volume, and a single
developer, microservices would add deployment and inter-service communication complexity
disproportionate to the benefit; the monolithic Flask API keeps the codebase's cyclomatic
complexity concentrated and measurable (Section [X], radon results) rather than distributed
across service boundaries where it would be harder to evaluate holistically. This trade-off
should be revisited if the system were extended to support multiple concurrent ML models or
significantly higher request volume.

**Synchronous request/response vs. streaming or message queues.** The `/predict` endpoint is a
simple synchronous HTTP request/response. This is justified by the measured sub-millisecond
XGBoost inference time (Section [X]) — there is no long-running computation to justify the
added complexity of asynchronous job queues or WebSocket streaming, both of which would be
necessary if inference took seconds rather than milliseconds (as it would for the LSTM
alternative, or for a larger deep learning model).

**Stateless API, no server-side session/database for predictions.** Each prediction request is
handled independently, with no server-side history retained; the "prediction history" seen in
the dashboard exists only in the browser's client-side state. This was a deliberate choice to
keep the deployed backend simple and to minimise the privacy exposure discussed in the Ethics
section (Section [X]) — no physiological data is logged or persisted server-side. The trade-off
is that prediction history is lost on page refresh and cannot be analysed in aggregate across
sessions or users; a production deployment intending longitudinal analysis would need to
introduce a database layer here; deliberately, and after the ethical/regulatory review this
dissertation argues is a prerequisite (Section [X]).

**Authentication architecture.** User accounts and authentication were added using a custom
token scheme (signed, time-limited tokens via `itsdangerous`) backed by a SQLite user store,
rather than an existing framework (e.g., Flask-Login with server-side sessions) or a third-party
identity provider (e.g., OAuth via Google/GitHub). This was a pragmatic choice suited to a
single-developer academic project — it avoids an external dependency and additional
infrastructure, at the cost of using a self-built solution rather than an audited third-party
one. For a real-world deployment handling sensitive health-adjacent data, an audited,
widely-used authentication library or managed identity provider would be the more defensible
choice, and this project's custom implementation should not be taken as a template for
production use without a proper security review beyond the scoped dependency audit already
performed.

**Deployment architecture.** The system is deployed as two independently hosted services: the
React frontend on Vercel (static hosting with a global CDN) and the Flask API on Render (a
managed container platform), communicating over HTTPS. This separation allows the frontend to
be served from a CDN with no cold-start delay, while isolating the heavier Python/ML dependencies
to the backend service. The trade-off, encountered directly during deployment, is operational
complexity: the two services must agree on CORS configuration and a shared API contract, and the
backend's free-tier hosting introduces a cold-start delay (up to ~60 seconds) after inactivity,
and an ephemeral filesystem that does not persist the SQLite user database across restarts. This
is a known, explicitly acknowledged limitation of the free-tier deployment choice, not an
architectural flaw in the design itself — a paid tier or a managed database service would resolve
it at additional cost, which was judged disproportionate for a dissertation prototype.

---

## 2. User Acceptance Testing Materials

A full moderated User Acceptance Testing (UAT) process was outside this project's timeline and
ethical-approval scope. However, an informal UAT pass using the **System Usability Scale (SUS)**
— a standard, validated 10-item questionnaire (Brooke, 1996) — is a low-cost, legitimate way to
gather real user feedback from a handful of peers, and is explicitly framed here as informal
feedback rather than a formal human-subjects study, avoiding any need for ethics approval.

### How to run this
1. Send the live URL (`https://stress-detection-project-exa37vp0f-hassanakhtar73307s-projects.vercel.app/`)
   and the 10 questions below to 3-5 people (coursemates, friends, family)
2. Ask them to register an account, click through several sample predictions, check the "How
   this works" panel, and then answer the 10 questions on a 1 (strongly disagree) to 5 (strongly
   agree) scale
3. Score using the standard SUS formula below

### The 10 questions (standard SUS wording, unmodified)
1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome/awkward to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

### Scoring formula
- For odd-numbered questions (1,3,5,7,9): score = (response − 1)
- For even-numbered questions (2,4,6,8,10): score = (5 − response)
- Sum all 10 adjusted scores, multiply by 2.5 → gives a score out of 100 per respondent
- Average across all respondents for your overall SUS score

### Interpreting the score (standard SUS benchmarks)
- Above 68 = above-average usability
- Below 68 = below-average usability
- Above 80 = considered excellent

### Suggested write-up once you have responses
"An informal System Usability Scale survey was conducted with N respondents (not a formal
human-subjects study; participants were personal contacts of the author, and no identifying data
was collected). The system achieved a mean SUS score of [X]/100, which [is above/is below] the
commonly cited average of 68, indicating [interpretation]. This should be read as an informal,
non-representative indication of usability rather than a statistically powered user study, given
the small and non-random sample."

---
*Reference to add in IEEE format: Brooke, J. (1996). SUS: A quick and dirty usability scale.
Usability Evaluation in Industry, 189(194), 4-7.*
