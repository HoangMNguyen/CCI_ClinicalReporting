# AWS usage tracker: beginner deployment guide

This folder contains the complete AWS backend for Clinical Reporting usage
tracking. You do **not** create a Windows/Linux server or an EC2 virtual
machine. AWS SAM creates these managed, serverless resources for you:

1. **API Gateway** provides one HTTPS `POST /run` address for the desktop
   application, plus `GET /stats` and `GET /stats/data` for the browser
   dashboard.
2. **Lambda** validates each request and updates the counts. A second,
   read-only Lambda serves the statistics dashboard.
3. **DynamoDB** stores the events and counters.
4. **IAM** gives the write Lambda permission to update only its DynamoDB
   table, and the stats Lambda permission only to query it.
5. **CloudWatch Logs** records Lambda invocation diagnostics. The functions do
   not log usernames, tokens, or request bodies themselves.

The desktop sends a random event ID, one of the event types below, the local
login name returned by Python (for example, `hmn39`), and the saved object's
name:

- `report_saved` after an Excel report is saved successfully, with the final
  Excel filename in `report_name`.
- `setting_saved` after a report setting is saved successfully, with the name
  entered by the user in `setting_name`.

It does not send report contents, setting contents, study names, directory
paths, or patient information. Network delivery remains silent and cannot make
either save operation fail.

## Before you begin

You need:

- An AWS account and permission to create CloudFormation, Lambda, API Gateway,
  DynamoDB, IAM role, S3 deployment, and CloudWatch resources.
- Windows PowerShell.
- Python 3.14, which is already installed on the current development machine.
- AWS CLI version 2.
- AWS SAM CLI.

Choose one AWS Region and use it throughout this guide. The examples use
`us-east-1`. Substitute your organization's approved Region if necessary.

Do not use AWS root-user access keys. In an organization, ask the AWS
administrator for an IAM Identity Center/SSO profile with deployment
permissions. For a personal account, configure IAM Identity Center or another
administrator-approved CLI identity before proceeding.

## Step 1: Install AWS CLI version 2

1. Open the official AWS installation page:
   <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>
2. Under **Windows**, download and run the 64-bit AWS CLI MSI installer.
3. Close PowerShell and open a new PowerShell window.
4. Verify the installation:

```powershell
aws --version
```

You should see an `aws-cli/2...` version. If PowerShell says `aws` is not
recognized, restart Windows or reinstall the MSI.

## Step 2: Connect AWS CLI to your AWS identity

For AWS IAM Identity Center/SSO, run:

```powershell
aws configure sso --profile cci-deploy
```

AWS asks for values supplied by your AWS administrator, including the SSO start
URL, SSO Region, AWS account, and permission set. When it asks for the default
deployment Region, enter `us-east-1` (or your approved Region). Use `json` for
the output format.

Then sign in and verify the account:

```powershell
aws sso login --profile cci-deploy
aws sts get-caller-identity --profile cci-deploy
```

The second command displays an account number and an ARN. Confirm that this is
the intended AWS account before deploying. AWS's SSO setup documentation is at
<https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html>.

If your organization gave you an access key instead of SSO, use this command
and enter the supplied values:

```powershell
aws configure --profile cci-deploy
aws sts get-caller-identity --profile cci-deploy
```

Never paste AWS access keys into this repository or its `.env` files.

## Step 3: Install AWS SAM CLI

1. Open the official SAM installation page:
   <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html>
2. In the **Windows** section, download and run the 64-bit MSI.
3. Open a new PowerShell window.
4. Verify the installation:

```powershell
sam --version
```

The template uses the AWS Lambda `python3.14` runtime, matching the Python
version on this workstation. A normal build does not require Docker.

## Step 4: Open this deployment folder

```powershell
Set-Location "C:\Users\hmn39\Dropbox\Current Work\CCI_ClinicalReporting\infra\run_counter"
```

Confirm that PowerShell can see the template:

```powershell
Get-Item template.yaml
```

The repository `.gitignore` excludes `.aws-sam/` and `samconfig.toml`. These are
generated deployment files; `samconfig.toml` can contain parameter values and
must not be committed.

## Step 5: Generate and temporarily save the application tokens

Two independent bearer tokens are used:

