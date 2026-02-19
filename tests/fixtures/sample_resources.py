"""Sample Azure API response fixtures for testing."""

SAMPLE_SUBSCRIPTIONS = [
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001",
        "name": "Production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "properties": {"state": "Enabled"},
    },
]

SAMPLE_RESOURCE_GROUPS = [
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production",
        "name": "rg-production",
        "location": "eastus",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {"environment": "production"},
        "properties": {},
    },
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking",
        "name": "rg-networking",
        "location": "eastus",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {"environment": "production"},
        "properties": {},
    },
]

SAMPLE_RESOURCES = [
    # Virtual Machine
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Compute/virtualMachines/web-vm-01",
        "name": "web-vm-01",
        "type": "microsoft.compute/virtualmachines",
        "location": "eastus",
        "resourceGroup": "rg-production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {"role": "webserver"},
        "properties": {
            "hardwareProfile": {"vmSize": "Standard_D2s_v3"},
            "networkProfile": {
                "networkInterfaces": [
                    {
                        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Network/networkInterfaces/web-vm-01-nic"
                    }
                ]
            },
        },
        "sku": None,
        "kind": None,
    },
    # Second VM
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Compute/virtualMachines/web-vm-02",
        "name": "web-vm-02",
        "type": "microsoft.compute/virtualmachines",
        "location": "eastus",
        "resourceGroup": "rg-production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {"role": "webserver"},
        "properties": {
            "hardwareProfile": {"vmSize": "Standard_D2s_v3"},
            "networkProfile": {
                "networkInterfaces": [
                    {
                        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Network/networkInterfaces/web-vm-02-nic"
                    }
                ]
            },
        },
        "sku": None,
        "kind": None,
    },
    # NIC 1
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Network/networkInterfaces/web-vm-01-nic",
        "name": "web-vm-01-nic",
        "type": "microsoft.network/networkinterfaces",
        "location": "eastus",
        "resourceGroup": "rg-production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {
            "ipConfigurations": [
                {
                    "properties": {
                        "subnet": {
                            "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/main-vnet/subnets/web-subnet"
                        },
                        "publicIPAddress": {
                            "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Network/publicIPAddresses/web-vm-01-pip"
                        },
                    }
                }
            ],
            "networkSecurityGroup": {
                "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/networkSecurityGroups/web-nsg"
            },
        },
        "sku": None,
        "kind": None,
    },
    # NIC 2
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Network/networkInterfaces/web-vm-02-nic",
        "name": "web-vm-02-nic",
        "type": "microsoft.network/networkinterfaces",
        "location": "eastus",
        "resourceGroup": "rg-production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {
            "ipConfigurations": [
                {
                    "properties": {
                        "subnet": {
                            "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/main-vnet/subnets/web-subnet"
                        },
                    }
                }
            ],
        },
        "sku": None,
        "kind": None,
    },
    # VNet
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/main-vnet",
        "name": "main-vnet",
        "type": "microsoft.network/virtualnetworks",
        "location": "eastus",
        "resourceGroup": "rg-networking",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {
            "addressSpace": {"addressPrefixes": ["10.0.0.0/16"]},
            "subnets": [
                {
                    "name": "web-subnet",
                    "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/main-vnet/subnets/web-subnet",
                    "properties": {
                        "addressPrefix": "10.0.1.0/24",
                        "networkSecurityGroup": {
                            "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/networkSecurityGroups/web-nsg"
                        },
                        "serviceEndpoints": [
                            {"service": "Microsoft.Sql"},
                            {"service": "Microsoft.Storage"},
                        ],
                    },
                },
                {
                    "name": "data-subnet",
                    "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/main-vnet/subnets/data-subnet",
                    "properties": {
                        "addressPrefix": "10.0.2.0/24",
                        "serviceEndpoints": [],
                    },
                },
            ],
            "virtualNetworkPeerings": [
                {
                    "name": "peer-to-hub",
                    "properties": {
                        "remoteVirtualNetwork": {
                            "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/hub-vnet"
                        },
                        "peeringState": "Connected",
                    },
                }
            ],
        },
        "sku": None,
        "kind": None,
    },
    # SQL Server
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Sql/servers/prod-sql-server",
        "name": "prod-sql-server",
        "type": "microsoft.sql/servers",
        "location": "eastus",
        "resourceGroup": "rg-production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {
            "privateEndpointConnections": [
                {
                    "properties": {
                        "privateEndpoint": {
                            "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/privateEndpoints/sql-pe"
                        }
                    }
                }
            ],
        },
        "sku": {"name": "GP_Gen5_2"},
        "kind": "v12.0",
    },
    # Private Endpoint
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/privateEndpoints/sql-pe",
        "name": "sql-pe",
        "type": "microsoft.network/privateendpoints",
        "location": "eastus",
        "resourceGroup": "rg-networking",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {
            "subnet": {
                "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/main-vnet/subnets/data-subnet"
            },
            "privateLinkServiceConnections": [
                {
                    "properties": {
                        "privateLinkServiceId": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Sql/servers/prod-sql-server"
                    }
                }
            ],
        },
        "sku": None,
        "kind": None,
    },
    # NSG
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/networkSecurityGroups/web-nsg",
        "name": "web-nsg",
        "type": "microsoft.network/networksecuritygroups",
        "location": "eastus",
        "resourceGroup": "rg-networking",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {
            "securityRules": [
                {
                    "name": "AllowHTTP",
                    "properties": {
                        "direction": "Inbound",
                        "access": "Allow",
                        "protocol": "Tcp",
                        "sourceAddressPrefix": "*",
                        "sourcePortRange": "*",
                        "destinationAddressPrefix": "10.0.1.0/24",
                        "destinationPortRange": "80",
                        "priority": 100,
                    },
                },
                {
                    "name": "AllowHTTPS",
                    "properties": {
                        "direction": "Inbound",
                        "access": "Allow",
                        "protocol": "Tcp",
                        "sourceAddressPrefix": "*",
                        "sourcePortRange": "*",
                        "destinationAddressPrefix": "10.0.1.0/24",
                        "destinationPortRange": "443",
                        "priority": 110,
                    },
                },
            ],
            "subnets": [
                {
                    "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/main-vnet/subnets/web-subnet"
                }
            ],
        },
        "sku": None,
        "kind": None,
    },
    # Storage Account
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Storage/storageAccounts/prodstorageacct",
        "name": "prodstorageacct",
        "type": "microsoft.storage/storageaccounts",
        "location": "eastus",
        "resourceGroup": "rg-production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {
            "networkAcls": {"defaultAction": "Deny"},
        },
        "sku": {"name": "Standard_LRS"},
        "kind": "StorageV2",
    },
    # Load Balancer
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Network/loadBalancers/web-lb",
        "name": "web-lb",
        "type": "microsoft.network/loadbalancers",
        "location": "eastus",
        "resourceGroup": "rg-production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {
            "backendAddressPools": [
                {
                    "properties": {
                        "backendIPConfigurations": [
                            {
                                "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Network/networkInterfaces/web-vm-01-nic/ipConfigurations/ipconfig1"
                            },
                            {
                                "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.Network/networkInterfaces/web-vm-02-nic/ipConfigurations/ipconfig1"
                            },
                        ]
                    }
                }
            ],
        },
        "sku": {"name": "Standard"},
        "kind": None,
    },
    # Key Vault
    {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-production/providers/Microsoft.KeyVault/vaults/prod-keyvault",
        "name": "prod-keyvault",
        "type": "microsoft.keyvault/vaults",
        "location": "eastus",
        "resourceGroup": "rg-production",
        "subscriptionId": "00000000-0000-0000-0000-000000000001",
        "tags": {},
        "properties": {},
        "sku": {"name": "standard"},
        "kind": None,
    },
]

