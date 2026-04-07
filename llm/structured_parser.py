import json
import re
from typing import Type, TypeVar, Any
from pydantic import BaseModel, ValidationError
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

T = TypeVar('T', bound=BaseModel)

class StructuredParsingError(Exception):
    pass

def _extract_text(msg: Any) -> str:
    """Extracts plain text from a message, handling various formats."""
    if isinstance(msg, str):
        return msg
    
    if hasattr(msg, "content"):
        content = msg.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = [block.get("text", "") for block in content if isinstance(block, dict)]
            return " ".join(texts)
        return str(content)
        
    return str(msg)

def _clean_json_string(raw: str) -> str:
    """Removes markdown fences or provider envelopes if any."""
    raw = raw.strip()
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw, re.DOTALL)
    if match:
        raw = match.group(1).strip()
    return raw

def invoke_structured(llm: Any, prompt_input: Any, schema: Type[T], retries: int = 2) -> T:
    """
    Invokes the LLM to get a structured output parsing exactly into the Pydantic schema.
    If it fails, automatically retries to repair the JSON.
    """
    # ensure prompt_input is a list of BaseMessages
    messages = []
    if isinstance(prompt_input, str):
        messages = [HumanMessage(content=prompt_input)]
    elif hasattr(prompt_input, "to_messages"):
        messages = prompt_input.to_messages()
    elif isinstance(prompt_input, list):
        for m in prompt_input:
            if isinstance(m, BaseMessage):
                messages.append(m)
            elif isinstance(m, dict) and "role" in m and "content" in m:
                if m["role"] == "user":
                    messages.append(HumanMessage(content=m["content"]))
                else:
                    messages.append(AIMessage(content=m["content"]))
            else:
                messages.append(HumanMessage(content=str(m)))
    else:
        messages = [HumanMessage(content=str(prompt_input))]
        
    schema_instruction = f"""
You must respond with ONLY valid JSON that strictly matches the following JSON schema:
{json.dumps(schema.model_json_schema(), indent=2)}

- Do not include markdown fences (e.g. ```json)
- Do not include explanations or introductory text
- Do not call any tool or function
- Return the raw JSON object directly
"""
    messages.append(HumanMessage(content=schema_instruction))
    
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = llm.invoke(messages)
            
            raw_text = _extract_text(response)
            clean_text = _clean_json_string(raw_text)
            
            # Find the JSON object/array bounds
            start_idx = -1
            end_idx = -1
            for i, c in enumerate(clean_text):
                if c in "{[":
                    start_idx = i
                    break
            
            for i in range(len(clean_text)-1, -1, -1):
                if clean_text[i] in "}]":
                    end_idx = i
                    break
                    
            if start_idx != -1 and end_idx != -1 and start_idx <= end_idx:
                clean_text = clean_text[start_idx:end_idx+1]
            
            # Parse and Validate
            parsed_json = json.loads(clean_text)
            return schema.model_validate(parsed_json)
            
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            last_error = str(e)
            if attempt < retries:
                repair_prompt = f"""
You previously generated invalid JSON output. 
Error:
{last_error}

Your task is to fix the output so it strictly adheres to this JSON schema:
{json.dumps(schema.model_json_schema(), indent=2)}

- Return ONLY valid JSON
- Do not include markdown fences
- Do not include explanations
- Do not call any tool or function
"""
                messages.append(AIMessage(content=raw_text if 'raw_text' in locals() else "Execution failed."))
                messages.append(HumanMessage(content=repair_prompt))

    raise StructuredParsingError(f"Failed to extract structured output for {schema.__name__} after {retries} retries. Last Error: {last_error}")