- `CounterToken` is shared by the desktop application and the write Lambda.
- `StatsToken` is the read-only access key typed into the browser dashboard.
  Keeping it separate means dashboard viewers never hold the write token that
  is embedded in desktop installations.

Generate two strong random tokens:

```powershell
$counterToken = python -c "import secrets; print(secrets.token_urlsafe(32))"
$statsToken = python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The tokens are stored temporarily in the PowerShell variables `$counterToken`
and `$statsToken`. Copy each to the clipboard when the deployment prompt asks
for it (`$counterToken | Set-Clipboard`, then later
`$statsToken | Set-Clipboard`).

Save both in an organization-approved password manager. CloudFormation marks
the parameters `NoEcho`, so the deployment output will not show them later.

## Step 6: Validate and build the AWS application

First validate the SAM/CloudFormation template:

```powershell
sam validate --lint --profile cci-deploy --region us-east-1
```

Expected result:

```text
template.yaml is a valid SAM Template
```

Build the Lambda deployment package:

```powershell
sam build
```

Expected result:

```text
Build Succeeded
```

SAM writes generated files under `.aws-sam/`. Do not edit those files; edit
`template.yaml` or `function/app.py`, then build again.

## Step 7: Deploy for the first time

Run the guided deployment:

```powershell
sam deploy --guided --profile cci-deploy --region us-east-1
```

Use these answers. Text inside parentheses explains the choice and should not
be typed:

```text
Stack Name: cci-clinical-reporting-usage
AWS Region: us-east-1
Parameter CounterToken: paste the counter token from Step 5
Parameter StatsToken: paste the stats token from Step 5
Confirm changes before deploy: Y
Allow SAM CLI IAM role creation: Y
Disable rollback: N
RunCounterFunction has no authentication defined, Is this okay?: Y
StatsFunction has no authentication defined, Is this okay?: Y
Save arguments to configuration file: N
```

The API Gateway routes have no API Gateway authorizer, which causes the
authentication warnings. Answering `Y` is expected because each Lambda itself
checks its bearer token before touching DynamoDB (the dashboard HTML shell is
served without a token but contains no data). The API also has request-rate
throttling configured.

Answer `N` to saving the configuration so SAM does not write the bearer token
to `samconfig.toml`.

SAM will:

1. Upload the Lambda package to a SAM-managed S3 deployment bucket.
2. Create a CloudFormation change set.
3. Create API Gateway, Lambda, DynamoDB, and IAM resources.
4. Print `Successfully created/updated stack` when complete.

The first deployment can take several minutes. Do not close PowerShell while it
is running.

## Step 8: Capture the endpoint and table name

The deployment output displays `RunCounterUrl`, `RunCounterTableName`, and
`StatsUrl`. You can retrieve them again with these commands:

```powershell
$counterStack = "cci-clinical-reporting-usage"
$counterRegion = "us-east-1"

$counterUrl = aws cloudformation describe-stacks `
    --stack-name $counterStack `
    --region $counterRegion `
    --profile cci-deploy `
    --query "Stacks[0].Outputs[?OutputKey=='RunCounterUrl'].OutputValue | [0]" `
    --output text

$counterTable = aws cloudformation describe-stacks `
    --stack-name $counterStack `
    --region $counterRegion `
    --profile cci-deploy `
    --query "Stacks[0].Outputs[?OutputKey=='RunCounterTableName'].OutputValue | [0]" `
    --output text

$counterUrl
$counterTable
```

The URL should resemble:

```text
https://abc123.execute-api.us-east-1.amazonaws.com/run
```

## Step 9: Test the AWS endpoint manually

Send one test report event as `hmn39`:

```powershell
$counterBody = @{
    event_id = [guid]::NewGuid().ToString()
    event_type = "report_saved"
    username = "hmn39"
    report_name = "Monthly Enrollment 260724_143000.xlsx"
} | ConvertTo-Json -Compress

$counterResponse = Invoke-WebRequest `
    -Method Post `
    -Uri $counterUrl `
    -Headers @{ Authorization = "Bearer $counterToken" } `
    -ContentType "application/json" `
    -Body $counterBody

$counterResponse.StatusCode
```

The expected status is `204`, meaning the event was accepted with no response
body.

Test a setting event by changing only the event type:

