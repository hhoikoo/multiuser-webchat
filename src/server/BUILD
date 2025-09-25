python_sources(name="lib")

pex_binary(
  name="app",
  entry_point="server.app",   # module path: src/ is the source root
  dependencies=[":lib"],
)
