import os
from openai import OpenAI
import logging
from tools import *
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

        self.temperature = float(os.getenv("TEMPERATURE"))
        self.loop_count = int(os.getenv("LOOP_COUNT"))

        # self.conversation_history = []
        # self.current_codebase = {}

        logging.basicConfig(
            filename='llm_queries.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
    
    def use_tools(self, context: list[dict[str, str]], message):
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            
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
                logging.info(f"Executing tool: {tool_name} with args: {arguments}")
                result = TOOLS[tool_name](**arguments)
                logging.info(f"Tool {tool_name} result: {result}")
            except Exception as e:
                result = f"{type(e).__name__}: {str(e)}"
                logging.error(f"Tool {tool_name} failed: {result}")
            
            # Add tool result to context
            context.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })

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
            logging.error(error_msg)
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
            # Ensure no exceptions or non-serializable objects
            safe_tool_call = sanitize(self.tool_json(message))
            context.append(safe_tool_call)

            # Execute tools safely
            try:
                self.use_tools(context, message)
            except Exception as e:
                error_msg = f"{type(e)}: {e}"
                logging.error(error_msg)
                context.append({"role": "assistant", "content": error_msg})

            # Continue loop
            return self.react_loop(context, max_loops - 1)

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

        logging.info(f"User: {user_id} | Query: {user_input}")

        # Start with the system message
        context = [{"role": "system", "content": self.system_prompt}]

        # Next with the user input
        context.append({"role": "user", "content": user_input})

        # Go through loop of response and tool calling
        try:
            response = self.react_loop(context, self.loop_count)
            message = response.choices[0].message
            
            if message.content:
                context.append({"role": "assistant", "content": message.content})
                return message.content
            else:
                # If no content, try one more time without tools to get a summary
                logging.warning("No content in final message. Requesting summary.")
                summary_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=context + [{"role": "user", "content": "Please provide a summary of what you did."}],
                    temperature=self.temperature
                )
                summary = summary_response.choices[0].message.content
                if summary:
                    return summary
                else:
                    return "No summary could be generated."
        except Exception as e:
            error_msg = f"Pipeline error: {e}"
            logging.error(error_msg)
            return error_msg