```powershell
$counterBody = @{
    event_id = [guid]::NewGuid().ToString()
    event_type = "setting_saved"
    username = "hmn39"
    setting_name = "baseline"
} | ConvertTo-Json -Compress

(Invoke-WebRequest `
    -Method Post `
    -Uri $counterUrl `
    -Headers @{ Authorization = "Bearer $counterToken" } `
    -ContentType "application/json" `
    -Body $counterBody).StatusCode
```

This should also return `204`.

## Step 10: Configure the Clinical Reporting application

Release executables can carry this configuration automatically. Create
`src/clinical_reporting/telemetry.json` from `telemetry.example.json`, then use
the repository's PyInstaller command, which embeds the file in the executable.
The real configuration is ignored by Git because it contains the shared bearer
token. Users of that executable do not need to set environment variables.

The environment-variable instructions below are optional overrides for source
runs, development, and troubleshooting.

For a temporary test, set these variables in the same PowerShell window that
will launch Clinical Reporting:

```powershell
$env:CLINICAL_REPORTING_RUN_COUNTER_URL = $counterUrl
$env:CLINICAL_REPORTING_RUN_COUNTER_TOKEN = $counterToken
```

Launch from the repository root:

```powershell
Set-Location "C:\Users\hmn39\Dropbox\Current Work\CCI_ClinicalReporting"
$env:PYTHONPATH = "src"
python -m clinical_reporting
```

To make the settings available after restart, store them in the current
Windows user's environment:

```powershell
[Environment]::SetEnvironmentVariable(
    "CLINICAL_REPORTING_RUN_COUNTER_URL",
    $counterUrl,
    "User"
)

[Environment]::SetEnvironmentVariable(
    "CLINICAL_REPORTING_RUN_COUNTER_TOKEN",
    $counterToken,
    "User"
)
```

Close and reopen the IDE/application after setting persistent variables.
Windows stores user environment variables locally; treat the bearer token as a
managed application credential.

If either variable is absent, tracking is disabled. If AWS is unavailable,
requests time out silently in the background and the user's report/setting save
still succeeds normally.

## Step 11: Generate real application events

1. Start Clinical Reporting after configuring the two variables.
2. Create and successfully save an Excel report using **Save Output**.
3. Enable setting saving, enter a setting name, and successfully click **Save
   Setting**.
4. No telemetry confirmation or error is shown. This is intentional.

The username is read from the local Windows/Python login. On the current
workstation, Python returns `hmn39`.

## Step 12: View events and counts in the AWS console

1. Sign in to the AWS Management Console.
2. Confirm the top-right Region matches the deployment Region (`us-east-1` in
   these examples).
3. Search for and open **DynamoDB**.
4. Choose **Tables** in the left navigation.
5. Select the table whose name starts with the CloudFormation stack name.
6. Choose **Explore table items**.

The table contains these counter groups:

| Partition key (`pk`) | Sort key (`sk`) | Meaning |
| --- | --- | --- |
| `COUNTER#REPORT_SAVED` | `TOTAL` | All successfully saved reports |
| `COUNTER#REPORT_SAVED` | `DAILY#YYYY-MM-DD` | Reports saved on that UTC date |
| `COUNTER#REPORT_SAVED` | `USER#hmn39` | Reports saved by `hmn39` |
| `COUNTER#SETTING_SAVED` | `TOTAL` | All successfully saved settings |
| `COUNTER#SETTING_SAVED` | `DAILY#YYYY-MM-DD` | Settings saved on that UTC date |
| `COUNTER#SETTING_SAVED` | `USER#hmn39` | Settings saved by `hmn39` |

Rows with `pk = EVENT` contain the event ID, event type, username, UTC server
timestamp, and either `report_name` or `setting_name`. These detail rows expire
after 90 days to limit retained identifiable usage data. Aggregate counter rows
do not expire.

If this stack previously ran the older report-only counter, its old
`pk=COUNTER` rows remain but are no longer incremented. The new categorized
counters begin when this version of the Lambda is deployed.

## Step 13: Read a count with AWS CLI (optional)

Report total:

```powershell
aws dynamodb get-item `
    --table-name $counterTable `
    --region $counterRegion `
    --profile cci-deploy `
    --consistent-read `
    --key '{"pk":{"S":"COUNTER#REPORT_SAVED"},"sk":{"S":"TOTAL"}}' `
    --query "Item.run_count.N" `
    --output text
