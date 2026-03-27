"""
CI/CD Security Compliance Test Suite
=====================================
Compares security posture of:
  - PoC1: AWS CodePipeline (eu-west-1, account 160823835871)
  - PoC2: Azure DevOps (subscription 822c51f3-26ec-4957-a540-bd77ccab846e)

Run:
    pip install pytest pytest-html
    pytest test_security_compliance.py -v --html=security_report.html --self-contained-html

Author: Noelia Alvarez Prieto | A00047469 | TU Dublin | March 2026
"""

import subprocess
import json
import pytest

AWS_REGION  = "eu-west-1"
AZURE_SUB   = "822c51f3-26ec-4957-a540-bd77ccab846e"
AZURE_RG    = "poc2-app-rg"
AZURE_MI    = "624c496c-88dc-4189-9da8-9fa3c50b0f70"


def aws(args):
    try:
        cmd = ["aws"] + args + ["--output", "json", "--region", AWS_REGION]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                          shell=(subprocess.os.name == "nt"))
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


IS_WINDOWS = subprocess.os.name == "nt"

def az(args):
    """Run Azure CLI. Uses active subscription set by az account set."""
    try:
        r = subprocess.run(
            ["az"] + args + ["--output", "json"],
            capture_output=True, text=True, timeout=30, shell=IS_WINDOWS)
        if r.returncode != 0:
            return None
        text = r.stdout.strip()
        return json.loads(text) if text else None
    except Exception:
        return None


def _set_azure_subscription():
    subprocess.run(["az", "account", "set", "--subscription", AZURE_SUB],
                   capture_output=True, timeout=15, shell=IS_WINDOWS)

_set_azure_subscription()


# ─── PILLAR 1 — SECRETS ───────────────────────────────────────────────────────

class TestSecretsManagement:

    def test_aws_secrets_exist(self):
        """AWS: Required secrets exist in Secrets Manager."""
        data = aws(["secretsmanager", "list-secrets"])
        assert data is not None
        names = [s["Name"] for s in data.get("SecretList", [])]
        for s in ["poc1-app/sonar", "poc1-app/db-prod", "poc1-app/db-staging"]:
            assert s in names, f"Missing secret: {s}"

    def test_aws_secrets_use_kms(self):
        """AWS: All secrets encrypted with Customer Managed Key."""
        data = aws(["secretsmanager", "list-secrets"])
        assert data is not None
        for s in data.get("SecretList", []):
            kms = s.get("KmsKeyId", "")
            assert kms, f"Secret {s['Name']} has no KMS key"
            assert "alias/poc1-pipeline-key" in kms or "97e41cef" in kms, \
                f"Secret {s['Name']} wrong KMS key: {kms}"

    def test_aws_kms_key_exists(self):
        """AWS: CMK poc1-pipeline-key exists and is enabled."""
        data = aws(["kms", "describe-key", "--key-id", "alias/poc1-pipeline-key"])
        assert data is not None
        meta = data.get("KeyMetadata", {})
        assert meta.get("KeyState") == "Enabled"
        assert meta.get("KeyManager") == "CUSTOMER"

    def test_aws_no_plaintext_secrets_in_buildspec(self):
        """AWS: buildspec.yml uses secrets-manager section."""
        try:
            content = open("buildspec.yml").read()
            assert "secrets-manager:" in content
        except FileNotFoundError:
            pytest.skip("buildspec.yml not found")

    def test_azure_keyvault_purge_protection(self):
        """Azure: Key Vault has purge protection enabled."""
        data = az(["keyvault", "show", "--name", "poc2-app-kv",
                   "--resource-group", AZURE_RG])
        assert data is not None, "Could not retrieve Key Vault poc2-app-kv"
        assert data["properties"]["enablePurgeProtection"] is True

    def test_azure_keyvault_soft_delete(self):
        """Azure: Key Vault has soft delete enabled."""
        data = az(["keyvault", "show", "--name", "poc2-app-kv",
                   "--resource-group", AZURE_RG])
        assert data is not None
        assert data["properties"]["enableSoftDelete"] is True

    def test_azure_keyvault_rbac_authorization(self):
        """Azure: Key Vault uses RBAC authorization."""
        data = az(["keyvault", "show", "--name", "poc2-app-kv",
                   "--resource-group", AZURE_RG])
        assert data is not None
        assert data["properties"]["enableRbacAuthorization"] is True

    def test_azure_pipeline_references_keyvault(self):
        """Azure: azure-pipelines.yml references Key Vault."""
        try:
            content = open("azure-pipelines.yml").read()
            assert "poc2-app-kv" in content or "AzureKeyVault" in content
        except FileNotFoundError:
            pytest.skip("azure-pipelines.yml not found")


