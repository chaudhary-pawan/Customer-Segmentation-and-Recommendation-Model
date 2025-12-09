import backend.main as m
print("main file:", m.__file__)
print("has app:", hasattr(m, "app"))
print("app type:", type(getattr(m, "app", None)))