```

Settings saved by `hmn39`:

```powershell
aws dynamodb get-item `
    --table-name $counterTable `
    --region $counterRegion `
    --profile cci-deploy `
    --consistent-read `
    --key '{"pk":{"S":"COUNTER#SETTING_SAVED"},"sk":{"S":"USER#hmn39"}}' `
    --query "Item.run_count.N" `
    --output text
```

## Step 14: View the statistics dashboard in a browser

The stack serves a read-only dashboard at the `StatsUrl` output, which looks
like:

```text
https://abc123.execute-api.us-east-1.amazonaws.com/stats
```

Open it in any browser. The page asks once for the access key; paste the
`StatsToken` from Step 5. The current deployment's URL and token are kept in
`stats_dashboard.json` beside this README (git-ignored, unlike the rest of
`infra/`; keep a copy in the password manager as well). The browser remembers the key locally (use **Forget
key** on a shared computer) and then shows:

- Total reports and settings saved, users seen, and the last activity time.
- A daily-trend chart for the last 90 days (falls back to a table if the
  network blocks the cdnjs.cloudflare.com chart library).
- Saves per user.
- The 50 most recent saves with username and report/setting name. These come
  from the detail rows, so they cover at most the last 90 days before TTL
  expiry.

All values are UTC, matching how the Lambda records counters. Share `StatsUrl`
and the `StatsToken` only with people approved to see usernames and report
filenames. The dashboard cannot modify any data: its Lambda holds only
DynamoDB `Query` permission, and the desktop write token is not accepted for
reading.

If the page loads but the key is rejected (`401`), the pasted value does not
match the deployed `StatsToken` parameter. Redeploy with the intended token or
retrieve the correct value from the password manager.

## Updating an existing deployment

Deploy the Lambda before distributing the updated desktop application. The new
Lambda remains compatible with older desktops that do not send a saved name,
so telemetry continues during the rollout. DynamoDB is schemaless and the
table's keys have not changed; this update requires no data migration and does
not replace or clear the existing table.

1. Open PowerShell and authenticate to the same AWS account used by the
   existing stack:

```powershell
aws sso login --profile cci-deploy
aws sts get-caller-identity --profile cci-deploy
```

Confirm that the account shown is the production account. If the profile uses
access keys instead of SSO, omit the first command.

2. Retrieve the existing endpoint and table name before making changes:

```powershell
$counterStack = "cci-clinical-reporting-usage"
$counterRegion = "us-east-1"
$counterProfile = "cci-deploy"

aws cloudformation describe-stacks `
    --stack-name $counterStack `
    --region $counterRegion `
    --profile $counterProfile `
    --query "Stacks[0].Outputs" `
    --output table
```

3. From the repository root, run the telemetry and Lambda tests:

```powershell
Set-Location "C:\Users\hmn39\Dropbox\Current Work\CCI_ClinicalReporting"
python -m pytest -q tests/unit/test_telemetry.py tests/ui/test_output_run_counter.py tests/unit/test_run_counter_lambda.py tests/unit/test_stats_lambda.py
```

4. Validate and build the updated Lambda package:

```powershell
Set-Location "C:\Users\hmn39\Dropbox\Current Work\CCI_ClinicalReporting\infra\run_counter"
sam validate --lint --profile $counterProfile --region $counterRegion
sam build
```

Both commands must succeed before deployment.

5. Deploy to the existing stack:

```powershell
sam deploy --guided --profile $counterProfile --region $counterRegion
```

At the prompts, use the existing stack name (`cci-clinical-reporting-usage`),
Region, and bearer token. Retrieve the token from the approved password manager
used for the first deployment. The first redeploy after the dashboard was
added also prompts for `StatsToken`; generate it as in Step 5 and store it in
the password manager, and on later updates paste the stored value. Confirm the
change set, allow SAM to use the existing IAM capabilities, keep rollback
enabled, accept the expected warnings about API Gateway authentication, and
answer `N` when asked to save arguments. Do not invent a new stack name or
counter token for a routine code update.

Review the change set before approving it. It should update the Lambda code; it
should not replace `RunCounterTable`. Wait for `Successfully created/updated
stack`.

6. Retrieve the endpoint again and send a named test event:

Copy the existing bearer token from the approved password manager, then load it
into the current PowerShell session without putting it in a command:

```powershell
$counterToken = Read-Host "Paste the existing counter token"
```

```powershell
$counterUrl = aws cloudformation describe-stacks `
    --stack-name $counterStack `
    --region $counterRegion `
    --profile $counterProfile `
    --query "Stacks[0].Outputs[?OutputKey=='RunCounterUrl'].OutputValue | [0]" `
    --output text

$testEventId = [guid]::NewGuid().ToString()
$counterBody = @{
    event_id = $testEventId
    event_type = "report_saved"
    username = "deployment-test"
    report_name = "Server Update Test.xlsx"
} | ConvertTo-Json -Compress

(Invoke-WebRequest `
    -Method Post `
    -Uri $counterUrl `
    -Headers @{ Authorization = "Bearer $counterToken" } `
    -ContentType "application/json" `
    -Body $counterBody).StatusCode
