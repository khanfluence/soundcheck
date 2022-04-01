from typing import Optional

import typer


class TyperExitError(typer.Exit):
    """An exception that indicates the application should exit with some status code
    and display a message."""

    def __init__(self, code: int, message: Optional[str] = None) -> None:
        self.message = message
        if message:
            if code:
                typer.echo("Error: ", nl=False, err=True)
            typer.echo(message, err=True)
        super().__init__(code=code)

    def __str__(self) -> str:
        string = f"[Exit status {self.exit_code}]"
        if self.message:
            string += f" {self.message}"
        return string