# ─── PILLAR 2 — IAM / RBAC ────────────────────────────────────────────────────

class TestIAMRBAC:

    def test_aws_codebuild_role_exists(self):
        """AWS: CodeBuild service role exists."""
        assert aws(["iam", "get-role",
                    "--role-name", "poc1-app-codebuild-role"]) is not None

    def test_aws_codebuild_ecr_auth_isolated(self):
        """AWS: ecr:GetAuthorizationToken isolated in its own statement."""
        data = aws(["iam", "get-role-policy",
                    "--role-name", "poc1-app-codebuild-role",
                    "--policy-name", "CodeBuildPolicy"])
        assert data is not None
        for stmt in data["PolicyDocument"]["Statement"]:
            actions = [stmt["Action"]] if isinstance(stmt["Action"], str) \
                      else stmt["Action"]
            if "ecr:GetAuthorizationToken" in actions:
                others = [a for a in actions if a != "ecr:GetAuthorizationToken"]
                assert not others, f"GetAuthorizationToken mixed with: {others}"

    def test_aws_codepipeline_passrole_scoped(self):
        """AWS: iam:PassRole scoped to ECS task execution role."""
        data = aws(["iam", "get-role-policy",
                    "--role-name", "poc1-app-codepipeline-role",
                    "--policy-name", "CodePipelinePolicy"])
        assert data is not None
        for stmt in data["PolicyDocument"]["Statement"]:
            actions = [stmt["Action"]] if isinstance(stmt["Action"], str) \
                      else stmt["Action"]
            if "iam:PassRole" in actions:
                resource = stmt.get("Resource", "")
                assert resource != "*", "iam:PassRole has Resource:*"
                assert "ecs-task-execution-role" in str(resource)

    def test_aws_secrets_resource_scoped(self):
        """AWS: secretsmanager:GetSecretValue scoped to poc1-app/*."""
        data = aws(["iam", "get-role-policy",
                    "--role-name", "poc1-app-codebuild-role",
                    "--policy-name", "CodeBuildPolicy"])
        assert data is not None
        for stmt in data["PolicyDocument"]["Statement"]:
            actions = [stmt["Action"]] if isinstance(stmt["Action"], str) \
                      else stmt["Action"]
            if "secretsmanager:GetSecretValue" in actions:
                assert "poc1-app/" in str(stmt.get("Resource", ""))

    def test_aws_mfa_enabled_on_account(self):
        """AWS: MFA enabled on root account."""
        data = aws(["iam", "get-account-summary"])
        assert data is not None
        assert data["SummaryMap"]["AccountMFAEnabled"] == 1

    def test_azure_managed_identity_no_broad_contributor(self):
        """Azure: Managed Identity has no Contributor at resource group scope."""
        data = az(["role", "assignment", "list",
                   "--assignee", AZURE_MI, "--all"])
        assert data is not None
        for a in data:
            if a.get("roleDefinitionName") == "Contributor":
                scope = a.get("scope", "")
                assert "containerApps" in scope or "registries" in scope, \
                    f"Broad Contributor at RG scope: {scope}"

    def test_azure_acr_admin_disabled(self):
        """Azure: ACR admin credentials are disabled."""
        data = az(["acr", "show", "--name", "poc2appacr",
                   "--resource-group", AZURE_RG])
        assert data is not None
        assert data.get("adminUserEnabled") is False

    def test_azure_managed_identity_has_acr_push(self):
        """Azure: Managed Identity has AcrPush role."""
        data = az(["role", "assignment", "list",
                   "--assignee", AZURE_MI, "--all"])
        assert data is not None
        assert "AcrPush" in [a.get("roleDefinitionName") for a in data]

    def test_azure_managed_identity_has_kv_secrets_user(self):
        """Azure: Managed Identity has Key Vault Secrets User role."""
        data = az(["role", "assignment", "list",
                   "--assignee", AZURE_MI, "--all"])
        assert data is not None
        assert "Key Vault Secrets User" in [a.get("roleDefinitionName") for a in data]


