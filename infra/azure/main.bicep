targetScope = 'resourceGroup'

@description('Azure region for the Container Apps environment.')
param location string = resourceGroup().location
@description('Container image for the FastAPI service.')
param apiImage string
@description('Container image for the Next.js web service. Build it with NEXT_PUBLIC_API_URL set to the API URL.')
param webImage string
@description('Public URL of the web application, used by the API CORS allow-list.')
param webOrigin string
@description('Comma-separated pseudonymous IDs allowed to use the admin role.')
param adminIds string = ''
@secure()
@description('Gemini API key. Keep this in a deployment secret or Azure Key Vault pipeline.')
param geminiApiKey string = ''
@secure()
@description('PostgreSQL connection string. Set this for production persistence.')
param databaseUrl string = ''
@secure()
param registryUsername string = ''
@secure()
param registryPassword string = ''
param registryServer string = ''

var suffix = uniqueString(resourceGroup().id)
var storageName = 'pati${suffix}'
var environmentName = 'pati-env'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'pati-logs'
  location: location
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource share 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  name: '${storage.name}/default/tutor-data'
  properties: {
    accessTier: 'Hot'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource environmentStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: environment
  name: 'tutor-data'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: 'tutor-data'
      accessMode: 'ReadWrite'
    }
  }
}

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'pati-api'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        { name: 'gemini-api-key'; value: geminiApiKey }
        { name: 'database-url'; value: databaseUrl }
        { name: 'registry-password'; value: registryPassword }
      ]
      registries: empty(registryServer) ? [] : [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: { cpu: 1.0; memory: '2Gi' }
          env: [
            { name: 'AI_TUTOR_ENV'; value: 'production' }
            { name: 'AI_TUTOR_API_HOST'; value: '0.0.0.0' }
            { name: 'AI_TUTOR_CORS_ORIGINS'; value: webOrigin }
            { name: 'AI_TUTOR_DEFAULT_RETRIEVAL'; value: 'pep_plan_rag' }
            { name: 'AI_TUTOR_ADMIN_IDS'; value: adminIds }
            { name: 'GEMINI_API_KEY'; secretRef: 'gemini-api-key' }
            { name: 'AI_TUTOR_DATABASE_URL'; secretRef: 'database-url' }
          ]
          volumeMounts: [{ volumeName: 'tutor-data'; mountPath: '/app/data/app' }]
        }
      ]
      scale: { minReplicas: 1; maxReplicas: 1 }
      volumes: [{ name: 'tutor-data'; storageType: 'AzureFile'; storageName: 'tutor-data' }]
    }
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'pati-web'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true; targetPort: 3000; transport: 'auto'; allowInsecure: false }
      registries: empty(registryServer) ? [] : [
        { server: registryServer; username: registryUsername; passwordSecretRef: 'registry-password' }
      ]
      secrets: [{ name: 'registry-password'; value: registryPassword }]
    }
    template: {
      containers: [{ name: 'web'; image: webImage; resources: { cpu: 0.5; memory: '1Gi' } }]
      scale: { minReplicas: 1; maxReplicas: 2 }
    }
  }
}

output apiFqdn string = api.properties.configuration.ingress.fqdn
output webFqdn string = web.properties.configuration.ingress.fqdn
