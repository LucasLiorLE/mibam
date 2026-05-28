import os
print("Testing stuff")

for f in os.listdir("tests"):
    if f.endswith(".py") and f != "test.py":
        print(f"Running {f}...")
        exec(open(os.path.join("tests", f)).read())