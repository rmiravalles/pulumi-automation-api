from components.azure_platform import AzurePlatform


def test_component_creation():
    component = AzurePlatform("test")
    assert component is not None