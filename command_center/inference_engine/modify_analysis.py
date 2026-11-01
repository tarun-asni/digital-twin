import logging

from audio_listener.llm_handler import LLMHandler

logger = logging.getLogger(__name__)

def modify_analysis(alert, message, inference_analysis=None):
    
    timestamp = getattr(alert, "start_time", None) or alert.timestamp
    
    llm_result = LLMHandler.call_claude_for_report(message, inference_analysis, timestamp, alert.end_time, alert.latitude, alert.longitude)

    if not llm_result:
        logger.error("No response from LLM")
        return None
    llm_response = llm_result["content"][0]["text"]
    
    logger.info("Got the response, storing it in the database...")
    alert.llm_response = llm_response
    alert.save()