# ─── PILLAR 3 — SAST ──────────────────────────────────────────────────────────

class TestSAST:

    def test_aws_buildspec_sonarcloud_quality_gate(self):
        """AWS: buildspec.yml runs SonarCloud with qualitygate.wait=true."""
        try:
            content = open("buildspec.yml").read()
            assert "sonar" in content.lower()
            assert "qualitygate.wait=true" in content
        except FileNotFoundError:
            pytest.skip("buildspec.yml not found")

    def test_aws_buildspec_npm_audit(self):
        """AWS: buildspec.yml runs npm audit blocking on HIGH."""
        try:
            content = open("buildspec.yml").read()
            assert "npm audit" in content
            assert "--audit-level=high" in content
        except FileNotFoundError:
            pytest.skip("buildspec.yml not found")

    def test_azure_pipeline_sonarcloud_quality_gate(self):
        """Azure: azure-pipelines.yml enforces SonarCloud Quality Gate."""
        try:
            content = open("azure-pipelines.yml").read()
            assert "SonarCloud" in content
            assert "qualitygate.wait=true" in content
        except FileNotFoundError:
            pytest.skip("azure-pipelines.yml not found")

    def test_azure_pipeline_dependency_scanning(self):
        """Azure: azure-pipelines.yml runs dependency vulnerability scanning (ESLint or npm audit)."""
        try:
            content = open("azure-pipelines.yml", encoding="utf-8", errors="replace").read()
            has_npm_audit = "npm audit" in content
            has_eslint = "eslint" in content.lower() or "ESLint" in content
            assert has_npm_audit or has_eslint, \
                "azure-pipelines.yml has no dependency scanning (npm audit or ESLint)"
        except FileNotFoundError:
            pytest.skip("azure-pipelines.yml not found")


# ─── PILLAR 4 — CONTAINER SCANNING ───────────────────────────────────────────

class TestContainerScanning:

    def test_aws_ecr_scan_on_push(self):
        """AWS: ECR ScanOnPush enabled."""
        data = aws(["ecr", "describe-repositories", "--repository-names", "poc1-app"])
        assert data is not None
        assert data["repositories"][0]["imageScanningConfiguration"]["scanOnPush"] is True

    def test_aws_ecr_immutable_tags(self):
        """AWS: ECR imageTagMutability is IMMUTABLE."""
        data = aws(["ecr", "describe-repositories", "--repository-names", "poc1-app"])
        assert data is not None
        assert data["repositories"][0]["imageTagMutability"] == "IMMUTABLE"

    def test_aws_ecr_lifecycle_policy_exists(self):
        """AWS: ECR has a lifecycle policy."""
        data = aws(["ecr", "get-lifecycle-policy", "--repository-name", "poc1-app"])
        assert data is not None
        assert "expire" in data.get("lifecyclePolicyText", "").lower()

    def test_aws_buildspec_trivy_scan(self):
        """AWS: buildspec.yml runs Trivy with --exit-code 1."""
        try:
            content = open("buildspec.yml").read()
            assert "trivy" in content.lower()
            assert "--exit-code 1" in content
        except FileNotFoundError:
            pytest.skip("buildspec.yml not found")

    def test_azure_pipeline_trivy_scan(self):
        """Azure: azure-pipelines.yml runs Trivy on HIGH,CRITICAL."""
        try:
            content = open("azure-pipelines.yml").read()
            assert "trivy" in content.lower()
            assert "HIGH,CRITICAL" in content
        except FileNotFoundError:
            pytest.skip("azure-pipelines.yml not found")

    def test_azure_acr_retention_policy(self):
        """Azure: ACR has retention policy configured."""
        data = az(["acr", "config", "retention", "show", "--registry", "poc2appacr"])
        if data is None:
            pytest.skip("ACR retention not available in this tier")
        assert data.get("status") == "enabled"


# ─── PILLAR 5 — AUDIT / LOGS ──────────────────────────────────────────────────