SAMPLE_NETWORK_RESOURCES = {
    "vnets": [SAMPLE_RESOURCES[4]],  # main-vnet
    "subnets": [],
    "nsgs": [SAMPLE_RESOURCES[7]],  # web-nsg
    "nics": [SAMPLE_RESOURCES[2], SAMPLE_RESOURCES[3]],  # NICs
    "public_ips": [],
    "load_balancers": [SAMPLE_RESOURCES[9]],  # web-lb
    "app_gateways": [],
    "firewalls": [],
    "private_endpoints": [SAMPLE_RESOURCES[6]],  # sql-pe
    "route_tables": [],
    "vnet_gateways": [],
    "peerings": [
        {
            "vnetId": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/main-vnet",
            "vnetName": "main-vnet",
            "peeringName": "peer-to-hub",
            "remoteVnetId": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/virtualNetworks/hub-vnet",
            "peeringState": "Connected",
        }
    ],
}

SAMPLE_NSG_RULES = [
    {
        "nsgId": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/networkSecurityGroups/web-nsg",
        "nsgName": "web-nsg",
        "resourceGroup": "rg-networking",
        "ruleName": "AllowHTTP",
        "direction": "Inbound",
        "access": "Allow",
        "protocol": "Tcp",
        "sourceAddressPrefix": "Internet",
        "sourcePortRange": "*",
        "destinationAddressPrefix": "10.0.1.0/24",
        "destinationPortRange": "80",
        "priority": 100,
    },
    {
        "nsgId": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/networkSecurityGroups/web-nsg",
        "nsgName": "web-nsg",
        "resourceGroup": "rg-networking",
        "ruleName": "AllowHTTPS",
        "direction": "Inbound",
        "access": "Allow",
        "protocol": "Tcp",
        "sourceAddressPrefix": "Internet",
        "sourcePortRange": "*",
        "destinationAddressPrefix": "10.0.1.0/24",
        "destinationPortRange": "443",
        "priority": 110,
    },
    {
        "nsgId": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-networking/providers/Microsoft.Network/networkSecurityGroups/web-nsg",
        "nsgName": "web-nsg",
        "resourceGroup": "rg-networking",
        "ruleName": "DenyAll",
        "direction": "Inbound",
        "access": "Deny",
        "protocol": "*",
        "sourceAddressPrefix": "*",
        "sourcePortRange": "*",
        "destinationAddressPrefix": "*",
        "destinationPortRange": "*",
        "priority": 4096,
    },
]
