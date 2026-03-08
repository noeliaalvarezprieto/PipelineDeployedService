// ---------------------------------------------------------------------------
// PoC2 — bicep/modules/resources.bicep
// All Azure resources deployed inside the resource group.
// This module is called by main.bicep.
// ---------------------------------------------------------------------------

targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// Parameters (passed from main.bicep)
// ---------------------------------------------------------------------------
param appName string
param location string
param acrName string
param keyVaultName string
param logAnalyticsName string
param appInsightsName string
param containerAppEnvName string
param stagingAppName string
param prodAppName string
param managedIdentityName string
param containerPort int
param initialImageTag string

// ---------------------------------------------------------------------------
// Managed Identity
// Equivalent to IAM roles in PoC1 — used by Container Apps to pull from ACR
// and read secrets from Key Vault (least-privilege).
// ---------------------------------------------------------------------------
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
  tags: {
    purpose: 'Container Apps ACR pull + Key Vault read'
  }
}

// ---------------------------------------------------------------------------
// Azure Container Registry
// Equivalent to Amazon ECR in PoC1.
// ---------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false   // Use managed identity, not admin credentials
    publicNetworkAccess: 'Enabled'
    zoneRedundancy: 'Disabled'
  }
  tags: {
    project: 'PoC2'
  }
}

// Grant the managed identity AcrPull role on the registry
// Equivalent to the ECR pull permissions in the PoC1 CodeBuild IAM role.
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, managedIdentity.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Log Analytics Workspace
// Equivalent to CloudWatch Log Groups in PoC1.
// ---------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// ---------------------------------------------------------------------------
// Application Insights
// Equivalent to CloudWatch metrics/dashboards in PoC1.
// ---------------------------------------------------------------------------
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    RetentionInDays: 30
  }
}

// ---------------------------------------------------------------------------
// Azure Key Vault
// Equivalent to AWS Secrets Manager in PoC1.
// Stores secrets injected into Container Apps at runtime — no plaintext
// credentials in any pipeline configuration file (satisfies K8 / SC7).
// ---------------------------------------------------------------------------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true     // Use RBAC, not legacy access policies
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    enabledForDiskEncryption: false
    publicNetworkAccess: 'Enabled'
  }
}

// Grant the managed identity Key Vault Secrets User role
// Equivalent to secretsmanager:GetSecretValue in PoC1 IAM policies.
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource kvSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentity.id, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Secret placeholders — values are set manually or via pipeline after provisioning.
// Names match the secrets referenced in azure-pipelines.yml AzureKeyVault tasks.
resource secretSonarToken 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'sonar-token'
  properties: {
    value: 'REPLACE_WITH_ACTUAL_SONAR_TOKEN'
    attributes: {
      enabled: true
    }
  }
}

resource secretTestDbUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'test-db-url'
  properties: {
    value: 'REPLACE_WITH_TEST_DATABASE_URL'
    attributes: {
      enabled: true
    }
  }
}

resource secretProdDbUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'prod-db-url'
  properties: {
    value: 'REPLACE_WITH_PROD_DATABASE_URL'
    attributes: {
      enabled: true
    }
  }
}

resource secretApiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'api-key'
  properties: {
    value: 'REPLACE_WITH_ACTUAL_API_KEY'
    attributes: {
      enabled: true
    }
  }
}

// ---------------------------------------------------------------------------
// Container Apps Environment
// Equivalent to the ECS Cluster + ALB combination in PoC1.
// ---------------------------------------------------------------------------
resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

// ---------------------------------------------------------------------------
// Staging Container App
// Equivalent to the ECS Fargate staging service in PoC1.
// Uses rolling update (no blue/green needed for staging).
// ---------------------------------------------------------------------------
resource stagingApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: stagingAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'   // Rolling update for staging
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'prod-db-url'
          keyVaultUrl: secretProdDbUrl.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'api-key'
          keyVaultUrl: secretApiKey.properties.secretUri
          identity: managedIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: appName
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'NODE_ENV'
              value: 'staging'
            }
            {
              name: 'PORT'
              value: string(containerPort)
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'prod-db-url'
            }
            {
              name: 'API_KEY'
              secretRef: 'api-key'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: containerPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: containerPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Production Container App
// Equivalent to the ECS Fargate production service + CodeDeploy in PoC1.
// Multiple revisions mode enabled for blue/green traffic splitting.
// ---------------------------------------------------------------------------
resource prodApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: prodAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      // MULTIPLE revisions mode = blue/green traffic splitting
      // Equivalent to CodeDeploy blue/green in PoC1.
      activeRevisionsMode: 'Multiple'
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'http'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'prod-db-url'
          keyVaultUrl: secretProdDbUrl.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'api-key'
          keyVaultUrl: secretApiKey.properties.secretUri
          identity: managedIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: appName
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'NODE_ENV'
              value: 'production'
            }
            {
              name: 'PORT'
              value: string(containerPort)
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'prod-db-url'
            }
            {
              name: 'API_KEY'
              secretRef: 'api-key'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: containerPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: containerPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 2    // Minimum 2 for production availability
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
output acrLoginServer string = acr.properties.loginServer
output stagingAppFqdn string = stagingApp.properties.configuration.ingress.fqdn
output prodAppFqdn string = prodApp.properties.configuration.ingress.fqdn
output managedIdentityClientId string = managedIdentity.properties.clientId
output keyVaultUri string = keyVault.properties.vaultUri
output logAnalyticsWorkspaceId string = logAnalytics.id
