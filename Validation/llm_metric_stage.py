from dotenv import load_dotenv
import torch
import os
from openai import OpenAI
from transformers import RobertaTokenizer, RobertaModel, AutoTokenizer, AutoModel
import torch.nn.functional as F
from typing import List, Dict, Any
from pathlib import Path
import json
import numpy as np


load_dotenv()

class LLMMetricStage:
    """Class to run the LLM Metric stage of the validation pipeline"""
    
    def __init__(self, output_dir: str, project_root: str, prompt_text: str):
        """
        Initialize the LLM Metric stage with where to write stage's output (this refers 
        to LLM outputs as well as values regarding embeddings), as well as the project root
        (where source code would be found)

        Args:
            output_dir: Path to directory to which this stage will write all generated artifacts
                        and/or log files (may be existing directory or nonexisting, in which case
                        a new directory will be created at the specified path)
            project_root: Path to project directory (where all source code/header files will be
                          found)
            prompt_text: Queries made by user to the LLM as well as referenced content within the
                         prompt.
                
            (NOTE: these may or may not be a relative path; if relative, this initializer normalizes
            the relative path to be an absolute path)
        """
        self.project_root = os.path.abspath(project_root)

        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.prompt_text = prompt_text
        
        # For embedding model getting the tokenizer, model, and determining device (GPU or CPU)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/unixcoder-base",
                                                       trust_remote_code=True)
        self.model_embed = AutoModel.from_pretrained("microsoft/unixcoder-base",
                                                       trust_remote_code=True,
                                                       use_safetensors=False).to(self.device)

        # For now, log directory is always nested inside LLMMetrics directory
        # ====================================================================
        # In the future, I'd like to make this a fourth parameter such that the user can
        #   specify where they would like logs to be written
        self.logs_dir = os.path.join(self.output_dir, "logs/")
        os.makedirs(self.logs_dir, exist_ok=True)
        
    def run(self):
        """
        Run the LLM Metric stage of validation pipeline.
        1.  Run the LLMEval and get outputs for 10 LLMs compute normalized average of those final scores.
        2.  Run cosine similarity of the prompt and generated code.
        """
        
        # # LLM Normalized Average and output files.
        output = self.LLMEval()
        
        valid_scores = []

        for i, src in enumerate(output, start=1):
            log_path_LLM = os.path.join(self.logs_dir, f"LLMMetric_LLM{i}log.json")

            with open(log_path_LLM, "w") as f:
                json.dump(src, f, indent=4)

            if "final_score" in src and isinstance(src["final_score"], (int, float)):
                valid_scores.append(src["final_score"])

        if valid_scores:
            llm_average = sum(valid_scores) / len(valid_scores)
        else:
            llm_average = 0.0

        llm_norm = llm_average / 100.0

        json_llm_norm = {"llm_avg_norm": llm_norm}
        log_path_llm_norm = os.path.join(self.logs_dir, f"LLM_Avg_Norm.json")
        
        with open(log_path_llm_norm, "w") as f:
            json.dump(json_llm_norm, f, indent=4)
            
        # Cosine Similarity between Prompt and Project.
        output_sim = self.compare_prompt_to_whole_project(self.prompt_text, self.project_root)
        file_sim = []
        
        # Compute Weighted Average for final Calculations as well as if it succeeded this stage.
        succ, combined_metric = self.final_calculations(llm_norm, output_sim)
        
        # Outputting the necessary content of the previous calculations.
        json_succ_output = {"Success": succ}
        log_path_succ = os.path.join(self.logs_dir, f"Success.json")
        
        with open(log_path_succ, "w") as f:
            json.dump(json_succ_output, f, indent=4)
        
        json_comb_final_metric_output = {"combined_metric": combined_metric}
        log_path_comb_final = os.path.join(self.logs_dir, f"Combined_Final_Metric.json")
        
        with open(log_path_comb_final, "w") as f:
            json.dump(json_comb_final_metric_output, f, indent=4)
            
        json_output_sim = {"total_similarity": output_sim}
        log_path_output_sim = os.path.join(self.logs_dir, f"LLMMetric_Total_Similarity.json")
        
        with open(log_path_output_sim, "w") as f:
            json.dump(json_output_sim, f, indent=4)
            
        for file_path, similarity in file_sim:
            base = os.path.splitext(os.path.basename(file_path))[0]
            log_path_file_sim = os.path.join(self.logs_dir, f"LLMMetric_File_Similarity_{base}.json")

            json_file_sim = {"file_similarity": similarity}
            with open(log_path_file_sim, "w") as f:
                json.dump(json_file_sim, f, indent=4)

        return {
            "success": succ == 0,
            "combined_metric": combined_metric,
            "llm_avg_norm": llm_norm,
            "total_similarity": output_sim
        }
                
                
    def final_calculations(self, llm_norm_val: float,
                           total_sim_val: float,
                           w1: float = 0.85,
                           w2: float = 0.15,
                           threshold: float = 0.65):
        """
        Docstring for final_calculations
        :param llm_norm_val: Normalized average of the final scores given by the LLM.
        :type llm_norm_val: float
        :param total_sim_val: Average semantic similarity value of all the files within a repo.
        :type total_sim_val: float
        :param w1: weight given to LLM. Set to 0.7
        :type w1: float
        :param w2: Weight given to semantic similarity. Set to 0.3
        :type w2: float
        :param threshold: The threshold given to pass this stage.
        :type threshold: float
        """
        
        res = w1 * llm_norm_val + w2 * total_sim_val
        if llm_norm_val >= 0.70:
            return 0, res
        if res >= threshold:
            return 0, res
        return -1, res
                
        
        
        
    def Sys_prompt_validator(self) -> str:
        # This is the System Prompt to determine how to give its response.
        return f"""You are a strict code evaluator for high-assurance systems.
    Your task is to evaluate how well a code file matches the user's prompt.
    Score each category from 0–5, then compute the final score (0–100).

    Scoring rubric:
    - Functional Alignment (0–5)
    - Architectural Alignment (0–5)
    - Safety & Correctness (0–5)
    - Completeness (0–5)
    - Irrelevance / Extra Code (0–5, where 5 means no irrelevant code)

    Return ONLY valid JSON:
    {{
      "functional": <0-5>,
      "architecture": <0-5>,
      "safety": <0-5>,
      "completeness": <0-5>,
      "irrelevance": <0-5>,
      "final_score": <0-100>,
      "explanation": "..."
    }}
    """
    
    def User_prompt_validator(self, prompt: str, code: str) -> str:
        # This is the user prompt where the user can input their prompt and code.
        return f"""PROMPT:
    {prompt}

    CODE:
    {code}
    """
    
    
    def GetCode(self, codeDir: str) -> str:
        """
        Recursively collect all .c and .h files from the project directory
        and combine them into one string for LLM evaluation.
        """
        directory = Path(codeDir)

        combined = ""

        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".c", ".h"]:
                combined += f"\n\n// FILE: {file_path.relative_to(directory)}\n"
                combined += file_path.read_text(encoding="utf-8", errors="ignore")
                combined += "\n"

        return combined
    
    def _is_inside_output_dir(self, file_path: str) -> bool:
        """
        Check whether a file is inside the output directory.
        This prevents generated logs/tests/results from being scored as source code.
        """
        file_path = os.path.abspath(file_path)
        output_dir = os.path.abspath(self.output_dir)

        return file_path.startswith(output_dir)
        
    def LLMEval(self) -> List[Dict]:
        """
        Docstring for LLMEval
        
        :return: This returns a list of the json outputs from the LLM (consisting of their response to similarity between prompt and code).
        :rtype: List[Dict]
        """
        # Get LLM information from .env file.
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE")
        )
        self.model = os.getenv("OPENAI_API_MODEL")
        
        res = []
        
        # Prompts LLM 10 times.
        for i in range(10):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.Sys_prompt_validator()},
                    {"role": "user", "content": self.User_prompt_validator(self.prompt_text ,self.GetCode(self.project_root))}
                ],
                temperature=0.7
            )

            llm_response = response.choices[0].message.content
            
            # parse JSON safely
            try:
                llm_json = json.loads(llm_response)
            except json.JSONDecodeError:
                llm_json = {"error": "invalid JSON", "raw": llm_response}

            res.append(llm_json)
        return res
            
        
    def cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Docstring for cosine_sim
        
        :param a: embedded prompt as a vector.
        :type a: np.ndarray
        :param b: embedded code as a vector
        :type b: np.ndarray
        :return: cosine similarity of the embedded prompt and code.
        :rtype: float
        """
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))
    
    def embed_text(self, text: str):
        """
        Docstring for embed_text
        
        :param text: The string containing either code or the natural language prompt.
        :type text: str
        """
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model_embed(**inputs)
            # Mean pool over the sequence
            embedding = outputs.last_hidden_state.mean(dim=1)

        return embedding.cpu()
    
    def compare_prompt_to_source_dir(self, prompt: str, source_dir: str, aggregation="mean"):
        """
        Given a prompt and a source directory, compute embedding similarity
        for all C files (.c/.h) and aggregate the similarity.

        Returns:
            overall_similarity: float
            file_similarities: list of tuples [(file_path, similarity), ...]
        """
        prompt_emb = self.embed_text(prompt)
        file_similarities = []
        
        # Goes through all files and computes embedding and computes cosine similarity for all files (seperate values).
        for root, _, files in os.walk(source_dir):
            for filename in files:
                if filename.endswith(".c") or filename.endswith(".h"):
                    full_path = os.path.join(root, filename)
                    if self._is_inside_output_dir(full_path):
                        continue  # skip files in the output directory
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            code = f.read()
                    except Exception as e:
                        print(f"Skipping {full_path}: {e}")
                        continue

                    code_emb = self.embed_text(code)
                    sim = F.cosine_similarity(prompt_emb, code_emb).item()
                    file_similarities.append((full_path, sim))

        if not file_similarities:
            return 0.0, []
        
        # Then aggregates all the cosine similarity values using some specified method to get overall similarity.
        if aggregation == "mean":
            overall_similarity = sum(sim for _, sim in file_similarities) / len(file_similarities)
        elif aggregation == "min":
            overall_similarity = min(sim for _, sim in file_similarities)
        else:
            raise ValueError("aggregation must be 'mean' or 'min'")

        # Sort files by similarity descending
        file_similarities.sort(key=lambda x: x[1], reverse=True)

        return overall_similarity, file_similarities
        
    
    def compare_prompt_to_whole_project(self, prompt: str, source_dir: str) -> float:
        """
        Compare the prompt against the full combined project code.
        This is better for checking whether the whole repo satisfies the prompt.
        """
        code = self.GetCode(source_dir)

        if not code.strip():
            return 0.0

        prompt_emb = self.embed_text(prompt)
        code_emb = self.embed_text(code)

        return F.cosine_similarity(prompt_emb, code_emb).item()