from .container import Container
from .cli_host import CliHost


def get_host() -> CliHost:
    import click
    return click.get_current_context().obj
