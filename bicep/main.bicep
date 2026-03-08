// ---------------------------------------------------------------------------
// PoC2 — bicep/main.bicep
// Azure infrastructure as Code — equivalent of PoC1 pipeline-stack.yaml
//
// Provisions:
//   - Resource Group (deployed at subscription scope)
//   - Azure Container Registry (ACR)
//   - Log Analytics Workspace
//   - Azure Monitor (Application Insights)
//   - Azure Key Vault + secrets placeholders
//   - Managed Identity (least-privilege, equivalent to IAM roles in PoC1)
//   - Azure Container Apps Environment
//   - Staging Container App
//   - Production Container App (multiple revisions enabled for blue/green)
//
// Deploy with:
//   az login
//   az account set --subscription <your-subscription-id>
//   az deployment sub create \
//     --location westeurope \
//     --template-file bicep/main.bicep \
//     --parameters @bicep/parameters.json
// ---------------------------------------------------------------------------

targetScope = 'subscription'

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------
@description('Base name for all resources')
param appName string = 'poc2-app'

@description('Azure region for all resources')
param location string = 'westeurope'

@description('Container port exposed by the application')
param containerPort int = 3000

@description('Docker image tag to deploy initially (updated by pipeline on each run)')
param initialImageTag string = 'latest'

@description('Email address for pipeline approval notifications')
param approverEmail string

@description('Your SonarCloud organisation slug')
param sonarOrgSlug string

// ---------------------------------------------------------------------------
// Variables
// ---------------------------------------------------------------------------
var resourceGroupName = '${appName}-rg'
var acrName = replace('${appName}acr', '-', '')   // ACR names: alphanumeric only
var keyVaultName = '${appName}-kv'
var logAnalyticsName = '${appName}-logs'
var appInsightsName = '${appName}-insights'
var containerAppEnvName = '${appName}-env'
var stagingAppName = '${appName}-staging'
var prodAppName = '${appName}-prod'
var managedIdentityName = '${appName}-identity'

// ---------------------------------------------------------------------------
// Resource Group
// ---------------------------------------------------------------------------
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: {
    project: 'PoC2'
    environment: 'all'
    managedBy: 'bicep'
  }
}

// ---------------------------------------------------------------------------
// All remaining resources are deployed inside the resource group
// ---------------------------------------------------------------------------
module resources 'modules/resources.bicep' = {
  name: 'poc2-resources'
  scope: rg
  params: {
    appName: appName
    location: location
    acrName: acrName
    keyVaultName: keyVaultName
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
    containerAppEnvName: containerAppEnvName
    stagingAppName: stagingAppName
    prodAppName: prodAppName
    managedIdentityName: managedIdentityName
    containerPort: containerPort
    initialImageTag: initialImageTag
  }
}

// ---------------------------------------------------------------------------
// Outputs (used by Azure Pipelines variable groups)
// ---------------------------------------------------------------------------
output resourceGroupName string = resourceGroupName
output acrLoginServer string = resources.outputs.acrLoginServer
output stagingAppFqdn string = resources.outputs.stagingAppFqdn
output prodAppFqdn string = resources.outputs.prodAppFqdn
output keyVaultName string = keyVaultName
output managedIdentityClientId string = resources.outputs.managedIdentityClientId
