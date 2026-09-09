@description('Azure region with DCasv5 Confidential VM capacity.')
@allowed([
  'japaneast'
])
param location string = 'japaneast'

@description('SSH user created on both experiment VMs.')
param adminUsername string = 'ieppadmin'

@secure()
@description('OpenSSH public key. Password authentication is disabled.')
param adminSshPublicKey string

@description('Single operator IPv4 CIDR, normally YOUR.PUBLIC.IP/32. SSH is denied from elsewhere.')
param adminSourceCidr string

@description('AMD SEV-SNP confidential VM size.')
param vmSize string = 'Standard_DC2as_v5'

@description('Public IEPP branch or tag installed by cloud-init.')
param ieppGitRef string = 'agent/l2-azure-cvm'

@description('UTC timestamp recorded as an expiry tag; teardown remains an explicit operator action.')
param deleteAfterUtc string

var prefix = 'iepp-l2'
var vmNames = [for i in range(0, 2): '${prefix}-node-${i + 1}']
var upstreamAttestationCommit = 'd42eb2dad2335ab9e516bb69180a227d4a10f86c'
var sourceCloudInit = loadTextContent('cloud-init.yaml')
var refCloudInit = replace(sourceCloudInit, '__IEPP_GIT_REF__', ieppGitRef)
var cloudInit = replace(refCloudInit, '__ATTESTATION_COMMIT__', upstreamAttestationCommit)
var commonTags = {
  project: 'IEPP'
  evidenceLevel: 'L2-experiment'
  deleteAfterUtc: deleteAfterUtc
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${prefix}-vnet'
  location: location
  tags: commonTags
  properties: {
    addressSpace: {
      addressPrefixes: ['10.82.0.0/16']
    }
  }
}

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: '${prefix}-nsg'
  location: location
  tags: commonTags
  properties: {
    securityRules: [
      {
        name: 'ssh-from-operator-only'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: adminSourceCidr
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource subnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'nodes'
  properties: {
    addressPrefix: '10.82.1.0/24'
    networkSecurityGroup: {
      id: nsg.id
    }
  }
}

resource publicIps 'Microsoft.Network/publicIPAddresses@2024-05-01' = [for (name, i) in vmNames: {
  name: '${name}-pip'
  location: location
  tags: commonTags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}]

resource nics 'Microsoft.Network/networkInterfaces@2024-05-01' = [for (name, i) in vmNames: {
  name: '${name}-nic'
  location: location
  tags: commonTags
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: {
            id: publicIps[i].id
          }
          subnet: {
            id: subnet.id
          }
        }
      }
    ]
  }
}]

resource vms 'Microsoft.Compute/virtualMachines@2024-07-01' = [for (name, i) in vmNames: {
  name: name
  location: location
  tags: union(commonTags, { experimentNode: string(i + 1) })
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    securityProfile: {
      securityType: 'ConfidentialVM'
      uefiSettings: {
        secureBootEnabled: true
        vTpmEnabled: true
      }
    }
    osProfile: {
      computerName: name
      adminUsername: adminUsername
      customData: base64(cloudInit)
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: adminSshPublicKey
            }
          ]
        }
      }
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-confidential-vm-jammy'
        sku: '22_04-lts-cvm'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        diskSizeGB: 30
        managedDisk: {
          storageAccountType: 'StandardSSD_LRS'
          securityProfile: {
            securityEncryptionType: 'VMGuestStateOnly'
          }
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nics[i].id
        }
      ]
    }
  }
}]

output nodePublicIps array = [for i in range(0, 2): publicIps[i].properties.ipAddress]
output nodePrivateIps array = [for i in range(0, 2): nics[i].properties.ipConfigurations[0].properties.privateIPAddress]
output attestationIssuer string = 'https://sharedjpe.jpe.attest.azure.net'
output pinnedAttestationToolCommit string = upstreamAttestationCommit
