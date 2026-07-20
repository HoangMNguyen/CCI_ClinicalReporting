# AWS run counter

This AWS SAM application deploys one `POST /run` endpoint backed by Lambda and
DynamoDB. Each authenticated, unique event increments both a total counter and
a UTC daily counter. Event IDs are retained for 90 days to make retries
idempotent; DynamoDB removes them automatically using TTL.

No report, study, filename, path, user, or patient data is sent.

## Deploy

Prerequisites: an AWS account, configured AWS CLI credentials, and the AWS SAM
CLI.

```powershell
cd infra/run_counter
sam build
sam deploy --guided
```

When prompted for `CounterToken`, provide a randomly generated value of at
least 24 characters. Keep the token out of source control. After deployment,
copy the `RunCounterUrl` stack output.

Configure both variables in the environment that launches the desktop app:

```powershell
$env:CLINICAL_REPORTING_RUN_COUNTER_URL = "https://example.execute-api.us-east-1.amazonaws.com/run"
$env:CLINICAL_REPORTING_RUN_COUNTER_TOKEN = "the-token-supplied-during-deployment"
$env:PYTHONPATH = "src"
python -m clinical_reporting
```

If either variable is absent, counting is disabled. Delivery runs on a daemon
thread with a two-second timeout. Successes and failures are intentionally not
shown or logged by the desktop application.

## Read the counts

In the DynamoDB console, open the deployed table and select **Explore table
items**. Counter records have `pk = COUNTER`:

- `sk = TOTAL` is the all-time successful-export count.
- `sk = DAILY#YYYY-MM-DD` is a UTC daily count.

Records with `pk = EVENT` support duplicate suppression and expire after 90
days; deleting them does not change the counters.

## Security notes

The bearer token prevents accidental or anonymous submissions but cannot be
considered permanently secret when distributed with a desktop application.
For stronger identity, place JWT authorization in front of the route or issue
separate revocable tokens to installations. Keep API throttling enabled and
configure AWS cost alerts appropriate to the account.
