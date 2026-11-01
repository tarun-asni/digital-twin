import json
import logging
import requests

from .prompt_handler import PromptHandler
from sensegrid.config import (
    API_KEY, MCP_URL, 
    ANTHROPIC_MODEL, ANTHROPIC_VERSION
    )


logger = logging.getLogger(__name__)


class LLMHandler:
    
    @staticmethod
    def data(prompt):
        
        headers = {
            "x-api-key": API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

        payload = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "temperature": 0.7,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        return headers, payload

    @staticmethod
    def call_claude_mcp(prompt):
        
        prompt = PromptHandler.prompt_for_voice(prompt)
        
        headers, payload = LLMHandler.data(prompt)

        try:
            response = requests.post(MCP_URL, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            message_content = response_data.get("content") or response_data.get("completion")

            try:
                # 1. Get the first item (the dictionary) and its 'text' value
                json_dict = message_content[0]['text']
                
                # 2. Parse the inner JSON string
                return json.loads(json_dict)
                
            except Exception as e:
                logger.error("❌ Failed to parse LLM response as JSON:", message_content)
                logger.error(f'Reason: {e}', exec_info=True)
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Claude MCP request failed: {e}")
            return None

    @staticmethod
    def call_claude_for_report(alert_message, analysis_report, timestamp, end_time, latitude, longitude):
        
        prompt = PromptHandler.prompt_for_inference(alert_message, analysis_report, timestamp, end_time, latitude, longitude)
        
        headers, payload = LLMHandler.data(prompt)
        
        try:
            response = requests.post(MCP_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Claude MCP request failed: {e}")
            return None
