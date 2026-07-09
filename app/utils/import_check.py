import importlib

MODULES = [
    "bot",
    "app.handlers",
    "app.handlers.admin",
]

for module in MODULES:
    print(f"Importing {module}...")
    importlib.import_module(module)

print("Import check passed")