```

`$counterToken` must contain the same bearer token supplied during deployment.
The expected status is `204`.

7. In the DynamoDB console, open the existing table, choose **Explore table
   items**, and locate the row with `pk = EVENT` and `sk = $testEventId`. Confirm
   that it contains `report_name = Server Update Test.xlsx`. This test row will
   expire through the existing 90-day TTL.

8. Build and distribute the updated desktop application only after the server
   check succeeds. Existing installed desktops keep working; newly updated
   desktops will begin adding `report_name` and `setting_name` to subsequent
   events.

## Removing the AWS backend

This permanently deletes the endpoint, Lambda, and DynamoDB table—including
all counts. Export any needed data first, then run:

```powershell
sam delete `
    --stack-name cci-clinical-reporting-usage `
    --region us-east-1 `
    --profile cci-deploy
```

Also remove the two `CLINICAL_REPORTING_RUN_COUNTER_*` environment variables
from deployed desktops.

## Troubleshooting

### `aws` or `sam` is not recognized

Close and reopen PowerShell. If it still fails, reinstall the corresponding MSI
and restart Windows.

### SSO token has expired

```powershell
aws sso login --profile cci-deploy
```

Then repeat the failed command.

### `AccessDenied` during deployment

The `cci-deploy` identity lacks permission to create one of the resources or
the Lambda IAM role. Send the complete AWS error to your AWS administrator and
ask for the missing deployment permission. Do not work around this with root
access keys.

### Manual endpoint returns `401`

The bearer token does not match the `CounterToken` used by the Lambda. Redeploy
the same stack with the intended token, then configure desktops with that exact
value.

### Manual endpoint returns `400`

The JSON is missing a valid UUID, supported event type, valid username, or a
valid saved name. Supported event types are exactly `report_saved` and
`setting_saved`. Names must be printable text no longer than 255 characters.

### Manual endpoint returns `503`

Open **CloudWatch** in the AWS console, choose **Log groups**, and open the log
group for `RunCounterFunction`. Also verify that the Lambda environment contains
`TABLE_NAME` and that its execution role can access the table.

### Application saves successfully but the count does not change

This can be expected because client delivery is deliberately silent. Check:

1. The two environment variables existed before the application was launched.
2. The URL ends in `/run`.
3. The token matches the deployment token.
4. The manual endpoint test returns `204`.
5. The DynamoDB console is open in the correct AWS Region.

## Security and privacy limitations

- The local username is useful for internal usage statistics but is not a
  cryptographically authenticated identity. A user who controls their machine
  can alter the environment or request.
- The shared bearer token prevents casual anonymous submissions, but a token
  distributed to a desktop can be extracted. Use organizational JWT/SSO
  authentication if this becomes an audit system rather than usage analytics.
- The dashboard's `StatsToken` grants read access to usernames, report
  filenames, and setting names. Distribute it only to approved viewers,
  remember that browsers that used the dashboard retain it until **Forget
  key** is used, and rotate it by redeploying with a new value if it leaks.
- Usernames, report filenames, and setting names may be identifiable data.
  Confirm notice, access, retention, and monitoring requirements with the
  relevant privacy/security owner.
- Never add report values, setting contents, directory paths, study names, or
  patient identifiers to this payload.
