import pulumi
from components.azure_platform import AzurePlatform

config = pulumi.Config("azure-native")

location = config.get("location") or "westeurope"

platform = AzurePlatform(
    "demo-platform",
    location=location
)

pulumi.export("platformName", "demo-platform")