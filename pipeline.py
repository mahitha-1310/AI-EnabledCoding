import os
from openai import OpenAI
import logging
from tools import *
from Validation.validation_pipeline import ValidationPipeline
import json

class CodebasePipeline:
    """Pipeline for processing codebases through an LLM with conversation memory."""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        """
        Initialize the pipeline.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (defaults to OPENAI_API_MODEL env var)
        """

        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_API_BASE")
        )
        self.model = model or os.getenv("OPENAI_API_MODEL")
        self.system_prompt = read_path("prompt/system_prompt.md")

        editor_path = os.getenv("EDITOR_PATH")
        output_path = os.getenv("OUTPUT_PATH")

        self.validator = ValidationPipeline(output_dir=output_path, source_dir=editor_path)

        self.temperature = float(os.getenv("TEMPERATURE"))
        self.loop_count = int(os.getenv("LOOP_COUNT"))

        # self.conversation_history = []
        # self.current_codebase = {}

        logging.basicConfig(
            filename='llm_queries.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def use_tools(self, context: list[dict[str, str]], message):
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            
            logging.info(f"=== TOOL CALL START ===")
            logging.info(f"Tool name: {tool_name}")
            logging.info(f"Tool call ID: {tool_call.id}")
            logging.info(f"Raw arguments: {tool_call.function.arguments}")
            
            if tool_name not in TOOLS:
                error_msg = f"Unknown tool: {tool_name}"
                logging.error(error_msg)
                context.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": error_msg
                })
                continue
            
            try:
                arguments = json.loads(tool_call.function.arguments)
                logging.info(f"Parsed arguments: {json.dumps(arguments, indent=2)}")
                logging.info(f"Executing tool: {tool_name}")
                
                result = TOOLS[tool_name](**arguments)
                
                logging.info(f"Tool {tool_name} SUCCESS")
                logging.info(f"Result type: {type(result)}")
                logging.info(f"Result: {json.dumps(result, indent=2)}")
                
            except json.JSONDecodeError as e:
                result = f"JSONDecodeError: Failed to parse arguments - {str(e)}"
                logging.error(f"Tool {tool_name} FAILED - JSON parsing error: {result}")
            except TypeError as e:
                result = f"TypeError: Invalid arguments - {str(e)}"
                logging.error(f"Tool {tool_name} FAILED - Type error: {result}")
            except FileNotFoundError as e:
                result = f"FileNotFoundError: {str(e)}"
                logging.error(f"Tool {tool_name} FAILED - File not found: {result}")
            except PermissionError as e:
                result = f"PermissionError: {str(e)}"
                logging.error(f"Tool {tool_name} FAILED - Permission denied: {result}")
            except Exception as e:
                result = f"{type(e).__name__}: {str(e)}"
                logging.error(f"Tool {tool_name} FAILED - Unexpected error: {result}")
                logging.exception("Full traceback:")
            
            # Add tool result to context
            context.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })
            logging.info(f"=== TOOL CALL END ===\n")

    def tool_json(self, message):
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
                for tool_call in message.tool_calls
            ]
        }

    def react_loop(self, context, max_loops):
        # Sanitizes objects before sending to OpenAI
        def sanitize(obj):
            if isinstance(obj, Exception):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize(i) for i in obj]
            return obj

        # Sanitize context before sending to API
        clean_context = sanitize(context)

        logging.info(f"--- REACT LOOP (remaining loops: {max_loops}) ---")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=clean_context,
                tools=SCHEMAS,
                temperature=self.temperature
            )
        except Exception as e:
            # If the API call itself fails, log and create a mock response
            error_msg = f"{type(e)}: {e}"
            logging.error(f"API call failed: {error_msg}")
            context.append({"role": "assistant", "content": error_msg})
            
            # Create a mock response object to maintain consistency
            from types import SimpleNamespace
            mock_message = SimpleNamespace(content=error_msg, tool_calls=None)
            mock_choice = SimpleNamespace(message=mock_message)
            mock_response = SimpleNamespace(choices=[mock_choice])
            return mock_response

        message = response.choices[0].message

        # Handle tool-calling loop
        if getattr(message, "tool_calls", None) and max_loops > 0:
            logging.info(f"Model requested {len(message.tool_calls)} tool call(s)")
            
            # Ensure no exceptions or non-serializable objects
            safe_tool_call = sanitize(self.tool_json(message))
            context.append(safe_tool_call)

            # Execute tools safely
            try:
                self.use_tools(context, message)
            except Exception as e:
                error_msg = f"{type(e)}: {e}"
                logging.error(f"Tool execution failed: {error_msg}")
                logging.exception("Full traceback:")
                context.append({"role": "assistant", "content": error_msg})

            # Continue loop
            return self.react_loop(context, max_loops - 1)
        
        logging.info("No more tool calls or max loops reached")
        return response

            

    def run(self, user_input: str, user_id: str) -> str:
        """
        Run the complete pipeline (single-shot, no conversation).
        
        Args:
            user_input: Instructions for the LLM
            user_id: Indicates a distinct user of the LLM service
            
        Returns:
            Text response from the LLM
        """

        logging.info(f"NEW PIPELINE RUN")
        logging.info(f"[USER] {user_id}")
        logging.info(f"[QUERY] {user_input}")

        # Start with the system message
        context = [{"role": "system", "content": self.system_prompt}]

        # Next with the user input
        context.append({"role": "user", "content": user_input})

        # Go through loop of response and tool calling
        try:
            while True:
                response = self.react_loop(context, self.loop_count)
                message = response.choices[0].message
                if message.content != None:
                    break
                else:
                    logging.warning("Answer could not be generated with specified loop count. Consider increasing LOOP_COUNT in .env")
                    logging.info("Running LLM again...")
            
            # if message.content:
            context.append({"role": "assistant", "content": message.content})
            logging.info(f"Final response: {message.content}")
            logging.info(f"Validation results:\n{self.validator.run()}")

            return message.content
        except Exception as e:
            error_msg = f"Pipeline error: {e}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
            return error_msg