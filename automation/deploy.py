import sys
from pathlib import Path

from pulumi import automation as auto


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def pulumi_program():
    if str(PROJECT_ROOT) not in sys.path:
        # Inline runtime can execute from automation/; include repo root for imports.
        sys.path.insert(0, str(PROJECT_ROOT))
    from pulumi_program import __main__


def deploy():
    stack = auto.create_or_select_stack(
        stack_name="dev",
        project_name="azure-automation-api",
        program=pulumi_program,
        opts=auto.LocalWorkspaceOptions(work_dir=str(PROJECT_ROOT)),
    )

    print("Installing plugins...")
    stack.workspace.install_plugin("azure-native", "v3.15.0")

    print("Setting config...")
    stack.set_config("azure-native:location", auto.ConfigValue(value="westeurope"))

    print("Deploying stack...")
    stack.up(on_output=print)


if __name__ == "__main__":
    deploy()