import pulumi
import pulumi_azure_native as azure


class AzurePlatform(pulumi.ComponentResource):

    def __init__(self, name, location="westeurope", opts=None):
        super().__init__("platform:index:AzurePlatform", name, None, opts)

        rg = azure.resources.ResourceGroup(
            f"{name}-rg",
            location=location,
            opts=pulumi.ResourceOptions(parent=self)
        )

        storage = azure.storage.StorageAccount(
            f"{name}storage",
            resource_group_name=rg.name,
            sku=azure.storage.SkuArgs(name="Standard_LRS"),
            kind="StorageV2",
            opts=pulumi.ResourceOptions(parent=self)
        )

        self.register_outputs({
            "resourceGroup": rg.name
        })