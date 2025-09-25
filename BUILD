python_requirements(
    name="requirements",
    source="pyproject.toml",
)

pex_binary(
    name="server",
    entry_point="server.app",
    dependencies=["src/server:lib"],
)
