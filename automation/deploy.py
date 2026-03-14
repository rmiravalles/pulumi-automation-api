from pulumi import automation as auto


def pulumi_program():
    from pulumi_program import __main__


def deploy():
    stack = auto.create_or_select_stack(
        stack_name="dev",
        project_name="azure-automation-api",
        program=pulumi_program,
    )

    print("Installing plugins...")
    stack.workspace.install_plugin("azure-native", "v3.15.0")

    print("Setting config...")
    stack.set_config("azure-native:location", auto.ConfigValue(value="westeurope"))

    print("Deploying stack...")
    stack.up(on_output=print)


if __name__ == "__main__":
    deploy()