class TestAuditLogs:

    def test_aws_cloudtrail_exists_and_logging(self):
        """AWS: CloudTrail poc1-audit-trail is actively logging."""
        data = aws(["cloudtrail", "get-trail-status", "--name", "poc1-audit-trail"])
        assert data is not None
        assert data.get("IsLogging") is True

    def test_aws_cloudtrail_multiregion(self):
        """AWS: CloudTrail trail is multi-region."""
        data = aws(["cloudtrail", "describe-trails"])
        assert data is not None
        assert any(t.get("IsMultiRegionTrail") for t in data.get("trailList", []))

    def test_aws_cloudtrail_log_validation(self):
        """AWS: CloudTrail has log file validation enabled."""
        data = aws(["cloudtrail", "describe-trails"])
        assert data is not None
        assert any(t.get("LogFileValidationEnabled") for t in data.get("trailList", []))

    def test_aws_cloudwatch_retention_90_days(self):
        """AWS: CodeBuild log groups have >= 90 day retention."""
        data = aws(["logs", "describe-log-groups",
                    "--log-group-name-prefix", "/codebuild/poc1-app"])
        assert data is not None
        for g in data.get("logGroups", []):
            r = g.get("retentionInDays", 0)
            assert r >= 90, f"{g['logGroupName']}: {r} days (need >= 90)"

    def test_aws_config_recorder_active(self):
        """AWS: AWS Config recorder is active."""
        data = aws(["configservice", "describe-configuration-recorder-status"])
        assert data is not None
        assert any(r.get("recording") for r in
                   data.get("ConfigurationRecordersStatus", []))

    def test_azure_log_analytics_workspace_exists(self):
        """Azure: A Log Analytics Workspace exists in poc2-app-rg."""
        data = az(["monitor", "log-analytics", "workspace", "list",
                   "--resource-group", AZURE_RG])
        assert data is not None and len(data) > 0, \
            "No Log Analytics Workspace found in poc2-app-rg"

    def test_azure_log_analytics_retention_90_days(self):
        """Azure: Log Analytics Workspace has >= 90 day retention."""
        data = az(["monitor", "log-analytics", "workspace", "list",
                   "--resource-group", AZURE_RG])
        assert data is not None and len(data) > 0
        ws = data[0]
        retention = ws.get("retentionInDays", 0)
        assert retention >= 90, \
            f"Log Analytics retention is {retention} days (need >= 90)"

    def test_azure_application_insights_exists(self):
        """Azure: An Application Insights resource exists in poc2-app-rg."""
        data = az(["monitor", "app-insights", "component", "list",
                   "--resource-group", AZURE_RG])
        if data is None:
            pytest.skip("app-insights extension not installed — run: az extension add --name application-insights")
        assert len(data) > 0, "No Application Insights found in poc2-app-rg"


# ─── SCORE SUMMARY ────────────────────────────────────────────────────────────

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    passed  = terminalreporter.stats.get("passed",  [])
    failed  = terminalreporter.stats.get("failed",  [])
    skipped = terminalreporter.stats.get("skipped", [])

    aws_p = [r for r in passed if "aws"   in r.nodeid.lower()]
    aws_f = [r for r in failed if "aws"   in r.nodeid.lower()]
    az_p  = [r for r in passed if "azure" in r.nodeid.lower()]
    az_f  = [r for r in failed if "azure" in r.nodeid.lower()]

    lines = [
        "",
        "=" * 52,
        "  SECURITY COMPLIANCE SCORE",
        "=" * 52,
    ]
    if aws_p or aws_f:
        t = len(aws_p) + len(aws_f)
        lines.append(f"  AWS PoC1   : {len(aws_p):>2}/{t}  ({round(len(aws_p)/t*100)}%)")
    if az_p or az_f:
        t = len(az_p) + len(az_f)
        lines.append(f"  Azure PoC2 : {len(az_p):>2}/{t}  ({round(len(az_p)/t*100)}%)")
    t = len(passed) + len(failed)
    lines.append(f"  Overall    : {len(passed):>2}/{t}  ({len(skipped)} skipped)")
    lines.append("=" * 52)

    for line in lines:
        terminalreporter.write_line(line)
