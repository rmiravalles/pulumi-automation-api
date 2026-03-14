import hashlib
from pathlib import Path

import pulumi
import pulumi_azure_native as azure


class AzurePlatform(pulumi.ComponentResource):

    @staticmethod
    def _storage_account_name(name: str) -> str:
        # Azure Storage account name must be globally unique, [a-z0-9], <= 24 chars.
        normalized = "".join(ch for ch in name.lower() if ch.isalnum())
        if not normalized:
            normalized = "platform"
        suffix = hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]
        max_prefix_len = 24 - len(suffix)
        prefix = normalized[:max_prefix_len]
        return f"{prefix}{suffix}"

    def __init__(self, name, location="westeurope", opts=None):
        super().__init__("platform:index:AzurePlatform", name, None, opts)

        rg = azure.resources.ResourceGroup(
            f"{name}-rg",
            location=location,
            opts=pulumi.ResourceOptions(parent=self)
        )

        storage_account_name = self._storage_account_name(name)
        storage = azure.storage.StorageAccount(
            f"{name}-storage",
            account_name=storage_account_name,
            resource_group_name=rg.name,
            sku=azure.storage.SkuArgs(name="Standard_LRS"),
            kind="StorageV2",
            opts=pulumi.ResourceOptions(parent=self)
        )

        static_website = azure.storage.StorageAccountStaticWebsite(
            f"{name}-website",
            account_name=storage.name,
            resource_group_name=rg.name,
            index_document="index.html",
            error404_document="index.html",
            opts=pulumi.ResourceOptions(parent=storage),
        )

        index_path = Path(__file__).resolve().parent.parent / "website" / "index.html"
        azure.storage.Blob(
            f"{name}-index",
            account_name=storage.name,
            resource_group_name=rg.name,
            container_name="$web",
            blob_name="index.html",
            content_type="text/html",
            source=pulumi.FileAsset(str(index_path)),
            opts=pulumi.ResourceOptions(parent=storage, depends_on=[static_website]),
        )

        website_url = storage.primary_endpoints.apply(lambda endpoints: endpoints.web)

        self.resource_group = rg.name
        self.storage_account_name = storage.name
        self.website_url = website_url

        self.register_outputs({
            "resourceGroup": self.resource_group,
            "storageAccountName": self.storage_account_name,
            "websiteUrl": self.website_url,
        })