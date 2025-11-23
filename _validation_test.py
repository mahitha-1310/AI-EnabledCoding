from Validation.validation_pipeline import ValidationPipeline
from Validation.compilation_stage import CompilationStage
import os
import json

test_dir = input("Enter the `Test<#>/` directory to test: ")

if (not os.path.exists("ValidationTests/" + test_dir)) or (not test_dir.strip()):
    print(f"No directory named \"{test_dir}\" found.")
    exit()

val_pipe = ValidationPipeline(
    output_dir="ValidationTests/" + test_dir,
    source_dir="ValidationTests/" + test_dir
)

results = val_pipe.run()

print(json.dumps(results, indent=2))