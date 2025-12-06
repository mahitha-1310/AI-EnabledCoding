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
        self.system_prompt = os.getenv("SYSTEM_PROMPT")

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
            # Get tool name
            tool_name = tool_call.function.name
            # Unknown? Move on...
            if tool_name not in TOOLS:
                print(f"Unknown tool: {tool_name}")
                continue
            
            try:
                # Load arguments
                arguments = json.loads(tool_call.function.arguments)
                # Call TOOL_DEFINITIONS[tool_name] as function 
                with TOOLS[tool_name] as f:
                    result = f(**arguments)
            except Exception as e:
                print(e)
                result = e
            finally:
                # Add tool result to context
                context.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
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
        # Send user input to LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=context,
            tools=SCHEMAS,
            temperature=self.temperature
        )

        message = response.choices[0].message

        # Does LLM want to call more tools?
        if message.tool_calls and max_loops > 0:
            # Send the response back to the context!
            context.append(self.tool_json(message))
            # Execute each tool call
            self.use_tools(context, message)

            message = self.react_loop(response, context, max_loops-1)
        
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
        response = self.react_loop(context, self.loop_count)

        message = response.choices[0].message
        
        if message.content:
            context.append({"role": "assistant", "content": message.content})
        
        return message.content