from Validation.validation_pipeline import ValidationPipeline
from Validation.compilation_stage import CompilationStage
import os
import json

# If testing LLMMetric make sure to add the sub directory as well.
test_dir = input("Enter the `Test<#>/` directory to test: ")

if (not os.path.exists("ValidationTests/" + test_dir)) or (not test_dir.strip()):
    print(f"No directory named \"{test_dir}\" found.")
    exit()

# For LLM Metric only made it work for Test 5.
prompt = None
if "Test5/Test5d/" or "Test5/Test5e/" in test_dir:
    prompt = """
Create a small high-assurance C calculator library.

The code should:
- Provide safe integer addition, subtraction, multiplication, and division.
- Use header files with function prototypes.
- Store results through output pointer parameters.
- Return clear status codes instead of crashing.
- Check for NULL output pointers.
- Check for division by zero.
- Include validation helper functions.
- Include a small main.c demo program.
- Organize the project using src/ and include/ folders.
"""
    
elif "Test5/" in test_dir:
    prompt = "Write a C function called checksum8 that computes an 8-bit checksum over an input buffer. The function should accept a pointer to unsigned bytes and a buffer length. It should return the sum of all bytes modulo 256."

val_pipe = ValidationPipeline(
    output_dir="ValidationTests/" + test_dir,
    source_dir="ValidationTests/" + test_dir,
    prompt=prompt
)

results = val_pipe.run()

print(json.dumps(results, indent=2))