from Validation.validation_pipeline import ValidationPipeline
import os
import json

# If testing LLMMetric make sure to add the sub directory as well.
test_dir = input("Enter the `Test<#>/` directory to test: ")
path = os.path.join("tests", "ValidationTests", test_dir)

if (not os.path.exists(path)) or (not test_dir.strip()):
    print(f"No directory named \"{test_dir}\" found.")
    exit()

# For LLM Metric only made it work for Test 5.
prompt = None
if "Test5/" in test_dir:
    prompt = "Write a C function called checksum8 that computes an 8-bit checksum over an input buffer. The function should accept a pointer to unsigned bytes and a buffer length. It should return the sum of all bytes modulo 256."

val_pipe = ValidationPipeline(
    output_dir=path,
    source_dir=path,
    prompt=prompt
)

results = val_pipe.run()